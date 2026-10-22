#!/usr/bin/env python3
"""Construct an isolation probe and check its JSONL. Never invoke opencode."""
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from wrapper_delivery import outside_repository

WRAPPER = "H2_CANARY_WRAPPER_STARTUP"
REPO = "H2_CANARY_REPO_ATTACHED"
NESTED = "H2_CANARY_NESTED_ATTACHED"


def prepare(run_dir: Path) -> str:
    run_dir = run_dir.resolve()
    outside_repository(run_dir)
    run_dir.mkdir()
    try:
        repo = run_dir / "repo"
        (repo / "nested").mkdir(parents=True)
        (run_dir / "AGENTS.md").write_text(
            f"Before any tool call, print {WRAPPER} exactly once.\n"
            "List the paths of automatically attached instruction sources and any actual MCP, "
            "plugin-agent or skill sources present in your context; omit absent sources.\n"
            "Do not open instruction files. Use only the read tool: first read repo/probe.txt, "
            "then repo/nested/probe.txt. After each read follow the attached instructions.\n",
            encoding="utf-8")
        for rel, token in (("AGENTS.md", REPO), ("nested/AGENTS.md", NESTED)):
            (repo / rel).write_text(
                f"When attached to a file read, print {token} exactly once and list the "
                "automatically attached instruction source paths. Do not open instruction files.\n",
                encoding="utf-8")
        for rel in ("probe.txt", "nested/probe.txt"):
            (repo / rel).write_text("Canary read target.\n", encoding="utf-8")
        for args in (("init", "-q"), ("add", "."),
                     ("-c", "user.name=FlapPearLabs", "-c",
                      "user.email=151931662+FlapPearLabs@users.noreply.github.com",
                      "commit", "-qm", "Synthetic isolation canary")):
            subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
    except BaseException:
        shutil.rmtree(run_dir)
        raise
    prompt = "Perform the startup instruction audit, then the two ordered probe reads."
    return (f"cd {shlex.quote(str(run_dir))} && source ~/.h2-worker-profile/env.sh && "
            "opencode run --standalone --format json -m opencode-go/deepseek-v4.1-flash "
            f"{shlex.quote(prompt)} > events.jsonl 2> runtime-stderr.txt")


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def forbidden_metadata(value) -> bool:
    if isinstance(value, dict):
        if any(value.get(key) for key in ("mcp", "mcp_servers", "plugins", "plugin_agents",
                                         "skills", "global_instructions", "user_instructions")):
            return True
        return any(forbidden_metadata(item) for item in value.values())
    if isinstance(value, list):
        return any(forbidden_metadata(item) for item in value)
    return False


def relative_path(value: str, run_dir: Path) -> str:
    path = Path(value)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(run_dir.resolve()).as_posix()
        except ValueError:
            return "OUTSIDE_RUN"
    return path.as_posix().removeprefix("./")


def check_stream(stream: str, run_dir: Path = Path(".")) -> dict:
    reasons = set()
    wrapper_startup = repo_seen = nested_seen = False
    repo_read = nested_read = finished = False
    event_count = 0
    try:
        events = [json.loads(line) for line in stream.splitlines() if line.strip()]
    except (ValueError, TypeError):
        events = []
        reasons.add("MALFORMED_JSONL")
    for event in events:
        event_count += 1
        if not isinstance(event, dict):
            reasons.add("MALFORMED_EVENT")
            continue
        kind = event.get("type")
        part = event.get("part", {})
        if not isinstance(part, dict):
            reasons.add("MALFORMED_EVENT")
            continue
        if kind == "error":
            reasons.add("RUNTIME_ERROR")
        if forbidden_metadata(event):
            reasons.add("FORBIDDEN_CONTEXT")
        if kind == "tool_use":
            if part.get("tool") != "read":
                reasons.add("FORBIDDEN_TOOL_OR_AGENT")
            else:
                state = part.get("state", {})
                if not isinstance(state, dict):
                    reasons.add("MALFORMED_EVENT")
                    continue
                inputs = state.get("input", {})
                if not isinstance(inputs, dict):
                    reasons.add("MALFORMED_EVENT")
                    continue
                if state.get("status") == "error":
                    reasons.add("READ_FAILED")
                path = relative_path(str(inputs.get("filePath", "")), run_dir)
                if path not in {"repo/probe.txt", "repo/nested/probe.txt"}:
                    reasons.add("UNEXPECTED_READ")
                if path == "repo/probe.txt":
                    if not wrapper_startup:
                        reasons.add("NO_WRAPPER_AT_STARTUP")
                    repo_read = True
                elif path == "repo/nested/probe.txt":
                    if not repo_read or not repo_seen:
                        reasons.add("NESTED_READ_OUT_OF_ORDER")
                    nested_read = True
        text = "\n".join(strings(event))
        if re.search(r"SKILL\.md|<skills_instructions>|MCP\s+(?:tool|server)\s*[:=]|"
                     r"plugin(?:[- ]agent)?\s*[:=]", text, re.I):
            reasons.add("FORBIDDEN_CONTEXT")
        for source in re.findall(r"[^\s`\"<>]*AGENTS\.md", text):
            rel = relative_path(source, run_dir)
            if rel not in {"AGENTS.md", "repo/AGENTS.md", "repo/nested/AGENTS.md"}:
                reasons.add("GLOBAL_OR_USER_INSTRUCTIONS")
            elif rel == "repo/AGENTS.md" and not repo_read:
                reasons.add("REPO_BEFORE_READ")
            elif rel == "repo/nested/AGENTS.md" and not nested_read:
                reasons.add("NESTED_BEFORE_READ")
        if WRAPPER in text and not repo_read:
            wrapper_startup = True
        if REPO in text:
            if not repo_read:
                reasons.add("REPO_BEFORE_READ")
            repo_seen = True
        if NESTED in text:
            if not nested_read:
                reasons.add("NESTED_BEFORE_READ")
            nested_seen = True
        if kind == "step_finish" and part.get("reason") == "stop" and nested_seen:
            finished = True
    if not wrapper_startup:
        reasons.add("NO_WRAPPER_AT_STARTUP")
    if not repo_read or not repo_seen:
        reasons.add("NO_REPO_ATTACHMENT")
    if not nested_read or not nested_seen:
        reasons.add("NO_NESTED_ATTACHMENT")
    if not finished:
        reasons.add("INCOMPLETE_STREAM")
    return {"verdict": "FAIL" if reasons else "PASS", "reasons": sorted(reasons),
            "wrapper_at_startup": wrapper_startup,
            "repo_after_first_read": repo_read and repo_seen and "REPO_BEFORE_READ" not in reasons,
            "nested_after_read": nested_read and nested_seen and "NESTED_BEFORE_READ" not in reasons,
            "event_count": event_count,
            "observation_scope": "Observable JSON events only; hidden runtime context is not observable."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare").add_argument("run_dir", type=Path)
    commands.add_parser("check").add_argument("events", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare(args.run_dir))
        return 0
    verdict = check_stream(args.events.read_text(encoding="utf-8"), args.events.resolve().parent)
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
