#!/usr/bin/env python3
"""Out-of-run access audit of one run's event stream (F9 / T22).

The worker contract confines every tool call to the wrapper, but nothing read the evidence that
already exists: `events.jsonl` records the input of every tool call — read/glob/grep/edit/write
paths and shell commands. This module replays that stream and reports, verbatim, every access that
resolves outside the run directory, plus every shell `git` invocation that tries to reach another
repository and every tool outside the frozen allow-list. A hit makes the run
INVALID:OUT_OF_RUN_ACCESS; it is registered and never re-run (protocol-v2 §6).

What is flagged:

  * a path argument (`path`, `filePath`, `file_path`, `directory`, `dir`) that resolves outside the
    run directory — relative paths resolve against the worker's cwd, which IS the run directory, so
    only absolute, `~`, `$HOME` and `..`-escaping values can hit;
  * the same rule applied to every token of a `bash` command (after `--flag=value` and `KEY=value`
    splitting). `~` and `$HOME` resolve to the profile home the worker was launched with, never to
    the operator's; a fixture may write the neutral token `<RUN_ROOT>`, which resolves to the run
    directory;
  * a diff path in the `patch` tool's `patchText` (`--- a/x`, `+++ b/x`, `diff --git a/x b/x`);
  * `git clone/fetch/pull/push/ls-remote/submodule`, `git remote add|set-url|update|prune|rename|
    remove`, and any `git -C <outside>`, `--git-dir=<outside>` or `--work-tree=<outside>`;
  * any tool that is not in `TOOL_ALLOW` (`webfetch`, `task`, `skill`, an `mcp__` tool …): a tool
    whose accesses this stream cannot show is not auditable from here.

The allow-list is frozen to what a test run genuinely needs: the pinned interpreter (its path and
prefix), `/usr`, `/bin`, `/sbin`, `/opt/homebrew`, `/System`, `/Library/Developer`, the OS temp
roots and `/dev/null`. Everything else is out of run. `-C` and the git location flags are judged
against the run directory only: a temp directory is a legitimate scratch target but not a
legitimate repository to run git in.

Scope of the verdict: OBSERVABLE tool calls only. Hidden runtime context, and any access a tool
performs internally without reporting it, is not observable from the event stream.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path, PurePosixPath

RUN_ROOT = "<RUN_ROOT>"
TOOL_ALLOW = frozenset({"read", "write", "edit", "multiedit", "patch", "bash", "glob", "grep",
                        "list", "todowrite", "todoread"})
PATH_TOOLS = frozenset({"read", "write", "edit", "multiedit", "patch", "glob", "grep", "list"})
SHELL_TOOLS = frozenset({"bash"})
PATH_KEYS = ("path", "filePath", "file_path", "directory", "dir")
COMMAND_KEYS = ("command", "cmd")
SYSTEM_ALLOW = ("/usr", "/bin", "/sbin", "/opt/homebrew", "/System", "/Library/Developer",
                "/dev/null", "/dev/stdout", "/dev/stderr")
# The OS temp roots a test run may legitimately write to. The broad `/var/folders` prefix is NOT
# allowed: only the temp dir itself and `/tmp` (with the real path its symlink points to, added in
# `allowed_roots`), so that a `..` escape from the wrapper lands outside this list and is reported.
TEMP_ALLOW = ("/tmp",)  # its resolved symlink target is added by allowed_roots
GIT_ESCAPE_SUBCOMMANDS = frozenset({"clone", "fetch", "pull", "push", "ls-remote", "submodule"})
GIT_REMOTE_SUBCOMMANDS = frozenset({"add", "set-url", "update", "prune", "rename", "remove"})
GIT_LOCATION_FLAGS = ("--git-dir=", "--work-tree=")
DIFF_PATH_RE = re.compile(r"^(?:diff --git a/(?P<both>\S+)|--- a/(?P<old>\S+)|\+\+\+ b/(?P<new>\S+))$",
                          re.M)


def allowed_roots(python: str | None = None) -> tuple[str, ...]:
    """The frozen system allow-list; the interpreter is resolved, never hard-coded."""
    interpreter = Path(python or sys.executable).resolve()
    values = {*SYSTEM_ALLOW, *TEMP_ALLOW, str(interpreter), str(interpreter.parent),
              str(Path(sys.prefix).resolve()), str(Path(tempfile.gettempdir()).resolve())}
    values |= {os.path.realpath(value) for value in list(values)}
    return tuple(sorted(values))


def resolve(value: str, run_dir: Path, home: str | None) -> str | None:
    """An absolute path for one value, or None when `~`/`$HOME` cannot be resolved."""
    text = value.strip().strip("'\"")
    if not text:
        return ""
    if text.startswith(RUN_ROOT):
        text = f"{run_dir}{text[len(RUN_ROOT):]}"
    else:
        for prefix in ("${HOME}", "$HOME"):
            if text == prefix or text.startswith((f"{prefix}/", f"{prefix} ")):
                if not home:
                    return None
                text = f"{home}{text[len(prefix):]}"
                break
        else:
            if text == "~" or text.startswith("~/"):
                if not home:
                    return None
                text = f"{home}{text[1:]}"
    if not os.path.isabs(text):
        text = os.path.join(str(run_dir), text)
    return os.path.realpath(text)


def inside(path: str, root: str) -> bool:
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root + os.sep)


def path_reason(value: str, run_dir: Path, home: str | None,
                allow: tuple[str, ...]) -> str | None:
    resolved = resolve(value, run_dir, home)
    if resolved is None:
        return "PATH_HOME_UNRESOLVED"
    if not resolved:
        return None
    if inside(resolved, str(run_dir)):
        return None
    if any(inside(resolved, root) for root in allow):
        return None
    return "PATH_OUTSIDE_RUN"


def token_values(token: str) -> list[str]:
    """The path-bearing values of one shell token (`--flag=value`, `KEY=value`, plain)."""
    text = token.strip()
    if "=" in text:
        text = text.split("=", 1)[1]
    return [text] if text else []


def git_hits(tokens: list[str], run_dir: Path, home: str | None) -> list[dict]:
    """Shell `git` invocations that reach another repository."""
    hits: list[dict] = []
    command = " ".join(tokens)
    for index, token in enumerate(tokens):
        if PurePosixPath(token).name != "git":
            continue
        args = tokens[index + 1:]
        for position, argument in enumerate(args):
            following = args[position + 1:position + 2]
            if argument in GIT_ESCAPE_SUBCOMMANDS:
                hits.append({"tool": "bash", "reason": "GIT_REMOTE_REPOSITORY",
                             "value": command, "path": argument})
            elif argument == "remote" and following and following[0] in GIT_REMOTE_SUBCOMMANDS:
                hits.append({"tool": "bash", "reason": "GIT_REMOTE_REPOSITORY",
                             "value": command, "path": f"remote {following[0]}"})
            elif argument == "-C" and following:
                resolved = resolve(following[0], run_dir, home)
                if resolved is None or not inside(resolved, str(run_dir)):
                    hits.append({"tool": "bash", "reason": "GIT_FOREIGN_REPOSITORY",
                                 "value": command, "path": following[0]})
            for flag in GIT_LOCATION_FLAGS:
                if argument.startswith(flag):
                    target = argument[len(flag):]
                    resolved = resolve(target, run_dir, home)
                    if resolved is None or not inside(resolved, str(run_dir)):
                        hits.append({"tool": "bash", "reason": "GIT_FOREIGN_REPOSITORY",
                                     "value": command, "path": target})
    return hits


def shell_hits(command: str, run_dir: Path, home: str | None,
               allow: tuple[str, ...]) -> list[dict]:
    """Every path-shaped token of one shell command, plus the git rules above."""
    try:
        tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:
        tokens = command.split()
    hits: list[dict] = []
    for token in tokens:
        for value in token_values(token):
            reason = path_reason(value, run_dir, home, allow)
            if reason:
                hits.append({"tool": "bash", "reason": reason, "value": command.strip(),
                             "path": value})
    hits.extend(git_hits(tokens, run_dir, home))
    return hits


def patch_paths(text) -> list[str]:
    if not isinstance(text, str):
        return []
    paths = []
    for match in DIFF_PATH_RE.finditer(text):
        value = match.group("both") or match.group("old") or match.group("new") or ""
        if value and value != "/dev/null":
            paths.append(value)
    return paths


def event_hits(event, index: int, run_dir: Path, home: str | None,
               allow: tuple[str, ...]) -> list[dict]:
    """The hits of one parsed event; a non-`tool_use` event carries no access."""
    if not isinstance(event, dict):
        return [{"event": index, "reason": "MALFORMED_EVENT", "value": str(event)[:200]}]
    if event.get("type") != "tool_use":
        return []
    part = event.get("part")
    if not isinstance(part, dict):
        return [{"event": index, "reason": "MALFORMED_EVENT", "value": ""}]
    tool = part.get("tool")
    state = part.get("state") if isinstance(part.get("state"), dict) else {}
    inputs = state.get("input") if isinstance(state.get("input"), dict) else {}
    if not isinstance(tool, str) or not tool:
        return [{"event": index, "reason": "TOOL_UNIDENTIFIED", "value": ""}]
    hits: list[dict] = []
    if tool not in TOOL_ALLOW:
        hits.append({"event": index, "tool": tool, "reason": "TOOL_NOT_ALLOWED", "value": tool})
    if tool in PATH_TOOLS:
        for key in PATH_KEYS:
            value = inputs.get(key)
            if not isinstance(value, str):
                continue
            reason = path_reason(value, run_dir, home, allow)
            if reason:
                hits.append({"event": index, "tool": tool, "reason": reason, "value": value})
    if tool in SHELL_TOOLS:
        for key in COMMAND_KEYS:
            command = inputs.get(key)
            if isinstance(command, str):
                hits.extend({"event": index, **hit}
                            for hit in shell_hits(command, run_dir, home, allow))
    if tool == "patch":
        for value in patch_paths(inputs.get("patchText")):
            reason = path_reason(value, run_dir, home, allow)
            if reason:
                hits.append({"event": index, "tool": tool, "reason": reason, "value": value})
    return hits


def audit(events_path: Path, run_dir: Path, *, home: str | None = None,
          python: str | None = None) -> dict:
    """Audit one run's event stream; every hit is kept verbatim."""
    run_dir = Path(run_dir).resolve()
    allow = allowed_roots(python)
    result = {"schema_version": 1, "program": "freeze-v2/access_audit.py",
              "run_dir": str(run_dir), "allow_list": list(allow),
              "observation_scope": ("Every tool_use input recorded in the run's event stream. "
                                    "Hidden runtime context and tool-internal accesses that emit "
                                    "no event are not observable."),
              "hits": [], "events": 0, "tool_calls": 0, "verdict": "PASS"}
    path = Path(events_path)
    if not path.is_file():
        result["hits"] = [{"reason": "MISSING_EVENT_STREAM", "value": str(path)}]
        result["verdict"] = "INVALID"
        return result
    seen: set[str] = set()
    for index, line in enumerate(path.read_text(encoding="utf-8", errors="replace")
                                 .splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            hit = {"event": index, "reason": "MALFORMED_EVENT_LINE", "value": line[:200]}
        else:
            result["events"] += 1
            if isinstance(event, dict) and event.get("type") == "tool_use":
                result["tool_calls"] += 1
            found = event_hits(event, index, run_dir, home, allow)
            hit = None
            for candidate in found:
                key = json.dumps(candidate, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    result["hits"].append(candidate)
            continue
        key = json.dumps(hit, sort_keys=True)
        if key not in seen:
            seen.add(key)
            result["hits"].append(hit)
    if result["hits"]:
        result["verdict"] = "INVALID"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--home", default=None,
                        help="the profile HOME the worker ran with; ~ and $HOME resolve to it")
    parser.add_argument("--python", default=None, help="the pinned interpreter to allow-list")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    result = audit(args.events, args.run_dir, home=args.home, python=args.python)
    target = args.out or args.run_dir / "access-audit.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"], "hits": len(result["hits"]),
                      "tool_calls": result["tool_calls"]}, sort_keys=True))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
