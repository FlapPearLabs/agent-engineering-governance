# Freeze v2 — 4-run parallel pilot batch at bf2ca30: F46–F47 (fix plan T45)

Implementer: opencode (deepseek-v4.1-flash via the implementation launcher). Ground rules and NEVER
TOUCH list of CODEX_PLAN.md §0 bind; write scope unchanged.

Accepted at bf2ca30 (Claude): independent parallel gates ALL PASS (11 experiment modules / 491);
F44 fixed live — run-plan started the first arms of f01, f02, f03, f04 within 10 s, in plan order;
F45 fixed — all 7 earlier real streams replay with 0 hits. Batch result: f02-v ACCEPT (audit PASS),
f04-v REJECT (audit PARTIAL), f01-c INVALID, f03-c INVALID.

## Findings

```text
F46 P1  EVENT LINES ARE SPLIT ON UNICODE LINE BOUNDARIES. h2r3-f01-c: one valid JSON event (a shell
        tool call whose command held a regex with U+2028/U+2029 and other Unicode separators) was
        split into five pieces by `str.splitlines()` in read_events (and any other reader of a
        JSONL stream), giving MALFORMED_EVENT_LINES:5 -> INVALID. JSON Lines are separated by "\n"
        only. Check every JSONL reader (driver events, audit events, registry, attempts, scheduler,
        egress logs, access_audit) and split on b"\n" / "\n" only.
F47 P2  A SCRIPT OR PATTERN ARGUMENT IS JUDGED AS A PATH. h2r3-f03-c: `sed -i '' '/^ROUTE n\/a .../d'
        .h2-telemetry.log` -> PATH_OUTSIDE_RUN for the sed script. The script/program/pattern
        operand of sed (first non-option operand, or each -e/--expression value), awk/gawk (first
        non-option operand, or -f is a path), grep/egrep/fgrep/rg (first non-option operand, or
        each -e/--regexp value; -f is a path) is not a path. Every other operand is judged as now.
```

## T45 — fix (one commit, speed-rule gate, NO re-pin: a protocol decision is pending)

1. F46 as above, with tests: a stream whose JSON line contains U+2028, U+2029, U+0085, \x0b, \x0c,
   \x1c-\x1e inside strings reads as ONE event; a genuinely truncated line is still MALFORMED.
2. F47 as above, with tests: the f03-c sed command (sanitised fixture derived from the real stream,
   read-only, path given at hand-off) has no hit for the script; `sed -i '' 's/x/y/' /outside/f`,
   `grep -e pat /outside/f`, `awk -f /outside/prog x` stay INVALID.
3. Gate: ruff, governance, public release, the freeze-v3 test module only; pin-test failures caused
   only by the changed files are expected and named in CODEX_REPORT (re-pin happens later).
