# Freeze v2 — user decision on denied out-of-run attempts (fix plan T46)

Implementer: opencode (deepseek-v4.1-flash via the implementation launcher). Ground rules and NEVER
TOUCH list of CODEX_PLAN.md §0 bind; write scope unchanged.

Accepted at 7b891c4 (Claude): F46 fixed (the f01-c stream reads as 194 events, 0 malformed); F47
fixed (the sed script is no longer a hit). Replaying the 4-run batch at bf2ca30 now leaves exactly
one hit in each of f01-c and f03-c, both worker path typos that the sandbox denies (an interpreter
path under the operator home that is not the allowed interpreter prefix; a misspelled run dir under
the shared runs root).

## Decision (user, 2026-10-27, before any counted run)

"采用 A：被沙箱拒绝的越界尝试记为证据并按臂报告，只有越界访问实际成功才判 INVALID；在第一次正式运行前写进协议。"

Rationale to record in protocol-v2 §4/§6: the static audit was the only barrier when the rule was
made (F9); since F16/F26/F31 the OS sandbox and the egress allowlist enforce confinement (verified
with the independent reviewer's own attacks). A denied attempt obtains nothing, so it cannot
contaminate a result; invalidating it only removes valid pairs (the 4-run batch lost 2 of 4 runs to
typos). Denied attempts stay visible as per-arm evidence; an asymmetry between arms is reported as a
finding in the closure.

## T46 — classify every out-of-run hit; re-pin; full gates (one commit)

1. Every access-audit hit (PATH_OUTSIDE_RUN, GIT_REMOTE_REPOSITORY, GIT_FOREIGN_REPOSITORY, and the
   other existing reasons) gets a `class`:
   - `DENIED_BY_POLICY` — the access cannot succeed under the launch's rendered sandbox profile and
     egress allowlist: the path resolves under a denied root (/Users, /private/tmp,
     /private/var/folders and their aliases) and NOT under any path that profile re-allows for that
     access type (launch dir, fresh home, interpreter prefix; for an ancestor `literal` only a
     directory listing of that exact node is allowed); or the target is a network location whose
     host is not on EGRESS_ALLOW. Decide it from the archived rendered profile of that launch and
     the frozen allowlist, never from the worker's text.
   - `POSSIBLE_SUCCESS` — any other out-of-run hit (e.g. a readable system file such as /etc/hosts
     that is not on the existing system allow-list): the access could have succeeded.
2. Verdict: DENIED_BY_POLICY hits are evidence only, recorded as `denied_attempts` (list) with their
   count; POSSIBLE_SUCCESS hits keep INVALID:OUT_OF_RUN_ACCESS exactly as now. Independently, any
   empirical breach makes the run INVALID:SANDBOX_BREACH: a read/grep/glob tool result returning
   content for a path under a denied root that the profile does not re-allow; an egress.jsonl ALLOW
   line for a host not on EGRESS_ALLOW; a failed confinement self-test that was not caught earlier.
3. Reporting: run.json and the registry line carry `denied_attempts` count; aggregate_runs.py
   reports per arm and per task the denied-attempt counts and lists, and the total per arm, in its
   output (a reported quantity, not a decision rule); the closure report discusses any asymmetry.
4. protocol-v2 §4 and §6 and README: the decision quote above, the date, the rationale, the two
   classes, the breach rule, and that this was fixed before the first counted run.
5. Tests: sanitised fixtures derived from the real f01-c and f03-c streams (read-only; paths given
   at hand-off) -> PASS with one DENIED_BY_POLICY attempt each; `cat /etc/hosts` -> INVALID
   (POSSIBLE_SUCCESS); a read of another run's file under the shared runs root -> evidence; a git
   clone of a GitHub URL -> evidence, but INVALID:SANDBOX_BREACH if the launch's egress.jsonl holds an
   ALLOW line for github.com; a read tool result that returned content for a denied path ->
   INVALID:SANDBOX_BREACH; every earlier pilot fixture still PASS; aggregate output shows per-arm
   denied-attempt counts.
6. Regenerate run plan / manifest / anchors / literals with the build programs; append a T45–T46
   section to CODEX_REPORT.md; run ALL gates of CODEX_PLAN §0 once; commit only if all pass.
