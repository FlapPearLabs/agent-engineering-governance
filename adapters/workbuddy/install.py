#!/usr/bin/env python3
"""INSTALL / VERIFY / ROLLBACK for the WorkBuddy git safety guard.

    python3 adapters/workbuddy/install.py install
    python3 adapters/workbuddy/install.py verify
    python3 adapters/workbuddy/install.py rollback
    python3 adapters/workbuddy/install.py status

DESIGN RULES
    * Idempotent. Running `install` twice must not duplicate the hook definition.
    * Reversible. Settings are backed up outside any repository before being touched; the
      backup path and digests are recorded so ROLLBACK is mechanical, not remembered.
    * Conservative about foreign state. A PreToolUse hook that matches Bash but is not this
      guard is treated as a conflict and stops the install:
          LOCAL_HOOK_CONFIGURATION_CONFLICT
      Entries for other tools/matchers are preserved byte-for-byte in meaning.
    * Never prints secrets. `settings.json` may hold credentials; only digests, key names
      and booleans are ever emitted.
    * Config location mirrors the runtime's own resolution:
      WORKBUDDY_CONFIG_DIR, else ~/.workbuddy  (see the evidence in
      audit/AS_IS_WORKBUDDY_V3.md section 2).

Exit codes: 0 = success, 1 = failure, 3 = conflict/stop condition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

GUARD_ID = "workbuddy-git-safety-guard"
SETTINGS_FILENAME = "settings.json"
BACKUP_KEEP = 10

SOURCE_HOOK = Path(__file__).resolve().parent / "hooks" / "git_safety_guard.py"

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_STOP = 3


def config_dir() -> Path:
    override = (os.environ.get("WORKBUDDY_CONFIG_DIR") or "").strip()
    return Path(override) if override else Path.home() / ".workbuddy"


def paths() -> dict:
    base = config_dir()
    install_dir = base / "hooks" / GUARD_ID
    return {
        "base": base,
        "settings": base / SETTINGS_FILENAME,
        "install_dir": install_dir,
        "installed_hook": install_dir / "git_safety_guard.py",
        "state": install_dir / "install-state.json",
        "backup_root": base / "backups" / GUARD_ID,
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def desired_command() -> str:
    return f"{sys.executable} {paths()['installed_hook']}"


def desired_entry() -> dict:
    return {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": desired_command(), "timeout": 10}],
    }


def read_settings(path: Path) -> dict:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("settings.json is not a JSON object")
    return data


def pretooluse_entries(settings: dict) -> list:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return []
    entries = hooks.get("PreToolUse")
    return entries if isinstance(entries, list) else []


def is_ours(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    for hook in entry.get("hooks") or []:
        if isinstance(hook, dict) and GUARD_ID in str(hook.get("command") or ""):
            return True
    return False


def matcher_matches_bash(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    matcher = entry.get("matcher")
    if matcher in (None, "", "*"):
        return True
    return isinstance(matcher, str) and "Bash" in matcher


def detect_conflict(entries: list) -> list[str]:
    """Foreign PreToolUse hooks that would also fire on Bash."""
    conflicts = []
    for entry in entries:
        if is_ours(entry) or not matcher_matches_bash(entry):
            continue
        for hook in entry.get("hooks") or []:
            if isinstance(hook, dict) and hook.get("command"):
                conflicts.append(str(hook.get("command"))[:80])
    return conflicts


def backup_settings(p: dict) -> Path | None:
    if not p["settings"].is_file():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    p["backup_root"].mkdir(parents=True, exist_ok=True)
    target = p["backup_root"] / f"{SETTINGS_FILENAME}.{stamp}.bak"
    shutil.copy2(p["settings"], target)
    (target.with_suffix(".bak.sha256")).write_text(sha256(target) + "\n", encoding="utf-8")
    # retain a bounded number of backups; oldest first
    backups = sorted(p["backup_root"].glob(f"{SETTINGS_FILENAME}.*.bak"))
    for stale in backups[:-BACKUP_KEEP]:
        stale.unlink(missing_ok=True)
        stale.with_suffix(".bak.sha256").unlink(missing_ok=True)
    return target


def write_settings(p: dict, settings: dict) -> None:
    p["settings"].parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
    tmp = p["settings"].with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p["settings"])


def read_state(p: dict) -> dict:
    if not p["state"].is_file():
        return {}
    try:
        data = json.loads(p["state"].read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def run_selfcheck(hook: Path) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            [sys.executable, str(hook), "--selfcheck"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}"
    if proc.returncode == 0:
        return True, "selfcheck OK"
    return False, (proc.stderr or proc.stdout or "selfcheck failed").strip()[:200]


def cmd_status(p: dict) -> int:
    state = read_state(p)
    print(f"config_dir          = {p['base']}")
    print(f"settings_present    = {p['settings'].is_file()}")
    print(f"hook_installed      = {p['installed_hook'].is_file()}")
    print(f"state_recorded      = {bool(state)}")
    print(f"source_sha256       = {sha256(SOURCE_HOOK)[:16]}...")
    if p["installed_hook"].is_file():
        print(f"installed_sha256    = {sha256(p['installed_hook'])[:16]}...")
    print(f"pretooluse_entries  = {len(pretooluse_entries(read_settings(p['settings']) if p['settings'].is_file() else {}))}")
    return EXIT_OK


def cmd_install(p: dict) -> int:
    if not SOURCE_HOOK.is_file():
        print(f"FAIL: source hook not found: {SOURCE_HOOK}")
        return EXIT_FAIL

    settings = read_settings(p["settings"]) if p["settings"].is_file() else {}
    entries = pretooluse_entries(settings)

    conflicts = detect_conflict(entries)
    if conflicts:
        print("STOP: LOCAL_HOOK_CONFIGURATION_CONFLICT")
        print("  A PreToolUse hook that also matches Bash is already configured and is not this guard.")
        print(f"  offending command count = {len(conflicts)}")
        print("  The existing configuration was NOT modified. Resolve the overlap explicitly first.")
        return EXIT_STOP

    our_entries = [entry for entry in entries if is_ours(entry)]
    if len(our_entries) > 1:
        print(f"STOP: LOCAL_HOOK_CONFIGURATION_CONFLICT (duplicate registrations = {len(our_entries)})")
        return EXIT_STOP

    source_digest = sha256(SOURCE_HOOK)
    installed_before = p["installed_hook"].is_file()
    installed_digest_before = sha256(p["installed_hook"]) if installed_before else None

    settings_changed = not (len(our_entries) == 1 and our_entries[0] == desired_entry())
    settings_existed_before = p["settings"].is_file()
    backup = None
    if settings_changed:
        backup = backup_settings(p)

    p["install_dir"].mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE_HOOK, p["installed_hook"])

    if settings_changed:
        remaining = [entry for entry in entries if not is_ours(entry)]
        hooks = settings.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            print("FAIL: settings['hooks'] is not an object; refusing to overwrite")
            return EXIT_FAIL
        hooks["PreToolUse"] = remaining + [desired_entry()]
        write_settings(p, settings)

    state = {
        "guard_id": GUARD_ID,
        "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_path": str(SOURCE_HOOK),
        "source_sha256": source_digest,
        "installed_hook": str(p["installed_hook"]),
        "installed_sha256": sha256(p["installed_hook"]),
        "settings_backup": str(backup) if backup else None,
        "settings_backup_sha256": sha256(backup) if backup else None,
        "settings_existed_before": settings_existed_before,
        "settings_changed": settings_changed,
        "previous_installed_sha256": installed_digest_before,
    }
    p["install_dir"].mkdir(parents=True, exist_ok=True)
    p["state"].write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    print("INSTALL = OK")
    print(f"  installed_hook      = {p['installed_hook']}")
    print(f"  installed_sha256    = {state['installed_sha256'][:16]}...")
    print(f"  settings_changed    = {settings_changed}")
    if backup:
        print("  settings_backup     = recorded (local-only, outside any repository)")
    elif settings_changed:
        print("  settings_backup     = NONE (no pre-existing file to back up; rollback will remove it)")
    else:
        print("  settings_backup     = NONE (settings unchanged - idempotent re-install)")
    print(f"  duplicate_guard     = NONE (idempotent: existing registration reused = {not settings_changed})")
    return EXIT_OK


def cmd_verify(p: dict) -> int:
    problems: list[str] = []

    if not p["installed_hook"].is_file():
        problems.append("installed hook file missing")
    else:
        if sha256(p["installed_hook"]) != sha256(SOURCE_HOOK):
            problems.append("installed hook digest != reviewed source digest")
        ok, detail = run_selfcheck(p["installed_hook"])
        if not ok:
            problems.append(f"installed hook selfcheck failed: {detail}")

    if not p["settings"].is_file():
        problems.append("settings.json missing")
    else:
        entries = pretooluse_entries(read_settings(p["settings"]))
        ours = [entry for entry in entries if is_ours(entry)]
        if len(ours) != 1:
            problems.append(f"expected exactly one registration, found {len(ours)}")
        elif ours[0] != desired_entry():
            problems.append("registration does not match the reviewed desired entry")
        conflicts = detect_conflict(entries)
        if conflicts:
            problems.append(f"conflicting foreign Bash PreToolUse hooks = {len(conflicts)}")

    state = read_state(p)
    if state and state.get("installed_sha256") and p["installed_hook"].is_file():
        if state["installed_sha256"] != sha256(p["installed_hook"]):
            problems.append("installed hook digest != recorded install-state digest")

    if problems:
        print("VERIFY = FAIL")
        for problem in problems:
            print(f"  - {problem}")
        return EXIT_FAIL
    print("VERIFY = OK (digest match, exactly one registration, selfcheck pass)")
    return EXIT_OK


def cmd_rollback(p: dict) -> int:
    state = read_state(p)
    settings = read_settings(p["settings"]) if p["settings"].is_file() else {}

    if p["settings"].is_file():
        backup_path = state.get("settings_backup")
        restored = False
        if backup_path and Path(backup_path).is_file():
            expected = state.get("settings_backup_sha256")
            actual = sha256(Path(backup_path))
            if expected and expected != actual:
                print("STOP: LOCAL_HOOK_CONFIGURATION_CONFLICT (backup digest mismatch)")
                return EXIT_STOP
            shutil.copy2(backup_path, p["settings"])
            restored = True
        if not restored:
            # No usable backup: remove only our own registration, keep everything else.
            entries = pretooluse_entries(settings)
            remaining = [entry for entry in entries if not is_ours(entry)]
            hooks = settings.get("hooks")
            if isinstance(hooks, dict):
                hooks["PreToolUse"] = remaining
                if not remaining:
                    hooks.pop("PreToolUse", None)
                if not hooks:
                    settings.pop("hooks", None)
            if settings or not state.get("settings_existed_before", True):
                # Restore the pre-install shape: if there was no file before installing,
                # leaving an empty `{}` behind is not a faithful rollback.
                if settings:
                    write_settings(p, settings)
                else:
                    p["settings"].unlink(missing_ok=True)

    if p["install_dir"].is_dir():
        shutil.rmtree(p["install_dir"])

    print("ROLLBACK = OK")
    print(f"  restored_from_backup          = {bool(state.get('settings_backup'))}")
    print(f"  settings_file_present_after   = {p['settings'].is_file()}")
    print(f"  install_dir_removed           = {not p['install_dir'].exists()}")
    print("  note: run `verify` and expect hook_installed = False")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WorkBuddy git safety guard installer")
    parser.add_argument("action", choices=["install", "verify", "rollback", "status"])
    args = parser.parse_args(argv)
    p = paths()
    try:
        return {
            "install": cmd_install,
            "verify": cmd_verify,
            "rollback": cmd_rollback,
            "status": cmd_status,
        }[args.action](p)
    except json.JSONDecodeError:
        print("FAIL: settings.json is not valid JSON; refusing to modify it")
        return EXIT_FAIL
    except OSError as exc:
        print(f"FAIL: {type(exc).__name__}")
        return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
