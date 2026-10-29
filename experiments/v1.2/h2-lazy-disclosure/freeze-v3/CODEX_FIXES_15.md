# Freeze v2 — pilot #10 at 8850187: F45 (fix plan T43)

Implementer: opencode (deepseek-v4.1-flash via the implementation launcher). Ground rules and NEVER
TOUCH list of CODEX_PLAN.md §0 bind; write scope unchanged. Runs in parallel with T42 (run_h2r2.py)
on the parallel branch; touch ONLY access_audit.py, its fixtures and tests (own class).

Accepted at 8850187 (Claude): independent parallel gates ALL PASS (11 experiment modules / 486).

## Finding

```text
F45 P1  HEREDOC BODIES ARE JUDGED AS SHELL PATHS. Live pilot #10 (8850187, h2r3-f01-c, 81 tool
        calls, worker workdir handling now correct) ended INVALID with two PATH_OUTSIDE_RUN hits
        for the path '/': the worker ran `cd <run>/repo && <PY> - <<'PY' ... PY` and the Python
        program in the heredoc body (e.g. a division `a / b`) was tokenised as shell words. A
        heredoc body is stdin data for the command, not shell syntax; what that program does with
        files is a dynamic construct, enforced by the sandbox exactly like `python -c`.
```

## T43 — heredoc bodies are data (one commit, speed-rule gate, no re-pin)

1. Before tokenising a shell command, cut every heredoc body (the lines after a `<<WORD`,
   `<<-WORD`, `<<'WORD'` or `<<"WORD"` operator up to the line holding exactly WORD, tabs stripped
   for `<<-`). The command line that carries the operator (command words, arguments, redirect
   targets such as `cat <<EOF > /outside/x`) is judged exactly as now; the body is not.
2. A heredoc body fed to an interpreter (python/python3/<PY>/node/ruby/perl/sh/bash/zsh, including
   `<PY> -`) is recorded in `unresolved_constructs` as HEREDOC_PROGRAM (evidence, never a verdict),
   like INLINE_PROGRAM for `-c`.
3. Tests: a sanitised fixture derived from the real pilot #10 stream (read-only; path given at
   hand-off) gives PASS with HEREDOC_PROGRAM evidence; `cat <<EOF > /outside/x` and
   `cat /outside/x <<EOF` stay INVALID; a body containing '/' or '../../x' is not a hit; every
   existing pilot fixture still PASS.
Gate: ruff, governance, public release, the freeze-v3 test module only; manifest-pin failures caused
only by the changed access_audit.py are expected and named in CODEX_REPORT (re-pin happens after
the merge).
