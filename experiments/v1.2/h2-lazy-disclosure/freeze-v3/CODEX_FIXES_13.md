# Freeze v2 — live pilot #9 at 6db87cf: F43 (fix plan T41)

Implementer: opencode (deepseek-v4.1-flash via the implementation launcher). Ground rules and NEVER
TOUCH list of CODEX_PLAN.md §0 bind; write scope unchanged.

Accepted at 6db87cf (Claude): independent parallel gates ALL PASS (11 experiment modules / 481
tests); F42 fixed — the real event streams of pilots #4c, #5, #6, #7 and #8 (234 tool calls) replay
through the T40 audit with 0 hits, and escapes (`cd repo; cd ..; cd ..`, `cd repo && cat ../../x`,
`cd .. && cat x`, a GitHub clone) stay INVALID.

## Finding

```text
F43 P1  THE SHELL TOOL'S `workdir` IS IGNORED. opencode's shell tool input carries
        {"command": ..., "workdir": <dir>} (85 of 149 real shell calls across the pilots set it).
        The audit resolves every relative token against the run dir, so live pilot #9 (6db87cf)
        ended INVALID with four PATH_OUTSIDE_RUN hits for `>> ../.h2-telemetry.log` issued with
        workdir = <run>/repo — i.e. <run>/.h2-telemetry.log, inside the run.
        Survey of every tool input key in the real streams: read {path, offset, limit},
        shell {command, workdir}, edit {path, oldString, newString}, write {path, content};
        `workdir` is the only path-carrying key the audit does not use.
```

## T41 — fix, re-pin, full gates (one commit)

1. For a shell tool call, the starting working directory of the command is its `workdir` (resolved
   like any path token, relative values against the run dir); the `workdir` itself is judged like a
   path (outside the run and the temp allow-list -> PATH_OUTSIDE_RUN); missing `workdir` -> the run
   dir as now. The same starting directory feeds the `cd` tracking and git_hits.
2. Defensive, not yet seen live: for glob/grep-style tools, a `pattern` or `include` value that is
   an absolute path or contains a `..` segment is judged as a path against the tool's `path` (or the
   run dir).
3. Tests: a sanitised fixture derived from the real pilot #9 stream (read-only; path given at
   hand-off) gives PASS; workdir = <run>/repo with `cat ../../x` -> INVALID; workdir outside the run
   -> INVALID; workdir = <run>/repo with `>> ../.h2-telemetry.log` -> PASS; a glob pattern
   `/LOCAL_USER or `../../**` -> INVALID; every existing pilot fixture still PASS.
4. Regenerate run plan / manifest / anchors / literals with the build programs; append a T41 section
   to CODEX_REPORT.md; run ALL gates of CODEX_PLAN §0 once; commit only if all pass.
