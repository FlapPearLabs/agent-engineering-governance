# Freeze v2 — live pilot #5 at T32 (efc46fc): F26–F29 (fix plan T36a, T36b, T37)

Implementer: opencode (deepseek-v4.1-flash, failover per the implementation launcher). The ground
rules and NEVER TOUCH list of CODEX_PLAN.md §0 bind; write scope unchanged. T36a and T36b run in
parallel on two branches (disjoint source files); T37 re-pins once after both are merged.

Accepted at efc46fc (Claude, live pilot #5, clean clone, no patches): F22 preflight PASS with a
per-home service port; F23 the real reachability probe ran; F24 the CONTRACT states
EXPECTED_HEAD = the delivered neutral head and the worker's S0 passed; the worker then fixed f01 —
mechanical ACCEPT (oracle FAIL->PASS in both spellings, scope OK, 69 tool calls, 15 min).
The run still ended INVALID: both access-audit hits are false positives (F27).

## Findings

```text
F26 P1  NETWORK EGRESS IS OPEN AND THE ANSWERS ARE PUBLIC. The governance repository is public on
        GitHub and its history holds every candidate fix. The sandbox confines files, not the
        network: inside it `curl https://github.com` returned 200. A worker that builds a URL
        dynamically (the F16 class) can fetch the answer and the static audit cannot see it.
F27 P1  ACCESS-AUDIT FALSE POSITIVES INVALIDATE A GENUINE RUN. Pilot #5 hits, both inside the run:
        (a) GIT_REMOTE_REPOSITORY for `git clone -q --no-hardlinks repo .tmp/h2-baseline-git`
            (source and target are the run's own repo/ and .tmp/);
        (b) PATH_OUTSIDE_RUN for `T=../.tmp/probe` after `cd <run>/repo` — the assignment value was
            resolved against the run dir instead of the directory the preceding `cd` set
            (`<run>/repo/../.tmp/probe` = `<run>/.tmp/probe`, inside).
F28 P3  macOS `mktemp -d` WITHOUT A TEMPLATE IGNORES TMPDIR (it uses the per-user confstr temp dir
        under /var/folders, which the sandbox denies). Measured: `TMPDIR=<x> mktemp -d` still
        returns /var/folders/... . Both arms are affected identically; the worker adapted. Disclose,
        do not open /var/folders.
F29 P3  sandbox_denied counts a tool output that merely CONTAINS "not permitted" (a read of a JSON
        schema file was recorded). Evidence-only, but wrong.
```

## Measured facts for F26 (Claude, opencode 2.0.25, sandbox-exec)

- opencode honours HTTPS_PROXY/HTTP_PROXY. The provider needs exactly two hosts:
  `opencode.ai:443` and `models.opencode.ai:443` (observed CONNECT targets).
- `opencode run --standalone` talks to its own server over an EPHEMERAL loopback port, so a
  sandbox that allows only the proxy port breaks it ("Transport: Was there a typo in the url or
  port?"). Working layout, verified end to end under the sandbox with a tool call:
  `opencode serve --hostname 127.0.0.1 --port <P>` and
  `opencode run --server http://127.0.0.1:<P> --auto --format json -m <model> <prompt>`, both with
  the same `OPENCODE_SERVER_PASSWORD=<random per launch>` and
  `NO_PROXY=no_proxy=127.0.0.1,localhost`, both inside the same rendered profile with:
    (deny network-outbound)
    (allow network-outbound (remote ip "localhost:<proxy port>") (remote ip "localhost:<P>"))
    (allow network-outbound (remote unix-socket))
    (deny network-bind)
    (allow network-bind (local ip "localhost:<P>"))
- Under that profile: direct `curl --noproxy '*' https://github.com` fails to connect, proxied curl
  gets 403 from the allowlist proxy, `git ls-remote https://github.com/...` fails, and loopback to
  any other local port (e.g. another opencode service) fails.

## T36a — access audit (F27, F29) — branch experiment/v1.2-h2-freeze-v2-par, access_audit.py + tests

1. git clone/fetch/pull: a source that resolves (after `cd`/`-C`) INSIDE the run dir or the temp
   allow-list is not an escape; a URL, a `host:path` scp form, or a path outside stays a hit.
2. Every path-shaped token, INCLUDING the value of a `NAME=value` assignment, resolves against the
   working directory established by the preceding `cd` in the same command (the F13 base), not the
   run dir.
3. sandbox_denied records an entry only when the tool output contains the EPERM text TOGETHER with
   a path outside the launch dir in the same error line (e.g. `<path>: Operation not permitted`,
   `PermissionError: ... '<path>'`); a file read whose content happens to contain the phrase is not
   an entry.
4. Keep every existing refusal. Tests: the two pilot #5 commands (sanitised fixture derived from the
   real stream, as the F10 rule requires) PASS; mutations still INVALID: `git clone
   https://github.com/x/y`, `git clone ../../other-repo`, `git clone host:repo`, `T=../../x; cat $T`
   after `cd repo`, `cd repo && cat ../../outside`; a read whose content says "Operation not
   permitted" is not sandbox_denied; a real EPERM line naming an outside path is.
Gate: speed rule (ruff, governance, public release, the freeze-v2 test module only; no re-pin).

## T36b — network egress allowlist (F26, F28) — main branch, after T33

1. New frozen module `egress_v2.py`: a CONNECT-only HTTPS proxy bound to 127.0.0.1 on a free port,
   started by the driver OUTSIDE the sandbox for every confined launch (worker, auditor, each
   reachability probe), allowlist = frozen constant `EGRESS_ALLOW = ("opencode.ai",
   "models.opencode.ai")` with port 443 only; non-CONNECT requests 403; every request logged to
   `<stream dir>/egress.jsonl` (time, host, port, ALLOW/DENY). Stopped after the launch.
2. Launch layout per confined launch: `opencode serve --hostname 127.0.0.1 --port <P>` inside the
   sandbox (P chosen free per launch, bounded collision retry like F22), then the frozen run
   command becomes `opencode run --server http://127.0.0.1:<P> --auto --format json -m <model>
   <prompt>`; a random per-launch OPENCODE_SERVER_PASSWORD (never logged); HTTPS_PROXY/HTTP_PROXY
   (both cases) = the proxy; NO_PROXY/no_proxy = 127.0.0.1,localhost. The serve process is killed
   with the launch's process group. WORKER_COMMAND/argv records reflect the new layout.
3. The sandbox template gains the network rules above (proxy port and P rendered per launch).
4. Confinement self-test gains: a direct TCP connect to an outside host (e.g. github.com:443) must
   fail, and a proxied CONNECT to a non-allowlisted host must be refused (proxy 403 logged);
   otherwise BLOCKED:SANDBOX_NOT_CONFINING.
5. Evidence: access audit gains `egress_denied` (DENY lines of egress.jsonl); like sandbox_denied it
   is reported per run and never changes a verdict (nothing crossed). protocol-v2 §4 and README
   record F26–F28, the allowlist, the server layout and the mktemp disclosure (F28).
Tests (no model): the proxy allows only the allowlist and logs; under the real sandbox (skipUnless
darwin) a direct connect to an outside host fails, loopback to a non-allowed port fails, and a
proxied non-allowlisted CONNECT gets 403; the rendered profile contains the rules with the right
ports; the worker argv uses --server with the per-launch port; a stub server + stub client pair
works end to end through the real sandbox with the per-launch password.
Gate: speed rule (no re-pin).

## T37 — merge, re-pin, full gates, report

Merge refs/heads/experiment/v1.2-h2-freeze-v2-par (T36a) into the main branch keeping both
sides; regenerate run plan / manifest / anchors / literals with the build programs; append a
T36–T37 section to CODEX_REPORT.md; run ALL gates once; commit only if all pass.
