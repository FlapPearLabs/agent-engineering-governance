#!/usr/bin/env python3
"""Construct an isolation probe and check its JSONL. Never invoke opencode.

`check` reads the REAL `opencode run --format json` event stream (F3): the top-level `type` is
`step_start | text | tool_use | step_finish | error`, the markers appear in `part.text`, and a read
is a `tool_use` part whose `state.input.path` names the file. Hand-made fixtures that spoke a
different schema — and a completion rule that required `step_finish(reason=stop)`, which the real
stream ends without — produced six false reasons on a correct run. The parser is now driven by the
schema the runtime emits, and it is proven against two real streams (one correct, one that leaked
the operator's skill catalogue) plus one mutated copy per refusal reason.

Scope of the verdict: OBSERVABLE events only. Hidden runtime context is not observable from here.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path, PurePosixPath

from wrapper_delivery import outside_repository, run_root_reason

WRAPPER = "H2_CANARY_WRAPPER_STARTUP"
REPO = "H2_CANARY_REPO_ATTACHED"
NESTED = "H2_CANARY_NESTED_ATTACHED"
READ_TARGETS = ("repo/probe.txt", "repo/nested/probe.txt")
ALLOWED_INSTRUCTION_PATHS = frozenset({"AGENTS.md", "repo/AGENTS.md", "repo/nested/AGENTS.md"})
# The runtime ships these two skills in every isolated profile; anything else named in the stream is
# a discovered skill catalogue, i.e. contamination (F4).
ALLOWED_SKILLS = frozenset({"opencode", "report"})
RUN_ROOT = "<RUN_ROOT>"
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
AGENTS_PATH_RE = re.compile(r"[^\s`\"'()\[\]]*AGENTS\.md")
NEGATION_RE = re.compile(r"\b(?:none|no|not|absent|without|zero)\b", re.I)
TOOL_SCHEMA = {"step_start", "text", "tool_use", "step_finish", "error"}


def prepare(run_dir: Path) -> str:
    run_dir = run_dir.resolve()
    outside_repository(run_dir)
    root_reason = run_root_reason(run_dir)
    if root_reason is not None:
        raise ValueError(root_reason)
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


def normalise_path(value: str, run_dir: Path) -> str:
    """A run-root-relative path: `<RUN_ROOT>/x`, an absolute path under the run dir, or `./x`."""
    value = value.strip()
    if not value:
        return ""
    if value.startswith(RUN_ROOT):
        return value[len(RUN_ROOT):].lstrip("/")
    path = PurePosixPath(value)
    if path.is_absolute():
        try:
            return Path(value).resolve().relative_to(run_dir.resolve()).as_posix()
        except ValueError:
            return "OUTSIDE_RUN"
    return path.as_posix().removeprefix("./")


def skill_names(line: str) -> set[str]:
    return {match.group(1) for match in BACKTICK_RE.finditer(line)
            if IDENTIFIER_RE.fullmatch(match.group(1))}


def text_reasons(text: str, run_dir: Path, repo_read: bool, nested_read: bool) -> set[str]:
    """Everything an observable text block may disclose, read line by line (one claim per line)."""
    reasons: set[str] = set()
    for line in text.splitlines():
        folded = line.casefold()
        if "skill" in folded:
            if "<skills_instructions>" in folded or "skill.md" in folded:
                reasons.add("FORBIDDEN_CONTEXT")
            if skill_names(line) - ALLOWED_SKILLS:
                reasons.add("SKILL_CATALOGUE_CONTAMINATION")
        if not NEGATION_RE.search(line):
            if "mcp" in folded:
                reasons.add("MCP_CONTAMINATION")
            if "plugin" in folded:
                reasons.add("PLUGIN_AGENT_CONTAMINATION")
        for source in AGENTS_PATH_RE.findall(line):
            rel = normalise_path(source, run_dir)
            if rel not in ALLOWED_INSTRUCTION_PATHS:
                reasons.add("GLOBAL_OR_USER_INSTRUCTIONS")
            elif rel == "repo/AGENTS.md" and not repo_read:
                reasons.add("REPO_BEFORE_READ")
            elif rel == "repo/nested/AGENTS.md" and not nested_read:
                reasons.add("NESTED_BEFORE_READ")
    return reasons


def check_stream(stream: str, run_dir: Path = Path(".")) -> dict:
    reasons: set[str] = set()
    wrapper_startup = repo_read = nested_read = False
    repo_marker = nested_marker = False
    step_finishes = 0
    last_kind = None
    try:
        events = [json.loads(line) for line in stream.splitlines() if line.strip()]
    except (ValueError, TypeError):
        events = []
        reasons.add("MALFORMED_JSONL")
    for event in events:
        if not isinstance(event, dict):
            reasons.add("MALFORMED_EVENT")
            continue
        kind = event.get("type")
        part = event.get("part", {})
        if not isinstance(part, dict):
            reasons.add("MALFORMED_EVENT")
            continue
        last_kind = kind
        if kind not in TOOL_SCHEMA:
            reasons.add("MALFORMED_EVENT")
        if kind == "error":
            reasons.add("RUNTIME_ERROR")
        if forbidden_metadata(event):
            reasons.add("FORBIDDEN_CONTEXT")
        if kind == "tool_use":
            tool = part.get("tool")
            if isinstance(tool, str) and tool.startswith("mcp__"):
                reasons.add("MCP_CONTAMINATION")
            elif tool != "read":
                reasons.add("FORBIDDEN_TOOL_OR_AGENT")
            else:
                state = part.get("state", {})
                inputs = state.get("input") if isinstance(state, dict) else None
                if not isinstance(inputs, dict):
                    reasons.add("MALFORMED_EVENT")
                    continue
                if state.get("status") == "error":
                    reasons.add("READ_FAILED")
                raw = inputs.get("path", inputs.get("filePath", ""))
                path = normalise_path(str(raw), run_dir)
                if path not in READ_TARGETS:
                    reasons.add("UNEXPECTED_READ")
                elif path == "repo/probe.txt":
                    if not wrapper_startup:
                        reasons.add("NO_WRAPPER_AT_STARTUP")
                    repo_read = True
                else:
                    if not (repo_read and repo_marker):
                        reasons.add("NESTED_READ_OUT_OF_ORDER")
                    nested_read = True
        reasons |= text_reasons("\n".join(strings(event)), run_dir, repo_read, nested_read)
        text = part.get("text") if kind == "text" else ""
        text = text if isinstance(text, str) else ""
        if WRAPPER in text and not (repo_read or nested_read):
            wrapper_startup = True
        if REPO in text:
            if not repo_read:
                reasons.add("REPO_BEFORE_READ")
            repo_marker = True
        if NESTED in text:
            if not nested_read:
                reasons.add("NESTED_BEFORE_READ")
            nested_marker = True
        if kind == "step_finish":
            step_finishes += 1
    if not wrapper_startup:
        reasons.add("NO_WRAPPER_AT_STARTUP")
    if not (repo_read and repo_marker):
        reasons.add("NO_REPO_ATTACHMENT")
    if not (nested_read and nested_marker):
        reasons.add("NO_NESTED_ATTACHMENT")
    if not events or not step_finishes or last_kind in ("step_start", "tool_use"):
        reasons.add("INCOMPLETE_STREAM")
    return {"verdict": "FAIL" if reasons else "PASS", "reasons": sorted(reasons),
            "wrapper_at_startup": wrapper_startup,
            "repo_after_first_read": repo_read and repo_marker and "REPO_BEFORE_READ" not in reasons,
            "nested_after_read": nested_read and nested_marker and "NESTED_BEFORE_READ" not in reasons,
            "event_count": len(events),
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
