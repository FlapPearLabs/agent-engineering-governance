#!/usr/bin/env python3
"""Out-of-run access audit of one run's event stream (F9 / T22), classified per hit (T46).

The worker contract confines every tool call to the wrapper, but nothing read the evidence that
already exists: `events.jsonl` records the input of every tool call — read/glob/grep/edit/write
paths and shell commands. This module replays that stream and reports, verbatim, every access that
resolves outside the run directory, plus every shell `git` invocation that tries to reach another
repository and every tool outside the frozen allow-list. Every hit is CLASSIFIED (T46, user decision
A): a hit that the launch's own rendered sandbox and the frozen egress allowlist provably refuse is
`DENIED_BY_POLICY` — recorded as `denied_attempts` and reported per arm, not a verdict — while a hit
that could have succeeded keeps making the run INVALID:OUT_OF_RUN_ACCESS; the run is registered and
never re-run (protocol-v2 §6). An access that DID succeed is a breach (INVALID:SANDBOX_BREACH).

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

A JSONL stream is split on "\n" only (F46): a JSON line ends at a newline and nowhere else, while
`str.splitlines()` also breaks on U+2028, U+2029, U+0085, `\v`, `\f` and `\x1c`–`\x1e`. Live pilot
h2r2-f01-c recorded one valid event whose shell command carried those characters inside a regex
string; read with `splitlines()` it became five lines and five MALFORMED_EVENT_LINE hits, and the run
was registered INVALID:MALFORMED_EVENT_LINES:5. A truncated line is still malformed.

A script, program or pattern operand is not a place (F47): the first non-option operand of `sed`
(its script), of `awk`/`gawk` (its program) and of `grep`/`egrep`/`fgrep`/`rg` (its pattern), and
every `-e`/`--expression`/`--regexp` value, is text the program interprets, not a path. A live
h2r2-f03-c stream was reported PATH_OUTSIDE_RUN for the `/^ROUTE …$/d` script of
`sed -i '' … .h2-telemetry.log`. `-f`/`--file` names a FILE and stays a path, as does every other
operand — including the input files after the script — judged exactly as before.

A heredoc body is NOT shell syntax and is never judged as one (F45): the lines after a `<<WORD`,
`<<-WORD`, `<<'WORD'` or `<<"WORD"` operator up to the line holding exactly WORD are stdin data for
the command that carries the operator, so they are cut before tokenising. The operator's own line —
command words, arguments, redirect targets such as `cat <<EOF > x` — is judged exactly as before. A
body fed to an interpreter (`python - <<'PY'`, `node`, `sh` …) is recorded as HEREDOC_PROGRAM
evidence, like the program of `-c`: what it does with files is a dynamic construct the sandbox
enforces.

The allow-list is frozen to what a test run genuinely needs: the pinned interpreter (its path and
prefix), `/usr`, `/bin`, `/sbin`, `/opt/homebrew`, `/System`, `/Library/Developer`, the OS temp
roots and `/dev/null`. Everything else is out of run. The git location flags are judged against
the run directory and, for the F13 reason above, the temp roots: a temp directory is a legitimate
scratch target and a legitimate place to run git in; every other repository is foreign.

T46 — WHETHER THE ATTEMPT COULD HAVE SUCCEEDED. The static audit was the only barrier when the
OUT_OF_RUN_ACCESS rule was made (F9). Since F16/F26/F31 the OS sandbox and the egress allowlist
enforce confinement, and the independent reviewer's own attacks were denied by them. A denied
attempt obtains nothing, so it cannot contaminate a result; invalidating it only removes valid
pairs — the 4-run pilot batch lost two of four runs to path typos, one of them an interpreter path
under the operator home that is not the allowed prefix, the other a misspelled run dir under the
shared runs root. The class of a hit is therefore decided from the launch's ARCHIVED rendered
profile and the frozen egress allowlist, NEVER from the worker's text:

  * `DENIED_BY_POLICY` — the access cannot succeed: the path resolves under a root the profile
    denies (`/Users`, `/private/tmp`, `/var/folders`, `/private/var/folders` and their aliases) and
    under no path that profile re-allows for that access type (launch dir, fresh home, interpreter
    prefix; an ancestor `literal` re-allows only that exact node — a directory listing — never a
    path below it), or the target is a network location whose host the allowlist does not carry.
    These are EVIDENCE: `denied_attempts`, with their count, per run.
  * `POSSIBLE_SUCCESS` — every other out-of-run hit, including every hit this audit cannot decide
    (no archived profile, an unresolvable `~`/`$HOME`, a tool outside the allow-list, a malformed
    line) and a readable system file such as `/etc/hosts` that is not on the system allow-list:
    the access could have succeeded, so the run keeps INVALID:OUT_OF_RUN_ACCESS exactly as before.

Independently of any static hit, an EMPIRICAL BREACH makes the run INVALID:SANDBOX_BREACH: a
`read` tool result that returned file CONTENT for a path under a denied root the profile does not
re-allow, an `ALLOW` line in the launch's `egress.jsonl` for a host off the allowlist, or a
confinement self-test that failed and was not caught before the launch (`breach`). T52: only a
`read` result is file content; a `glob`/`grep`/`list` result is a listing or a match, and a
message that merely mentions a path is text — neither is evidence that the denied bytes were
obtained.

T52 — THE ALLOW-LIST AND THE EMPIRICAL CONFIRMATION.

  * The system allow-list carries the pinned interpreter's REAL install prefix and stdlib
    directory, resolved the way the launch's profile resolves them (T51.3), not only `sys.prefix`
    of whatever interpreter runs the audit: a venv's `sys.prefix` is the venv, while the standard
    library lives under `sys.base_prefix`, and a worker reading
    `<base_prefix>/lib/pythonX.Y/unittest/loader.py` was reported INVALID:OUT_OF_RUN_ACCESS for
    reading the very interpreter it was launched with (live H2-R2 h2r2-f03-c).
  * POSSIBLE_SUCCESS is kept for an access that could still have succeeded. A READ of a path that
    does not exist — checked against the run's post-launch SNAPSHOT and the filesystem — is
    provisional denial evidence; a recorded successful content result overrides that inference.
    A token carrying glob syntax is a pattern, not a place, and is never existence-checked: the pattern
    string need not exist for the glob to match files that do. A WRITE outside the launch's write
    whitelist is the same: the profile's `(deny file-write* (subpath "/"))` proves it cannot be
    created. When the driver collected the launch's sandbox violation log (T51.4,
    `violations.jsonl`), a same-kind path denial within the supplied launch window can confirm
    that class; absent or uncorrelated evidence cannot change it.
  * A URL's host is the authority AFTER any `user:pass@` credential prefix: `https://u:p@host/x`
    names `host`, not `u` (review finding 3).
  * A read of a path that exists keeps POSSIBLE_SUCCESS: `/etc/hosts` is readable and is not on
    the frozen list, so reading it still invalidates the run.

Scope of the verdict: OBSERVABLE tool calls only. Hidden runtime context, and any access a tool
performs internally without reporting it, is not observable from the event stream.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys
import sysconfig
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath

from egress_v2 import EGRESS_ALLOW

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
# T52: the program run to read a FOREIGN interpreter's install prefix and stdlib directory; the
# running interpreter answers for itself, so the common case starts no process.
INTERPRETER_PROBE = ("import json, sys, sysconfig\n"
                     "print(json.dumps({'base_prefix': sys.base_prefix, 'prefix': sys.prefix,\n"
                     "                  'stdlib': sysconfig.get_path('stdlib')}))\n")
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
# F47 / T45: the program whose first non-option operand is a script/program/pattern, not a place,
# the options whose VALUE is such a pattern, and the options whose value is a FILE of them.
SCRIPT_TOOLS = frozenset({"sed", "gsed", "awk", "gawk", "grep", "egrep", "fgrep", "rg"})
SCRIPT_VALUE_FLAGS = {"sed": ("-e", "--expression"), "gsed": ("-e", "--expression"),
                      "grep": ("-e", "--regexp"), "egrep": ("-e", "--regexp"),
                      "fgrep": ("-e", "--regexp"), "rg": ("-e", "--regexp")}
SCRIPT_FILE_FLAGS = ("-f", "--file")
DIFF_PATH_RE = re.compile(r"^(?:diff --git a/(?P<both>\S+)|--- a/(?P<old>\S+)|\+\+\+ b/(?P<new>\S+))$",
                          re.M)
# F16 / T29: constructs a static tokenizer cannot resolve. They are EVIDENCE, not hits: the OS
# sandbox is the enforcing barrier, and a denied dynamic attempt obtained nothing.
INTERPRETERS = frozenset({"python", "python3", "sh", "bash", "zsh", "perl", "ruby", "node"})
DECODERS = frozenset({"base64", "xxd"})
UNRESOLVED_REASONS = {"command_substitution": "COMMAND_SUBSTITUTION",
                      "backtick": "BACKTICK", "eval": "EVAL", "inline_program": "INLINE_PROGRAM",
                      "decoder": "DECODER", "xargs": "XARGS",
                      "heredoc_program": "HEREDOC_PROGRAM"}
DENIED_TEXT = "operation not permitted"
DENIED_REASON = "SANDBOX_DENIED"
ABS_PATH_RE = re.compile(r"/[^\s'\"`:,;()\[\]{}<>]+")
# F45 / T43: `<<WORD`, `<<-WORD`, `<<'WORD'` and `<<"WORD"`; the quoted forms keep their bytes but
# the delimiter that ends the body is the word itself.
HEREDOC_OPERATOR_RE = re.compile(
    r"(?P<operator><<(?P<dash>-)?[ \t]*)"
    r"(?:'(?P<single>[^']*)'|\"(?P<double>[^\"]*)\"|(?P<word>[^\s;&|<>()]+))")

# T46: the two classes of one hit, the profile rules they are decided from, and the breach kinds.
DENIED_BY_POLICY = "DENIED_BY_POLICY"
POSSIBLE_SUCCESS = "POSSIBLE_SUCCESS"
HIT_CLASSES = (DENIED_BY_POLICY, POSSIBLE_SUCCESS)
# T52: the two policy facts that make a hit evidence even when the profile rules are silent, and
# the `policy` field a hit carries when one of them decided it.
PATH_NOT_FOUND = "PATH_DOES_NOT_EXIST"
VIOLATION_CONFIRMED = "VIOLATION_LOG"
# The tools whose RESULT carries file CONTENT, and the tools whose input is a write (never read-only).
# T52: a glob/grep/list result is a listing or a match, not the bytes of the path — only `read`
# returns a file's content, so only `read` can turn a denied path into a breach.
CONTENT_TOOLS = frozenset({"read"})
WRITE_TOOLS = frozenset({"write", "edit", "multiedit", "patch"})
READ_OPS = frozenset({"file-read-data", "file-read*"})
WRITE_OPS = frozenset({"file-write*", "file-write-data", "file-write-create"})
ALLOW_RULE_RE = re.compile(r"^\(allow\s+(?P<ops>[a-z0-9*-]+(?:\s+[a-z0-9*-]+)*)")
DENY_RULE_RE = re.compile(r"^\(deny\s+(?P<ops>[a-z0-9*-]+(?:\s+[a-z0-9*-]+)*)")
RULE_CLAUSE_RE = re.compile(r"\((literal|subpath|regex)\s+(?:\"([^\"]*)\"|#\"([^\"]*)\"#)\)")
# T52: the authority of a URL, credentials included; the host is extracted after the last `@`.
URL_AUTHORITY_RE = re.compile(r"[a-z][a-z0-9+.-]*://(?P<authority>[^/\s?#]+)", re.IGNORECASE)
HOSTNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z][A-Za-z0-9-]*$")
BREACH_DENIED_CONTENT = "READ_CONTENT_UNDER_DENIED_ROOT"
BREACH_EGRESS = "EGRESS_ALLOW_NOT_ALLOWLISTED"
BREACH_CONFINEMENT = "CONFINEMENT_SELF_TEST_FAILED"
BREACH_PREFIX = "SANDBOX_BREACH"
# T52: the record keys a T51.4 violation line may use for the place it names.
VIOLATION_PATH_KEYS = ("path", "file", "target")
VIOLATION_HOST_KEYS = ("host", "domain")
# T52: a token that carries glob syntax is a PATTERN, not a literal place: the glob can match files
# that exist even though the pattern string itself does not, so existence never decides its class.
GLOB_META_RE = re.compile(r"[*?\[\]{}]")


def interpreter_report(executable: Path) -> dict | None:
    """The install prefix and stdlib of a FOREIGN interpreter, or None when it cannot be asked.

    The running interpreter answers about itself without a process (see `interpreter_prefixes`);
    this is the fallback that keeps a re-audit with a different interpreter honest instead of
    allow-listing the auditor's own tree as if it were the worker's.
    """
    try:
        completed = subprocess.run([str(executable), "-I", "-c", INTERPRETER_PROBE],
                                   capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    try:
        report = json.loads(completed.stdout.strip().split("\n")[-1])
    except ValueError:
        return None
    return report if isinstance(report, dict) else None


def interpreter_prefixes(python: str | None = None) -> set[str]:
    """The pinned interpreter's real install prefix (base AND venv) and its stdlib directory.

    T52 / T51.3: a sandbox profile re-allows `sys.base_prefix` and the stdlib directory of the
    pinned interpreter, so the audit must carry exactly those. `sys.prefix` alone is the venv (or
    the auditor's own tree when it is a different interpreter), and a read of the standard library
    is then reported out-of-run for an access the launch allowed.
    """
    executable = Path(os.path.realpath(python or sys.executable))
    if executable == Path(os.path.realpath(sys.executable)):
        report = {"base_prefix": sys.base_prefix, "prefix": sys.prefix,
                  "stdlib": sysconfig.get_path("stdlib")}
    else:
        report = interpreter_report(executable) or {}
    return {value for value in report.values() if isinstance(value, str) and value}


def allowed_roots(python: str | None = None) -> tuple[str, ...]:
    """The frozen system allow-list; the interpreter is resolved, never hard-coded."""
    interpreter = Path(python or sys.executable).resolve()
    values = {*SYSTEM_ALLOW, *TEMP_ALLOW, str(interpreter), str(interpreter.parent),
              str(Path(sys.prefix).resolve()), str(Path(tempfile.gettempdir()).resolve()),
              *interpreter_prefixes(python)}
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
    if root == os.sep:
        return True                                 # every absolute path is under the root
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


def path_exists(resolved: str, run_dir: Path, snapshot: Path | None = None) -> bool:
    """Whether one resolved path EXISTED for the launch: in its snapshot, or on disk now.

    T52: the run directory's own authority is the post-launch SNAPSHOT the driver took (a worker
    may have deleted the file afterwards, and the live tree is then no longer the launch's), while
    a path outside the run directory can only be judged from the filesystem as it is read here.
    `lexists` and not `exists`: a dangling symlink is still a node the read would have found, so
    the conservative answer is "may have succeeded".
    """
    if os.path.lexists(resolved):
        return True
    if snapshot is None:
        return False
    try:
        relative = Path(resolved).relative_to(Path(run_dir))
    except ValueError:
        return False
    return os.path.lexists(Path(snapshot) / relative)


def path_hit(value: str, run_dir: Path, home: str | None, allow: tuple[str, ...],
             rules: dict | None = None, *, write: bool = False,
             base: str | None = None, snapshot: Path | None = None) -> dict | None:
    """One path-shaped value as a hit (already classified, T46), or None when it is allowed.

    The class is decided from the RESOLVED path and the archived profile of the same launch, so a
    relative token is judged in the directory the command actually stood in, never in the run
    directory by assumption. An absent READ target is provisional denial evidence; a recorded
    successful content result overrides it in audit(). A WRITE can create its target and
    stays POSSIBLE_SUCCESS unless the write whitelist refuses it (which `path_class` decides). A
    value carrying glob syntax is a PATTERN and is never existence-checked: the pattern string is
    not a place, and what it matches may well exist.
    """
    reason = path_reason(value, run_dir, home, allow, base=base)
    if reason is None:
        return None
    resolved = resolve(value, run_dir, home, base=base)
    hit = {"reason": reason, "value": value, "class": path_class(resolved, rules, write=write)}
    if resolved:
        hit["resolved"] = resolved
    if (hit["class"] == POSSIBLE_SUCCESS and not write and resolved
            and not GLOB_META_RE.search(value) and not path_exists(resolved, run_dir, snapshot)):
        hit["class"] = DENIED_BY_POLICY
        hit["policy"] = PATH_NOT_FOUND
    return hit


def policy_of(hit: dict) -> dict:
    """The extra evidence fields of one path hit: its resolved spelling, and what decided its class."""
    evidence = {}
    if hit.get("resolved"):
        evidence["resolved"] = hit["resolved"]
    if hit.get("policy"):
        evidence["policy"] = hit["policy"]
    return evidence


def profile_statements(text: str) -> list[str]:
    """The top-level `( ... )` statements of a rendered profile, each joined onto one line.

    A rendered deny block is written over several lines (`(deny file-read-data file-write*` then
    one `(subpath "…")` per line and a closing `)`), and a rule is only readable once its clauses
    are back on the same line; a comment line outside a statement is skipped.
    """
    statements: list[str] = []
    current: list[str] = []
    depth = 0
    for raw in text.split("\n"):
        line = raw.strip()
        if not current and not line.startswith("("):
            continue                                    # a comment, a blank line
        current.append(line)
        depth += line.count("(") - line.count(")")
        if depth <= 0:
            statements.append(" ".join(part for part in current if part))
            current = []
            depth = 0
    if current:
        statements.append(" ".join(current))
    return statements


def profile_rules(profile) -> dict | None:
    """The deny roots and the allow rules of one ARCHIVED rendered profile, or None.

    None — no profile, an unreadable one, or one with no deny block — means NOTHING can be called
    `DENIED_BY_POLICY`: the audit refuses to excuse an access on a profile it cannot read, so such
    a hit stays `POSSIBLE_SUCCESS` and keeps the run INVALID.
    """
    if profile is None:
        return None
    try:
        text = Path(profile).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    deny_read: set[str] = set()
    deny_write: set[str] = set()
    allow: list[dict] = []
    for statement in profile_statements(text):
        clauses = [(kind, quoted or regex)
                   for kind, quoted, regex in RULE_CLAUSE_RE.findall(statement)]
        match = DENY_RULE_RE.match(statement)
        if match is not None:
            ops = set(match.group("ops").split())
            values = {value for kind, value in clauses if kind == "subpath" and value}
            # `(deny file-write* (subpath "/"))` is the WRITE whitelist, not a read denial: the
            # two surfaces are kept apart, or every readable system file would look denied.
            if ops & READ_OPS:
                deny_read |= values
            if ops & WRITE_OPS:
                deny_write |= values
            continue
        match = ALLOW_RULE_RE.match(statement)
        if match is None or not clauses:
            continue
        ops = set(match.group("ops").split())
        allow.append({"read": bool(ops & READ_OPS), "write": bool(ops & WRITE_OPS),
                      "clauses": clauses})
    if not (deny_read or deny_write):
        return None
    return {"deny_read": sorted(deny_read), "deny_write": sorted(deny_write), "allow": allow}


def path_class(resolved: str | None, rules: dict | None, *, write: bool = False) -> str:
    """The class of one resolved path: DENIED only when the archived profile provably refuses it."""
    if not resolved or rules is None:
        return POSSIBLE_SUCCESS
    for rule in rules["allow"]:
        if (write and not rule["write"]) or (not write and not rule["read"]):
            continue
        for kind, value in rule["clauses"]:
            if kind == "subpath" and value and inside(resolved, value):
                return POSSIBLE_SUCCESS
            # An ancestor `literal` re-allows the node itself (a directory listing), never a path
            # below it: the contents of an ancestor stay unreadable (README §3 discloses the names).
            if kind == "literal" and value and os.path.realpath(value) == resolved:
                return POSSIBLE_SUCCESS
    roots = rules["deny_write"] if write else rules["deny_read"]
    if any(inside(resolved, root) for root in roots):
        return DENIED_BY_POLICY
    return POSSIBLE_SUCCESS


def url_host(authority: str) -> str:
    """The host of one URL authority: credentials stripped first, then the port (T52 / finding 3).

    `user:pass@host:8080` names `host`: reading the authority from the left reported the USER as
    the host, so a credential-prefixed URL escaped the egress check on both sides.
    """
    host = authority.rsplit("@", 1)[-1]
    if host.startswith("["):                       # an IPv6 literal: `[::1]:8080`
        end = host.find("]")
        return host[:end + 1] if end != -1 else host
    return host.split(":", 1)[0]


def network_hosts(value: str) -> list[str]:
    """The host names a command names: URL authorities and scp `host:path` forms."""
    text = str(value or "")
    hosts = {url_host(match.group("authority")).lower()
             for match in URL_AUTHORITY_RE.finditer(text)}
    hosts.discard("")
    for token in shell_tokens(text):
        token = token.strip("'\"")
        if not token or token in OPERATORS or "://" in token or not GIT_SCP_RE.match(token):
            continue
        host = token.split(":", 1)[0].rsplit("@", 1)[-1]
        if HOSTNAME_RE.match(host):
            hosts.add(host)
    return sorted(hosts)


def network_class(command: str) -> str:
    """DENIED when every host the command names is off the frozen egress allowlist (T46)."""
    hosts = network_hosts(command)
    if hosts and not any(host in EGRESS_ALLOW for host in hosts):
        return DENIED_BY_POLICY
    return POSSIBLE_SUCCESS


def event_breach(event, run_dir: Path, home: str | None, rules: dict | None) -> list[dict]:
    """T46 / T52: a `read` result that RETURNED file content for a path the profile denies.

    The attempt is read from the recorded input and the outcome from the recorded result: a call
    whose status is not `completed`, or whose output is empty, obtained nothing and is no breach.
    T52: only `read` returns a file's content. A `glob`, `grep` or `list` result is a listing or a
    match, and any message may mention a path without either holding its bytes, so none of them
    is a breach (review finding 4); they remain hits only through the input path they name.
    """
    if not isinstance(event, dict) or event.get("type") != "tool_use":
        return []
    part = event.get("part") if isinstance(event.get("part"), dict) else {}
    tool = part.get("tool")
    if tool not in CONTENT_TOOLS:
        return []
    state = part.get("state") if isinstance(part.get("state"), dict) else {}
    if state.get("status") not in (None, "completed"):
        return []
    output = state.get("output")
    if not isinstance(output, str) or not output.strip():
        return []
    inputs = state.get("input") if isinstance(state.get("input"), dict) else {}
    values = [inputs.get(key) for key in PATH_KEYS]
    if tool in SEARCH_TOOLS:
        values.extend(value for value in (inputs.get(key) for key in SEARCH_PATH_KEYS)
                      if isinstance(value, str) and path_shaped_search(value))
    breaches: list[dict] = []
    for value in values:
        if not isinstance(value, str):
            continue
        resolved = resolve(value, run_dir, home)
        if path_class(resolved, rules) != DENIED_BY_POLICY:
            continue
        breaches.append({"kind": BREACH_DENIED_CONTENT, "tool": tool, "path": value,
                         "value": output.strip()[:200]})
    return breaches


def egress_breach(log_path) -> list[dict]:
    """T46: an ALLOW line for a host the frozen egress allowlist does not carry.

    A DENY line is the proxy refusing (evidence, F26); an ALLOW line for any other host would mean
    the allowlist did not hold — that is a breach, not a hit.
    """
    if log_path is None:
        return []
    path = Path(log_path)
    if not path.is_file():
        return []
    breaches: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("verdict") != "ALLOW":
            continue
        host = entry.get("host")
        if isinstance(host, str) and host and host not in EGRESS_ALLOW:
            breaches.append({"kind": BREACH_EGRESS, "host": host, "port": entry.get("port"),
                             "at": entry.get("at")})
    return breaches


def confinement_breach(confinement) -> list[dict]:
    """T46: a confinement self-test that is not PASS (defensive: the driver blocks on it first)."""
    if not isinstance(confinement, dict):
        return []
    verdict = confinement.get("verdict")
    if verdict is None or verdict == "PASS":
        return []
    reasons = [str(item) for item in confinement.get("reasons", [])]
    return [{"kind": BREACH_CONFINEMENT, "verdict": verdict, "reasons": reasons}]


def read_violations(source) -> list[dict]:
    """The per-launch sandbox violation records the driver collected (T51.4), in order.

    `source` is a `violations.jsonl` path or an iterable of already-parsed records. A missing file
    is no violation, never a failure: the log is empirical CONFIRMATION of a class the archived
    profile already decides, so its absence changes nothing (T52).
    """
    if source is None:
        return []
    if isinstance(source, (str, os.PathLike)):
        path = Path(source)
        if not path.is_file():
            return []
        records: list[dict] = []
        # F46 / T45: a JSONL stream is separated by "\n" only.
        for line in path.read_text(encoding="utf-8", errors="replace").split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict):
                records.append(entry)
        return records
    return [entry for entry in source if isinstance(entry, dict)]


def violation_places(records) -> tuple[frozenset[str], frozenset[str]]:
    """The paths and hosts a launch's violation records name, normalised for comparison.

    A record may carry the place under any of the T51.4 key spellings; a record that says
    `denied: false` or `verdict: ALLOW` is not a denial and names nothing here.
    """
    paths: set[str] = set()
    hosts: set[str] = set()
    for record in records or ():
        if not isinstance(record, dict):
            continue
        if record.get("denied") is False or str(record.get("verdict", "")).upper() == "ALLOW":
            continue
        for key in VIOLATION_PATH_KEYS:
            value = record.get(key)
            if isinstance(value, str) and value:
                paths.add(os.path.realpath(value))
        for key in VIOLATION_HOST_KEYS:
            value = record.get(key)
            if isinstance(value, str) and value:
                hosts.add(value.lower())
    return frozenset(paths), frozenset(hosts)


def violation_confirms(candidate: dict, records: list[dict], launch_window=None, pid=None) -> bool:
    """Confirm only a same-kind path denial with a timestamp inside the launch window.

    Missing or malformed bounds or timestamps cannot establish launch attribution. The caller
    retains the original records, including PID and timestamp, for inspection.
    """
    try:
        start, end = (datetime.datetime.fromisoformat(str(value)) for value in launch_window)
        if start.tzinfo is None or end.tzinfo is None or start > end:
            return False
    except (TypeError, ValueError):
        return False
    tool = candidate.get("tool")
    if tool in WRITE_TOOLS:
        operation_prefix = "file-write-"
    elif tool in PATH_TOOLS or tool in SHELL_TOOLS:
        # Shell paths are statically classified as reads; a write denial cannot confirm them.
        operation_prefix = "file-read-"
    else:
        return False
    path = candidate.get("resolved")
    if not isinstance(path, str) or not os.path.isabs(path):
        return False
    for record in records:
        if record.get("denied") is False or str(record.get("verdict", "")).upper() == "ALLOW":
            continue
        if not str(record.get("operation", "")).startswith(operation_prefix):
            continue
        if pid is not None and record.get("pid") is not None and str(record["pid"]) != str(pid):
            continue
        try:
            timestamp = datetime.datetime.fromisoformat(str(record.get("ts")))
            if timestamp.tzinfo is None or not start <= timestamp <= end:
                continue
        except (TypeError, ValueError):
            continue
        if any(isinstance(record.get(key), str) and os.path.isabs(record[key])
               and os.path.realpath(record[key]) == os.path.realpath(path)
               for key in VIOLATION_PATH_KEYS):
            return True
    return False


def breach_reasons(breaches) -> list[str]:
    """The registration reasons of one breach: `SANDBOX_BREACH:<kind>:<detail>` (T46)."""
    reasons = []
    for item in breaches or ():
        detail = item.get("path") or item.get("host") or item.get("verdict") or ""
        reasons.append(f"{BREACH_PREFIX}:{item.get('kind')}:{detail}")
    return reasons


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


def arithmetic_end(line: str, index: int) -> int:
    """The index after the `))` that closes an arithmetic expansion opened before `index`."""
    depth = 0
    while index < len(line):
        char = line[index]
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        elif char == ")" and line.startswith("))", index):
            return index + 2
        index += 1
    return index


def heredoc_operators(line: str) -> list[dict]:
    """The heredoc operators of one line: delimiter, `<<-` tab stripping, and the line prefix.

    The scan is quote-aware, so a `<<` inside a quoted argument (`python -c 'print(1 << 2)'`) or
    inside `$((...))` is not an operator; the shell's own heredoc forms are (F45).
    """
    operators: list[dict] = []
    index = 0
    quote = ""
    while index < len(line):
        char = line[index]
        if quote:
            if char == "\\" and quote == '"':
                index += 2
                continue
            if char == quote:
                quote = ""
            index += 1
            continue
        if char in "'\"":
            quote = char
            index += 1
            continue
        if char == "\\":
            index += 2
            continue
        if line.startswith("$((", index):
            index = arithmetic_end(line, index + 3)
            continue
        if char == "#" and (index == 0 or line[index - 1].isspace()):
            break
        if line.startswith("<<<", index):
            while index < len(line) and line[index] == "<":
                index += 1
            continue
        if line.startswith("<<", index):
            match = HEREDOC_OPERATOR_RE.match(line, index)
            if match:
                delimiter = match.group("single")
                if delimiter is None:
                    delimiter = match.group("double")
                if delimiter is None:
                    delimiter = match.group("word")
                if delimiter:
                    operators.append({"delimiter": delimiter,
                                      "strip_tabs": match.group("dash") == "-",
                                      "prefix": line[:index]})
                    index = match.end()
                    continue
        index += 1
    return operators


def split_heredocs(command: str) -> tuple[str, list[dict]]:
    """The command lines with every heredoc body cut out, and the bodies themselves.

    A body starts on the line after its operator and ends on the line holding exactly the
    delimiter (leading tabs stripped for `<<-`); the delimiter line is part of the body, not a
    command. The operator's own line is kept verbatim, because its words, arguments and redirect
    targets are shell syntax and are judged as before (F45).
    """
    lines = command.split("\n")
    kept: list[str] = []
    bodies: list[dict] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        kept.append(line)
        for operator in heredoc_operators(line):
            body: list[str] = []
            while index < len(lines):
                candidate = lines[index]
                index += 1
                compared = candidate.lstrip("\t") if operator["strip_tabs"] else candidate
                if compared == operator["delimiter"]:
                    break
                body.append(candidate)
            bodies.append({"delimiter": operator["delimiter"],
                           "strip_tabs": operator["strip_tabs"],
                           "prefix": operator["prefix"], "body": "\n".join(body)})
    return "\n".join(kept), bodies


def command_name(prefix: str) -> str:
    """The program word of the command segment that ends at `prefix`, or "" when there is none.

    A `NAME=value` prefix is an assignment, not the program; a control operator starts a new
    segment, so `cd x && python -` names `python`.
    """
    name = ""
    for token in shell_tokens(prefix):
        if token in OPERATORS:
            name = ""
        elif not name and "=" not in token:
            name = PurePosixPath(token).name
    return name


def script_indexes(name: str, tokens: list[str], start: int, end: int) -> set[int]:
    """The script/program/pattern token indexes of one sed/awk/grep invocation (F47 / T45).

    `start`..`end` is the argument list of a program named `name`, ending at a control operator.
    Every `-e`/`--expression`/`--regexp` value is a pattern, and so is the first non-option
    operand — unless a script/pattern FILE was named (`-f`/`--file`, whose value is a path) or the
    patterns were given explicitly, in which case the positional operands are FILE operands and
    stay judged. An empty token (BSD `sed -i ''`) is an option's own argument, never an operand.
    """
    skip: set[int] = set()
    values = SCRIPT_VALUE_FLAGS.get(name, ())
    short = tuple(flag for flag in values if flag.startswith("-") and not flag.startswith("--"))
    explicit = False
    script_file = False
    operands: list[int] = []
    index = start
    while index < end:
        token = tokens[index]
        if token in values:
            explicit = True
            if index + 1 < end:
                skip.add(index + 1)
            index += 2
            continue
        if any(token.startswith(f"{flag}=") for flag in values) or (
                any(token.startswith(flag) and len(token) > len(flag) for flag in short)):
            explicit = True
            skip.add(index)
        elif token.startswith("-") and token != "-":
            if token in SCRIPT_FILE_FLAGS:
                script_file = True
                index += 2
                continue
            script_file = script_file or token.startswith(("-f", "--file="))
        elif token.strip():
            operands.append(index)
        index += 1
    if operands and not explicit and not script_file:
        skip.add(operands[0])
    return skip


def script_operand_indexes(tokens: list[str]) -> set[int]:
    """Every token of a command list that is a script/program/pattern rather than a place (F47).

    The list is walked segment by segment — a control operator starts a new command, and a
    `NAME=value` prefix is an assignment rather than the program word — so `cd repo && sed …` is
    read as `sed` with the script the audit must not judge as a path, while `cat x | grep pat` is
    read as two commands.
    """
    skip: set[int] = set()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in OPERATORS or "=" in token:
            index += 1
            continue
        end = index + 1
        while end < len(tokens) and tokens[end] not in OPERATORS:
            end += 1
        name = PurePosixPath(token).name
        if name in SCRIPT_TOOLS:
            skip |= script_indexes(name, tokens, index + 1, end)
        index = end
    return skip


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
                      home: str | None, temps: tuple[str, ...],
                      rules: dict | None = None, snapshot: Path | None = None) -> list[dict]:
    """One git invocation: remote escapes, and a foreign effective repository (F13 / F27a).

    T46: a remote escape is judged by the hosts it names (the frozen egress allowlist is what can
    stop it), a foreign effective repository by the same profile rules as any other path. T52: a
    repository directory that does not exist cannot be read, so that hit is evidence too.
    """
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
                     "value": command, "path": subcommand or "git",
                     "class": network_class(command)})
    if unresolved is not None:
        hits.append({"tool": "shell", "reason": "GIT_FOREIGN_REPOSITORY",
                     "value": command, "path": unresolved,
                     "class": POSSIBLE_SUCCESS})
    elif not inside(repo, str(run_dir)) and not any(inside(repo, root) for root in temps):
        hit = {"tool": "shell", "reason": "GIT_FOREIGN_REPOSITORY",
               "value": command, "path": repo, "class": path_class(repo, rules)}
        if hit["class"] == POSSIBLE_SUCCESS and not path_exists(repo, run_dir, snapshot):
            hit["class"] = DENIED_BY_POLICY
            hit["policy"] = PATH_NOT_FOUND
        hits.append(hit)
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
             cwd: str | None = None, rules: dict | None = None,
             snapshot: Path | None = None) -> list[dict]:
    """Shell `git` invocations that reach another repository.

    The working directory follows a `cd` in the same command list; an argument list ends at the
    first control operator. Both are what make a scripted `cd <run> && ... && git -C repo ...`
    judgeable, and what keeps another program's `-C` out of git's argument list (F12 / F13).
    F42 / T40: the `cd` operand is consumed, so it can never be mistaken for a `git` invocation.
    F43: `cwd` is the tool call's `workdir` when it has one, the run directory otherwise.
    T46: `rules` is the archived profile of the same launch, used to classify each hit.
    T52: `snapshot` decides whether a foreign repository directory existed at all.
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
        hits.extend(git_argument_hits(args, command, cwd, run_dir, home, temps, rules,
                                         snapshot))
    return hits


def shell_hits(command: str, run_dir: Path, home: str | None, allow: tuple[str, ...],
               cwd: str | None = None, rules: dict | None = None,
               snapshot: Path | None = None) -> list[dict]:
    """Every path-shaped token of one shell command, plus the git rules above.

    F27b: resolution follows the working directory the same command established with `cd`, so an
    assignment and any other relative token are judged against where the worker actually stood.
    F42 / T40: the operand of a `cd` is judged against the working directory BEFORE that `cd` (it
    is the directory the tokens after it are judged in), so `cd repo ... cd ..` is a return into
    the run directory, not an escape from it.
    F43: `cwd` is the tool call's `workdir` (the directory the command starts in) when it has one,
    the run directory otherwise; the `cd` tracking and `git_hits` start from the same place.
    F45 / T43: heredoc bodies are cut before tokenising, so a program's stdin data is never read as
    shell words; the operator line itself is judged in full.
    F47 / T45: the script/program/pattern operand of sed/awk/grep is text the program interprets,
    not a place, so it is the one kind of operand that is not judged as a path.
    T46: a shell token is classified as a READ, the weaker of the two accesses: a path the profile
    re-allows for reading but not for writing therefore stays `POSSIBLE_SUCCESS`.
    T52: `snapshot` is the run's post-launch copy; recorded content overrides an absent path.
    """
    command_line, _ = split_heredocs(command)
    tokens = shell_tokens(command_line)
    # F47: a script/pattern token is skipped, so `sed -i '' '/^ROUTE …/d' .h2-telemetry.log` is
    # judged on its input file and not on its own script.
    scripts = script_operand_indexes(tokens)
    hits: list[dict] = []

    def judge(values: list[str], base: str) -> None:
        for value in values:
            hit = path_hit(value, run_dir, home, allow, rules, base=base, snapshot=snapshot)
            if hit:
                hits.append({"tool": "shell", "reason": hit["reason"],
                             "value": command.strip(), "path": value,
                             "class": hit["class"], **policy_of(hit)})

    cwd = cwd or str(run_dir)
    index = 0
    while index < len(tokens):
        position = index
        token = tokens[index]
        index += 1
        if token in OPERATORS:
            continue
        if position in scripts:
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
    hits.extend(git_hits(tokens, run_dir, home, cwd, rules, snapshot))
    return hits


def shell_workdir(inputs: dict, run_dir: Path, home: str | None,
                  allow: tuple[str, ...], rules: dict | None = None,
                  snapshot: Path | None = None) -> tuple[str, list[dict]]:
    """F43: the directory one shell command starts in, and a hit when that place is out of run.

    The `workdir` is a path like any other (a relative value resolves against the run directory,
    `~`/`$HOME` against the profile home) and is judged with the same allow-list. An unreadable or
    absent value leaves the run directory as the base, which is what the audit always assumed.
    T52: a directory that does not exist cannot be the working directory of a command that ran, so
    a `workdir` the snapshot and the filesystem do not hold is evidence, not a hit.
    """
    base = str(run_dir)
    hits: list[dict] = []
    for key in SHELL_WORKDIR_KEYS:
        value = inputs.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        hit = path_hit(value, run_dir, home, allow, rules, snapshot=snapshot)
        if hit:
            hits.append(hit)
        resolved = resolve(value, run_dir, home)
        if resolved:
            base = resolved
    return base, hits


def search_input_hits(inputs: dict, run_dir: Path, home: str | None,
                      allow: tuple[str, ...], rules: dict | None = None,
                      snapshot: Path | None = None) -> list[dict]:
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
        hit = path_hit(value, run_dir, home, allow, rules, base=base, snapshot=snapshot)
        if hit:
            hits.append(hit)
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
    """The F16 constructs of one shell command: evidence that static resolution is incomplete.

    F45 / T43: heredoc bodies are cut first — their contents are data, not shell syntax — and a
    body fed to an interpreter is recorded as HEREDOC_PROGRAM, like the program of `-c`.
    """
    command_line, heredocs = split_heredocs(command)
    found: list[str] = []
    if "$(" in command_line:
        found.append(UNRESOLVED_REASONS["command_substitution"])
    if "`" in command_line:
        found.append(UNRESOLVED_REASONS["backtick"])
    tokens = shell_tokens(command_line)
    names = [PurePosixPath(token).name for token in tokens]
    if "eval" in names:
        found.append(UNRESOLVED_REASONS["eval"])
    for index, token in enumerate(tokens):
        if token == "-c" and index and names[index - 1] in INTERPRETERS:
            found.append(UNRESOLVED_REASONS["inline_program"])
            break
    if any(command_name(body["prefix"]) in INTERPRETERS for body in heredocs):
        found.append(UNRESOLVED_REASONS["heredoc_program"])
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
    # F46 / T45: a JSONL stream is separated by "\n" only; splitlines() also breaks on U+2028 etc.
    for line in path.read_text(encoding="utf-8", errors="replace").split("\n"):
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
               allow: tuple[str, ...], rules: dict | None = None,
               snapshot: Path | None = None) -> list[dict]:
    """The hits of one parsed event; a non-`tool_use` event carries no access.

    Every hit carries its `class` (T46): a `DENIED_BY_POLICY` hit obtained nothing and is reported
    as evidence, a `POSSIBLE_SUCCESS` hit keeps the run INVALID. T52: a read whose target does not
    exist (checked against `snapshot` and the filesystem) is evidence absent a successful result.
    """
    if not isinstance(event, dict):
        return [{"event": index, "reason": "MALFORMED_EVENT", "value": str(event)[:200],
                 "class": POSSIBLE_SUCCESS}]
    if event.get("type") != "tool_use":
        return []
    part = event.get("part")
    if not isinstance(part, dict):
        return [{"event": index, "reason": "MALFORMED_EVENT", "value": "",
                 "class": POSSIBLE_SUCCESS}]
    tool = part.get("tool")
    state = part.get("state") if isinstance(part.get("state"), dict) else {}
    inputs = state.get("input") if isinstance(state.get("input"), dict) else {}
    if not isinstance(tool, str) or not tool:
        return [{"event": index, "reason": "TOOL_UNIDENTIFIED", "value": "",
                 "class": POSSIBLE_SUCCESS}]
    hits: list[dict] = []
    if tool not in TOOL_ALLOW:
        hits.append({"event": index, "tool": tool, "reason": "TOOL_NOT_ALLOWED", "value": tool,
                     "class": POSSIBLE_SUCCESS})
    if tool in PATH_TOOLS:
        write = tool in WRITE_TOOLS
        for key in PATH_KEYS:
            value = inputs.get(key)
            if not isinstance(value, str):
                continue
            hit = path_hit(value, run_dir, home, allow, rules, write=write, snapshot=snapshot)
            if hit:
                hits.append({"event": index, "tool": tool, **hit})
    if tool in SHELL_TOOLS:
        base, workdir_hits = shell_workdir(inputs, run_dir, home, allow, rules,
                                           snapshot=snapshot)
        hits.extend({**hit, "event": index, "tool": tool} for hit in workdir_hits)
        for key in COMMAND_KEYS:
            command = inputs.get(key)
            if isinstance(command, str):
                hits.extend({**hit, "event": index, "tool": tool}
                            for hit in shell_hits(command, run_dir, home, allow, cwd=base,
                                                  rules=rules, snapshot=snapshot))
    if tool in SEARCH_TOOLS:
        hits.extend({**hit, "event": index, "tool": tool}
                    for hit in search_input_hits(inputs, run_dir, home, allow, rules,
                                                 snapshot=snapshot))
    if tool == "patch":
        for value in patch_paths(inputs.get("patchText")):
            hit = path_hit(value, run_dir, home, allow, rules, write=True, snapshot=snapshot)
            if hit:
                hits.append({"event": index, "tool": tool, **hit})
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
          python: str | None = None, profile=None, egress_log=None,
          confinement=None, snapshot=None, violations=None, launch_window=None) -> dict:
    """Audit one run's event stream; every hit is kept verbatim and classified (T46).

    `profile` is the ARCHIVED rendered profile of the same launch, `egress_log` that launch's
    `egress.jsonl`, `confinement` its self-test record: the first decides the class of every path
    hit, all three feed the breach rule. A hit is never softened by anything the worker says.
    T52: `snapshot` is the run's post-launch snapshot (a path that it does not hold and that the
    filesystem does not hold either is provisionally absent), and `violations` the launch's T51.4
    `violations.jsonl` (or its parsed records): a same-kind path denial within the supplied
    launch window can confirm a denial. Recorded content overrides post-launch absence.
    """
    run_dir = Path(run_dir).resolve()
    allow = allowed_roots(python)
    rules = profile_rules(profile)
    violation_records = read_violations(violations)
    result = {"schema_version": 1, "program": "freeze-v3/access_audit.py",
              "run_dir": str(run_dir), "allow_list": list(allow),
              "observation_scope": ("Every tool_use input recorded in the run's event stream. "
                                    "Hidden runtime context and tool-internal accesses that emit "
                                    "no event are not observable."),
              "sandbox_scope": ("The OS sandbox is the enforcing barrier (F16); a denied dynamic "
                                "attempt obtained nothing and is recorded as sandbox_denied, not "
                                "as a hit."),
              "classification_scope": ("Every hit is DENIED_BY_POLICY only when the archived "
                                       "rendered profile of this launch proves the access cannot "
                                       "succeed, or when the access was impossible (a target that "
                                       "does not exist, a write outside the write whitelist) or a "
                                       "launch violation record names it; otherwise it is "
                                       "POSSIBLE_SUCCESS."),
              "profile": str(profile) if profile is not None else None,
              "snapshot": str(snapshot) if snapshot is not None else None,
              "violations": str(violations) if isinstance(violations, (str, os.PathLike)) else None,
              "deny_roots": ({"read": rules["deny_read"], "write": rules["deny_write"]}
                             if rules else {"read": [], "write": []}),
              "hits": [], "denied_attempts": [], "denied_attempts_count": 0, "breach": [],
              "unresolved_constructs": [], "sandbox_denied": [],
              "sandbox_violations": violation_records,
              "sandbox_violations_count": len(violation_records),
              "events": 0, "tool_calls": 0, "verdict": "PASS"}
    path = Path(events_path)
    if not path.is_file():
        result["hits"] = [{"reason": "MISSING_EVENT_STREAM", "value": str(path),
                           "class": POSSIBLE_SUCCESS}]
        result["verdict"] = "INVALID"
        return result
    seen: set[str] = set()

    def keep(bucket: str, candidate: dict) -> None:
        key = json.dumps(candidate, sort_keys=True)
        if key not in seen:
            seen.add(key)
            result[bucket].append(candidate)

    # F46 / T45: one JSON line ends at "\n" and nowhere else, so a line that carries U+2028,
    # U+2029, U+0085, \v, \f or \x1c-\x1e inside a string is read as ONE event.
    for index, line in enumerate(path.read_text(encoding="utf-8", errors="replace")
                                 .split("\n"), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            keep("hits", {"event": index, "reason": "MALFORMED_EVENT_LINE", "value": line[:200],
                          "class": POSSIBLE_SUCCESS})
            continue
        result["events"] += 1
        if isinstance(event, dict) and event.get("type") == "tool_use":
            result["tool_calls"] += 1
        for candidate in event_hits(event, index, run_dir, home, allow, rules, snapshot):
            # T46: a denied attempt is evidence with its count; a possible success keeps the run
            # INVALID:OUT_OF_RUN_ACCESS, exactly as before. T52: a violation record naming the
            # same operation and place within the launch window can confirm the denial.
            part = event.get("part") if isinstance(event, dict) else None
            state = part.get("state") if isinstance(part, dict) else None
            state = state if isinstance(state, dict) else {}
            output = state.get("output")
            returned_content = (candidate.get("tool") in CONTENT_TOOLS | SHELL_TOOLS
                                and state.get("status") == "completed"
                                and isinstance(output, str) and bool(output.strip()))
            if candidate.get("policy") == PATH_NOT_FOUND and returned_content:
                candidate["class"] = POSSIBLE_SUCCESS
                candidate.pop("policy")
            if (candidate.get("class") == POSSIBLE_SUCCESS and not returned_content
                    and violation_confirms(candidate, violation_records, launch_window,
                                           event.get("pid") if isinstance(event, dict) else None)):
                candidate["class"] = DENIED_BY_POLICY
                candidate["policy"] = VIOLATION_CONFIRMED
            keep("denied_attempts" if candidate.get("class") == DENIED_BY_POLICY else "hits",
                 candidate)
        evidence = event_evidence(event, run_dir)
        for field in ("unresolved_constructs", "sandbox_denied"):
            for candidate in evidence[field]:
                keep(field, candidate)
        for candidate in event_breach(event, run_dir, home, rules):
            keep("breach", candidate)
    for candidate in (*egress_breach(egress_log), *confinement_breach(confinement)):
        keep("breach", candidate)
    result["denied_attempts_count"] = len(result["denied_attempts"])
    if result["hits"] or result["breach"]:
        result["verdict"] = "INVALID"
    return result


# T52 — THE REPLAY. The measurement is: run THIS audit over every archived real stream of the
# H2-R2 round and of the pilots, and record which runs it would call VALID and which INVALID. It is
# a harness measurement; the round's own registration is read as the v2 baseline and never rewritten.
REPLAY_SCHEMA = 1
REPLAY_SCOPE = ("Every archived worker-launch stream of a runs root: "
                ".driver/<run>/attempt-<n>/events.jsonl for each attempt, or the run's own "
                "events.jsonl when no attempt copy was kept. Probe, gate and audit streams are "
                "different launches with their own profiles and are not replayed.")
REPLAY_V2_SOURCE = ("the verdict the run's own access-audit.json recorded (read, never recomputed: "
                    "this replay does not re-score the round)")
REPLAY_STREAM_RE = re.compile(r"^attempt-(?P<number>\d+)")
INTERPRETER_NAME_RE = re.compile(r"python(\d+(\.\d+)*)?")
NO_STREAM = "NO_STREAM"
UNRECORDED = "UNRECORDED"


def attempt_streams(driver_dir: Path) -> list[Path]:
    """The worker-launch streams of one run, oldest attempt first.

    A superseded attempt directory holds no `events.jsonl` (the launch never produced a stream), so
    a plain glob is the whole filter; the numeric sort keeps `attempt-10` after `attempt-9`.
    """
    found = [path for path in Path(driver_dir).glob("attempt-*/events.jsonl") if path.is_file()]

    def key(path: Path) -> tuple[int, str]:
        match = REPLAY_STREAM_RE.match(path.parent.name)
        return (int(match.group("number")) if match else 0, path.parent.name)

    return sorted(found, key=key)


def launch_context(stream: Path) -> dict:
    """The archived inputs of one launch, all next to its `events.jsonl` (T51.1 / T51.4).

    `home-<n>` is the attempt's own fresh home; the profile, the post-launch snapshot and the
    violation log are written by the driver into the same stream directory. A run-level stream (a
    pilot that kept no attempt copy) has none of them, and the audit then decides on the stream and
    the filesystem alone, which is exactly what its classification scope says.
    """
    directory = Path(stream).parent
    attempt = REPLAY_STREAM_RE.match(directory.name)
    home = directory.parent / f"home-{attempt.group('number')}" if attempt else None
    profile = directory / "worker.sb"
    snapshot = directory / "snapshot"
    violations = directory / "violations.jsonl"
    return {"home": str(home) if home is not None and home.is_dir() else None,
            "profile": profile if profile.is_file() else None,
            "snapshot": snapshot if snapshot.is_dir() else None,
            "violations": violations if violations.is_file() else None,
            "egress_log": directory / "egress.jsonl"}


def replay_reason(result: dict) -> str:
    """One audit result's reason in rule terms: `REASON:count`, never a path or a command.

    The replay fixture is committed, so a reason may only carry codes and counts; the concrete
    values stay in the per-launch `access-audit.json` the run already keeps.
    """
    parts = sorted(f"{name}:{count}" for name, count in
                   Counter(str(hit.get("reason")) for hit in result["hits"]).items())
    parts += sorted(f"{name}:{count}" for name, count in
                    Counter(str(item.get("kind")) for item in result["breach"]).items())
    return ", ".join(parts) if parts else "no out-of-run access"


def recorded_verdict(run_dir: Path) -> str:
    """The verdict the run's own archived `access-audit.json` recorded, or UNRECORDED."""
    try:
        verdict = json.loads((Path(run_dir) / "access-audit.json").read_text(
            encoding="utf-8")).get("verdict")
    except (OSError, ValueError, TypeError, AttributeError):
        return UNRECORDED
    return {"PASS": "VALID", "INVALID": "INVALID"}.get(verdict, UNRECORDED)


def is_run_dir(path: Path) -> bool:
    """A run directory of this experiment: `h2r2-<task>-<arm>` under a batch root."""
    return path.is_dir() and path.name.startswith("h2r2-")


def batch_roots(runs_root: Path) -> list[Path]:
    """The directories of one runs root that hold runs: the root itself and each batch below it.

    A batch root holds `.driver/` (the driver's own tree) or the run directories directly; the
    early pilots kept no attempt copy at all and are recognised by their run directory alone.
    """
    root = Path(runs_root)
    found = []
    if (root / ".driver").is_dir() or any(is_run_dir(path) for path in root.iterdir()):
        found.append(root)
    found.extend(sorted(path for path in root.iterdir()
                        if path.is_dir() and ((path / ".driver").is_dir()
                                              or any(is_run_dir(item)
                                                     for item in path.iterdir()))))
    return found


def profile_interpreter(profile) -> str | None:
    """The interpreter executable an ARCHIVED profile re-allows for reading, or None (T52).

    The replay has to resolve the interpreter the LAUNCH ran with, not the one running the replay:
    the driver rendered the pinned interpreter into the profile as a read subpath, and with it the
    audit can ask that interpreter for its own install prefix and stdlib directory.
    """
    rules = profile_rules(profile)
    if rules is None:
        return None
    for rule in rules["allow"]:
        if not rule["read"]:
            continue
        for kind, value in rule["clauses"]:
            if kind != "subpath" or not value:
                continue
            if INTERPRETER_NAME_RE.fullmatch(PurePosixPath(value.rstrip("/")).name):
                return value
    return None


def replay(runs_root, *, python: str | None = None) -> dict:
    """Replay every archived run stream under one runs root through this audit (T52).

    For each run: the verdict its own `access-audit.json` recorded (`v2`, read not recomputed), the
    verdict this audit gives its LAST attempt (the stream the run registered), the reason in rule
    terms, and — when the run was retried — the earlier attempts beside it. The interpreter is the
    one the launch itself ran with (read from its archived profile) and only falls back to `python`.
    Nothing host-specific is written: no absolute path, no home, no command text, so the summary
    can be committed.
    """
    root = Path(runs_root)
    runs: list[dict] = []
    for batch in batch_roots(root):
        for run_dir in sorted(path for path in batch.iterdir()
                              if is_run_dir(path) and ((batch / ".driver" / path.name).is_dir()
                                                       or (path / "events.jsonl").is_file())):
            driver_dir = batch / ".driver" / run_dir.name
            streams = attempt_streams(driver_dir)
            if not streams and (run_dir / "events.jsonl").is_file():
                streams = [run_dir / "events.jsonl"]
            record = {"root": batch.name, "run": run_dir.name,
                      "v2": recorded_verdict(run_dir)}
            attempts = []
            for stream in streams:
                context = launch_context(stream)
                interpreter = profile_interpreter(context["profile"]) or python
                result = audit(stream, run_dir, home=context["home"], python=interpreter,
                               profile=context["profile"], egress_log=context["egress_log"],
                               snapshot=context["snapshot"], violations=context["violations"])
                attempts.append({
                    "stream": stream.parent.name if stream.parent != run_dir else "run-dir",
                    "v3": "VALID" if result["verdict"] == "PASS" else "INVALID",
                    "reason": replay_reason(result),
                    "denied_attempts": result["denied_attempts_count"],
                    "breach": len(result["breach"])})
            record["attempts"] = len(attempts)
            if attempts:
                record.update({"v3": attempts[-1]["v3"], "reason": attempts[-1]["reason"],
                               "denied_attempts": attempts[-1]["denied_attempts"],
                               "breach": attempts[-1]["breach"]})
                if len(attempts) > 1:
                    record["earlier"] = attempts[:-1]
            else:
                record.update({"v3": NO_STREAM, "reason": "no archived event stream",
                               "denied_attempts": 0, "breach": 0})
            runs.append(record)
    return {"schema_version": REPLAY_SCHEMA, "program": "freeze-v3/access_audit.py",
            "scope": REPLAY_SCOPE, "v2_source": REPLAY_V2_SOURCE, "runs": runs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", type=Path, nargs="?")
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--home", default=None,
                        help="the profile HOME the worker ran with; ~ and $HOME resolve to it")
    parser.add_argument("--python", default=None, help="the pinned interpreter to allow-list")
    parser.add_argument("--profile", default=None,
                        help="the ARCHIVED rendered sandbox profile of the same launch")
    parser.add_argument("--egress-log", default=None,
                        help="the launch's egress.jsonl, read for an ALLOW the allowlist forbids")
    parser.add_argument("--snapshot", default=None,
                        help="the run's post-launch snapshot; a path absent from it and from disk "
                             "did not exist for the launch")
    parser.add_argument("--violations", default=None,
                        help="the launch's T51.4 violations.jsonl, empirical confirmation of a denial")
    parser.add_argument("--replay", type=Path, default=None,
                        help="replay every archived run stream under this runs root (T52)")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    if args.replay is not None:
        summary = replay(args.replay, python=args.python)
        text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
        if args.out is not None:
            args.out.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        verdicts = Counter(record["v3"] for record in summary["runs"])
        print(json.dumps({"runs": len(summary["runs"]), "verdicts": dict(sorted(verdicts.items()))},
                         sort_keys=True))
        return 0
    if args.events is None or args.run_dir is None:
        parser.error("events and --run-dir are required unless --replay is given")
    result = audit(args.events, args.run_dir, home=args.home, python=args.python,
                   profile=args.profile, egress_log=args.egress_log, snapshot=args.snapshot,
                   violations=args.violations)
    target = args.out or args.run_dir / "access-audit.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"], "hits": len(result["hits"]),
                      "denied_attempts": result["denied_attempts_count"],
                      "breach": len(result["breach"]),
                      "tool_calls": result["tool_calls"]}, sort_keys=True))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
