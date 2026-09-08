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
    CODEGRAPH_REBUILD_REQUIRED    review R6-F6: a REGISTERED graph that no longer
                                  passes its health probe is CORRUPT / PARTIAL /
                                  INCOMPATIBLE — report the reason, NEVER auto
                                  delete, NEVER auto full init; an explicit
                                  orchestrator rebuild authority is required
                                  (record-rebuild). While unresolved MEDIUM/HIGH
                                  falls back to MODE C manual grounding.
    NO_REPO                       not a git worktree → no-op

Surface-coherence signal (NOT a lifecycle decision — it is emitted by
`blast-radius` and by the invariant checker, review R6-F4):

    UNAPPROVED_DELTA_DETECTED     OBSERVED_DELTA ⊄ APPROVED_EDIT_SURFACE. An
                                  already-changed file never authorises itself
                                  on recompute; widening requires an explicit
                                  authority action (--target / EXPECTED_EDIT_SURFACE).

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
                                       # R6-F2: WRITE-ONCE — a second record-init on
                                       # an already-registered scope is rejected
                                       # (GRAPH_INIT_ALREADY_RECORDED)
  python codegraph_lifecycle.py record-rebuild --authority CODEGRAPH_REBUILD_AUTHORIZED
                                       [--lane]   # R6-F6: the ONLY path that may
                                       rewrite an existing graph_init record; it is
                                       the explicit orchestrator rebuild authority.
                                       It is never reached silently by record-init.
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
CODEGRAPH_REBUILD_REQUIRED = "CODEGRAPH_REBUILD_REQUIRED"
NO_REPO = "NO_REPO"
# review R6-F4: a SURFACE-COHERENCE SIGNAL, not a lifecycle decision. Emitted by
# `blast-radius` (recompute) and by the LC-INV8 invariant; it deliberately stays
# outside DECISIONS so the lifecycle enum remains closed.
UNAPPROVED_DELTA_DETECTED = "UNAPPROVED_DELTA_DETECTED"

DECISIONS = frozenset({
    INIT_ONCE, CANONICAL_INIT_REQUIRED_AT_MAIN, FULL_INIT_FORBIDDEN,
    INCREMENTAL_SYNC_ONCE, NO_SYNC,
    GROUNDING_REQUIRED, BLAST_RADIUS_REQUIRED, BLAST_RADIUS_EXPANSION_REQUIRED,
    ALLOW_WRITE, MARK_DIRTY, SYNC_FAILED_DEFERRED, CODEGRAPH_REBUILD_REQUIRED,
    NO_REPO,
})

# review R6-F2 / R6-F6: the explicit rebuild authority token. Without it no code
# path may rewrite an existing graph_init record.
REBUILD_AUTHORITY = "CODEGRAPH_REBUILD_AUTHORIZED"

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


_HEALTH_CACHE = {}


def graph_health(graph_owner_dir):
    """(ok, evidence). Injectable mechanical health probe (review R4-D).

    Production default: the REAL `codegraph status` CLI must exit 0 — a bare
    .codegraph directory is NOT health evidence. Synthetic tests inject a mock
    probe via ZCODE_CODEGRAPH_HEALTH_CMD (shlex-split command line, run with
    cwd=graph_owner_dir); production never sets that variable.

    Memoised per process (review R6-F6): the invariant checker and `decide()` may
    consult health many times in one process; re-running the real CLI that often
    would be both slow and non-deterministic. One process = one probe result per
    (directory, probe command)."""
    custom = os.environ.get("ZCODE_CODEGRAPH_HEALTH_CMD", "")
    try:
        key = (os.path.realpath(graph_owner_dir), custom)
    except Exception:  # pragma: no cover - defensive
        key = (str(graph_owner_dir), custom)
    if key in _HEALTH_CACHE:
        return _HEALTH_CACHE[key]
    result = _graph_health_uncached(graph_owner_dir, custom)
    _HEALTH_CACHE[key] = result
    return result


def _graph_health_uncached(graph_owner_dir, custom):
    """Uncached health probe — see graph_health()."""
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


def _rebuild_detail(scope, graph_dir, evidence):
    """Review R6-F6 detail string — the corrupt/partial index recovery state."""
    return ("%s graph at %s is CORRUPT / PARTIAL / INCOMPATIBLE (%s) — "
            "CODEGRAPH_REBUILD_REQUIRED: report the reason, NEVER auto-delete the index, NEVER "
            "auto full init; an explicit orchestrator rebuild authority is required "
            "(`record-rebuild --authority %s%s`). Until it is resolved MEDIUM/HIGH grounding "
            "falls back to MODE C manual grounding (never blocked, never silently graph-backed)."
            % (scope, graph_dir, evidence, REBUILD_AUTHORITY,
               " --lane" if scope == "lane" else ""))


def mode_a_base_coherence(worktree, wt_state):
    """(mismatch, detail) — review R6-F5 mechanical Mode A coherence invariant.

    An honest Mode A structural grounding requires the canonical graph base to
    be the SAME base as the lane:

        LANE_BASE_SHA (TICKET_BASE_SHA / grounding BASE_SHA)
        == CANONICAL_GRAPH_INDEX_SHA (the base graph the lane would consume)

    When main and the canonical graph advance A → B while the lane stays at A,
    calling the lane's coverage "BASE_ONLY + DELTA_BY_DIFF" would be dishonest —
    the canonical graph is now the graph of a DIFFERENT base. Mismatch means
    MODE_A_BASE_MISMATCH: the orchestrator must reconcile (update/integrate the
    lane, upgrade to MODE B candidate-exact, or MODE C manual grounding) before
    any MEDIUM/HIGH production write/review may claim Mode A grounding."""
    main_dir = repo_main_dir(worktree) or worktree
    _stale, index_sha, _owner_head, _scope = graph_freshness(worktree, "A")
    canonical_graph_sha = str(cs.load(main_dir).get("last_sync_head") or index_sha or "")
    lane_base = str((wt_state.get("grounding_receipt") or {}).get("BASE_SHA")
                    or wt_state.get("ticket_base_sha") or "")
    if not lane_base or not canonical_graph_sha:
        return False, ""  # nothing to compare → not decidable here, not a mismatch
    if lane_base != canonical_graph_sha:
        return True, ("MODE_A_BASE_MISMATCH LANE_BASE_SHA=%s CANONICAL_GRAPH_INDEX_SHA=%s — the "
                      "canonical graph has advanced past the lane base; do NOT silently present "
                      "the latest-main graph as this lane's base graph (review R6-F5). Reconcile "
                      "FIRST: (A) update/integrate the lane onto the current authorized base, "
                      "(B) upgrade to MODE B candidate-exact graph, or (C) MODE C manual "
                      "candidate grounding."
                      % (lane_base[:12], canonical_graph_sha[:12]))
    return False, ""


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


def _in_graph_index(worktree, rel_path):
    """The CodeGraph index directory is a machine-local build artifact (contract
    §6.4) — like runtime state it can never be part of an edit surface or of a
    production source delta (review R6-F3/F4)."""
    try:
        idx = os.path.realpath(index_dir(worktree))
        target = os.path.realpath(os.path.join(os.path.realpath(worktree), rel_path))
        return target == idx or target.startswith(idx + os.sep)
    except Exception:
        return False


def _surface_path(worktree, rel_path):
    """True when a git-visible path belongs to a real edit surface / production
    delta (runtime-local state and the graph index are machine-local)."""
    return (not _in_runtime_state(worktree, rel_path)
            and not _in_graph_index(worktree, rel_path))


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
                # review R6-F7b: `git diff --name-only -z` already supplies NUL
                # boundaries — stripping would mutate legal filenames (leading /
                # trailing spaces are legal on every mainstream filesystem).
                # Only the empty NUL field (the terminating one) is skipped; the
                # exact bytes between NULs are preserved.
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


def production_delta_present(worktree):
    """(present, paths) — uncommitted PRODUCTION SOURCE delta (review R6-F3:
    defense in depth for the shell gap). Tracked edits, untracked production
    files, deletes and BOTH rename endpoints count; runtime-local state and the
    CodeGraph index directory do not (machine-local artifacts).

    present is None when git cannot answer → the caller must fail closed
    ("cannot prove a clean tree"), never silently report clean."""
    st = _git(["status", "--porcelain=v1", "-z"], worktree)
    if st is None or st.returncode != 0:
        return None, []
    try:
        files = _parse_status_z(st.stdout)
    except ValueError:
        return None, []
    prod = sorted(p for p in files
                  if _surface_path(worktree, p) and cs.classify(p) == "graph")
    return (bool(prod), prod)


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
    """Returns (record, error). Authority and observation are SEPARATE sets
    (review R6-F4) — overloading one set let an already-illegal edit authorise
    itself on recompute:

        APPROVED_EDIT_SURFACE  AUTHORITY. Derived ONLY from explicit intended
                               targets / EXPECTED_EDIT_SURFACE / an explicit
                               authorized expansion. NEVER from observed git
                               changes, NEVER from CodeGraph impact.
        OBSERVED_DELTA         EVIDENCE ONLY. Tracked changes, untracked
                               changes, deletes, renames (both endpoints).
        IMPACT_SURFACE         STRUCTURAL AWARENESS ONLY. CodeGraph
                               callers/callees/impact — it does NOT authorise
                               editing every impacted file.

    Invariant: OBSERVED_DELTA ⊆ APPROVED_EDIT_SURFACE, else
    UNAPPROVED_DELTA_DETECTED and the record carries surface_coherent=False.

    At ticket start base == HEAD, so a delta-only radius would be empty — the
    authority side is what makes a legitimate first write possible.

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
    observed = sorted(p for p in set(delta) if _surface_path(worktree, p))
    approved = sorted({norm_rel(worktree, t) for t in (targets or []) if t})
    impact = sorted({str(x) for x in (impact_files or [])})
    unapproved = sorted(set(observed) - set(approved))
    files = sorted(set(approved) | set(observed) | set(impact))
    mode = "GIT_DELTA"
    if targets:
        mode = "TARGETS_PLUS_GIT_DELTA"
    if impact_files:
        mode = "TARGETS_PLUS_GRAPH" if targets else "GIT_DELTA_PLUS_GRAPH"
    rec = {
        "base": base or "",
        "head": head,
        "mode": mode if resolved else "UNRESOLVED",
        "resolved": resolved,
        # R6-F4: authority, observation and impact are three distinct surfaces
        "approved_edit_surface": approved,
        "observed_delta": observed,
        "impact_surface": impact,
        "unapproved_delta": unapproved,
        "surface_coherent": not unapproved,
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
                # review R6-F6: a REGISTERED lane graph that no longer passes its
                # health probe is CORRUPT/PARTIAL — explicit rebuild authority,
                # never a silent re-init and never an auto-delete.
                ok, evidence = graph_health(worktree)
                if not ok:
                    return CODEGRAPH_REBUILD_REQUIRED, _rebuild_detail("lane", worktree, evidence)
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
            # review R6-F6: a REGISTERED canonical graph that no longer passes
            # its health probe is CORRUPT/PARTIAL/INCOMPATIBLE.
            ok, evidence = graph_health(main_dir)
            if not ok:
                return CODEGRAPH_REBUILD_REQUIRED, _rebuild_detail("canonical", main_dir, evidence)
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
        # review R6-F4: authority is APPROVED_EDIT_SURFACE, not "files" (the
        # union) and never the observed git delta.
        if not isinstance(br, dict) or not br.get("approved_edit_surface") or not br.get("base"):
            return BLAST_RADIUS_REQUIRED, ("no APPROVED_EDIT_SURFACE on record — run `blast-radius "
                                           "--base <BASE_SHA> --target <files>` before the write "
                                           "(review R6-F4: OBSERVED_DELTA is evidence, never "
                                           "authority)")
        if not br.get("resolved", False) or br.get("mode") == "UNRESOLVED":
            return BLAST_RADIUS_REQUIRED, ("blast radius UNRESOLVED (git could not prove the "
                                           "delta) — production write blocked (review F2)")
        # review R6-F5: Mode A base/graph coherence — at grounding/review time
        # the lane base and the canonical graph base must be the SAME base, or
        # the coverage claim "BASE_ONLY + DELTA_BY_DIFF" is dishonest.
        if not br_fresh(worktree, br):
            return BLAST_RADIUS_REQUIRED, ("blast radius computed at head=%s left HEAD ancestry "
                                           "(head=%s) — recompute incrementally, not a full init"
                                           % (br.get("head"), head_sha(worktree)))
        # review R6-F5: Mode A base/graph coherence — at grounding/review time
        # the lane base and the canonical graph base must be the SAME base, or
        # the coverage claim "BASE_ONLY + DELTA_BY_DIFF" is dishonest. Blocked
        # until the orchestrator reconciles (integrate / MODE B / MODE C).
        mismatch, mdetail = mode_a_base_coherence(worktree, wt_state)
        if mismatch:
            return BLAST_RADIUS_REQUIRED, mdetail
        approved = set(br.get("approved_edit_surface") or [])
        if file_path:
            rel = norm_rel(worktree, file_path)
            if rel not in approved:
                # review F3: tracked/untracked must not decide scope authority
                return BLAST_RADIUS_EXPANSION_REQUIRED, (
                    "%s is outside the APPROVED_EDIT_SURFACE (%d approved files) — tracked or "
                    "new, the approved surface is the authority; explicitly expand the intended "
                    "edit surface (`blast-radius --target %s`) and recompute before widening "
                    "the edit (review R6-F4)" % (rel, len(approved), rel))
        detail = ("grounding + approved edit surface satisfied TICKET=%s approved=%d"
                  % (wt_state.get("grounding_receipt", {}).get("TICKET", ""), len(approved)))
        # review R6-F4: an already-changed file never authorises itself. The
        # write on an APPROVED target proceeds, but the incoherence is emitted
        # on every pre-edit decision (never silent) and LC-INV8 fails `verify`.
        unapproved = sorted(br.get("unapproved_delta") or [])
        if unapproved:
            detail += (" UNAPPROVED_DELTA_DETECTED=%s (OBSERVED_DELTA ⊄ APPROVED_EDIT_SURFACE — "
                       "reconcile before review/handoff; an already-changed file never "
                       "authorises itself on recompute)" % ",".join(unapproved))
        return ALLOW_WRITE, detail

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
    # Everything below is a GRAPH OWNER context: MODE A at the main checkout, or
    # a MODE B lane (which owns its own graph).
    owner_dir = worktree if mode == "B" else main_dir
    owner_state = wt_state if mode == "B" else repo_state
    owner_scope = "lane" if mode == "B" else "canonical"
    # review R6-F6: a registered graph that fails its health probe is
    # CORRUPT / PARTIAL / INCOMPATIBLE — an explicit fail-safe lifecycle state,
    # never a deadlock and never a silent full re-init.
    if init_done(owner_state):
        ok, evidence = graph_health(owner_dir)
        if not ok:
            return CODEGRAPH_REBUILD_REQUIRED, _rebuild_detail(owner_scope, owner_dir, evidence)
    if dirty:
        return INCREMENTAL_SYNC_ONCE, "graph_dirty=YES → sync once, then record-sync-result --ok"
    # review R6-F3 (defense in depth): a production source delta a worker made
    # through Bash never fires a PostToolUse marker. Lifecycle boundaries must
    # therefore inspect the Git source delta mechanically, so the graph sync is
    # required even when HEAD is unchanged and graph_dirty is absent.
    if init_done(owner_state):
        present, paths = production_delta_present(worktree)
        if present is None:
            return INCREMENTAL_SYNC_ONCE, (
                "graph delta UNRESOLVED (git could not prove a clean tree) — fail closed: "
                "incremental sync once, then record-sync-result --ok (review R6-F3)")
        if present:
            return INCREMENTAL_SYNC_ONCE, (
                "uncommitted PRODUCTION source delta (review R6-F3 mechanical git evidence, no "
                "PostToolUse marker fired): %s — HEAD unchanged and graph_dirty=NO, the graph "
                "still needs an incremental sync, then record-sync-result --ok"
                % ",".join(paths[:5]))
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
    # review R6-F6: while the registered graph is corrupt, decide() honestly
    # answers CODEGRAPH_REBUILD_REQUIRED — the sync-posture invariants below
    # (LC-INV3/4/7) presuppose a healthy graph and must not fire against the
    # recovery state.
    rebuild_required = canonical_init and not graph_health(main_dir)[0]
    if wt_state.get("last_sync_failed") and graph_exists and not rebuild_required:
        for intent in sorted(SYNC_INTENTS):
            dec, _ = decide(intent, worktree)
            if dec == INIT_ONCE:
                findings.append("LC-INV3 intent=%s fell back to INIT_ONCE after sync failure" % intent)
    # LC-INV4  dirty ⇒ the next sync-intent decision is INCREMENTAL_SYNC_ONCE
    #          (review R5-F2: EXCEPT an ordinary MODE A lane, where a source
    #          edit is candidate delta — the honest graph answer is NO_SYNC)
    if (wt_state.get("graph_dirty") and not wt_state.get("last_sync_failed")
            and graph_exists and not rebuild_required):
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
    if (graph_exists and stale and owner_here and not wt_state.get("last_sync_failed")
            and not rebuild_required):
        for intent in sorted(SYNC_INTENTS):
            dec, _ = decide(intent, worktree)
            if dec != INCREMENTAL_SYNC_ONCE:
                findings.append("LC-INV7 GRAPH_OWNER_HEAD_FRESHNESS intent=%s returned %s "
                                "(GRAPH_INDEX_SHA=%s != GRAPH_OWNER_HEAD=%s)"
                                % (intent, dec, index_sha[:12], owner_head[:12]))
    # LC-INV8  (review R6-F4) OBSERVED_DELTA ⊆ APPROVED_EDIT_SURFACE. An
    #          already-changed file is evidence, never authority: a recorded
    #          blast radius whose observed delta spills outside the approved
    #          surface is an invariant breach, not a recompute away.
    br = wt_state.get("blast_radius")
    if isinstance(br, dict) and br.get("approved_edit_surface") is not None:
        unapproved = sorted(set(br.get("observed_delta") or [])
                            - set(br.get("approved_edit_surface") or []))
        if unapproved:
            findings.append("LC-INV8 %s files=%s (OBSERVED_DELTA is not a subset of "
                            "APPROVED_EDIT_SURFACE — an already-changed file never authorises "
                            "itself)" % (UNAPPROVED_DELTA_DETECTED, ",".join(unapproved)))
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
        # review R6-F2: record-init is REGISTRATION of a successfully initialized
        # graph — it is WRITE-ONCE and is NOT a freshness-update mechanism.
        # Freshness advances ONLY through a successful incremental sync
        # (`codegraph sync` → `record-sync-result --ok` → last_sync_head = the
        # graph owner's actual HEAD). An explicit rebuild is a SEPARATE recovery
        # path (record-rebuild) and must never be reachable silently from here.
        existing = cs.load(graph_owner)
        if init_done(existing):
            owner_head = head_sha(graph_owner)
            out("ERROR=GRAPH_INIT_ALREADY_RECORDED scope=%s head=%s recorded_at=%s — record-init "
                "is WRITE-ONCE (review R6-F2); graph indexed at %s while the graph owner HEAD is "
                "%s is a FRESHNESS problem, not an init problem: run `codegraph sync` then "
                "`record-sync-result --ok`. A corrupt/incompatible graph is an explicit rebuild "
                "(`record-rebuild --authority %s%s`)."
                % (scope, existing["graph_init"].get("head", ""),
                   existing["graph_init"].get("initialized_at", ""),
                   (existing["graph_init"].get("head", "") or "?")[:12],
                   (owner_head or "?")[:12], REBUILD_AUTHORITY,
                   " --lane" if lane else ""))
            return 0
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
            "FORBIDDEN; record-init is WRITE-ONCE per review R6-F2)"
            % (scope, state["graph_init"]["head"],
               state["graph_init"]["mode"], evidence))
        return 0

    if cmd == "record-rebuild":
        # review R6-F6: the SEPARATE, EXPLICIT recovery path for a corrupt /
        # partial / incompatible graph. It is the only operation allowed to
        # rewrite an existing graph_init record, and only when the orchestrator
        # states the rebuild authority verbatim.
        lane = "--lane" in args
        main_dir = repo_main_dir(worktree) or worktree
        graph_owner = worktree if lane else main_dir
        scope = "lane" if lane else "canonical"
        if flag(args, "--authority") != REBUILD_AUTHORITY:
            out("ERROR=CODEGRAPH_REBUILD_AUTHORITY_REQUIRED scope=%s — a rebuild is an explicit "
                "orchestrator authority action; pass `--authority %s` (review R6-F6: record-init "
                "must never rebuild silently)" % (scope, REBUILD_AUTHORITY))
            return 0
        state = cs.load(graph_owner)
        rec = state.get("graph_init")
        # review R6-F6: rebuild is RECOVERY of an existing registration at the
        # SAME scope — a lane rebuild requires a lane record, a canonical
        # rebuild requires a canonical record (a same-file canonical record
        # must never silently authorise a lane rebuild, or vice versa).
        if not (isinstance(rec, dict) and rec.get("initialized_at")
                and rec.get("scope") == scope):
            out("ERROR=CODEGRAPH_REBUILD_REQUIRES_EXISTING_RECORD scope=%s — no graph_init record "
                "exists at this scope; a first-time graph is registered with `record-init%s`, "
                "rebuild is recovery only" % (scope, " --lane" if lane else ""))
            return 0
        if not os.path.isdir(index_dir(graph_owner)):
            out("ERROR=GRAPH_REBUILD_REJECTED INDEX_MISSING scope=%s graph_dir=%s — rebuild the "
                "index first, then record it" % (scope, index_dir(graph_owner)))
            return 0
        ok, evidence = graph_health(graph_owner)
        if not ok:
            out("ERROR=GRAPH_REBUILD_REJECTED CODEGRAPH_HEALTH_UNPROVEN scope=%s evidence=%s — "
                "a rebuild is only recorded after the index is actually healthy"
                % (scope, evidence))
            return 0
        owner_head = head_sha(graph_owner)
        explicit = flag(args, "--head")
        if explicit and owner_head and explicit != owner_head:
            out("ERROR=GRAPH_REBUILD_HEAD_MISMATCH scope=%s --head=%s graph_owner_head=%s"
                % (scope, explicit, owner_head))
            return 0
        if not owner_head:
            out("ERROR=GRAPH_REBUILD_HEAD_UNAVAILABLE scope=%s — cannot record a rebuild without "
                "a resolvable graph-owner HEAD" % scope)
            return 0
        prev = rec
        rec = {
            "initialized_at": prev.get("initialized_at") or cs.now_utc(),
            "head": owner_head,
            "worktree": os.path.realpath(worktree),
            "mode": flag(args, "--mode", prev.get("mode", "full")),
            "scope": scope,
            "health_evidence": evidence,
            "rebuilt_at": cs.now_utc(),
            "rebuild_count": int(prev.get("rebuild_count") or 0) + 1,
            "rebuild_reason": flag(args, "--reason", "UNSPECIFIED"),
        }
        state["graph_init"] = rec
        state["last_sync_failed"] = False
        state["last_sync_head"] = owner_head
        state["graph_dirty"] = False
        cs.save(graph_owner, state)
        out("GRAPH_REBUILD_RECORDED scope=%s head=%s rebuild_count=%s reason=%s health=%s"
            % (scope, rec["head"], rec["rebuild_count"], rec["rebuild_reason"], evidence))
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
        out("BLAST_RADIUS=RECORDED mode=%s resolved=%s base=%s count=%d APPROVED=%d OBSERVED=%d "
            "IMPACT=%d SURFACE_COHERENT=%s"
            % (rec["mode"], rec["resolved"], rec["base"], rec["count"],
               len(rec["approved_edit_surface"]), len(rec["observed_delta"]),
               len(rec["impact_surface"]), "YES" if rec["surface_coherent"] else "NO"))
        if not rec["surface_coherent"]:
            # review R6-F4: an already-changed file is EVIDENCE, never authority.
            # Recomputing without an explicit expansion leaves it unauthorized,
            # and the incoherence is emitted instead of being absorbed.
            out("%s files=%s — OBSERVED_DELTA ⊄ APPROVED_EDIT_SURFACE (review R6-F4); these "
                "files stay UNAUTHORIZED until an explicit authority action widens the surface: "
                "`blast-radius --target <file>` (or EXPECTED_EDIT_SURFACE) then recompute. "
                "Recomputing alone never approves an already-changed file."
                % (UNAPPROVED_DELTA_DETECTED, ",".join(rec["unapproved_delta"])))
        return 0

    if cmd == "record-sync-result":
        state = cs.load(worktree)
        ok = "--ok" in args
        state["last_sync_failed"] = not ok
        if ok:
            state["graph_dirty"] = False
            state["candidate_delta_dirty"] = False
            # review R6-F2: freshness advances ONLY through a successful
            # incremental sync — last_sync_head binds the ACTUAL graph owner
            # HEAD (never a stale cached value).
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
