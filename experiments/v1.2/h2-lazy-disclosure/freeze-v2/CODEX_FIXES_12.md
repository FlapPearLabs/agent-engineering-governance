# Freeze v2 — live pilot #8 at 0335de8: F42 (fix plan T40)

Implementer: opencode (deepseek-v4.1-flash via the implementation launcher). Ground rules and NEVER
TOUCH list of CODEX_PLAN.md §0 bind; write scope unchanged.

Accepted at 0335de8 (Claude): write scope and identity; independent parallel gates ALL PASS
(11 experiment modules / 478 tests, scripts 602, ruff, governance 35/35, public release 0, manifest
PASS); T38a/T38b behaviour re-checked with the reviewer's own attack scripts (system-dir writes,
outside signals, DNS / unix sockets / other loopback / public IP all denied; worker code in the
acceptance gates cannot write outside; the detached survivor is swept and the verdict comes from the
snapshot; the reviewer's aggregate scenarios give the pre-registered results).

## Finding

```text
F42 P1  CD ARGUMENT JUDGED AGAINST ITS OWN TARGET. Live pilot #8 (0335de8, h2r2-f01-c) ended
        INVALID with one access-audit hit, PATH_OUTSIDE_RUN for `..` in
        `...; cd repo && <PY> -m unittest ...; cd ..; git -C repo status ...` — the worker went back
        from repo/ to the run dir, which is inside. In shell_hits (and git_hits) the loop updates
        `cwd` when it meets the `cd` token and THEN checks the next token (the cd argument) against
        the already-updated cwd: `cd ..` from <run>/repo is judged as <run>/.. (outside). `cd repo`
        only escaped by luck (<run>/repo/repo is still inside). Every genuine run that does
        `cd repo ... cd ..` would be INVALID.
```

## T40 — fix, re-pin, full gates (one commit)

1. The argument of `cd` is judged against the working directory BEFORE that `cd` (it is then the new
   cwd for the tokens after it). Same ordering in git_hits. Keep every existing rule.
2. Tests: a sanitised fixture derived from the real pilot #8 event (read-only; path given at hand-off; placeholders
   like the existing pilot fixtures) gives PASS; `cd repo; cd ..; cd ..` (escaping the run dir),
   `cd repo && cat ../../x`, `cd .. && cat x` from the run dir stay INVALID; `cd repo; cd ..; ls`
   is PASS.
3. Regenerate run plan / manifest / anchors / literals with the build programs; append a T40
   section to CODEX_REPORT.md; run ALL gates of CODEX_PLAN §0 once; commit only if all pass.
