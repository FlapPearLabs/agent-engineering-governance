#!/usr/bin/env python3
"""Construct the isolation probe, attest the worker profile, and check the JSONL.

Three jobs, none of which calls a model:

`prepare <run_dir>` builds the wrapper canary (wrapper AGENTS.md, repo AGENTS.md, nested
AGENTS.md) in a synthetic repository and prints the exact command string for the operator. The
implementer never runs it.

`preflight <run_dir> --profile-env <env.sh>` (F5) replaces free-text self-report with a
deterministic configuration report. It runs ONLY `opencode debug paths` and `opencode debug
config` with the profile environment and cwd = run_dir, and writes `<run_dir>/preflight.json`.
PASS requires: the runtime's home/data/config/cache/state (and every other state path it
prints) is under the profile home; the config sources are exactly the profile's
`opencode.json` and the profile config directory; and that file's bytes equal the frozen
template `worker-profile/opencode.json`. The `tmp` entry is the OS temp root, not profile
state, and is required to be absolute rather than under the profile home -- that is the one
narrowing of "every printed path", and it is recorded as evidence, not ignored.

`check <events.jsonl>` reads the REAL `opencode run --format json` stream: the top-level `type`
is `step_start | text | tool_use | step_finish | error`, markers appear in `part.text`, and a
read is a `tool_use` part whose `state.input.path` names the file. Claims about MCP servers,
plugin agents and skills come ONLY from the machine-readable line

    H2_CANARY_SOURCES mcp=<integer> plugin_agents=<integer> skills=<comma-separated names>

which the canary instructions require. Free prose no longer decides those three claims (F5: a
correct live run FAILed because a heading said "MCP / plugin-agent sources present" and the
model's wording changes every run). Every ordering, attachment and instruction-path rule is
unchanged, and a tool-use event naming an `mcp__` tool still fails regardless.

Scope of the verdict: OBSERVABLE events only. Hidden runtime context is not observable from here.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
from hashlib import sha256
from pathlib import Path, PurePosixPath

from wrapper_delivery import outside_repository, run_root_reason

WRAPPER = "H2_CANARY_WRAPPER_STARTUP"
REPO = "H2_CANARY_REPO_ATTACHED"
NESTED = "H2_CANARY_NESTED_ATTACHED"
READ_TARGETS = ("repo/probe.txt", "repo/nested/probe.txt")
ALLOWED_INSTRUCTION_PATHS = frozenset({"AGENTS.md", "repo/AGENTS.md", "repo/nested/AGENTS.md"})
# The runtime ships these two skills in every isolated profile; anything else named by the
# runtime's own source line is a discovered skill catalogue, i.e. contamination (F4).
ALLOWED_SKILLS = frozenset({"opencode", "report"})
RUN_ROOT = "<RUN_ROOT>"
SOURCES_PREFIX = "H2_CANARY_SOURCES"
SOURCES_RE = re.compile(
    r"^H2_CANARY_SOURCES\s+mcp=(\d+)\s+plugin_agents=(\d+)\s+skills=(.*)$")
IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
AGENTS_PATH_RE = re.compile(r"[^\s`\"'()\[\]]*AGENTS\.md")
TOOL_SCHEMA = {"step_start", "text", "tool_use", "step_finish", "error"}

# --- preflight (F5): what the profile must look like before a run may start -------------
PROFILE_STATE_KEYS = ("home", "data", "config", "cache", "state", "bin", "log", "repos", "db")
REQUIRED_PROFILE_KEYS = ("home", "data", "config", "cache", "state")
TMP_KEY = "tmp"
CONFIG_DIR_REL = ".config/opencode"
CONFIG_NAME = "opencode.json"
PREFLIGHT_COMMANDS = (("debug", "paths"), ("debug", "config"))
PREFLIGHT_TIMEOUT = 120
CONFIG_TEMPLATE = Path(__file__).resolve().with_name("worker-profile") / CONFIG_NAME


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
            "List the paths of automatically attached instruction sources, then print exactly "
            "one line of the form\n"
            f"{SOURCES_PREFIX} mcp=<integer> plugin_agents=<integer> "
            "skills=<comma-separated names>\n"
            "counting only the MCP servers and plugin agents actually present in your context "
            "and naming every skill source you can see; use 0 and an empty list when there are "
            "none.\n"
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
    prompt = ("Perform the startup instruction audit, state the machine-readable sources line, "
              "then the two ordered probe reads.")
    return (f"cd {shlex.quote(str(run_dir))} && source ~/.h2-worker-profile/env.sh && "
            "opencode run --standalone --format json -m opencode-go/deepseek-v4.1-flash "
            f"{shlex.quote(prompt)} > events.jsonl 2> runtime-stderr.txt")


# --- preflight (F5) ---------------------------------------------------------------------

def parse_profile_env(text: str) -> dict[str, str]:
    """`export KEY=VALUE` lines of the profile env file, without executing the file."""
    env: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, separator, value = line.partition("=")
        if not separator:
            continue
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def parse_debug_paths(text: str) -> dict[str, str]:
    """`opencode debug paths`: one `<name> <absolute path>` pair per line."""
    paths: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        name, _, value = line.partition(" ")
        value = value.strip()
        if name and value:
            paths[name] = value
    if not paths:
        raise ValueError("EMPTY_DEBUG_PATHS")
    return paths


def parse_debug_config(text: str) -> list[dict[str, str]]:
    """`opencode debug config`: the ordered list of configuration sources it loaded."""
    sources = json.loads(text)
    if not isinstance(sources, list):
        raise ValueError("CONFIG_SOURCES_NOT_A_LIST")
    out = []
    for source in sources:
        if (not isinstance(source, dict) or not isinstance(source.get("type"), str)
                or not isinstance(source.get("path"), str)):
            raise ValueError("CONFIG_SOURCE_MALFORMED")
        out.append({"type": source["type"], "path": source["path"]})
    return out


def expected_config_sources(profile_home: str) -> set[tuple[str, str]]:
    home = profile_home.rstrip("/")
    return {("document", f"{home}/{CONFIG_DIR_REL}/{CONFIG_NAME}"),
            ("directory", f"{home}/{CONFIG_DIR_REL}")}


def evaluate_preflight(paths_text: str, config_text: str, *, profile_home: str,
                       template: bytes | None, config_file: bytes | None) -> dict:
    """The pure decision: no subprocess, no filesystem. `profile_home` is normalised."""
    reasons: set[str] = set()
    home = profile_home.rstrip("/")
    try:
        paths = parse_debug_paths(paths_text)
    except (ValueError, TypeError):
        paths = {}
        reasons.add("PREFLIGHT_UNPARSEABLE_PATHS")
    for key in REQUIRED_PROFILE_KEYS:
        if key not in paths:
            reasons.add(f"PREFLIGHT_PATH_MISSING:{key}")
    if "home" in paths and paths["home"] != home:
        reasons.add("PREFLIGHT_HOME_MISMATCH")
    for key in PROFILE_STATE_KEYS:
        if key == "home" or key not in paths:
            continue
        value = paths[key].rstrip("/")
        if not (value == home or value.startswith(f"{home}/")):
            reasons.add(f"PREFLIGHT_PATH_OUTSIDE_PROFILE:{key}")
    for key in paths:
        if key not in PROFILE_STATE_KEYS and key != TMP_KEY:
            reasons.add(f"PREFLIGHT_UNKNOWN_PATH_KEY:{key}")
    if TMP_KEY not in paths:
        reasons.add(f"PREFLIGHT_PATH_MISSING:{TMP_KEY}")
    elif not (paths[TMP_KEY].startswith("/") or paths[TMP_KEY].startswith("<")):
        reasons.add("PREFLIGHT_TMP_NOT_ABSOLUTE")
    try:
        sources = parse_debug_config(config_text)
    except (ValueError, TypeError, json.JSONDecodeError):
        sources = []
        reasons.add("PREFLIGHT_UNPARSEABLE_CONFIG")
    if "PREFLIGHT_UNPARSEABLE_CONFIG" not in reasons:
        actual = {(source["type"], source["path"].rstrip("/")) for source in sources}
        if actual != expected_config_sources(home):
            reasons.add("CONFIG_SOURCES_MISMATCH")
    if template is None:
        reasons.add("PREFLIGHT_TEMPLATE_UNAVAILABLE")
    if config_file is None:
        reasons.add("PREFLIGHT_CONFIG_UNREADABLE")
    elif template is not None and config_file != template:
        reasons.add("CONFIG_TEMPLATE_MISMATCH")
    return {"verdict": "FAIL" if reasons else "PASS",
            "reasons": sorted(reasons),
            "profile_home": home,
            "paths": paths,
            "config_sources": sources,
            "template_sha256": sha256(template).hexdigest() if template is not None else None,
            "config_file_sha256": (sha256(config_file).hexdigest()
                                   if config_file is not None else None),
            "observation_scope": ("Runtime configuration report only; no worker, session or "
                                  "model call was made.")}


def run_command(argv, cwd: Path, env: dict[str, str], timeout: int = PREFLIGHT_TIMEOUT):
    try:
        result = subprocess.run(list(argv), cwd=str(cwd), env=dict(env), capture_output=True,
                                text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return result.returncode, result.stdout


def read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def preflight(run_dir: Path, profile_env: Path) -> dict:
    """Attest the isolated profile and leave `<run_dir>/preflight.json`. Never runs a model."""
    run_dir = Path(run_dir).resolve()
    if not run_dir.is_dir():
        raise ValueError("RUN_DIR_MISSING")
    try:
        env = parse_profile_env(Path(profile_env).read_text(encoding="utf-8"))
    except OSError:
        env = {}
    home = env.get("HOME", "").rstrip("/")
    command_reasons: list[str] = []
    child_env = {**os.environ, **env}
    if not home:
        command_reasons.append("PREFLIGHT_PROFILE_ENV_UNREADABLE" if not env
                               else "PREFLIGHT_NO_PROFILE_HOME")
    outputs = {"paths": "", "config": ""}
    for name in ("paths", "config"):
        if command_reasons:
            continue
        code, out = run_command(["opencode", "debug", name], run_dir, child_env)
        if code != 0:
            command_reasons.append(f"PREFLIGHT_COMMAND_FAILED:{name}")
            continue
        outputs[name] = out
    config_file = None
    if home:
        config_file = read_bytes(Path(home) / CONFIG_DIR_REL / CONFIG_NAME)
    verdict = evaluate_preflight(outputs["paths"], outputs["config"],
                                 profile_home=home or "<NO_PROFILE_HOME>",
                                 template=read_bytes(CONFIG_TEMPLATE),
                                 config_file=config_file)
    if command_reasons:
        verdict["reasons"] = sorted(set(verdict["reasons"]) | set(command_reasons))
        verdict["verdict"] = "FAIL"
    verdict["commands_run"] = ([["opencode", "debug", name] for name in ("paths", "config")]
                               if not command_reasons else [])
    (run_dir / "preflight.json").write_text(json.dumps(verdict, indent=2) + "\n",
                                            encoding="utf-8")
    return verdict


# --- check: the real event stream --------------------------------------------------------

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


def sources_claims(texts) -> tuple[dict | None, set[str]]:
    """The MCP / plugin / skill claim comes ONLY from the machine-readable line (F5)."""
    lines = [line.strip() for text in texts for line in text.splitlines()
             if line.strip().startswith(SOURCES_PREFIX)]
    if len(lines) != 1:
        return None, {"NO_SOURCES_LINE"}
    match = SOURCES_RE.match(lines[0])
    if match is None:
        return None, {"NO_SOURCES_LINE"}
    skills = [name.strip() for name in match.group(3).split(",") if name.strip()]
    claims = {"mcp": int(match.group(1)), "plugin_agents": int(match.group(2)),
              "skills": skills}
    reasons: set[str] = set()
    if claims["mcp"]:
        reasons.add("MCP_CONTAMINATION")
    if claims["plugin_agents"]:
        reasons.add("PLUGIN_AGENT_CONTAMINATION")
    if set(skills) - ALLOWED_SKILLS or any(not IDENTIFIER_RE.fullmatch(n) for n in skills):
        reasons.add("SKILL_CATALOGUE_CONTAMINATION")
    return claims, reasons


def text_reasons(text: str, run_dir: Path, repo_read: bool, nested_read: bool) -> set[str]:
    """Instruction-source paths and injected skill content, read line by line.

    MCP / plugin-agent / skill *claims* are deliberately absent here: they come from the
    machine-readable sources line (`sources_claims`), so prose can no longer fabricate or hide
    them. The checks below are content markers and path rules, not self-report.
    """
    reasons: set[str] = set()
    for line in text.splitlines():
        folded = line.casefold()
        if "skill" in folded and ("<skills_instructions>" in folded or "skill.md" in folded):
            reasons.add("FORBIDDEN_CONTEXT")
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
    claims, claim_reasons = sources_claims(
        event["part"]["text"] for event in events
        if isinstance(event, dict) and event.get("type") == "text"
        and isinstance(event.get("part"), dict)
        and isinstance(event["part"].get("text"), str))
    reasons |= claim_reasons
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
            "sources_line": claims,
            "event_count": len(events),
            "observation_scope": "Observable JSON events only; hidden runtime context is not observable."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare").add_argument("run_dir", type=Path)
    commands.add_parser("check").add_argument("events", type=Path)
    pre = commands.add_parser("preflight")
    pre.add_argument("run_dir", type=Path)
    pre.add_argument("--profile-env", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare(args.run_dir))
        return 0
    if args.command == "preflight":
        try:
            verdict = preflight(args.run_dir, args.profile_env)
        except ValueError as exc:
            print(json.dumps({"verdict": "FAIL", "reasons": [str(exc)]}, indent=2))
            return 1
        print(json.dumps(verdict, indent=2))
        return 0 if verdict["verdict"] == "PASS" else 1
    verdict = check_stream(args.events.read_text(encoding="utf-8"), args.events.resolve().parent)
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
