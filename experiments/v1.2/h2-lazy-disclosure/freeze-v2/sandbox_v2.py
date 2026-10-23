#!/usr/bin/env python3
"""OS confinement, fresh per-run state and driver-held launch streams (F16/F17/F19/F21, T29).

Three facts this module exists for:

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

The template is frozen (`worker-sandbox.sb.template`, hashed in freeze-manifest.json) and every
rendered profile is saved with its sha256 next to the launch it confines.

A missing `sandbox-exec` makes `available()` false; the driver turns that into
BLOCKED:SANDBOX_UNAVAILABLE. A rendered profile that does not actually deny a planted file, deny a
`-c` read of it and allow a write inside the launch directory makes the confinement self-test fail,
which the driver turns into BLOCKED:SANDBOX_NOT_CONFINING.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from wrapper_delivery import sha256

TEMPLATE_NAME = "worker-sandbox.sb.template"
TEMPLATE_PATH = Path(__file__).resolve().with_name(TEMPLATE_NAME)
PLACEHOLDER = "{{ALLOW}}"
BINARY = "sandbox-exec"
# The shared roots whose contents no launch may read or write. Only names, never a user-specific
# path: the operator's own home is one entry of the first root, not a hard-coded path.
DENY_ROOTS = ("/Users", "/private/tmp", "/var/folders", "/private/var/folders")
PROFILE_NAME = "worker.sb"
DENIED_TEXT = "operation not permitted"

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

AUTH_EXPORT = ("opencode", "auth", "export", "--standalone", "opencode")
AUTH_IMPORT = ("opencode", "auth", "import", "--standalone")
AUTH_LOGOUT = ("opencode", "auth", "logout")
AUTH_TIMEOUT = 120


def binary() -> str | None:
    return shutil.which(BINARY)


def available() -> bool:
    """sandbox-exec exists on this platform; the driver refuses to launch without it."""
    return sys.platform == "darwin" and binary() is not None


def template_bytes() -> bytes:
    return TEMPLATE_PATH.read_bytes()


def spellings(path) -> list[str]:
    """The path as given and its resolved spelling, so a symlinked temp root is covered too."""
    values = {str(Path(path)), os.path.realpath(str(path))}
    return sorted(values)


def interpreter_roots(python: str | None = None) -> list[str]:
    """The interpreter and its prefixes: the one read-only region a launch may always read."""
    executable = Path(python or sys.executable)
    roots: set[str] = set()
    for candidate in (executable, Path(os.path.realpath(str(executable)))):
        roots.add(str(candidate))
        roots.add(str(candidate.parent))
        roots.add(str(candidate.parent.parent))
    for prefix in (sys.prefix, sys.base_prefix):
        roots.add(str(Path(prefix)))
        roots.add(os.path.realpath(str(prefix)))
    return sorted(roots)


def allow_rules(launch: Path, home: Path, python: str | None = None) -> list[str]:
    """The rendered allow block: ancestors as literals, then the launch, the home and the python."""
    literals: set[str] = set()
    for path in (Path(launch), Path(home)):
        for parent in (path, *path.parents):
            if str(parent) == "/":
                continue
            literals.update(spellings(parent))
    rules = [f'(allow file-read-data (literal "{value}"))' for value in sorted(literals)]
    writable: set[str] = set()
    for path in (Path(launch), Path(home)):
        writable.update(spellings(path))
    rules.extend(f'(allow file-read-data file-write* (subpath "{value}"))'
                 for value in sorted(writable))
    rules.extend(f'(allow file-read-data (subpath "{value}"))'
                 for value in interpreter_roots(python))
    return rules


def render(launch: Path, home: Path, python: str | None = None) -> str:
    """The frozen template with this launch's allow block substituted."""
    text = template_bytes().decode("utf-8")
    if text.count(PLACEHOLDER) != 1:
        raise ValueError("SANDBOX_TEMPLATE_PLACEHOLDER_MISMATCH")
    return text.replace(PLACEHOLDER, "\n".join(allow_rules(launch, home, python)) + "\n")


def profile(stream_dir: Path, launch: Path, home: Path, python: str | None = None) -> dict:
    """Save the rendered profile beside the launch's driver-held streams and hash it."""
    stream_dir = Path(stream_dir)
    stream_dir.mkdir(parents=True, exist_ok=True)
    path = stream_dir / PROFILE_NAME
    text = render(Path(launch), Path(home), python)
    path.write_text(text, encoding="utf-8")
    return {"path": str(path), "sha256": sha256(text.encode("utf-8")),
            "template": TEMPLATE_NAME, "template_sha256": sha256(template_bytes()),
            "launch": str(launch), "home": str(home), "interpreter": str(python or sys.executable),
            "deny_roots": list(DENY_ROOTS)}


def confine(profile_path, argv) -> list[str]:
    """The executable argv of one confined launch."""
    return [BINARY, "-f", str(profile_path), *[str(item) for item in argv]]


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
              token: str | None = None) -> dict:
    """No model: the rendered profile must deny two reads and allow the launch directory.

    `cat` and a `-c` program must both fail on the planted file and must not echo its token, and a
    write inside the launch directory must succeed. The write probe is removed again.
    """
    python = python or sys.executable
    launch = Path(launch)
    run_dir = str(launch)
    target = Path(run_dir) / CONFINE_WRITE
    prefix = [BINARY, "-f", str(profile_path)]
    try:
        cat = run([*prefix, "cat", str(planted)], launch, token)
        code = run([*prefix, python, "-c", f"open({str(planted)!r}).read()"], launch, token)
        write = run([*prefix, python, "-c",
                     f"open({str(target)!r}, 'w').write('confinement-ok')"], launch, token)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"verdict": "FAIL", "reasons": [f"CONFINEMENT_PROBE_FAILED:{type(exc).__name__}"],
                "planted": str(planted)}
    wrote = target.is_file() and target.read_text(encoding="utf-8") == "confinement-ok"
    target.unlink(missing_ok=True)
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
    return {"verdict": "FAIL" if reasons else "PASS", "reasons": sorted(reasons),
            "profile_sha256": sha256(Path(profile_path).read_bytes()),
            "planted": str(planted), "cat": cat, "python_read": code, "python_write": write,
            "observation_scope": "EPERM on two reads of a driver-planted file; one allowed write."}


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
        exported = subprocess.run(list(exporter), cwd=str(cwd), env=dict(master_env),
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
        imported = subprocess.run(list(importer), cwd=str(cwd), env=dict(env),
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
        result = subprocess.run(list(argv), cwd=str(cwd), env=dict(env),
                                stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=AUTH_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return {"ran": False, "command": list(argv), "returncode": None}
    return {"ran": True, "command": list(argv), "returncode": result.returncode,
            "stderr_sha256": sha256(result.stderr or b"")}


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
                python: str | None = None) -> dict:
        return profile(stream_dir, launch, home, python)

    def confine(self, profile_path, argv) -> list[str]:
        return confine(profile_path, argv)

    def self_test(self, profile_path, launch: Path, planted: Path, python: str | None = None,
                  token: str | None = None) -> dict:
        return self_test(profile_path, launch, planted, python, token)


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
