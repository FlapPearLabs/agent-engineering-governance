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
  * the `workdir` of a shell tool call (F43): it is the directory the command starts in, so it is
    judged like a path — outside the run directory and the allow-list is a hit — and it is the base
    that every relative token of that command, every `cd` in it and git's effective repository
    resolve against. A missing `workdir` means the run directory, as before. 85 of the 149 real
    shell calls across the pilot set carry it, and ignoring it reported the live pilot #9 stream
    INVALID for `>> ../.h2-telemetry.log` issued with `workdir = <run>/repo`, which is
    `<run>/.h2-telemetry.log` — inside the run;
  * for glob/grep-style tools (F43, defensive: no live stream has done it yet), a `pattern` or
    `include` value that is itself a place rather than a name — an absolute path, or one carrying a
    `..` segment — judged like a path against the tool's own `path`, or the run directory;
  * the same rule applied to every token of a shell command (`shell`, and `bash` for streams that
    still name it that way) after `--flag=value` and `KEY=value` splitting. The command is
    tokenised with SHELL PUNCTUATION, so `a && b; c | d` yields `a`, `b`, `c`, `d`, not one token
    whose path is glued to a separator (F12: `source /dev/null;` used to report `/dev/null;`).
    `~` and `$HOME` resolve to the profile home the worker was launched with, never to the
    operator's; a fixture may write the neutral token `<RUN_ROOT>`, which resolves to the run
    directory. Every token — the value of a `NAME=value` assignment included — resolves against
    the working directory the SAME command established with a preceding `cd`, not against the run
    directory: `cd repo && T=../.tmp/probe` names `<run>/.tmp/probe`, which is inside, while
    `cd repo && T=../../x` names the parent of the run and is a hit (F27b). The operand of a `cd`
    is the one exception to reading left to right, because it names the directory the tokens
    after it are judged in: `cd repo ... cd ..` returns to `<run>` and is judged against
    `<run>/repo` before the return, so a scripted excursion into `repo/` and back is not an
    escape (F42);
  * a diff path in the `patch` tool's `patchText` (`--- a/x`, `+++ b/x`, `diff --git a/x b/x`);
  * `git push`, `git ls-remote`, `git submodule`, `git remote add|set-url|update|prune|rename|
    remove`, and a git command whose EFFECTIVE repository — the working directory after any `cd`
    in the same command, then every `-C`, `--git-dir` and `--work-tree` — resolves outside the run
    directory AND outside the OS temp roots (F13: a run may legitimately archive its base into a
    temp directory and run git and tests there; the `-C` of another program in the same pipeline,
    such as `tar -x -C`, is not git's);
  * `git clone/fetch/pull` judged by its SOURCE (F27a): a LOCAL path that resolves, after any `cd`
    or `-C`, inside the run directory is the run's own repository being copied and is not an
    escape, while a URL, an scp `host:path` form, a local path outside the run directory (the OS
    temp roots included: a source there is another repository whose provenance the audit cannot
    establish) or no source at all stays a hit. A bare name is a local path only for `clone`; for
    `fetch` and `pull` it is a remote name unless it is path-shaped (`x/…`, `./…`, `../…`);
  * any tool that is not in `TOOL_ALLOW` (`webfetch`, `task`, `skill`, an `mcp__` tool …): a tool
    whose accesses this stream cannot show is not auditable from here.

The allow-list is frozen to what a test run genuinely needs: the pinned interpreter (its path and
prefix), `/usr`, `/bin`, `/sbin`, `/opt/homebrew`, `/System`, `/Library/Developer`, the OS temp
roots and `/dev/null`. Everything else is out of run. The git location flags are judged against
the run directory and, for the F13 reason above, the temp roots: a temp directory is a legitimate
scratch target and a legitimate place to run git in; every other repository is foreign.

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
TOOL_ALLOW = frozenset({"read", "write", "edit", "multiedit", "patch", "bash", "shell", "glob",
                        "grep", "list", "todowrite", "todoread"})
PATH_TOOLS = frozenset({"read", "write", "edit", "multiedit", "patch", "glob", "grep", "list"})
# F10: opencode's isolated profile names the shell tool `shell`, not `bash` (measured live).
SHELL_TOOLS = frozenset({"bash", "shell"})
PATH_KEYS = ("path", "filePath", "file_path", "directory", "dir")
COMMAND_KEYS = ("command", "cmd")
# F43: the shell tool's starting directory, and the pattern-carrying keys of the search tools.
SHELL_WORKDIR_KEYS = ("workdir",)
SEARCH_TOOLS = frozenset({"glob", "grep"})
SEARCH_PATH_KEYS = ("pattern", "include")
SYSTEM_ALLOW = ("/usr", "/bin", "/sbin", "/opt/homebrew", "/System", "/Library/Developer",
                "/dev/null", "/dev/stdout", "/dev/stderr")
# The OS temp roots a test run may legitimately write to. The broad `/var/folders` prefix is NOT
# allowed: only the temp dir itself and `/tmp` (with the real path its symlink points to, added in
# `allowed_roots`), so that a `..` escape from the wrapper lands outside this list and is reported.
TEMP_ALLOW = ("/tmp",)  # its resolved symlink target is added by allowed_roots
# F27a: clone/fetch/pull are judged by their source; push/ls-remote/submodule always reach outward.
GIT_LOCAL_SOURCE_SUBCOMMANDS = frozenset({"clone", "fetch", "pull"})
GIT_ALWAYS_REMOTE_SUBCOMMANDS = frozenset({"push", "ls-remote", "submodule"})
GIT_REMOTE_SUBCOMMANDS = frozenset({"add", "set-url", "update", "prune", "rename", "remove"})
GIT_REMOTE_PREFIXES = ("http://", "https://", "ssh://", "git://", "ftp://", "ftps://", "file://")
# `host:path` / `user@host:path`: a colon before any slash is a remote, not a local path.
GIT_SCP_RE = re.compile(r"^[^/\s]+:")
GIT_LOCATION_FLAGS = ("--git-dir=", "--work-tree=")
# Shell control operators: a command list is analysed segment by segment (F12), and a git argument
# list ends at the first operator, so `tar -x -C <dir>` after a pipe is never read as git's own -C.
OPERATORS = frozenset({";", ";;", "&", "&&", "|", "||", "(", ")", "{", "}", "\n"})
DIFF_PATH_RE = re.compile(r"^(?:diff --git a/(?P<both>\S+)|--- a/(?P<old>\S+)|\+\+\+ b/(?P<new>\S+))$",
                          re.M)
# F16 / T29: constructs a static tokenizer cannot resolve. They are EVIDENCE, not hits: the OS
# sandbox is the enforcing barrier, and a denied dynamic attempt obtained nothing.
INTERPRETERS = frozenset({"python", "python3", "sh", "bash", "zsh", "perl", "ruby", "node"})
DECODERS = frozenset({"base64", "xxd"})
UNRESOLVED_REASONS = {"command_substitution": "COMMAND_SUBSTITUTION",
                      "backtick": "BACKTICK", "eval": "EVAL", "inline_program": "INLINE_PROGRAM",
                      "decoder": "DECODER", "xargs": "XARGS"}
DENIED_TEXT = "operation not permitted"
DENIED_REASON = "SANDBOX_DENIED"
ABS_PATH_RE = re.compile(r"/[^\s'\"`:,;()\[\]{}<>]+")


def allowed_roots(python: str | None = None) -> tuple[str, ...]:
    """The frozen system allow-list; the interpreter is resolved, never hard-coded."""
    interpreter = Path(python or sys.executable).resolve()
    values = {*SYSTEM_ALLOW, *TEMP_ALLOW, str(interpreter), str(interpreter.parent),
              str(Path(sys.prefix).resolve()), str(Path(tempfile.gettempdir()).resolve())}
    values |= {os.path.realpath(value) for value in list(values)}
    return tuple(sorted(values))


def temp_roots() -> tuple[str, ...]:
    """The OS temp roots a run may treat as scratch, including as a git working directory (F13)."""
    values = {*TEMP_ALLOW, str(Path(tempfile.gettempdir()).resolve())}
    values |= {os.path.realpath(value) for value in list(values)}
    return tuple(sorted(values))


def resolve(value: str, run_dir: Path, home: str | None, base: str | None = None) -> str | None:
    """An absolute path for one value, or None when `~`/`$HOME` cannot be resolved.

    `base` is the directory a relative value is resolved against: the run directory by default,
    or the working directory a preceding `cd` established inside the same shell command.
    """
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
        text = os.path.join(base or str(run_dir), text)
    return os.path.realpath(text)


def inside(path: str, root: str) -> bool:
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root + os.sep)


def path_reason(value: str, run_dir: Path, home: str | None,
                allow: tuple[str, ...], base: str | None = None) -> str | None:
    resolved = resolve(value, run_dir, home, base=base)
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


def shell_tokens(command: str) -> list[str]:
    """Shell tokens with punctuation split off, so a separator is never glued to a path (F12)."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError:
        return command.split()


def git_subcommand(args: list[str]) -> tuple[str, list[str]]:
    """The subcommand of one git argument list and its positional arguments.

    Global options that consume a value (`-C <dir>`, `--git-dir <dir>`, `--work-tree <dir>`) are
    skipped, so `git -C repo clone repo .tmp/x` is read as `clone` with two operands.
    """
    index = 0
    while index < len(args):
        argument = args[index]
        if argument in ("-C", "--git-dir", "--work-tree") and index + 1 < len(args):
            index += 2
            continue
        if argument.startswith("-"):
            index += 1
            continue
        return argument, [item for item in args[index + 1:] if not item.startswith("-")]
    return "", []


def remote_source(value: str) -> bool:
    """A URL or an scp `host:path` form: a source that is not a local path at all."""
    return value.startswith(GIT_REMOTE_PREFIXES) or bool(GIT_SCP_RE.match(value))


def local_source(value: str, cwd: str, run_dir: Path, home: str | None,
                 path_shaped_only: bool) -> bool:
    """True when `value` is the run's own repository, reached from the current directory."""
    if remote_source(value):
        return False
    if path_shaped_only and "/" not in value and not value.startswith("."):
        return False
    resolved = resolve(value, run_dir, home, base=cwd)
    return bool(resolved) and inside(resolved, str(run_dir))


def git_argument_hits(args: list[str], command: str, cwd: str, run_dir: Path,
                      home: str | None, temps: tuple[str, ...]) -> list[dict]:
    """One git invocation: remote escapes, and a foreign effective repository (F13 / F27a)."""
    hits: list[dict] = []
    repo = cwd
    unresolved: str | None = None
    for position, argument in enumerate(args):
        following = args[position + 1:position + 2]
        targets = []
        if argument == "-C" and following:
            targets.append(following[0])
        targets.extend(argument[len(flag):] for flag in GIT_LOCATION_FLAGS
                       if argument.startswith(flag))
        for target in targets:
            resolved = resolve(target, run_dir, home, base=repo)
            if resolved is None:
                unresolved = target
            else:
                repo = resolved
    subcommand, operands = git_subcommand(args)
    remote_hit = False
    if subcommand in GIT_ALWAYS_REMOTE_SUBCOMMANDS:
        remote_hit = True
    elif subcommand == "remote" and operands and operands[0] in GIT_REMOTE_SUBCOMMANDS:
        remote_hit = True
    elif subcommand in GIT_LOCAL_SOURCE_SUBCOMMANDS:
        # F27a: the source of a clone/fetch/pull is the run's own repository when it resolves
        # inside the run directory; everything else (a URL, an scp form, a path outside, no
        # operand at all) still reaches outward.
        path_shaped_only = subcommand != "clone"
        if not operands or not all(local_source(value, cwd, run_dir, home, path_shaped_only)
                                   for value in operands):
            remote_hit = True
    if remote_hit:
        hits.append({"tool": "shell", "reason": "GIT_REMOTE_REPOSITORY",
                     "value": command, "path": subcommand or "git"})
    if unresolved is not None:
        hits.append({"tool": "shell", "reason": "GIT_FOREIGN_REPOSITORY",
                     "value": command, "path": unresolved})
    elif not inside(repo, str(run_dir)) and not any(inside(repo, root) for root in temps):
        hits.append({"tool": "shell", "reason": "GIT_FOREIGN_REPOSITORY",
                     "value": command, "path": repo})
    return hits


def cd_argument(tokens: list[str], index: int) -> tuple[str | None, int]:
    """The operand of the `cd` whose token ends at `index - 1`, and the index after it.

    F42 / T40: a `cd` consumes its operand, so the operand is never read again as a command of its
    own (a directory literally named `git` is not a `git` invocation).
    """
    following = tokens[index:index + 1]
    if not following or following[0] in OPERATORS:
        return None, index
    return following[0], index + 1


def git_hits(tokens: list[str], run_dir: Path, home: str | None,
             cwd: str | None = None) -> list[dict]:
    """Shell `git` invocations that reach another repository.

    The working directory follows a `cd` in the same command list; an argument list ends at the
    first control operator. Both are what make a scripted `cd <run> && ... && git -C repo ...`
    judgeable, and what keeps another program's `-C` out of git's argument list (F12 / F13).
    F42 / T40: the `cd` operand is consumed, so it can never be mistaken for a `git` invocation.
    F43: `cwd` is the tool call's `workdir` when it has one, the run directory otherwise.
    """
    hits: list[dict] = []
    command = " ".join(tokens)
    temps = temp_roots()
    cwd = cwd or str(run_dir)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if token in OPERATORS:
            continue
        name = PurePosixPath(token).name
        if name == "cd":
            argument, index = cd_argument(tokens, index)
            if argument is None:
                continue
            resolved = resolve(argument, run_dir, home, base=cwd)
            if resolved:
                cwd = resolved
            continue
        if name != "git":
            continue
        args: list[str] = []
        for argument in tokens[index:]:
            if argument in OPERATORS:
                break
            args.append(argument)
        hits.extend(git_argument_hits(args, command, cwd, run_dir, home, temps))
    return hits


def shell_hits(command: str, run_dir: Path, home: str | None, allow: tuple[str, ...],
               cwd: str | None = None) -> list[dict]:
    """Every path-shaped token of one shell command, plus the git rules above.

    F27b: resolution follows the working directory the same command established with `cd`, so an
    assignment and any other relative token are judged against where the worker actually stood.
    F42 / T40: the operand of a `cd` is judged against the working directory BEFORE that `cd` (it
    is the directory the tokens after it are judged in), so `cd repo ... cd ..` is a return into
    the run directory, not an escape from it.
    F43: `cwd` is the tool call's `workdir` (the directory the command starts in) when it has one,
    the run directory otherwise; the `cd` tracking and `git_hits` start from the same place.
    """
    tokens = shell_tokens(command)
    hits: list[dict] = []

    def judge(values: list[str], base: str) -> None:
        for value in values:
            reason = path_reason(value, run_dir, home, allow, base=base)
            if reason:
                hits.append({"tool": "shell", "reason": reason, "value": command.strip(),
                             "path": value})

    cwd = cwd or str(run_dir)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if token in OPERATORS:
            continue
        judge(token_values(token), cwd)
        if PurePosixPath(token).name != "cd":
            continue
        argument, index = cd_argument(tokens, index)
        if argument is None:
            continue
        judge(token_values(argument), cwd)
        resolved = resolve(argument, run_dir, home, base=cwd)
        if resolved:
            cwd = resolved
    hits.extend(git_hits(tokens, run_dir, home, cwd))
    return hits


def shell_workdir(inputs: dict, run_dir: Path, home: str | None,
                  allow: tuple[str, ...]) -> tuple[str, list[dict]]:
    """F43: the directory one shell command starts in, and a hit when that place is out of run.

    The `workdir` is a path like any other (a relative value resolves against the run directory,
    `~`/`$HOME` against the profile home) and is judged with the same allow-list. An unreadable or
    absent value leaves the run directory as the base, which is what the audit always assumed.
    """
    base = str(run_dir)
    hits: list[dict] = []
    for key in SHELL_WORKDIR_KEYS:
        value = inputs.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        reason = path_reason(value, run_dir, home, allow)
        if reason:
            hits.append({"reason": reason, "value": value})
        resolved = resolve(value, run_dir, home)
        if resolved:
            base = resolved
    return base, hits


def search_input_hits(inputs: dict, run_dir: Path, home: str | None,
                      allow: tuple[str, ...]) -> list[dict]:
    """F43: a glob/grep `pattern`/`include` that is a place, judged against the tool's `path`.

    A pattern is a name (`*.py`) until it is absolute or carries a `..` segment; then it names a
    directory tree, and it is judged like any other path token. No live stream has done this yet;
    the rule is here so that the audit does not depend on that luck.
    """
    base = str(run_dir)
    raw = inputs.get("path")
    if isinstance(raw, str) and raw.strip():
        resolved = resolve(raw, run_dir, home)
        if resolved:
            base = resolved
    hits: list[dict] = []
    for key in SEARCH_PATH_KEYS:
        value = inputs.get(key)
        if not isinstance(value, str) or not path_shaped_search(value):
            continue
        reason = path_reason(value, run_dir, home, allow, base=base)
        if reason:
            hits.append({"reason": reason, "value": value})
    return hits


def path_shaped_search(value: str) -> bool:
    """True when a search pattern names a place: absolute, `~`/`$HOME`, or with a `..` segment."""
    text = value.strip().strip("'\"")
    if not text:
        return False
    if text.startswith(("/", RUN_ROOT, "$HOME", "${HOME}")) or text == "~" or text.startswith("~/"):
        return True
    return ".." in PurePosixPath(text).parts


def unresolved_constructs(command: str) -> list[str]:
    """The F16 constructs of one shell command: evidence that static resolution is incomplete."""
    found: list[str] = []
    if "$(" in command:
        found.append(UNRESOLVED_REASONS["command_substitution"])
    if "`" in command:
        found.append(UNRESOLVED_REASONS["backtick"])
    tokens = shell_tokens(command)
    names = [PurePosixPath(token).name for token in tokens]
    if "eval" in names:
        found.append(UNRESOLVED_REASONS["eval"])
    for index, token in enumerate(tokens):
        if token == "-c" and index and names[index - 1] in INTERPRETERS:
            found.append(UNRESOLVED_REASONS["inline_program"])
            break
    if any(name in DECODERS for name in names):
        found.append(UNRESOLVED_REASONS["decoder"])
    if "xargs" in names:
        found.append(UNRESOLVED_REASONS["xargs"])
    return sorted(set(found))


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def sandbox_denied(event, run_dir: Path) -> list[dict]:
    """F16 / T29, tightened by F29: a denial line of a tool result naming an outside path.

    This is recorded as evidence, never as a hit: the attempt obtained nothing, and the run is
    reported in the closure report rather than invalidated for what the barrier already stopped.
    The EPERM text and the path must sit on the SAME line of the tool output: a file whose content
    merely contains "Operation not permitted" is a document, not a denial (F29). The comparison is
    against the launch directory only: a shared temporary root is legitimately allow-listed for
    static tokens, but a denied read below it is still a denied read.
    """
    text = "\n".join(strings(event))
    entries: list[dict] = []
    seen: set[str] = set()
    for line in text.splitlines():
        if DENIED_TEXT not in line.casefold():
            continue
        for candidate in ABS_PATH_RE.findall(line):
            if candidate in seen or inside(os.path.realpath(candidate), str(run_dir)):
                continue
            seen.add(candidate)
            entries.append({"reason": DENIED_REASON, "path": candidate,
                            "value": line.strip()[:300]})
    return entries


def egress_denied(log_path) -> list[dict]:
    """F26 / T36b: the DENY lines of one launch's egress log.

    The allowlist proxy (`egress_v2.py`) writes one line per request. A DENY line means the
    sandboxed process asked for a host the proxy refused, so nothing crossed: like `sandbox_denied`
    this is EVIDENCE reported per run, never a hit and never a verdict by itself. The field is
    attached by the driver, which owns the log path; this function only reads the log.
    """
    path = Path(log_path)
    if not path.is_file():
        return []
    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("verdict") == "DENY":
            entries.append(entry)
    return entries


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
        base, workdir_hits = shell_workdir(inputs, run_dir, home, allow)
        hits.extend({**hit, "event": index, "tool": tool} for hit in workdir_hits)
        for key in COMMAND_KEYS:
            command = inputs.get(key)
            if isinstance(command, str):
                hits.extend({**hit, "event": index, "tool": tool}
                            for hit in shell_hits(command, run_dir, home, allow, cwd=base))
    if tool in SEARCH_TOOLS:
        hits.extend({**hit, "event": index, "tool": tool}
                    for hit in search_input_hits(inputs, run_dir, home, allow))
    if tool == "patch":
        for value in patch_paths(inputs.get("patchText")):
            reason = path_reason(value, run_dir, home, allow)
            if reason:
                hits.append({"event": index, "tool": tool, "reason": reason, "value": value})
    return hits


def event_evidence(event, run_dir: Path) -> dict:
    """F16 / T29: the evidence fields that never change a verdict by themselves."""
    evidence = {"unresolved_constructs": [], "sandbox_denied": []}
    if not isinstance(event, dict) or event.get("type") != "tool_use":
        return evidence
    part = event.get("part") if isinstance(event.get("part"), dict) else {}
    tool = part.get("tool")
    state = part.get("state") if isinstance(part.get("state"), dict) else {}
    inputs = state.get("input") if isinstance(state.get("input"), dict) else {}
    if tool in SHELL_TOOLS:
        for key in COMMAND_KEYS:
            command = inputs.get(key)
            if isinstance(command, str):
                for construct in unresolved_constructs(command):
                    evidence["unresolved_constructs"].append(
                        {"tool": tool, "construct": construct,
                         "command": command.strip()[:200]})
    evidence["sandbox_denied"] = sandbox_denied(event, run_dir)
    return evidence


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
              "sandbox_scope": ("The OS sandbox is the enforcing barrier (F16); a denied dynamic "
                                "attempt obtained nothing and is recorded as sandbox_denied, not "
                                "as a hit."),
              "hits": [], "unresolved_constructs": [], "sandbox_denied": [],
              "events": 0, "tool_calls": 0, "verdict": "PASS"}
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
            evidence = event_evidence(event, run_dir)
            for field in ("unresolved_constructs", "sandbox_denied"):
                for candidate in evidence[field]:
                    key = json.dumps(candidate, sort_keys=True)
                    if key not in seen:
                        seen.add(key)
                        result[field].append(candidate)
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
