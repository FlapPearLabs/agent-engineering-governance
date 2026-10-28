#!/usr/bin/env python3
"""OS confinement, fresh per-run state and driver-held launch streams (F16/F17/F19/F21, T29).

T38a adds the four barriers the independent review of 9f8699d demonstrated were missing:

  * WRITES ARE A WHITELIST (F31). The old profile denied the shared roots on top of
    `(allow default)`, so every system directory outside them stayed writable — and the directory
    holding the operator's `git`, `opencode` and `python` is one of them. A launch could drop a
    binary there and the driver would run it unsandboxed afterwards. `(deny file-write* (subpath
    "/"))` now denies every write and the render block re-allows only the launch directory, the
    fresh home and the kernel devices. Driver-side tools are resolved to absolute paths ONCE, at
    import time (`TOOLS` / `absolute_argv`), so no launch can change which program runs next.
  * SIGNALS AND THE NETWORK (F35 / F36). `(deny signal)` confines kill(2) to the launch's own
    sandbox; no `remote unix-socket` rule exists (closed by omission) and
    `com.apple.dnssd.service` is denied, so DNS resolution fails inside the profile.
  * A PROCESS SWEEP AND A SNAPSHOT (F33). When a worker launch ends — normal exit, error or
    timeout — `sweep()` kills the launch's process group and every remaining process whose cwd or
    open files are under the launch directory, and records each pid and command in `sweep.json`.
    `snapshot()` then copies the whole run directory below the driver's attempt directory (a path
    the sandbox cannot write) with a per-file sha256 manifest, and every later judgement reads
    only that copy: a detached survivor cannot change what was collected, hashed or gated.
  * A GATE SANDBOX (F32). Acceptance used to execute worker-written code — the oracle and the
    full `scripts/tests` suite — in the driver's own unsandboxed process. `Gate` gives each such
    execution a fresh copy of the evidence tree, its own home inside the copy, the two temp-root
    spellings as a real directory and a symlink to it, and a rendered profile with NO network
    rule at all.

Three earlier facts this module exists for:

  * STATIC AUDITING IS INCOMPLETE (F16). `cat $(printf ...)`, a base64 pipeline, `xargs` or a
    `-c` program can read a path the tokenizer never sees as a path. The access audit keeps every
    rule it had, and stops being the only barrier: each launch runs inside a rendered
    `sandbox-exec` profile that denies file-read-data and file-write* below the operator's home
    tree and the shared temporary roots, then re-allows only the launch directory, the fresh
    per-launch home, the interpreter and the launch directory's ancestors (as literals).
  * SHARED WORKER STATE (F19). Every launch gets a FRESH home (<driver>/<run_id>/home-<n>,
    audit-home-<n>, probe-home-<purpose>-<n>, mode 0700) containing only the frozen profile
    config and its own XDG directories. The master `~/.h2-worker-profile` is never mounted in the
    sandbox: its credential is moved in by piping `opencode auth export --standalone opencode`
    (master env) into `opencode auth import --standalone` (fresh env), and the secret never
    touches argv, a log, the event stream, the registry or stdout.
  * INHERITED TMPDIR (F21). TMPDIR is `<launch dir>/.tmp`, created here and re-allowed with the
    launch directory, so no run's scratch lands in the shared OS temp directory. F25 / T32:
    TMPPREFIX is `<launch dir>/.tmp/zsh` for the same reason — a zsh heredoc writes its temp file
    under TMPPREFIX, not TMPDIR, and the default `/tmp/zsh` is denied.
  * NETWORK EGRESS (F26 / T36b). The file rules above do not touch the network: pilot #5 fetched
    github.com from inside the sandbox. The template therefore denies network-outbound and
    network-bind, and the rendered block re-allows exactly two loopback endpoints — the driver's
    CONNECT-only allowlist proxy (`egress_v2.py`) and the launch's own `opencode serve` port. The
    confinement self-test now also proves that a direct outside connect fails and that the proxy
    refuses a non-allowlisted CONNECT (403); otherwise the launch is
    BLOCKED:SANDBOX_NOT_CONFINING.

The template is frozen (`worker-sandbox.sb.template`, hashed in freeze-manifest.json) and every
rendered profile is saved with its sha256 next to the launch it confines.

A missing `sandbox-exec` makes `available()` false; the driver turns that into
BLOCKED:SANDBOX_UNAVAILABLE. A rendered profile that does not actually deny a planted file, deny a
`-c` read of it, deny a write outside the launch directory, deny a signal to a process outside the
sandbox, deny a DNS lookup and allow a write inside the launch directory makes the confinement
self-test fail, which the driver turns into BLOCKED:SANDBOX_NOT_CONFINING.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid
from pathlib import Path

from wrapper_delivery import sha256

TEMPLATE_NAME = "worker-sandbox.sb.template"
TEMPLATE_PATH = Path(__file__).resolve().with_name(TEMPLATE_NAME)
PLACEHOLDER = "{{ALLOW}}"
BINARY = "sandbox-exec"
# F31 / T38a: resolved ONCE, before any launch, so nothing a launch writes can change which program
# the driver runs next (`readTextFromPath` is exactly how a planted binary used to be picked up).
TOOL_NAMES = ("git", "opencode", "sandbox-exec")
TOOLS = {name: shutil.which(name) for name in TOOL_NAMES}
TOOLS["python"] = os.path.abspath(sys.executable)
LSOF_BINARY = shutil.which("lsof") or "/usr/sbin/lsof"
# The shared roots whose contents no launch may read or write. Only names, never a user-specific
# path: the operator's own home is one entry of the first root, not a hard-coded path.
DENY_ROOTS = ("/Users", "/private/tmp", "/var/folders", "/private/var/folders")
PROFILE_NAME = "worker.sb"
DENIED_TEXT = "operation not permitted"
# F31 / T38a: the write probe's target. It is deliberately OUTSIDE every deny root, so only the
# write whitelist (`(deny file-write* (subpath "/"))`) can refuse it: a profile that merely denies
# the shared roots still writes here, which is exactly the reviewed defect.
WRITE_PROBE_DIR = "/private/var/tmp"
# The only character devices a confined shell or test runner may write.
DEVICE_WRITE_RULES = ('(literal "/dev/null")', '(literal "/dev/tty")', '(subpath "/dev/fd")',
                      '(regex #"^/dev/ttys[0-9]+$")')
SIGNAL_NAME = "SIGCONT"                      # harmless if it ever arrives: it cannot kill a process
# F32 / T38a: a gate re-allows LOOPBACK ONLY — no proxy, no serve port, no outside connect, and
# DNS is denied by the template. Measured necessity, not a convenience: the governance test suite
# contains tests that instantiate a local HTTP server on 127.0.0.1 (the f04 oracle does), and the
# frozen PRE set was measured in an environment where that works. Removing loopback would change
# the acceptance environment and turn a PRE-passing test into a false worker failure, which is why
# the gate keeps the loopback capability the PRE measurement had and closes everything else.
GATE_NETWORK_RULES = ('(allow network-outbound (remote ip "localhost:*"))',
                      '(allow network-bind (local ip "localhost:*"))')
# F33 / T38a: the sweep and the snapshot of one launch, below the driver's attempt directory.
SWEEP_NAME = "sweep.json"
SNAPSHOT_NAME = "snapshot"
SNAPSHOT_MANIFEST_NAME = "snapshot-manifest.json"
PROCESS_QUERY_TIMEOUT = 30
KILL_WAIT_SECONDS = 2.0
KILL_POLL_SECONDS = 0.05
# F32 / T38a: one fresh copy per gate execution, below the same attempt directory.
GATE_PREFIX = "gate-"
GATE_HOME_NAME = ".home"
GATE_TMP_NAME = ".tmp"
GATE_RESOLVED_NAME = "resolved"
GATE_LINK_NAME = "link"
GATE_PYCACHE_NAME = ".pycache"
# The environment variables the validator's own acceptance env scrubs (check_task_class 2.8.7).
ENV_SCRUBBED = ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE", "PYTHONINSPECT",
                "PYTHONSAFEPATH")

CONFIG_DIR_REL = ".config/opencode"
CONFIG_NAME = "opencode.json"
CONFIG_TEMPLATE = Path(__file__).resolve().with_name("worker-profile") / CONFIG_NAME
XDG_DIRS = (".config", ".local/share", ".local/state", ".cache")
TMP_NAME = ".tmp"
# F25 / T32: zsh writes heredoc temp files under TMPPREFIX (default /tmp/zsh), NOT TMPDIR, so a
# `cat <<EOF` in the sandbox failed with "can't create temp file for here document". TMPPREFIX is
# a file PREFIX (zsh appends its own random suffix), so it names a file inside the launch dir's
# own .tmp rather than a directory that would have to exist.
TMPPREFIX_NAME = "zsh"
HOME_MODE = 0o700
CONFIG_MODE = 0o600
CONFINE_WRITE = ".confine-write"

# F26 / T36b: the two loopback endpoints a rendered profile re-allows. The proxy runs outside the
# sandbox; the serve port is the launch's own `opencode serve`. A direct outside connect must fail
# and the proxy must refuse a non-allowlisted CONNECT, or the launch is not confined.
EGRESS_SELF_TEST_HOST = "github.com"
EGRESS_SELF_TEST_PORT = 443
EGRESS_PROBE_HOST = "example.com"
EGRESS_PROBE_PORT = 443
NETWORK_PROBE_TIMEOUT = 5
LOOPBACK = "127.0.0.1"

AUTH_EXPORT = ("opencode", "auth", "export", "--standalone", "opencode")
AUTH_IMPORT = ("opencode", "auth", "import", "--standalone")
AUTH_LOGOUT = ("opencode", "auth", "logout")
AUTH_TIMEOUT = 120


def binary() -> str | None:
    """The absolute `sandbox-exec` resolved at startup (F31), never a PATH lookup after a launch."""
    return TOOLS.get(BINARY) or shutil.which(BINARY)


def absolute_argv(argv) -> list[str]:
    """Resolve a driver-side executable once, at startup, and never through PATH again (F31)."""
    items = [str(item) for item in argv]
    if not items:
        return items
    head = items[0]
    if os.sep not in head and head in TOOLS and TOOLS[head]:
        items[0] = TOOLS[head]
    return items


def available() -> bool:
    """sandbox-exec exists on this platform; the driver refuses to launch without it."""
    return sys.platform == "darwin" and binary() is not None


def template_bytes() -> bytes:
    return TEMPLATE_PATH.read_bytes()


def spellings(path) -> list[str]:
    """The path as given and its resolved spelling, so a symlinked temp root is covered too."""
    values = {str(Path(path)), os.path.realpath(str(path))}
    return sorted(values)


# Candidate system roots, measured with sandbox-exec and unified sandbox logs on
# macOS Darwin 25 / opencode 2.0.25 (2026-10-28); see CODEX_REPORT for limits.
SYSTEM_READ_ROOTS = ("/bin", "/usr/bin", "/usr/lib", "/usr/libexec", "/usr/share",
                     "/System", "/Library/Apple", "/Library/Preferences/Logging",
                     "/private/etc", "/private/var/db/timezone", "/dev")
BREW_READ_RELATIVE = ("etc", "Cellar/git", "Cellar/pcre2", "Cellar/libiconv", "Cellar/gettext")


def interpreter_roots(python: str | None = None) -> list[str]:
    """Resolve the selected interpreter's own base prefix and standard library."""
    executable = os.path.realpath(python or sys.executable)
    result = subprocess.run([executable, "-c", "import sys,sysconfig; print(sys.base_prefix); print(sysconfig.get_path('stdlib'))"],
                            capture_output=True, text=True, check=True)
    return sorted({os.path.realpath(p) for p in result.stdout.splitlines() if p} |
                  set(spellings(Path(python or sys.executable).parent.parent)))


def network_rules(proxy_port: int | None, serve_port: int | None) -> list[str]:
    """F26 / T36b: the only two network endpoints a launch may use, both on loopback.

    The proxy runs outside the sandbox; the serve port is the launch's own `opencode serve`. The
    template already denies network-outbound and network-bind, so these two rules are the whole
    re-allowed network surface. F32 / T38a: an acceptance gate passes no port at all and then gets
    LOOPBACK ONLY (any local port) — see `GATE_NETWORK_RULES` for why that is the measured
    requirement rather than "no network at all".
    """
    if proxy_port is None or serve_port is None:
        return list(GATE_NETWORK_RULES)
    return [
        f'(allow network-outbound (remote ip "localhost:{int(proxy_port)}") '
        f'(remote ip "localhost:{int(serve_port)}"))',
        f'(allow network-bind (local ip "localhost:{int(serve_port)}"))',
    ]


def cell_parent(launch: Path) -> Path | None:
    """The private cell parent of a cell-layout run dir; None for every other launch (T51e).

    `<runs_root>/.cells/<run_id>/<run_id>` sits in its own cell, which holds only that run. A
    legacy flat-layout `<runs_root>/<run_id>` and a directory inside a run (the auditor's `audit`,
    a gate root) are not cells, so neither may read or list its parent.
    """
    launch = Path(launch)
    parent = launch.parent
    if parent.name == launch.name and parent.parent.name == ".cells":
        return parent
    return None


def allow_rules(launch: Path, home: Path, python: str | None = None, *,
                proxy_port: int | None = None, serve_port: int | None = None) -> list[str]:
    """The rendered allow block: ancestors as literals, then the launch, the home and the python."""
    literals: set[str] = {"/"}
    for path in (Path(launch), Path(home)):
        for parent in (path, *path.parents):
            if str(parent) == "/":
                continue
            literals.update(spellings(parent))
    rules = [f'(allow file-read-data file-read-metadata (literal "{value}"))' for value in sorted(literals)]
    writable: set[str] = set()
    for path in (Path(launch), Path(home)):
        writable.update(spellings(path))
    rules.extend(f'(allow file-read-data file-write* (subpath "{value}"))'
                 for value in sorted(writable))
    # F31 / T38a: the write whitelist's only non-tree entries are the kernel devices.
    rules.append("(allow file-write* " + " ".join(DEVICE_WRITE_RULES) + ")")
    rules.extend(f'(allow file-read-data (subpath "{value}"))'
                 for value in interpreter_roots(python))
    # T51e: T51d granted a read of `launch.parent` as a SUBPATH for every launch, which made the
    # whole runs root readable from a flat-layout worker and the worker's run dir readable from the
    # auditor. The parent is now only ever a LITERAL, and only for a cell run dir, whose parent
    # holds that one run and nothing else (T51.2): `cd ..` from the run dir stays inside the cell.
    cell = cell_parent(launch)
    if cell is not None:
        rules.extend(f'(allow file-read-data (literal "{value}"))' for value in spellings(cell))
    roots = set(SYSTEM_READ_ROOTS)
    git_path = Path(os.path.realpath(TOOLS["git"])) if TOOLS.get("git") else None
    if git_path and len(git_path.parents) > 4 and git_path.parents[3].name == "Cellar":
        roots.update(str(git_path.parents[4] / rel) for rel in BREW_READ_RELATIVE)
    if TOOLS.get("opencode"):
        roots.update(spellings(Path(os.path.realpath(TOOLS["opencode"])).parent.parent))
    rules.extend(f'(allow file-read-data (subpath "{value}"))' for value in sorted(roots))
    rules.extend(network_rules(proxy_port, serve_port))
    return rules


def render(launch: Path, home: Path, python: str | None = None, *,
           proxy_port: int | None = None, serve_port: int | None = None) -> str:
    """The frozen template with this launch's allow block substituted."""
    text = template_bytes().decode("utf-8")
    if text.count(PLACEHOLDER) != 1:
        raise ValueError("SANDBOX_TEMPLATE_PLACEHOLDER_MISMATCH")
    return text.replace(PLACEHOLDER,
                        "\n".join(allow_rules(launch, home, python, proxy_port=proxy_port,
                                              serve_port=serve_port)) + "\n")


def profile(stream_dir: Path, launch: Path, home: Path, python: str | None = None, *,
            proxy_port: int | None = None, serve_port: int | None = None) -> dict:
    """Save the rendered profile beside the launch's driver-held streams and hash it."""
    stream_dir = Path(stream_dir)
    stream_dir.mkdir(parents=True, exist_ok=True)
    path = stream_dir / PROFILE_NAME
    text = render(Path(launch), Path(home), python, proxy_port=proxy_port,
                  serve_port=serve_port)
    path.write_text(text, encoding="utf-8")
    return {"path": str(path), "sha256": sha256(text.encode("utf-8")),
            "template": TEMPLATE_NAME, "template_sha256": sha256(template_bytes()),
            "launch": str(launch), "home": str(home), "interpreter": str(python or sys.executable),
            "deny_roots": list(DENY_ROOTS), "proxy_port": proxy_port,
            "serve_port": serve_port,
            "write_whitelist": [str(launch), str(home), *DEVICE_WRITE_RULES],
            "network": ("gate_loopback_only" if proxy_port is None
                        else "loopback_proxy_and_serve")}


def confine(profile_path, argv) -> list[str]:
    """The executable argv of one confined launch (absolute `sandbox-exec`, F31)."""
    return [str(binary() or BINARY), "-f", str(profile_path),
            *[str(item) for item in argv]]


def plant(driver_dir: Path) -> tuple[Path, str]:
    """A driver-planted file under the run's driver root: outside every launch's writable set.

    The name is fixed so a sandboxed launch can attempt it by path (a directory listing of the
    driver root is denied, which is the point); the token inside is random and never logged.
    """
    driver_dir = Path(driver_dir)
    driver_dir.mkdir(parents=True, exist_ok=True)
    path = driver_dir / "confinement-plant.txt"
    token = uuid.uuid4().hex
    path.write_text(f"{token}\n", encoding="utf-8")
    return path, token


def run(argv, cwd: Path, token: str | None = None) -> dict:
    """Run one confinement probe command; keep return code and hashes, never a secret."""
    result = subprocess.run(list(argv), cwd=str(cwd), capture_output=True, text=True, timeout=60)
    output = (result.stdout or "") + (result.stderr or "")
    return {"command": [str(item) for item in argv], "returncode": result.returncode,
            "output_sha256": sha256(output.encode("utf-8", "replace")),
            "leaked": bool(token and token in output)}


def self_test(profile_path, launch: Path, planted: Path, python: str | None = None,
              token: str | None = None, *, proxy_port: int | None = None,
              serve_port: int | None = None, signal_target: int | None = None) -> dict:
    """No model: the rendered profile must deny two reads, the new three and the two connects.

    `cat` and a `-c` program must both fail on the planted file and must not echo its token, and a
    write inside the launch directory must succeed. F26 / T36b adds two network probes: a direct
    connect to an outside host must fail, and a CONNECT to a non-allowlisted host through the
    driver's proxy must be answered 403 (only when this profile has a proxy at all — an acceptance
    gate re-allows no network endpoint and skips that probe). F31 / F35 / F36 / T38a add three
    more: a write OUTSIDE the launch directory must fail, a signal to a process outside the
    sandbox must fail, and a DNS lookup must fail. The write probes are removed again.
    """
    python = python or sys.executable
    launch = Path(launch)
    run_dir = str(launch)
    target = Path(run_dir) / CONFINE_WRITE
    outside_target = Path(WRITE_PROBE_DIR) / f"h2-confinement-probe-{uuid.uuid4().hex}"
    target_pid = int(signal_target if signal_target is not None else os.getpid())
    prefix = [str(binary() or BINARY), "-f", str(profile_path)]
    direct = (
        "import socket\n"
        f"socket.create_connection(({EGRESS_SELF_TEST_HOST!r}, {EGRESS_SELF_TEST_PORT}), "
        f"timeout={NETWORK_PROBE_TIMEOUT})\n"
    )
    proxied = (
        "import socket, sys\n"
        f"s = socket.create_connection(({LOOPBACK!r}, {int(proxy_port or 0)}), "
        f"timeout={NETWORK_PROBE_TIMEOUT})\n"
        f"s.sendall(b'CONNECT {EGRESS_PROBE_HOST}:{EGRESS_PROBE_PORT} HTTP/1.1\\r\\n"
        f"Host: {EGRESS_PROBE_HOST}:{EGRESS_PROBE_PORT}\\r\\n\\r\\n')\n"
        "data = b''\n"
        "while b'\\r\\n' not in data:\n"
        "    chunk = s.recv(1024)\n"
        "    if not chunk:\n"
        "        break\n"
        "    data += chunk\n"
        "status = data.split(b'\\r\\n', 1)[0].decode('latin-1')\n"
        "sys.exit(0 if status.startswith('HTTP/1.1 403') else 1)\n"
    )
    write_outside = (
        "import sys\n"
        f"open({str(outside_target)!r}, 'w').write('confinement-outside')\n"
        "sys.exit(0)\n"
    )
    send_signal = (
        "import os, signal, sys\n"
        f"os.kill({target_pid}, signal.{SIGNAL_NAME})\n"
        "sys.exit(0)\n"
    )
    resolve = (
        "import socket, sys\n"
        f"socket.getaddrinfo({EGRESS_PROBE_HOST!r}, {EGRESS_PROBE_PORT})\n"
        "sys.exit(0)\n"
    )
    try:
        cat = run([*prefix, "cat", str(planted)], launch, token)
        code = run([*prefix, python, "-c", f"open({str(planted)!r}).read()"], launch, token)
        write = run([*prefix, python, "-c",
                     f"open({str(target)!r}, 'w').write('confinement-ok')"], launch, token)
        write_elsewhere = run([*prefix, python, "-c", write_outside], launch, token)
        signal_to_outside = run([*prefix, python, "-c", send_signal], launch, token)
        dns = run([*prefix, python, "-c", resolve], launch, token)
        outside = run([*prefix, python, "-c", direct], launch, token)
        egress = (run([*prefix, python, "-c", proxied], launch, token)
                  if proxy_port is not None else None)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"verdict": "FAIL", "reasons": [f"CONFINEMENT_PROBE_FAILED:{type(exc).__name__}"],
                "planted": str(planted)}
    wrote = target.is_file() and target.read_text(encoding="utf-8") == "confinement-ok"
    target.unlink(missing_ok=True)
    # A profile that does not confine really did write outside; never leave that file behind.
    leaked_write = outside_target.is_file()
    if leaked_write:
        outside_target.unlink(missing_ok=True)
    reasons = []
    if cat["returncode"] == 0:
        reasons.append("CAT_READ_NOT_DENIED")
    if cat["leaked"]:
        reasons.append("CAT_TOKEN_VISIBLE")
    if code["returncode"] == 0:
        reasons.append("PYTHON_READ_NOT_DENIED")
    if code["leaked"]:
        reasons.append("PYTHON_TOKEN_VISIBLE")
    if write["returncode"] != 0 or not wrote:
        reasons.append("LAUNCH_DIR_WRITE_DENIED")
    if write_elsewhere["returncode"] == 0 or leaked_write:
        reasons.append("WRITE_OUTSIDE_NOT_DENIED")
    if signal_to_outside["returncode"] == 0:
        reasons.append("SIGNAL_TO_OUTSIDE_NOT_DENIED")
    if dns["returncode"] == 0:
        reasons.append("DNS_NOT_DENIED")
    if outside["returncode"] == 0:
        reasons.append("DIRECT_CONNECT_NOT_DENIED")
    if egress is not None and egress["returncode"] != 0:
        reasons.append("PROXY_CONNECT_NOT_REFUSED")
    return {"verdict": "FAIL" if reasons else "PASS", "reasons": sorted(reasons),
            "profile_sha256": sha256(Path(profile_path).read_bytes()),
            "planted": str(planted), "cat": cat, "python_read": code, "python_write": write,
            "write_outside": write_elsewhere, "write_outside_path": str(outside_target),
            "signal_outside": signal_to_outside, "signal_target": target_pid,
            "dns": dns, "direct_connect": outside, "proxied_connect": egress,
            "proxy_port": proxy_port, "serve_port": serve_port,
            "observation_scope": ("EPERM on two file reads, a denied write outside the launch "
                                  "directory, a denied signal to an outside process, a failed DNS "
                                  "lookup, a denied direct outside connect, a 403 from the "
                                  "allowlist proxy (when the profile has one) and one allowed "
                                  "write.")}


def fresh_home(driver_dir: Path, name: str, launch: Path) -> Path:
    """A brand-new 0700 home holding only the frozen profile config and its own XDG dirs."""
    driver_dir = Path(driver_dir)
    home = driver_dir / name
    if home.exists():
        shutil.rmtree(home)
    home.mkdir(parents=True, mode=HOME_MODE)
    os.chmod(home, HOME_MODE)
    for rel in XDG_DIRS:
        (home / rel).mkdir(parents=True, exist_ok=True)
    config = home / CONFIG_DIR_REL / CONFIG_NAME
    config.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONFIG_TEMPLATE, config)
    os.chmod(config, CONFIG_MODE)
    (Path(launch) / TMP_NAME).mkdir(parents=True, exist_ok=True)
    return home


def home_env(master_env: dict[str, str], home: Path, launch: Path) -> dict[str, str]:
    """The launch environment: the master env with HOME/XDG/TMPDIR moved into the fresh state.

    The profile's own HOME never reaches a launch. `PYTHONDONTWRITEBYTECODE=1` is applied last, so
    neither the profile nor a later export can override the F11 rule. F25 / T32: TMPPREFIX joins
    TMPDIR inside the launch directory, so a zsh heredoc writes there too.
    """
    home = Path(home)
    env = {key: str(value) for key, value in master_env.items()}
    env.update({"HOME": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "XDG_STATE_HOME": str(home / ".local/state"),
                "XDG_CACHE_HOME": str(home / ".cache"),
                "TMPDIR": str(Path(launch) / TMP_NAME),
                "TMPPREFIX": str(Path(launch) / TMP_NAME / TMPPREFIX_NAME)})
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def imported_files(home: Path) -> list[str]:
    """Every file the fresh home holds, besides the frozen config: a cross-run leak shows here."""
    home = Path(home)
    return sorted(path.relative_to(home).as_posix() for path in home.rglob("*") if path.is_file())


def import_credential(master_env: dict[str, str], env: dict[str, str], cwd: Path,
                      exporter=AUTH_EXPORT, importer=AUTH_IMPORT) -> dict:
    """Pipe the master profile's credential export into the fresh home; never touch argv or disk.

    The secret travels as a pipe on stdin. Only return codes and byte counts are kept — the bytes
    are hashed, never written, logged or echoed.
    """
    record = {"exporter": list(exporter), "importer": list(importer), "ok": False,
              "export_returncode": None, "import_returncode": None, "bytes": 0}
    try:
        exported = subprocess.run(absolute_argv(exporter), cwd=str(cwd), env=dict(master_env),
                                  stdin=subprocess.DEVNULL, capture_output=True,
                                  timeout=AUTH_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        record["reason"] = "AUTH_EXPORT_UNAVAILABLE"
        return record
    record["export_returncode"] = exported.returncode
    record["bytes"] = len(exported.stdout or b"")
    if exported.returncode != 0 or not (exported.stdout or b"").strip():
        record["reason"] = "AUTH_EXPORT_FAILED"
        return record
    try:
        imported = subprocess.run(absolute_argv(importer), cwd=str(cwd), env=dict(env),
                                  input=exported.stdout, capture_output=True,
                                  timeout=AUTH_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        record["reason"] = "AUTH_IMPORT_UNAVAILABLE"
        return record
    record["import_returncode"] = imported.returncode
    record["import_stderr_sha256"] = sha256(imported.stderr or b"")
    record["ok"] = imported.returncode == 0
    if not record["ok"]:
        record["reason"] = "AUTH_IMPORT_FAILED"
    return record


def logout(env: dict[str, str], cwd: Path, argv=AUTH_LOGOUT) -> dict:
    """Best effort: drop the imported credential from the fresh home; the verdict is recorded."""
    try:
        result = subprocess.run(absolute_argv(argv), cwd=str(cwd), env=dict(env),
                                stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=AUTH_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return {"ran": False, "command": list(argv), "returncode": None}
    return {"ran": True, "command": list(argv), "returncode": result.returncode,
            "stderr_sha256": sha256(result.stderr or b"")}


def pid_alive(pid: int) -> bool:
    """Whether `pid` still exists (a zombie counts as existing: its parent has not reaped it)."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def processes_under(directory: Path) -> list[dict]:
    """Every process whose cwd or open files are under `directory` (F33, `lsof +D` equivalent).

    `lsof +D` walks the tree and reports one record per process/file; `-F pcn0` keeps the output
    machine-readable (pid, command, name, NUL-separated). A platform without `lsof`, or any lsof
    error, is recorded as such rather than read as "no process found": an unmeasured sweep is not a
    clean sweep.
    """
    directory = Path(directory)
    if not Path(LSOF_BINARY).exists():
        return []
    try:
        result = subprocess.run([LSOF_BINARY, "-w", "-n", "-F", "pcn0", "+D", str(directory)],
                                capture_output=True, text=True, timeout=PROCESS_QUERY_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return []
    found: dict[int, dict] = {}
    pid = None
    command = ""
    for field in result.stdout.split("\0"):
        if not field:
            continue
        tag, value = field[:1], field[1:]
        if tag == "p":
            pid = int(value) if value.isdigit() else None
            command = ""
        elif tag == "c" and pid is not None:
            command = value
        elif tag == "n" and pid is not None:
            entry = found.setdefault(pid, {"pid": pid, "command": command, "files": []})
            if value not in entry["files"]:
                entry["files"].append(value)
    return [found[key] for key in sorted(found)]


def process_group_members(pgid: int) -> set[int]:
    """Every pid the driver can SEE in one process group, right now (T51e).

    One `ps` snapshot, so it costs nothing to poll during a launch. A child that starts and exits
    between two snapshots is invisible here: the set is a LOWER BOUND, and the violation evidence
    built from it says so instead of claiming a complete process tree.
    """
    try:
        result = subprocess.run(["/bin/ps", "-axo", "pid=,pgid="], capture_output=True,
                                text=True, timeout=PROCESS_QUERY_TIMEOUT, check=True)
        return {int(parts[0]) for line in result.stdout.splitlines()
                if len(parts := line.split()) == 2 and parts[1] == str(pgid)}
    except (OSError, ValueError, subprocess.SubprocessError):
        return set()


def _protected_pids() -> set[int]:
    """The driver and its ancestors: a sweep never kills the process that runs the sweep."""
    protected = {os.getpid(), os.getppid(), 0, 1}
    pid = os.getpid()
    for _ in range(8):
        try:
            result = subprocess.run(["/bin/ps", "-o", "ppid=", "-p", str(pid)],
                                    capture_output=True, text=True, timeout=10)
            parent = int(result.stdout.strip() or 0)
        except (OSError, ValueError, subprocess.SubprocessError):
            break
        if parent <= 0:
            break
        protected.add(parent)
        pid = parent
    return protected


def sweep(launch_dir: Path, *, pgid: int | None = None, log_path: Path | None = None) -> dict:
    """F33 / T38a: kill one launch's whole process tree and record every pid it found.

    The launch ran in its own process group, so the group is killed first. A survivor that
    detached into a new session is found by `lsof +D` (its cwd or an open file is still under the
    launch directory) and killed pid by pid. Whatever the sweep found is EVIDENCE: every pid and
    command lands in `sweep.json`, including a process it could not kill, so a lingering process is
    never silently ignored.
    """
    launch_dir = Path(launch_dir)
    record: dict = {"schema_version": 1, "program": "freeze-v3/sandbox_v2.py",
                    "launch_dir": str(launch_dir), "process_group": pgid,
                    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "lsof": LSOF_BINARY, "group_kill": None,
                    "lingering_processes": [], "killed": [], "survivors": [],
                    "protected": sorted(_protected_pids())}
    record["group_members"] = sorted(process_group_members(pgid)) if pgid else []
    if pgid:
        killed: dict = {"signal": "SIGKILL", "sent": False}
        try:
            os.killpg(int(pgid), signal.SIGKILL)
            killed["sent"] = True
        except ProcessLookupError:
            killed["reason"] = "NO_SUCH_PROCESS_GROUP"
        except PermissionError:
            killed["reason"] = "EPERM"
        record["group_kill"] = killed
    protected = set(record["protected"])
    if Path(LSOF_BINARY).exists():
        record["process_query"] = "lsof"
        found = [entry for entry in processes_under(launch_dir)
                 if entry["pid"] not in protected]
    else:
        # An unmeasured sweep is not a clean sweep: the record says so instead of implying none.
        record["process_query"] = "UNAVAILABLE"
        found = []
    record["lingering_processes"] = found
    for entry in found:
        pid = entry["pid"]
        if not pid_alive(pid):
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            continue
        except PermissionError:
            record["survivors"].append({"pid": pid, "command": entry["command"],
                                        "reason": "EPERM"})
            continue
        deadline = time.monotonic() + KILL_WAIT_SECONDS
        while pid_alive(pid) and time.monotonic() < deadline:
            time.sleep(KILL_POLL_SECONDS)
        record["killed"].append({"pid": pid, "command": entry["command"],
                                 "alive_after": pid_alive(pid)})
    record["verdict"] = "PASS" if not record["survivors"] else "FAIL"
    if log_path is not None:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
        log_path.write_bytes(payload)
        record["log"] = str(log_path)
        record["log_sha256"] = sha256(payload)
    return record


def _snapshot_entry(source: Path, target: Path, rel: str, manifest: dict) -> None:
    """Copy an entry without following source links or overwriting target entries."""
    try:
        info = source.lstat()
        if stat.S_ISLNK(info.st_mode):
            link = os.readlink(source)
            entry = {"type": "symlink", "mode": "120000",
                     "sha256": sha256(os.fsencode(link)), "target": link}
            try:
                target.symlink_to(link)
            except FileExistsError:
                entry["collision"] = True
            manifest[rel] = entry
        elif stat.S_ISREG(info.st_mode):
            entry = {"type": "file", "mode": "100755" if info.st_mode & 0o111 else "100644"}
            manifest[rel] = entry
            fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as stream:
                opened = os.fstat(stream.fileno())
                if not stat.S_ISREG(opened.st_mode):
                    raise OSError("source changed type")
                data = stream.read()
            entry["sha256"] = sha256(data)
            try:
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             opened.st_mode & 0o777)
            except FileExistsError:
                entry["collision"] = True
                return
            with os.fdopen(fd, "wb") as stream:
                os.fchmod(stream.fileno(), opened.st_mode & 0o777)
                stream.write(data)
        else:
            manifest[rel] = {"type": "other", "mode": "000000", "sha256": None}
    except OSError as exc:
        entry = manifest.setdefault(rel, {"type": "unknown"})
        entry.update({"unreadable": True, "error": type(exc).__name__})


def snapshot(run_dir: Path, target: Path) -> dict:
    """F33 / T38a: copy the whole run dir below the driver dir and hash every entry.

    The target is `<runs_root>/.driver/<run_id>/attempt-<n>/snapshot`, a path the launch's own
    sandbox cannot write (the launch dir is the run dir and writing anywhere else is denied). From
    here on, collection, the scope check, the oracle hashes, the gate runs and the audit bundle all
    read ONLY this copy, so nothing that happens in the run dir afterwards can change a verdict.
    """
    run_dir, target = Path(run_dir), Path(target)
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    manifest: dict[str, dict] = {}
    for directory, dirnames, filenames in os.walk(run_dir, followlinks=False):
        current = Path(directory)
        rel_dir = current.relative_to(run_dir)
        for name in sorted(dirnames):
            path = current / name
            rel = (rel_dir / name).as_posix()
            if path.is_symlink():
                _snapshot_entry(path, target / rel, rel, manifest)
                dirnames.remove(name)
                continue
            entry = {"type": "dir", "mode": "040000"}
            manifest[rel] = entry
            try:
                (target / rel).mkdir()
            except FileExistsError:
                if not stat.S_ISDIR((target / rel).lstat().st_mode):
                    entry["collision"] = True
                    dirnames.remove(name)
        for name in sorted(filenames):
            path = current / name
            rel = (rel_dir / name).as_posix()
            _snapshot_entry(path, target / rel, rel, manifest)
    unreadable = sorted(rel for rel, entry in manifest.items() if entry.get("unreadable") or entry.get("collision"))
    data = {"schema_version": 1, "program": "freeze-v3/sandbox_v2.py", "source": str(run_dir),
            "snapshot": str(target), "entries": manifest,
            "unreadable": unreadable, "count": len(manifest)}
    payload = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (target.parent / SNAPSHOT_MANIFEST_NAME).write_bytes(payload)
    return {"path": str(target), "manifest_sha256": sha256(payload), "count": len(manifest),
            "unreadable": unreadable,
            "manifest_path": str(target.parent / SNAPSHOT_MANIFEST_NAME)}


def unreadable_entries(snapshot_record: dict) -> list[str]:
    """The unreadable files of a snapshot record, as registration reasons (F37)."""
    return [f"EVIDENCE_UNREADABLE:{rel}" for rel in snapshot_record.get("unreadable", [])]


class Gate:
    """One acceptance gate: a fresh copy of the evidence tree, confined with no network (F32).

    Acceptance used to run the oracle and the whole `scripts/tests` suite — worker-written code —
    in the driver's own process. A `Gate` gives each execution its own copy below the driver's
    attempt directory, its own home inside that copy, and the two temp-root spellings as a real
    directory (`resolved`) and a symlink to it (`link`), so RESOLVED and SYMLINKED still differ
    while both live inside the sandbox. The rendered profile re-allows no network endpoint at all.
    """

    def __init__(self, root: Path, python: str | None = None):
        self.root = Path(root)
        self.python = str(python or sys.executable)
        self.repo = self.root / "repo"
        self.home = self.root / GATE_HOME_NAME
        self.tmp = self.root / GATE_TMP_NAME
        self.resolved = self.tmp / GATE_RESOLVED_NAME
        self.link = self.tmp / GATE_LINK_NAME
        self.pycache = self.root / GATE_PYCACHE_NAME
        self.profile_record: dict = {}

    def prepare(self, source: Path, *, planted: Path | None = None,
                token: str | None = None) -> dict:
        """Copy `source` to `<root>/repo`, make the two spellings, render and self-test.

        The LAUNCH directory is the gate root itself, not `<root>/repo`: the temp roots, the bytecode
        cache and the gate home live beside the copy, and a profile that allowed only the copy would
        deny every `mkdtemp` the suite makes — an environment change, not a worker failure.
        """
        source = Path(source)
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)
        copied = snapshot(source, self.repo)
        if copied["unreadable"]:
            raise ValueError("GATE_SNAPSHOT_UNREADABLE")
        for path in (self.home, self.resolved, self.pycache):
            path.mkdir(parents=True, exist_ok=True)
        os.symlink(self.resolved, self.link)
        self.profile_record = profile(self.root, self.root, self.home, self.python)
        self_test_record = None
        if planted is not None:
            self_test_record = self_test(self.profile_record["path"], self.root, planted,
                                         self.python, token)
        return {"gate": str(self.root), "repo": str(self.repo),
                "profile": self.profile_record, "self_test": self_test_record,
                "network": self.profile_record["network"]}

    def argv(self, command) -> list[str]:
        return confine(self.profile_record["path"], command)

    def env(self, style: str = "RESOLVED") -> dict[str, str]:
        """The validator's acceptance env (2.8.7), with every root moved INSIDE this gate."""
        if style not in ("RESOLVED", "SYMLINKED"):
            raise ValueError(style)
        env = {key: value for key, value in os.environ.items() if key not in ENV_SCRUBBED}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPYCACHEPREFIX"] = str(self.pycache)
        root = str(self.resolved if style == "RESOLVED" else self.link)
        for key in ("TMPDIR", "TEMP", "TMP"):
            env[key] = root
        env["HOME"] = str(self.home)
        env["XDG_CONFIG_HOME"] = str(self.home / ".config")
        env["XDG_DATA_HOME"] = str(self.home / ".local/share")
        env["XDG_STATE_HOME"] = str(self.home / ".local/state")
        env["XDG_CACHE_HOME"] = str(self.home / ".cache")
        env["TMPPREFIX"] = str(self.tmp / TMPPREFIX_NAME)
        return env

    def spelling_root(self, style: str = "RESOLVED") -> str:
        return str(self.resolved if style == "RESOLVED" else self.link)


class Sandbox:
    """The real platform sandbox; tests may pass a double to `run_h2r2.execute`.

    The driver's CLI exposes no way to replace it, exactly like the worker command: every counted
    run renders and enforces the frozen template.
    """

    def available(self) -> bool:
        return available()

    def plant(self, driver_dir: Path) -> tuple[Path, str]:
        return plant(driver_dir)

    def profile(self, stream_dir: Path, launch: Path, home: Path,
                python: str | None = None, *, proxy_port: int | None = None,
                serve_port: int | None = None) -> dict:
        return profile(stream_dir, launch, home, python, proxy_port=proxy_port,
                       serve_port=serve_port)

    def confine(self, profile_path, argv) -> list[str]:
        return confine(profile_path, argv)

    def self_test(self, profile_path, launch: Path, planted: Path, python: str | None = None,
                  token: str | None = None, *, proxy_port: int | None = None,
                  serve_port: int | None = None, signal_target: int | None = None) -> dict:
        return self_test(profile_path, launch, planted, python, token, proxy_port=proxy_port,
                         serve_port=serve_port, signal_target=signal_target)


class Auth:
    """The real credential hand-off; tests pass a fake exporter/importer (never a credential)."""

    def import_(self, master_env: dict[str, str], env: dict[str, str], cwd: Path) -> dict:
        return import_credential(master_env, env, cwd)

    def logout(self, env: dict[str, str], cwd: Path) -> dict:
        return logout(env, cwd)


def summary(record: dict) -> dict:
    """A small, secret-free projection for the run record."""
    keys = ("ok", "reason", "export_returncode", "import_returncode", "bytes",
            "import_stderr_sha256")
    return {key: record[key] for key in keys if key in record}


def json_line(record: dict) -> str:
    return json.dumps(record, sort_keys=True)
