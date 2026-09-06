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

Closed decision enum (contract §6.7):

    INIT_ONCE                     index absent AND no init record → full init allowed
    FULL_INIT_FORBIDDEN           init record present → full init is never legal
    INCREMENTAL_SYNC_ONCE         dirty → sync exactly once, then clear the flag
    NO_SYNC                       clean → nothing to do
    GROUNDING_REQUIRED            MEDIUM/HIGH production write without receipt
    BLAST_RADIUS_REQUIRED         receipt present but blast radius missing/stale
    BLAST_RADIUS_EXPANSION_REQUIRED  writing a tracked file outside the computed set
    ALLOW_WRITE                   pre-edit gate satisfied
    MARK_DIRTY                    post-edit: flag set, sync deferred
    SYNC_FAILED_DEFERRED          sync failed → report; NEVER fall back to full init
    NO_REPO                       not a git worktree → no-op

Runtime-local state additions (contract §6.4 — machine-local, never committed):

    graph_init      = {"initialized_at", "head", "worktree", "mode"}
    blast_radius    = {"base", "head", "mode", "files", "count", "computed_at"}
    last_sync_failed = bool      → keeps a failed sync from degrading into a re-init

CLI:

  python codegraph_lifecycle.py decide --intent <INTENT> [--risk R] [--file F]
                                       [--request-full-init]
  python codegraph_lifecycle.py record-init [--head SHA] [--mode full]
  python codegraph_lifecycle.py blast-radius [--base SHA] [--impact-file JSON]
  python codegraph_lifecycle.py record-sync-result --ok|--fail
  python codegraph_lifecycle.py verify          # invariant self-check

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
    INIT_ONCE, FULL_INIT_FORBIDDEN, INCREMENTAL_SYNC_ONCE, NO_SYNC,
    GROUNDING_REQUIRED, BLAST_RADIUS_REQUIRED, BLAST_RADIUS_EXPANSION_REQUIRED,
    ALLOW_WRITE, MARK_DIRTY, SYNC_FAILED_DEFERRED, NO_REPO,
})

# intents whose correct answer is "sync once if dirty" (contract §6.6 JIT rule)
SYNC_INTENTS = frozenset({"query", "review", "blast-radius", "handoff", "stop"})
ALL_INTENTS = frozenset({"session-start", "pre-edit", "post-edit"}) | SYNC_INTENTS

LOW = "LOW"
RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def _git(args, cwd, timeout=10):
    try:
        return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, errors="replace")
    except Exception:
        return None


def head_sha(worktree):
    r = _git(["rev-parse", "HEAD"], worktree)
    return r.stdout.strip() if r and r.returncode == 0 else ""


def is_repo(worktree):
    r = _git(["rev-parse", "--show-toplevel"], worktree)
    return bool(r and r.returncode == 0)


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


# --- blast radius -------------------------------------------------------------

def _in_runtime_state(worktree, rel_path):
    """Runtime-local state is machine-local bookkeeping, never part of an edit
    surface (contract §6.4). Excluded so it cannot pollute a blast radius."""
    try:
        rr = os.path.realpath(str(cs.runtime_root()))
        target = os.path.realpath(os.path.join(os.path.realpath(worktree), rel_path))
        return target == rr or target.startswith(rr + os.sep)
    except Exception:
        return False


def changed_files(worktree, base):
    """(files, resolved). Git-visible delta base..HEAD plus uncommitted changes."""
    files = set()
    if base:
        r = _git(["diff", "--name-only", "%s...HEAD" % base], worktree)
        if r is not None and r.returncode == 0:
            files |= {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}
        else:
            r2 = _git(["diff", "--name-only", base, "HEAD"], worktree)
            if r2 is not None and r2.returncode == 0:
                files |= {ln.strip() for ln in r2.stdout.splitlines() if ln.strip()}
    st = _git(["status", "--porcelain"], worktree)
    if st is not None and st.returncode == 0:
        for ln in st.stdout.splitlines():
            ln = ln.strip()
            if len(ln) > 3:
                files.add(ln[3:].split(" -> ")[-1].strip().strip('"'))
    return sorted(f for f in files if not _in_runtime_state(worktree, f)), True


def is_tracked(worktree, rel_path):
    r = _git(["ls-files", "--error-unmatch", "--", rel_path], worktree)
    return bool(r and r.returncode == 0)


def compute_blast_radius(worktree, base, impact_files=None, targets=None):
    """Returns (record, error). The blast radius is the intended edit surface,
    NOT merely 'what already changed' — at ticket start base == HEAD, so a
    delta-only radius would be empty and would reject every legitimate write.

    impact set = TARGETS ∪ (git delta base..HEAD) ∪ (CodeGraph impact, optional)

    Never silently downgrades: when git cannot answer, mode = UNRESOLVED
    (contract §7 fail-closed semantics)."""
    if not is_repo(worktree):
        return None, "NOT_A_GIT_REPO"
    head = head_sha(worktree)
    delta, _ = changed_files(worktree, base)
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
        "mode": mode,
        "files": files,
        "count": len(files),
        "computed_at": cs.now_utc(),
    }
    return rec, ""


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


# --- decision core ------------------------------------------------------------

def decide(intent, worktree, risk=LOW, file_path="", request_full_init=False):
    """Returns (decision, detail). The single normative answer for this intent."""
    intent = (intent or "").strip().lower()
    if intent not in ALL_INTENTS:
        return NO_SYNC, "unknown intent=%r (legal: %s)" % (intent, "/".join(sorted(ALL_INTENTS)))
    if not is_repo(worktree):
        return NO_REPO, "not a git worktree"

    state = cs.load(worktree)
    has_index = index_present(worktree)
    initialized = init_done(state)
    dirty = bool(state.get("graph_dirty"))

    # -- session start: init at most once, never per session (contract §6.2)
    if intent == "session-start":
        if request_full_init or not has_index:
            if initialized or has_index:
                # index or init record already exists → re-init is never legal
                dec = FULL_INIT_FORBIDDEN if (request_full_init or initialized) else NO_SYNC
                if not has_index and initialized:
                    return FULL_INIT_FORBIDDEN, (
                        "index absent but init record present (initialized_at=%s) — an index "
                        "rebuild requires explicit authorization (contract §6.2 CORRUPT/"
                        "VERSION_INCOMPATIBLE), never a session-start default"
                        % state.get("graph_init", {}).get("initialized_at", ""))
                return dec, ("already initialized (initialized_at=%s head=%s); incremental sync "
                             "only, never a full re-init"
                             % (state.get("graph_init", {}).get("initialized_at", ""),
                                state.get("graph_init", {}).get("head", "")))
            return INIT_ONCE, ("no index, no init record → full init allowed EXACTLY ONCE; "
                               "run record-init immediately after")
        if state.get("last_sync_failed"):
            return SYNC_FAILED_DEFERRED, ("previous sync failed; retry incremental sync — "
                                          "failure never escalates to full init")
        return (INCREMENTAL_SYNC_ONCE if dirty else NO_SYNC), \
            ("graph_dirty=%s last_sync_head=%s" % ("YES" if dirty else "NO",
                                                   state.get("last_sync_head", "")))

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
            if not isinstance(state.get("grounding_receipt"), dict):
                return GROUNDING_REQUIRED, ("CODEGRAPH_GROUNDING_REQUIRED risk=%s (guard module "
                                            "unavailable; conservative)" % risk_u)

        br = state.get("blast_radius")
        if not isinstance(br, dict) or not br.get("files") or not br.get("base"):
            return BLAST_RADIUS_REQUIRED, ("no blast radius on record — run `blast-radius --base "
                                           "<BASE_SHA>` before the write")
        if br.get("mode") == "UNRESOLVED":
            return BLAST_RADIUS_REQUIRED, "blast radius UNRESOLVED; recompute before the write"
        if br.get("head") and head_sha(worktree) and br.get("head") != head_sha(worktree):
            return BLAST_RADIUS_REQUIRED, ("blast radius computed at head=%s, current head=%s — "
                                           "recompute (incremental, not a full init)"
                                           % (br.get("head"), head_sha(worktree)))
        if file_path:
            rel = norm_rel(worktree, file_path)
            if rel not in set(br.get("files") or []):
                if is_tracked(worktree, rel):
                    return BLAST_RADIUS_EXPANSION_REQUIRED, \
                        ("%s is tracked but outside the computed blast radius (%d files); "
                         "recompute blast radius before widening the edit surface"
                         % (rel, br.get("count", 0)))
                return ALLOW_WRITE, "new (untracked) file %s — outside blast radius by definition" % rel
        return ALLOW_WRITE, ("grounding + blast radius satisfied TICKET=%s files=%d"
                             % (state.get("grounding_receipt", {}).get("TICKET", ""),
                                br.get("count", 0)))

    # -- after editing: mark dirty only (contract §6.6 — never a per-edit sync)
    if intent == "post-edit":
        return MARK_DIRTY, "dirty flag set; sync deferred to query/review/handoff/stop"

    # -- query / review / blast-radius / handoff / stop: JIT sync once (§6.6)
    if not has_index and not initialized:
        return INIT_ONCE, "no index and no init record → init once, then incremental"
    if state.get("last_sync_failed"):
        return SYNC_FAILED_DEFERRED, ("sync previously failed; retry incremental sync — never "
                                      "escalate to full init")
    if dirty:
        return INCREMENTAL_SYNC_ONCE, "graph_dirty=YES → sync once, then mark-graph-synced"
    return NO_SYNC, "graph clean at head=%s" % (state.get("last_sync_head", "") or head_sha(worktree))


# --- invariants ---------------------------------------------------------------

def verify(worktree):
    """Mechanical invariant check (contract §6.7). Returns (ok, findings)."""
    findings = []
    state = cs.load(worktree)
    initialized = init_done(state)

    # LC-INV1  once initialized, no intent may ever yield INIT_ONCE again
    for intent in sorted(ALL_INTENTS):
        dec, _ = decide(intent, worktree, risk=LOW, file_path="", request_full_init=True)
        if initialized and dec == INIT_ONCE:
            findings.append("LC-INV1 intent=%s returned INIT_ONCE despite init record" % intent)
    # LC-INV2  session-start on an initialized repo is never INIT_ONCE
    if initialized:
        dec, _ = decide("session-start", worktree)
        if dec == INIT_ONCE:
            findings.append("LC-INV2 session-start returned INIT_ONCE on initialized repo")
    # LC-INV3  a failed sync never degrades into a full init
    if state.get("last_sync_failed") and (index_present(worktree) or initialized):
        for intent in sorted(SYNC_INTENTS):
            dec, _ = decide(intent, worktree)
            if dec == INIT_ONCE:
                findings.append("LC-INV3 intent=%s fell back to INIT_ONCE after sync failure" % intent)
    # LC-INV4  dirty ⇒ the next sync-intent decision is INCREMENTAL_SYNC_ONCE
    if state.get("graph_dirty") and not state.get("last_sync_failed") \
            and (index_present(worktree) or initialized):
        for intent in sorted(SYNC_INTENTS):
            dec, _ = decide(intent, worktree)
            if dec != INCREMENTAL_SYNC_ONCE:
                findings.append("LC-INV4 intent=%s returned %s while dirty" % (intent, dec))
    # LC-INV5  decisions are drawn from the closed enum
    for intent in sorted(ALL_INTENTS):
        dec, _ = decide(intent, worktree, risk="HIGH", file_path="src/app.py")
        if dec not in DECISIONS:
            findings.append("LC-INV5 intent=%s produced non-enum decision %r" % (intent, dec))
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
                             request_full_init=req_full)
        out("CODEGRAPH_LIFECYCLE_DECISION=%s INTENT=%s %s" % (dec, intent.lower(), detail))
        return 0

    if cmd == "record-init":
        state = cs.load(worktree)
        state["graph_init"] = {
            "initialized_at": cs.now_utc(),
            "head": flag(args, "--head") or head_sha(worktree),
            "worktree": os.path.realpath(worktree),
            "mode": flag(args, "--mode", "full"),
        }
        state["last_sync_failed"] = False
        cs.save(worktree, state)
        out("GRAPH_INIT_RECORDED head=%s mode=%s (full init will now be FORBIDDEN)"
            % (state["graph_init"]["head"], state["graph_init"]["mode"]))
        return 0

    if cmd == "blast-radius":
        base = flag(args, "--base", "")
        impact_files = None
        targets = [a for i, a in enumerate(args)
                   if a == "--target" and i + 1 < len(args) for a in [args[i + 1]]]
        targets = [norm_rel(worktree, t) for t in targets]
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
        out("BLAST_RADIUS=RECORDED mode=%s base=%s count=%d" % (rec["mode"], rec["base"], rec["count"]))
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
