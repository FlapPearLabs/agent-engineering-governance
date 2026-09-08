#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CodeGraph lifecycle decision surface — contract §6.7 (INIT ONCE / SYNC CONTINUOUSLY).

ONE canonical decision point for the whole lifecycle, so no session, hook or
orchestrator has to re-derive the rule from prose:

    new repo            → INIT_ONCE                (exactly one full init)
    thereafter          → INCREMENTAL_SYNC_ONCE    (never a full init again)
    before editing code → GROUNDING_REQUIRED / BLAST_RADIUS_REQUIRED
    after editing       → MARK_DIRTY               (dirty flag only, no sync)
    review/handoff/stop → INCREMENTAL_SYNC_ONCE when dirty, else NO_SYNC
    never               → FULL_INIT every session   (→ FULL_INIT_FORBIDDEN)

Graph modes (contract codegraph-grounding.md §1-§4; review F1 — a worktree is
NOT automatically an independent full-index candidate):

  MODE A (default)   canonical repo/base graph. The init record is REPO-LEVEL
                     (keyed by the main checkout, shared by every worktree):
                     init once globally for that graph; worktree lanes reuse
                     the base graph + delta-by-diff; NO per-worktree full init.
  MODE B (explicit)  candidate-exact / HIGH lanes opt in via --lane-mode B or
                     env ZCODE_CODEGRAPH_LANE_MODE=B. The lane keeps its OWN
                     graph: lane-local init once, incremental sync thereafter.
                     Init bookkeeping is worktree-local (--lane).
  MODE C             manual grounding (MANUAL_GROUNDING_RECEIPT, mode=manual);
                     no graph requirements beyond grounding.

Closed decision enum (contract §6.7):

    INIT_ONCE                     init allowed EXACTLY ONCE (canonical in MODE A,
                                  lane-local in MODE B)
    CANONICAL_INIT_REQUIRED_AT_MAIN  review R4-C: an ordinary MODE A worktree
                                  lane NEVER inits itself — while the canonical
                                  graph is missing, every init-offering intent
                                  points at the main checkout
    FULL_INIT_FORBIDDEN           init record/index present → full init is never legal
    INCREMENTAL_SYNC_ONCE         dirty → sync exactly once, then clear the flag
    NO_SYNC                       clean → nothing to do
    GROUNDING_REQUIRED            MEDIUM/HIGH production write without a valid receipt
    BLAST_RADIUS_REQUIRED         radius missing / stale / UNRESOLVED (review F2:
                                  unresolved means NO production write)
    BLAST_RADIUS_EXPANSION_REQUIRED  target outside the approved edit surface
                                  (review F3: tracked or untracked — scope
                                  authority is the approved surface, not git
                                  index membership)
    ALLOW_WRITE                   pre-edit gate satisfied
    MARK_DIRTY                    post-edit: flag set, sync deferred
    SYNC_FAILED_DEFERRED          sync failed → report; NEVER fall back to full init
    NO_REPO                       not a git worktree → no-op

Runtime-local state additions (contract §6.4 — machine-local, never committed):

    graph_init      = {"initialized_at", "head", "worktree", "mode", "scope"}
                      scope="canonical" lives in the repo-level state file
                      (keyed by the main checkout); scope="lane" is worktree-local.
                      The recorded head is ALWAYS the graph owner's actual HEAD
                      (review R5-F5: canonical record-init binds the main
                      checkout's HEAD even when invoked from a lane).
    blast_radius    = {"base", "head", "mode", "resolved", "files", "count",
                       "computed_at"}  — review F2: `resolved` is normative.
    last_sync_failed = bool      → keeps a failed sync from degrading into a re-init
    candidate_delta_dirty = bool (MODE A lanes only; review R5-F2) — a source
                      edit inside an ordinary MODE A lane is CANDIDATE DELTA
                      (fresh git diff is the evidence), NEVER a lane CodeGraph
                      sync requirement. Dirty-state truth table:
                          canonical source change → graph_dirty (canonical graph)
                          MODE B lane source edit → graph_dirty (lane graph)
                          MODE A lane source edit → candidate_delta_dirty (no lane sync)
                      Lifecycle boundaries additionally consult cheap mechanical
                      git evidence (status --porcelain=v1 -z) so Bash-made
                      edits are not missed when no Edit marker fired — JIT,
                      never per-edit.

CLI:

  python codegraph_lifecycle.py decide --intent <INTENT> [--risk R] [--file F]
                                       [--request-full-init] [--lane-mode A|B]
  python codegraph_lifecycle.py record-init [--head SHA] [--mode full] [--lane]
                                       # R4-D: health probe must pass on the exact
                                       # graph scope (canonical | lane); default probe
                                       # = real `codegraph status`; tests inject
                                       # ZCODE_CODEGRAPH_HEALTH_CMD
  python codegraph_lifecycle.py blast-radius [--base SHA] [--target F ...] [--impact-file JSON]
  python codegraph_lifecycle.py record-sync-result --ok|--fail
  python codegraph_lifecycle.py verify          # invariant self-check (exit 1 = breach)

INTENT ∈ session-start | pre-edit | post-edit | query | review | handoff | stop

Any failure exits 0 (hooks must never block the runtime); `verify` exits 1 on an
invariant breach so CI/tests can gate on it.
"""
import json
import os
import subprocess
import sys

import _continuity_state as cs

try:  # reuse the single source of truth for the grounding rule (contract §7)
    import grounding_guard as gg
except Exception:  # pragma: no cover - defensive
    gg = None

# --- decision enum ------------------------------------------------------------

INIT_ONCE = "INIT_ONCE"
CANONICAL_INIT_REQUIRED_AT_MAIN = "CANONICAL_INIT_REQUIRED_AT_MAIN"
FULL_INIT_FORBIDDEN = "FULL_INIT_FORBIDDEN"
INCREMENTAL_SYNC_ONCE = "INCREMENTAL_SYNC_ONCE"
NO_SYNC = "NO_SYNC"
GROUNDING_REQUIRED = "GROUNDING_REQUIRED"
BLAST_RADIUS_REQUIRED = "BLAST_RADIUS_REQUIRED"
BLAST_RADIUS_EXPANSION_REQUIRED = "BLAST_RADIUS_EXPANSION_REQUIRED"
ALLOW_WRITE = "ALLOW_WRITE"
MARK_DIRTY = "MARK_DIRTY"
SYNC_FAILED_DEFERRED = "SYNC_FAILED_DEFERRED"
NO_REPO = "NO_REPO"

DECISIONS = frozenset({
    INIT_ONCE, CANONICAL_INIT_REQUIRED_AT_MAIN, FULL_INIT_FORBIDDEN,
    INCREMENTAL_SYNC_ONCE, NO_SYNC,
    GROUNDING_REQUIRED, BLAST_RADIUS_REQUIRED, BLAST_RADIUS_EXPANSION_REQUIRED,
    ALLOW_WRITE, MARK_DIRTY, SYNC_FAILED_DEFERRED, NO_REPO,
})

# intents whose correct answer is "sync once if dirty" (contract §6.6 JIT rule)
SYNC_INTENTS = frozenset({"query", "review", "blast-radius", "handoff", "stop"})
ALL_INTENTS = frozenset({"session-start", "pre-edit", "post-edit"}) | SYNC_INTENTS
# intents that may legitimately offer the one-time init (review R4-C)
INIT_OFFERING_INTENTS = frozenset({"session-start"}) | SYNC_INTENTS

LOW = "LOW"
RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def _git(args, cwd, timeout=10):
    # One retry on spawn/transport failure (review R5 DIRTY-DETECTION
    # ROBUSTNESS): a transient Windows git-spawn failure must not be mistaken
    # for mechanical evidence (e.g. is_repo → NO_REPO, or "cannot see
    # uncommitted changes"). Two attempts, then fail honestly.
    last = None
    for _ in range(2):
        try:
            return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                                  timeout=timeout, errors="replace")
        except Exception as exc:
            last = exc
    del last  # both attempts failed — the caller receives None (fail-honest)
    return None


def head_sha(worktree):
    r = _git(["rev-parse", "HEAD"], worktree)
    return r.stdout.strip() if r and r.returncode == 0 else ""


def is_repo(worktree):
    r = _git(["rev-parse", "--show-toplevel"], worktree)
    return bool(r and r.returncode == 0)


def repo_main_dir(worktree):
    """Canonical repo working dir — the checkout that owns the MODE A base
    graph and its repo-level init record. None when git cannot answer."""
    r = _git(["rev-parse", "--path-format=absolute", "--git-common-dir"], worktree)
    if not (r and r.returncode == 0):
        return None
    gd = r.stdout.strip()
    if not gd:
        return None
    d = os.path.dirname(gd)
    return d or worktree


def index_dir(worktree):
    """CodeGraph index location; overridable so non-ZCode adapters can point at
    their own per-directory database (contract §6.1/§6.5)."""
    override = os.environ.get("ZCODE_CODEGRAPH_INDEX_DIR")
    return override or os.path.join(worktree, ".codegraph")


def index_present(worktree):
    return os.path.isdir(index_dir(worktree))


def init_done(state):
    rec = state.get("graph_init")
    return isinstance(rec, dict) and bool(rec.get("initialized_at"))


def lane_mode_of(explicit=None):
    mode = explicit or os.environ.get("ZCODE_CODEGRAPH_LANE_MODE", "A")
    mode = str(mode).upper()
    return mode if mode in ("A", "B") else "A"


def graph_freshness(worktree, mode=None):
    """(stale, index_sha, owner_head, scope) — mechanical freshness evidence
    for the graph this worktree consumes (review R5-F1).

    GRAPH_OWNER_HEAD = git rev-parse HEAD at the ACTUAL graph owner
                       (main checkout for MODE A, the lane itself for MODE B).
    GRAPH_INDEX_SHA  = last successful sync SHA, else graph_init.head.
    stale            = both SHAs exist and differ → the healthy existing graph
                       must be answered INCREMENTAL_SYNC_ONCE even when
                       GRAPH_DIRTY = NO (pull / merge / ff / checkout /
                       external commit never fire an Edit marker).
    """
    mode = lane_mode_of(mode)
    main_dir = repo_main_dir(worktree) or worktree
    if mode == "B":
        owner = worktree
        owner_state = cs.load(worktree)
        scope = "lane"
    else:
        owner = main_dir
        owner_state = cs.load(main_dir)
        scope = "canonical"
    owner_head = head_sha(owner)
    rec = owner_state.get("graph_init") if init_done(owner_state) else {}
    index_sha = str(owner_state.get("last_sync_head") or "")
    if not index_sha and isinstance(rec, dict):
        index_sha = str(rec.get("head") or "")
    stale = bool(owner_head and index_sha and index_sha != owner_head)
    return stale, index_sha, owner_head, scope


def graph_health(graph_owner_dir):
    """(ok, evidence). Injectable mechanical health probe (review R4-D).

    Production default: the REAL `codegraph status` CLI must exit 0 — a bare
    .codegraph directory is NOT health evidence. Synthetic tests inject a mock
    probe via ZCODE_CODEGRAPH_HEALTH_CMD (shlex-split command line, run with
    cwd=graph_owner_dir); production never sets that variable."""
    custom = os.environ.get("ZCODE_CODEGRAPH_HEALTH_CMD", "")
    if custom:
        try:
            import shlex
            argv = shlex.split(custom)
        except ValueError:
            return False, "HEALTH_CMD_UNPARSEABLE"
    else:
        argv = ["codegraph", "status"]
    try:
        r = subprocess.run(argv, cwd=graph_owner_dir, capture_output=True, text=True,
                           timeout=60, errors="replace")
    except FileNotFoundError:
        return False, "CODEGRAPH_CLI_NOT_FOUND"
    except Exception as exc:  # defensive: probe must never crash the hook
        return False, "PROBE_ERROR:%s" % type(exc).__name__
    label = "custom-probe" if custom else "codegraph-status"
    return r.returncode == 0, "%s rc=%d" % (label, r.returncode)


# --- blast radius (review F2: fail closed) ------------------------------------

def _in_runtime_state(worktree, rel_path):
    """Runtime-local state is machine-local bookkeeping, never part of an edit
    surface (contract §6.4). Excluded so it cannot pollute a blast radius."""
    try:
        rr = os.path.realpath(str(cs.runtime_root()))
        target = os.path.realpath(os.path.join(os.path.realpath(worktree), rel_path))
        return target == rr or target.startswith(rr + os.sep)
    except Exception:
        return False


def _parse_status_z(raw):
    """NUL-safe porcelain v1 parse → set of paths (both rename endpoints).

    Review R5-F3: the previous `ln.strip(); ln[3:]` slice corrupted the common
    unstaged form " M src/app.py" into "rc/app.py". This parser NEVER strips
    before slicing, handles unstaged/staged/untracked/rename records and
    filenames containing spaces, and RAISES ValueError on any record it cannot
    mechanically trust — a parser failure must become resolved=False /
    mode=UNRESOLVED evidence, never wrong-path resolved evidence.
    """
    files = set()
    records = raw.split("\x00")
    if records and records[-1] == "":
        records.pop()
    i = 0
    while i < len(records):
        rec = records[i]
        i += 1
        if not rec:
            continue
        if len(rec) < 4 or rec[2] != " ":
            raise ValueError("malformed porcelain record %r" % rec[:80])
        xy = rec[:2]
        path = rec[3:]
        if not path:
            raise ValueError("empty path in porcelain record")
        if "R" in xy or "C" in xy:
            files.add(path)
            if i >= len(records):
                raise ValueError("rename/copy record without its pair record")
            pair = records[i]
            i += 1
            if not pair:
                raise ValueError("empty rename/copy pair record")
            files.add(pair)
        else:
            files.add(path)
    return files


def changed_files(worktree, base):
    """(files, resolved). Git-visible delta base..HEAD plus uncommitted changes.
    NUL-safe throughout (review R5-F3): `git status --porcelain=v1 -z` and
    `git diff --name-only -z`. resolved=False when git cannot PROVE the delta
    (diff unavailable), cannot see uncommitted changes (status unavailable), or
    the porcelain parse fails — the caller must then mark the radius UNRESOLVED
    (review F2: an unprovable radius is not a radius)."""
    files = set()
    diff_ok = True
    if base:
        r = _git(["diff", "--name-only", "-z", "%s...HEAD" % base], worktree)
        if not (r is not None and r.returncode == 0):
            r = _git(["diff", "--name-only", "-z", base, "HEAD"], worktree)
        if r is not None and r.returncode == 0:
            for p in r.stdout.split("\x00"):
                p = p.strip()
                if p:
                    files.add(p.replace("\\", "/"))
        else:
            diff_ok = False  # base unresolvable → cannot prove the delta
    st = _git(["status", "--porcelain=v1", "-z"], worktree)
    if st is None or st.returncode != 0:
        return sorted(files), False  # cannot see uncommitted changes either
    try:
        files |= _parse_status_z(st.stdout)
    except ValueError:
        return sorted(files), False  # untrustworthy parse → fail closed
    return sorted(f for f in files if not _in_runtime_state(worktree, f)), diff_ok


def mechanical_delta_present(worktree):
    """Cheap git mechanical evidence of an uncommitted source delta (review R5
    DIRTY-DETECTION ROBUSTNESS: lifecycle boundaries must not rely solely on
    PostToolUse Edit/Write markers — a worker may edit via Bash). Returns
    True/False; None when git cannot answer (fail-honest, never silently
    'clean'). Not run per-edit — only at lifecycle boundaries."""
    st = _git(["status", "--porcelain=v1", "-z"], worktree)
    if st is None or st.returncode != 0:
        return None
    try:
        return bool(_parse_status_z(st.stdout))
    except ValueError:
        return None


def norm_rel(worktree, file_path):
    """Normalise a possibly-absolute path to a repo-relative POSIX path."""
    if not file_path:
        return ""
    if os.path.isabs(file_path):
        try:
            file_path = os.path.relpath(os.path.realpath(file_path),
                                        os.path.realpath(worktree))
        except Exception:
            pass
    p = file_path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def br_fresh(worktree, br):
    """Blast radius stays valid while its recorded head remains in HEAD's
    ancestry — the worker's own commits do NOT force a recompute (same rule as
    grounding freshness, contract §7)."""
    base = str(br.get("head") or "")
    head = head_sha(worktree)
    if not base or not head:
        return True
    if gg is not None and hasattr(gg, "base_is_fresh"):
        fresh, _decided = gg.base_is_fresh(base, head, worktree)
        return fresh
    return base == head


def compute_blast_radius(worktree, base, impact_files=None, targets=None):
    """Returns (record, error). The blast radius is the intended edit surface,
    NOT merely 'what already changed' — at ticket start base == HEAD, so a
    delta-only radius would be empty and would reject every legitimate write.

    impact set = TARGETS ∪ (git delta base..HEAD) ∪ (CodeGraph impact, optional)

    Fail closed (review F2): a missing base, an unresolvable base, or a git
    failure sets resolved=False / mode=UNRESOLVED — the record may exist as
    evidence but it authorises NO production write."""
    if not is_repo(worktree):
        return None, "NOT_A_GIT_REPO"
    head = head_sha(worktree)
    resolved = True
    if base:
        delta, resolved = changed_files(worktree, base)
    else:
        delta, resolved = [], False  # no base → no provable delta
    files = set(delta)
    mode = "GIT_DELTA"
    if targets:
        files |= set(targets)
        mode = "TARGETS_PLUS_GIT_DELTA"
    if impact_files:
        files |= set(impact_files)
        mode = "TARGETS_PLUS_GRAPH" if targets else "GIT_DELTA_PLUS_GRAPH"
    files = sorted(f for f in files if not _in_runtime_state(worktree, f))
    rec = {
        "base": base or "",
        "head": head,
        "mode": mode if resolved else "UNRESOLVED",
        "resolved": resolved,
        "files": files,
        "count": len(files),
        "computed_at": cs.now_utc(),
    }
    return rec, ""


# --- decision core ------------------------------------------------------------

def decide(intent, worktree, risk=LOW, file_path="", request_full_init=False,
           lane_mode=None):
    """Returns (decision, detail). The single normative answer for this intent."""
    intent = (intent or "").strip().lower()
    if intent not in ALL_INTENTS:
        return NO_SYNC, "unknown intent=%r (legal: %s)" % (intent, "/".join(sorted(ALL_INTENTS)))
    if not is_repo(worktree):
        return NO_REPO, "not a git worktree"

    mode = lane_mode_of(lane_mode)
    main_dir = repo_main_dir(worktree) or worktree
    is_lane = os.path.realpath(worktree) != os.path.realpath(main_dir)
    repo_state = cs.load(main_dir)   # canonical (MODE A) init bookkeeping
    wt_state = cs.load(worktree)     # lane-local runtime state
    canonical_init = init_done(repo_state)
    lane_init = init_done(wt_state)
    has_index = index_present(worktree)
    main_index = index_present(main_dir)
    dirty = bool(wt_state.get("graph_dirty"))

    # -- session start: init at most once, never per session (contract §6.2)
    if intent == "session-start":
        if mode == "B":
            # explicit candidate-exact lane: its OWN graph, init once per lane
            if lane_init:
                if request_full_init:
                    return FULL_INIT_FORBIDDEN, ("MODE B lane graph already initialized "
                                                 "(initialized_at=%s); full init is never "
                                                 "legal again"
                                                 % wt_state["graph_init"].get("initialized_at", ""))
                if wt_state.get("last_sync_failed"):
                    return SYNC_FAILED_DEFERRED, ("previous lane sync failed; retry incremental "
                                                  "sync — failure never escalates to full init")
                stale, index_sha, owner_head, _ = graph_freshness(worktree, "B")
                if dirty or stale:
                    why = "lane graph_dirty=YES" if dirty else \
                        ("lane GRAPH_INDEX_SHA=%s != GRAPH_OWNER_HEAD=%s (review R5-F1)"
                         % (index_sha[:12], owner_head[:12]))
                    return INCREMENTAL_SYNC_ONCE, \
                        "MODE B lane graph initialized; %s → incremental sync once" % why
                return NO_SYNC, "MODE B lane graph initialized; incremental sync only"
            if not has_index:
                return INIT_ONCE, ("MODE B lane graph missing → lane init allowed EXACTLY "
                                   "ONCE; run record-init --lane immediately after")
            if request_full_init:
                return FULL_INIT_FORBIDDEN, \
                    "MODE B lane index present; a full init is not a session-start action"
            stale, index_sha, owner_head, _ = graph_freshness(worktree, "B")
            if dirty or stale:
                return INCREMENTAL_SYNC_ONCE, "MODE B lane index present; sync needed"
            return NO_SYNC, "MODE B lane index present; incremental sync only"
        # MODE A (default): one canonical graph per repo — review F1
        if canonical_init:
            if request_full_init:
                return FULL_INIT_FORBIDDEN, ("canonical graph already initialized "
                                             "(initialized_at=%s head=%s); worktree lanes "
                                             "reuse the base graph + delta-by-diff — a "
                                             "per-worktree full init is never legal"
                                             % (repo_state["graph_init"].get("initialized_at", ""),
                                                repo_state["graph_init"].get("head", "")))
            if wt_state.get("last_sync_failed"):
                return SYNC_FAILED_DEFERRED, ("previous sync failed; retry incremental sync — "
                                              "failure never escalates to full init")
            stale, index_sha, owner_head, _ = graph_freshness(worktree, "A")
            if dirty or stale:
                why = "graph_dirty=YES" if dirty else \
                    ("GRAPH_INDEX_SHA=%s != GRAPH_OWNER_HEAD=%s (review R5-F1: pull/merge/"
                     "ff/checkout/external commit never fire an Edit marker)"
                     % (index_sha[:12], owner_head[:12]))
                return INCREMENTAL_SYNC_ONCE, \
                    ("MODE A: reuse canonical graph + delta-by-diff; %s → incremental sync "
                     "once, never a full init" % why)
            return NO_SYNC, ("MODE A: reuse canonical graph + delta-by-diff (lane has no graph "
                             "of its own); graph clean at owner head=%s" % head_sha(main_dir))
        if is_lane:
            # review R4-C: a lane must not perform — or offer — the canonical
            # init for ANY intent; the one-time init belongs to the main checkout
            return CANONICAL_INIT_REQUIRED_AT_MAIN, ("MODE A: canonical graph not initialized "
                                                     "— run the one-time init at the main "
                                                     "checkout (%s); this worktree lane never "
                                                     "inits itself" % main_dir)
        if main_index or has_index:
            if request_full_init:
                return FULL_INIT_FORBIDDEN, ("CodeGraph index already present — a full init "
                                             "is not a session-start action (contract §6.2); "
                                             "run record-init to canonically register it")
            if wt_state.get("last_sync_failed"):
                return SYNC_FAILED_DEFERRED, ("previous sync failed; retry incremental sync")
            stale, index_sha, owner_head, _ = graph_freshness(worktree, "A")
            if dirty or stale:
                why = "graph_dirty=YES" if dirty else \
                    "graph stale: GRAPH_INDEX_SHA=%s != GRAPH_OWNER_HEAD=%s (review R5-F1)" \
                    % (index_sha[:12], owner_head[:12])
                return INCREMENTAL_SYNC_ONCE, \
                    "index present without a canonical record; %s; register via record-init" % why
            return NO_SYNC, "index present without a canonical record; register via record-init"
        return INIT_ONCE, ("no canonical graph, no init record → repo-wide init allowed "
                           "EXACTLY ONCE; run record-init immediately after")

    # -- before editing: grounding first, then blast radius (contract §7)
    if intent == "pre-edit":
        risk_u = str(risk or LOW).upper()
        needs_grounding = (RISK_ORDER.get(risk_u, 0) >= RISK_ORDER["MEDIUM"]
                           and cs.classify(file_path) == "graph")
        if not needs_grounding:
            return ALLOW_WRITE, "risk=%s below grounding threshold or non-production target" % risk_u
        if gg is not None:
            gdecision, gdetail = gg.decide(file_path, risk_u, worktree)
            if gdecision == "BLOCK":
                return GROUNDING_REQUIRED, gdetail
        else:
            if not isinstance(wt_state.get("grounding_receipt"), dict):
                return GROUNDING_REQUIRED, ("CODEGRAPH_GROUNDING_REQUIRED risk=%s (guard module "
                                            "unavailable; conservative)" % risk_u)

        br = wt_state.get("blast_radius")
        if not isinstance(br, dict) or not br.get("files") or not br.get("base"):
            return BLAST_RADIUS_REQUIRED, ("no blast radius on record — run `blast-radius "
                                           "--base <BASE_SHA> --target <files>` before the write")
        if not br.get("resolved", False) or br.get("mode") == "UNRESOLVED":
            return BLAST_RADIUS_REQUIRED, ("blast radius UNRESOLVED (git could not prove the "
                                           "delta) — production write blocked (review F2)")
        if not br_fresh(worktree, br):
            return BLAST_RADIUS_REQUIRED, ("blast radius computed at head=%s left HEAD ancestry "
                                           "(head=%s) — recompute incrementally, not a full init"
                                           % (br.get("head"), head_sha(worktree)))
        if file_path:
            rel = norm_rel(worktree, file_path)
            if rel not in set(br.get("files") or []):
                # review F3: tracked/untracked must not decide scope authority
                return BLAST_RADIUS_EXPANSION_REQUIRED, (
                    "%s is outside the approved blast radius / EXPECTED_EDIT_SURFACE "
                    "(%d files) — tracked or new, the approved surface is the authority; "
                    "explicitly expand the intended edit surface and recompute blast-radius "
                    "before widening the edit" % (rel, br.get("count", 0)))
        return ALLOW_WRITE, ("grounding + blast radius satisfied TICKET=%s files=%d"
                             % (wt_state.get("grounding_receipt", {}).get("TICKET", ""),
                                br.get("count", 0)))

    # -- after editing: mark dirty only (contract §6.6 — never a per-edit sync)
    if intent == "post-edit":
        return MARK_DIRTY, "dirty flag set; sync deferred to query/review/handoff/stop"

    # -- query / review / blast-radius / handoff / stop: JIT sync once (§6.6)
    if mode == "B" and not has_index and not lane_init:
        return INIT_ONCE, "MODE B lane graph missing → init once for this lane, then incremental"
    if mode == "A" and not canonical_init:
        if is_lane:
            # review R4-C: ALL sync intents on an ordinary MODE A worktree lane
            # refuse to init — the canonical init belongs at the main checkout
            return CANONICAL_INIT_REQUIRED_AT_MAIN, ("MODE A lane must not init itself (review "
                                                     "R4-C) — run the one-time init at the main "
                                                     "checkout, then sync incrementally")
        if not has_index and not main_index:
            return INIT_ONCE, ("no canonical graph and no index → init once (repo-wide, at the "
                               "main checkout), then incremental")
        # main checkout with an existing index but no canonical record: fall
        # through to sync handling; register the graph via record-init
    if wt_state.get("last_sync_failed"):
        return SYNC_FAILED_DEFERRED, ("sync previously failed; retry incremental sync — never "
                                      "escalate to full init")
    # review R5-F2: an ordinary MODE A worktree lane never owns a graph — a
    # source edit there (marker OR cheap mechanical git evidence; the worker
    # may edit via Bash) is CANDIDATE DELTA, not a lane CodeGraph sync. The
    # canonical graph stays BASE_ONLY + DELTA_BY_DIFF; review/handoff/stop
    # never demand an impossible lane sync.
    if mode == "A" and is_lane:
        marked = bool(wt_state.get("candidate_delta_dirty") or wt_state.get("graph_dirty"))
        git_delta = mechanical_delta_present(worktree)
        label = "YES" if (marked or git_delta) else ("UNKNOWN" if git_delta is None else "NO")
        stale_note = ""
        if graph_freshness(worktree, "A")[0]:
            stale_note = (" canonical graph is stale (graph-owner HEAD moved) — its "
                          "incremental sync belongs at the main checkout")
        return NO_SYNC, ("MODE A lane: CANDIDATE_DELTA_DIRTY=%s (marker=%s git=%s) — coverage="
                         "BASE_ONLY+DELTA_BY_DIFF, no lane CodeGraph sync exists, the canonical "
                         "graph remains BASE_ONLY + DELTA_BY_DIFF (review R5-F2)%s"
                         % (label, marked, git_delta, stale_note))
    if dirty:
        return INCREMENTAL_SYNC_ONCE, "graph_dirty=YES → sync once, then record-sync-result --ok"
    # review R5-F1: mechanical graph freshness — GRAPH_INDEX_SHA must equal
    # GRAPH_OWNER_HEAD even when no Edit marker ever fired (pull / merge /
    # fast-forward / checkout / external commit)
    stale, index_sha, owner_head, fscope = graph_freshness(worktree, mode)
    if stale:
        return INCREMENTAL_SYNC_ONCE, ("graph freshness (review R5-F1): GRAPH_INDEX_SHA=%s != "
                                       "GRAPH_OWNER_HEAD=%s (scope=%s) → incremental sync once, "
                                       "never a full init"
                                       % (index_sha[:12], owner_head[:12], fscope))
    return NO_SYNC, "graph clean at head=%s" % (wt_state.get("last_sync_head", "") or head_sha(worktree))


# --- invariants ---------------------------------------------------------------

def verify(worktree):
    """Mechanical invariant check (contract §6.7). Returns (ok, findings)."""
    findings = []
    main_dir = repo_main_dir(worktree) or worktree
    canonical_init = init_done(cs.load(main_dir))

    # LC-INV1  once the canonical init record exists, no intent may yield
    #          INIT_ONCE again in MODE A (lane-local MODE B is exempt by design)
    for intent in sorted(ALL_INTENTS):
        dec, _ = decide(intent, worktree, risk=LOW, file_path="", request_full_init=True,
                        lane_mode="A")
        if canonical_init and dec == INIT_ONCE:
            findings.append("LC-INV1 intent=%s returned INIT_ONCE despite canonical init record" % intent)
    # LC-INV2  session-start on a canonically initialized repo is never INIT_ONCE
    if canonical_init:
        dec, _ = decide("session-start", worktree, lane_mode="A")
        if dec == INIT_ONCE:
            findings.append("LC-INV2 session-start returned INIT_ONCE on initialized repo")
    # LC-INV3  a failed sync never degrades into a full init
    wt_state = cs.load(worktree)
    graph_exists = index_present(worktree) or canonical_init or init_done(wt_state)
    if wt_state.get("last_sync_failed") and graph_exists:
        for intent in sorted(SYNC_INTENTS):
            dec, _ = decide(intent, worktree)
            if dec == INIT_ONCE:
                findings.append("LC-INV3 intent=%s fell back to INIT_ONCE after sync failure" % intent)
    # LC-INV4  dirty ⇒ the next sync-intent decision is INCREMENTAL_SYNC_ONCE
    #          (review R5-F2: EXCEPT an ordinary MODE A lane, where a source
    #          edit is candidate delta — the honest graph answer is NO_SYNC)
    if wt_state.get("graph_dirty") and not wt_state.get("last_sync_failed") and graph_exists:
        lane_a = os.path.realpath(worktree) != os.path.realpath(main_dir) \
            and lane_mode_of() == "A"
        for intent in sorted(SYNC_INTENTS):
            dec, _ = decide(intent, worktree)
            if lane_a:
                if dec != NO_SYNC:
                    findings.append("LC-INV4 mode=A lane intent=%s returned %s while "
                                    "candidate-dirty (expected NO_SYNC — no lane graph "
                                    "sync exists)" % (intent, dec))
            elif dec != INCREMENTAL_SYNC_ONCE:
                findings.append("LC-INV4 intent=%s returned %s while dirty" % (intent, dec))
    # LC-INV5  decisions are drawn from the closed enum (both modes)
    for m in ("A", "B"):
        for intent in sorted(ALL_INTENTS):
            dec, _ = decide(intent, worktree, risk="HIGH", file_path="src/app.py", lane_mode=m)
            if dec not in DECISIONS:
                findings.append("LC-INV5 mode=%s intent=%s non-enum decision %r" % (m, intent, dec))
    # LC-INV6  (review R4-C) a MODE A worktree lane NEVER gets INIT_ONCE — for
    #          ANY intent; while the canonical graph is missing every
    #          init-offering intent answers CANONICAL_INIT_REQUIRED_AT_MAIN
    if os.path.realpath(worktree) != os.path.realpath(main_dir):
        for intent in sorted(ALL_INTENTS):
            dec, _ = decide(intent, worktree, lane_mode="A")
            if dec == INIT_ONCE:
                findings.append("LC-INV6 MODE_A_LANE_NEVER_INIT_ONCE intent=%s returned INIT_ONCE"
                                % intent)
        if not canonical_init:
            for intent in sorted(INIT_OFFERING_INTENTS):
                dec, _ = decide(intent, worktree, lane_mode="A")
                if dec != CANONICAL_INIT_REQUIRED_AT_MAIN:
                    findings.append("LC-INV6 MODE_A_LANE_NEVER_INIT_ONCE intent=%s → %s "
                                    "(expected CANONICAL_INIT_REQUIRED_AT_MAIN)" % (intent, dec))
    # LC-INV7  (review R5-F1) GRAPH_INDEX_SHA != GRAPH_OWNER_HEAD ⇒ every sync
    #          intent answers INCREMENTAL_SYNC_ONCE even when GRAPH_DIRTY=NO —
    #          enforced at the graph owner's checkout (a MODE A lane reports
    #          staleness in its NO_SYNC note without demanding a lane sync)
    stale, index_sha, owner_head, _fscope = graph_freshness(worktree)
    owner_here = os.path.realpath(worktree) == os.path.realpath(main_dir) \
        or lane_mode_of() == "B"
    if graph_exists and stale and owner_here and not wt_state.get("last_sync_failed"):
        for intent in sorted(SYNC_INTENTS):
            dec, _ = decide(intent, worktree)
            if dec != INCREMENTAL_SYNC_ONCE:
                findings.append("LC-INV7 GRAPH_OWNER_HEAD_FRESHNESS intent=%s returned %s "
                                "(GRAPH_INDEX_SHA=%s != GRAPH_OWNER_HEAD=%s)"
                                % (intent, dec, index_sha[:12], owner_head[:12]))
    return (not findings), findings


# --- CLI ----------------------------------------------------------------------

def out(line):
    print(line)


def flag(args, name, default=None):
    return args[args.index(name) + 1] if name in args and len(args) > args.index(name) + 1 else default


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    args = argv[1:]
    worktree = os.environ.get("ZCODE_PROJECT_DIR") or os.getcwd()

    if cmd == "decide":
        intent = flag(args, "--intent", "")
        risk = flag(args, "--risk", LOW)
        file_path = flag(args, "--file", "")
        req_full = "--request-full-init" in args
        dec, detail = decide(intent, worktree, risk=risk, file_path=file_path,
                             request_full_init=req_full,
                             lane_mode=flag(args, "--lane-mode"))
        out("CODEGRAPH_LIFECYCLE_DECISION=%s INTENT=%s MODE=%s %s"
            % (dec, intent.lower(), lane_mode_of(flag(args, "--lane-mode")), detail))
        return 0

    if cmd == "record-init":
        lane = "--lane" in args
        main_dir = repo_main_dir(worktree) or worktree
        # review R4-D: record-init verifies ONLY the canonical graph path;
        # record-init --lane verifies ONLY the lane graph path — a lane index
        # can never masquerade as the canonical init.
        graph_owner = worktree if lane else main_dir
        scope = "lane" if lane else "canonical"
        # review F7/R4-D: honest init — a bare (or absent) .codegraph directory
        # is NOT health evidence; a real health probe must succeed, or one
        # failed init would lock the repo as "initialized"
        if not os.path.isdir(index_dir(graph_owner)):
            out("ERROR=GRAPH_INIT_REJECTED INDEX_MISSING scope=%s graph_dir=%s — the graph "
                "directory does not exist" % (scope, index_dir(graph_owner)))
            return 0
        ok, evidence = graph_health(graph_owner)
        if not ok:
            out("ERROR=GRAPH_INIT_REJECTED CODEGRAPH_HEALTH_UNPROVEN scope=%s evidence=%s — "
                "record-init requires real index health (production default: `codegraph status`; "
                "tests inject ZCODE_CODEGRAPH_HEALTH_CMD)" % (scope, evidence))
            return 0
        # review R5-F5: the recorded init SHA is the GRAPH OWNER's actual HEAD —
        # canonical record-init invoked from a lane binds the MAIN checkout's
        # HEAD, lane record-init binds the lane's own HEAD; an explicit --head
        # must never silently contradict the graph owner's actual HEAD.
        owner_head = head_sha(graph_owner)
        explicit = flag(args, "--head")
        if explicit and owner_head and explicit != owner_head:
            out("ERROR=GRAPH_INIT_HEAD_MISMATCH scope=%s --head=%s graph_owner_head=%s — the "
                "recorded init SHA must be the graph owner's actual HEAD (review R5-F5)"
                % (scope, explicit, owner_head))
            return 0
        target_dir = graph_owner
        state = cs.load(target_dir)
        state["graph_init"] = {
            "initialized_at": cs.now_utc(),
            "head": explicit or owner_head,
            "worktree": os.path.realpath(worktree),
            "mode": flag(args, "--mode", "full"),
            "scope": scope,
            "health_evidence": evidence,
        }
        state["last_sync_failed"] = False
        cs.save(target_dir, state)
        out("GRAPH_INIT_RECORDED scope=%s head=%s mode=%s health=%s (full init will now be "
            "FORBIDDEN)" % (scope, state["graph_init"]["head"],
                            state["graph_init"]["mode"], evidence))
        return 0

    if cmd == "blast-radius":
        base = flag(args, "--base", "")
        impact_files = None
        targets = [norm_rel(worktree, args[i + 1])
                   for i, a in enumerate(args) if a == "--target" and i + 1 < len(args)]
        ip = flag(args, "--impact-file")
        if ip and os.path.isfile(ip):
            try:
                data = json.loads(open(ip, encoding="utf-8").read())
                if isinstance(data, list):
                    impact_files = [str(x) for x in data]
                elif isinstance(data, dict):
                    impact_files = [str(x) for x in (data.get("files") or data.get("impact") or [])]
            except Exception:
                out("ERROR=BLAST_RADIUS_IMPACT_UNREADABLE")
                return 0
        state0 = cs.load(worktree)
        if not base:
            base = (state0.get("grounding_receipt") or {}).get("BASE_SHA", "") \
                or state0.get("last_sync_head", "")
        if not targets:
            # seed the intended edit surface from the grounding receipt when the
            # caller did not name targets explicitly
            surface = (state0.get("grounding_receipt") or {}).get("EXPECTED_EDIT_SURFACE", "")
            if isinstance(surface, str) and surface:
                targets = [norm_rel(worktree, s.strip()) for s in surface.split(",") if s.strip()]
        rec, err = compute_blast_radius(worktree, base, impact_files, targets or None)
        if rec is None:
            out("ERROR=BLAST_RADIUS_UNRESOLVED reason=%s" % err)
            return 0
        state = cs.load(worktree)
        state["blast_radius"] = rec
        cs.save(worktree, state)
        out("BLAST_RADIUS=RECORDED mode=%s resolved=%s base=%s count=%d"
            % (rec["mode"], rec["resolved"], rec["base"], rec["count"]))
        return 0

    if cmd == "record-sync-result":
        state = cs.load(worktree)
        ok = "--ok" in args
        state["last_sync_failed"] = not ok
        if ok:
            state["graph_dirty"] = False
            state["last_sync_head"] = head_sha(worktree) or state.get("last_sync_head", "")
            state["last_sync_at"] = cs.now_utc()
        cs.save(worktree, state)
        out("SYNC_RESULT=%s %s" % ("OK" if ok else "FAILED",
                                   "" if ok else "(deferred; retry incremental sync — never full init)"))
        return 0

    if cmd == "verify":
        ok, findings = verify(worktree)
        for f in findings:
            out("LC_INVARIANT_VIOLATION %s" % f)
        out("LIFECYCLE_INVARIANTS=%s" % ("PASS" if ok else "FAIL"))
        return 0 if ok else 1

    out("ERROR=UNKNOWN_COMMAND %s" % cmd)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("CODEGRAPH_LIFECYCLE_DECISION=ERROR (non-blocking)")
        sys.exit(0)
