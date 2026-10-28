# Freeze v2 — acceptance round 5 of 12b1728: F8–F9 closed; live pilot exposes F10–F13 (fix plan T24–T25)

Implementer: opencode (deepseek-v4.1-flash). The ground rules, NEVER TOUCH list and GATES of
CODEX_PLAN.md §0 still bind every task; write scope unchanged.

Accepted at 12b1728 (verified by Claude): write scope; identity; every gate green on independent
re-run (experiments 378 OK, manifest PASS). F8 closed — in a real prepared f01 run repo/ has 0
refs, `git rev-list --all` = 1 commit (B'), no remote, no alternates, the candidate object is
absent, `git log --all --grep` finds nothing, no governance path under repo/.git. F9 closed for
paths — crafted events reading the governance checkout (absolute, `../`, `~`, `git -C <other
repo>`, grep of the home dir) are all INVALID. Re-measure on the new layout: WRAPPER neutral
10/10, positive control ACCEPT 10/10.

## Live pilot (not counted; separate runs root, `run_h2r2.py run h2r3-f01-c`)

The frozen driver ran a real worker end to end in 9.3 min (preflight PASS, contract rendered,
worker report written, collect, acceptance, access audit, registry). Result: INVALID, audit
SKIPPED. Its event stream is the ground truth for the fixes below and is given at hand-off.

```text
F10 P1  REAL SHELL TOOL IS `shell`, NOT `bash`. In opencode 2.0.25's isolated profile the tool
        names are read / glob / grep / shell / write / edit (measured live; file tools use the
        input key `path`). TOOL_ALLOW and SHELL_TOOLS only know `bash`, so every shell call is
        TOOL_NOT_ALLOWED: the pilot got 25 such hits and EVERY run would be INVALID.
F11 P1  THE WORKER'S OWN TEST RUN GETS IT REJECTED. Mechanical verdict REJECT:
        WORKER_SCOPE_DENIED for scripts/tests/__pycache__/*.cpython-313.pyc (three files).
        Running the oracle as the contract instructs writes bytecode under scripts/tests/, which
        the T10 prefix rule rightly refuses. Fix the cause, not the rule: the frozen worker
        environment sets PYTHONDONTWRITEBYTECODE=1 (and the contract's commands keep `-s`), so
        no bytecode is written innocently; a .pyc that still appears under repo/ stays a
        refusal (bytecode can carry code — validator BYTECODE rule).
F12 P2  SHELL TOKENISATION. With `shell` treated as the shell tool, the pilot's
        `... && source /dev/null; <PY> -m unittest ...` yields PATH_OUTSIDE_RUN for
        `/dev/null;` (separator glued to the path). Tokenise with shell punctuation
        (e.g. shlex with punctuation_chars) before resolving paths.
F13 P2  TEMP-DIR WORK FLAGGED AS A FOREIGN REPOSITORY. The pilot ran
        `cd <run> && rm -rf <TMP>/h2-base-check && mkdir -p … && git -C repo archive HEAD |
        tar -x -C <TMP>/h2-base-check && cd <TMP>/h2-base-check && <PY> -m unittest …`
        and got GIT_FOREIGN_REPOSITORY. The git command targets the run's own repo/; the temp dir
        is allow-listed. GIT_FOREIGN_REPOSITORY must fire only when the git command's effective
        repository (after `cd` and `-C`) resolves outside the run dir AND outside the temp
        allow-list.
```

## T24 — close F10–F13

- access_audit: allow `shell` and analyse it as the shell tool (keep `bash` too); accept the
  `path` key (and any other path-carrying key you find in the real stream); shell-aware
  tokenisation (F12); the F13 rule above. Keep every existing refusal.
- run_h2r2: add PYTHONDONTWRITEBYTECODE=1 to the frozen worker environment (and the auditor's);
  record it in protocol-v2 §4/§5 and README; pin in the manifest.
- Fixtures: commit a sanitised copy of the pilot's REAL event stream (paths replaced by
  placeholders, re-expanded in the test); with T24 it must give access-audit PASS. Mutations of
  it — a read of a path outside the run, `git -C <outside repo>`, `cat ~/x`, a `../` escape —
  must each give INVALID. From now on any fixture that imitates opencode events must be derived
  from a real recorded stream, never written from imagination (that is how `bash` slipped in).
- A test that a worker env built by run_h2r2 contains PYTHONDONTWRITEBYTECODE=1 and nothing
  outside PATH, LANG, the profile exports and that variable.

## T25 — re-pin and report

Regenerate run plan / manifest / literals; append a T24–T25 section to CODEX_REPORT.md.
