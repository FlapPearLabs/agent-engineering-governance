#!/usr/bin/env python3
"""WORKBUDDY_PRE_TOOL_USE_GIT_SAFETY_GUARD — minimal hard-safety hook (V1).

PURPOSE
    Deny, before execution, the small set of Git command forms that the governance
    hard invariants already prohibit outright. Nothing else.

        git push / git send-pack --force / -f / --force-with-lease / --mirror
        git push carrying a force injected through git config - matched by the CARRIER KEY
        named in the command string (`remote.<name>.mirror`, `remote.<name>.push`), whatever
        the injection spelling
        git reset --hard
        git clean with --force and no dry-run

DESIGN CONSTRAINTS (deliberate, see adapters/workbuddy/README.md)
    * NOT a general command sandbox and NOT a policy engine. V1 has no machine-readable
      execution-state authority, so anything whose legality depends on state is left
      alone: `git rebase`, `git commit --amend`, Edit and Write are NEVER blocked here.
    * NOT a file-scope authorizer. Automated write-surface authorization is out of scope.
    * Stdlib only. No network, no filesystem writes, no subprocesses.
    * The denied command text is never echoed and never persisted: the denial carries a
      stable category id only, so the hook cannot become a place where command content
      (possibly containing credentials) leaks into logs.
    * Failure behaviour: an INTERNAL ERROR ALLOWS WITH A STDERR DIAGNOSTIC. This hook is
      defense-in-depth, not the primary gate; a crashing safety net must not brick every
      ordinary Bash call. The stdlib-only surface keeps this path effectively unreachable,
      and the test matrix asserts it.

HOOK CONTRACT (WorkBuddy / CodeBuddy PreToolUse)
    stdin  : JSON with hook_event_name, tool_name, tool_input
    stdout : optional JSON decision
    exit 0 : allow (no decision emitted)
    exit 2 : block the tool call; stdout JSON `reason` / `hookSpecificOutput` is surfaced

KNOWN NON-COVERAGE (honest boundary, not an oversight)
    Recorded so a reviewer does not read the deny set as complete. This guard is a *static
    text classifier*, NOT a shell evaluator, and it is defense-in-depth rather than a sandbox.

    1. refspec force push (`git push origin +main`) is NOT matched: `+` cannot be told apart
       from an unusual ref name without real ref resolution, and a false deny on an ordinary
       push was judged the worse failure.
    2. Shell evaluation escapes static text entirely, and these are NOT caught:
           C="git push -f"; $C          B=git; A='push -f'; $B $A
           `git push -f`                $(git push -f)
           alias g=git; g push -f       function g { git "$@"; }; g push -f
           ./some-renamed-wrapper push -f
       Anything that hides the literal tokens `git` + `push` + a force flag behind shell
       expansion, aliasing, or a wrapper script is invisible to this analysis. A session-level
       permission rule or a host-side deny mapping is the correct layer for that; this hook
       deliberately does not pretend to be one.
    3. A force carrier that is NOT present in the command text at all: a repository- or
       global-level config file (`remote.origin.mirror true`, or a `remote.<name>.push`
       entry with a `+` refspec written into `.git/config` or `~/.gitconfig`), or an
       environment variable exported before the session started. This guard reads only the
       command string it is handed; persistent state is owned by the repository and the host,
       not by this classifier.
    4. STRUCTURAL BOUNDARY - read this one first. A static classifier over an UNPARSED shell
       command string cannot be made CLOSED. Three consecutive review rounds each found a new
       open axis, and each time the finding was the same shape: "bypassed AND undisclosed".
           round 5   spelling        --config-env separated ; the GIT_CONFIG_* block
           round 6   quoting         git -c remote."origin".mirror=true push origin
           round 6   option arity    git --attr-source HEAD push -f   (an unknown
                                     value-taking global option swallows the subcommand)
           round 6   plumbing        git send-pack --force <url> <refspec>
       Round 7 closed those four instances. The AXES stay open:
           * a value-taking global option absent from _GIT_VALUE_FLAGS can still swallow the
             subcommand - that list is an enumeration and git may add options;
           * a refs-updating plumbing command outside _PUSH_LIKE;
           * any shell construct that removes the literal tokens from the string (item 2).
       The correct layer for a CLOSED guarantee is NOT this hook. It is a host-side policy that
       runs AFTER git has parsed its own arguments, or server-side branch protection on the
       remote. Use this guard as a fast, cheap, fail-closed speed bump - not as the enforcement
       boundary. Recorded because the durable fix for "bypassed AND undisclosed" is honest
       disclosure, not one more pattern.

MEASUREMENT BASIS (why the deny set is what it is)
    The deny set is derived from MEASUREMENT, not from belief about git. Each candidate was
    run on git 2.53.0 against a divergent local/remote pair and judged by whether the remote
    ref actually moved ("(forced update)"). Result:

        REAL FORCE   --force | -f | --force-with-lease | --mirror
                     any command-line config injection naming remote.<name>.mirror or
                     remote.<name>.push - every one of these spellings was measured:
                         -c remote.<name>.mirror=true
                         -c remote.<name>.push=+<refspec>
                         --config-env=remote.<name>.mirror=V        (joined)
                         --config-env remote.<name>.mirror=V        (separated)
                         GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.<name>.mirror
                             GIT_CONFIG_VALUE_0=true
                         git --config=remote.<name>.mirror=true     (spelling git rejects)
        NOT FORCE    --force-if-includes alone          (adjunct to --force-with-lease;
                                                         every real co-occurrence is already
                                                         caught by the --force /
                                                         --force-with-lease rules)
                     -c push.force=true                 (git has no `push.force` key)
                     GIT_PUSH_FORCE=1 / PUSH_FORCE=1    (git honours no such variable)
        `git help --config` lists push.default / push.followTags / push.useForceIfIncludes
        and no `push.force`.

    Review rounds 1-3 added deny rules for the two NOT FORCE forms, on the mistaken premise
    that they force. Round 4 REMOVED them: denying a valid, non-forcing command serves no
    invariant and violates R8 ("which demonstrated failure does this prevent?"). Round 4 also
    ADDED `--mirror` and the config-injected carriers, which measurably do force and were
    previously allowed.

    Round 5 applied the same ruler twice more:
      * ADDED `--config-env=<name>=<envvar>` - the long-form sibling of `-c`, and a real git
        option. `V=true git --config-env=remote.origin.mirror=V push origin` measured as a
        forced update and was allowed. Its value is not in the command text and the hook
        cannot see the shell environment, so a matching key is denied FAIL-CLOSED even when
        the variable happens to hold a falsy value. That is a deliberate accepted false
        positive, recorded rather than hidden.
      * REMOVED `--force-if-includes`. Measured alone it does not force (rc=1, remote
        unmoved), and whenever it really accompanies a force, `--force` or
        `--force-with-lease` is already present and already denied - so it contributed ZERO
        marginal detection while adding false-positive surface, exactly the judgment used in
        round 4. Code and the table above previously contradicted each other; they agree now.

    Round 6 STOPPED ENUMERATING SPELLINGS. Rounds 4 and 5 each added one config injection
    spelling and each time the next round of review found the one after it. That is a signal
    about shape, not about diligence: the carrier is the KEY, not the mechanism. The guard now
    matches `remote.<name>.mirror` / `remote.<name>.push` whenever a push is present, so every
    SPELLING of that one mechanism is covered by a single rule. That is a statement about
    spellings, NOT about closure - round 6 review immediately defeated it through quoting and
    option arity, which round 7 fixed as instances while leaving the axes open (item 4). The
    previous sentence in this paragraph claimed more than the measurement supported. Net effect: `_config_assignments`, `_push_force_via_git_config`,
    `_truthy` and the two per-spelling regexes were DELETED - classification logic fell from
    355 to 343 lines. The file length is unchanged because the deleted mechanics were replaced
    by the documentation the new rule needs.

    Round 7 changed three things and, more importantly, one claim:
      * carrier detection now runs over TOKENS (already de-quoted) instead of the raw string,
        so `git -c remote."origin".mirror=true push origin` - measured forcing - is caught;
      * it no longer needs the subcommand to be located, so `git --attr-source HEAD
        -c remote.origin.mirror=true push origin` is caught even though the arity bug hides the
        subcommand;
      * `--attr-source` joined _GIT_VALUE_FLAGS and `send-pack` is now push-equivalent, both
        because they were measured to force while being allowed.
    And the claim: "every spelling ... is covered by the same rule" held only for new spellings
    of the same mechanism, not for quoting or option-arity tricks. Corrected above, and the
    structural boundary is now stated as its own non-coverage item rather than implied away.
"""

from __future__ import annotations

import json
import re
import sys

DENY_EXIT_CODE = 2
GUARD_ID = "WORKBUDDY_PRE_TOOL_USE_GIT_SAFETY_GUARD"

# Stable category ids; part of the denial contract. GIT_PUSH_FORCE names the CATEGORY
# (a force push). It is not, and never was, an environment variable git honours.
CATEGORY_PUSH_FORCE = "GIT_PUSH_FORCE"
CATEGORY_RESET_HARD = "GIT_RESET_HARD"
CATEGORY_CLEAN_FORCE = "GIT_CLEAN_FORCE"

DENIED_CATEGORIES = (CATEGORY_PUSH_FORCE, CATEGORY_RESET_HARD, CATEGORY_CLEAN_FORCE)

# Shell statement separators. Splitting here means `a && git push -f` is classified even
# when prefixed by unrelated commands.
_SEPARATORS = re.compile(r"\|\||&&|;|\||\n|\r")

# git global flags that consume a following value token. `--config-env` takes its value as a
# SEPARATE token - proved by `git --config-env push origin` answering "fatal: invalid config
# format: push", i.e. it swallowed `push`. Leaving it out made _split_subcommand misread
# `git --config-env remote.origin.mirror=V push origin` as subcommand "remote.origin.mirror=V",
# so the push was never seen. Measured: that spelling force-updates the remote.
_GIT_VALUE_FLAGS = {
    "-C",
    "-c",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--exec-path",
    "--config-env",
    "--attr-source",
}


def _segments(command: str) -> list[str]:
    return [part for part in _SEPARATORS.split(command) if part and part.strip()]


def _tokenize(segment: str) -> list[str]:
    """Minimal quote-aware tokenizer. Unbalanced quotes are tolerated (no crash)."""
    tokens: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    for ch in segment:
        if escaped:
            current.append(ch)
            escaped = False
            continue
        if ch == "\\" and quote != "'":
            escaped = True
            continue
        if quote is not None:
            if ch == quote:
                quote = None
            else:
                current.append(ch)
            continue
        if ch in ("'", '"'):
            quote = ch
            continue
        if ch.isspace():
            if current:
                tokens.append("".join(current))
                current = []
            continue
        current.append(ch)
    if current:
        tokens.append("".join(current))
    return tokens


def _is_git_invocation(token: str) -> bool:
    return token.rsplit("/", 1)[-1] == "git"


def _short_flag_letters(token: str) -> set[str]:
    """Letters of a short-flag cluster: -fd -> {f, d}; --force -> {}."""
    if len(token) >= 2 and token.startswith("-") and not token.startswith("--"):
        return set(token[1:])
    return set()


def _split_subcommand(tokens: list[str], index: int) -> tuple[str | None, list[str]]:
    """Given tokens[index] == 'git', return (subcommand, remaining tokens)."""
    j = index + 1
    while j < len(tokens) and tokens[j].startswith("-"):
        token = tokens[j]
        if token in _GIT_VALUE_FLAGS:
            j += 2
        else:
            j += 1
    if j >= len(tokens):
        return None, []
    return tokens[j], tokens[j + 1 :]


# The force-carrier CONFIG KEYS, matched directly in the command text.
#
# Why the key and not the mechanism: rounds 4 and 5 each added one config injection spelling,
# and each time review found the next one (`--config-env` joined, then its space-separated
# form, then the `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_n` / `GIT_CONFIG_VALUE_n` environment
# block). Enumerating spellings is the wrong shape - a spelling added by a future git would
# silently escape. The carrier is the KEY; matching it covers every present and future
# spelling with one rule.
#
# Accepted fail-closed false positives (documented in the README, consistent with this
# guard's existing stance on `echo 'git push -f'`):
#   * `git -c remote.origin.mirror=false push origin` - names the key but cannot force.
#   * `git push origin && git config remote.origin.mirror true` - sets the key only AFTER
#     the push, so this push is not forced.
#   * a ref that merely happens to be spelled `remote.x.mirror`.
# Each costs one nonsensical command form; a silent force push costs a rewritten history.
_FORCE_CONFIG_KEY = re.compile(r"remote\.[^\s\"'=:]{1,128}\.(?:mirror|push)", re.IGNORECASE)

# Subcommands that update remote refs and therefore accept the force flags. `send-pack` is the
# plumbing equivalent of `push`; measured: `git send-pack --force <url> <refspec>` force-updated
# the remote while this guard allowed it.
_PUSH_LIKE = ("push", "send-pack")


def _push_is_forced(tokens: list[str], rest: list[str]) -> bool:
    """Force expressed by a FLAG on the push itself. Key-injected force is handled separately
    by _FORCE_CONFIG_KEY, which is spelling-independent."""
    for token in rest:
        if token in ("--force", "--mirror"):
            return True
        if token.startswith("--force-with-lease"):
            return True
        if "f" in _short_flag_letters(token):
            return True
    return False


def _reset_is_hard(rest: list[str]) -> bool:
    return any(token == "--hard" for token in rest)


def _clean_is_forced_without_dry_run(rest: list[str]) -> bool:
    dry_run = any(token == "--dry-run" or "n" in _short_flag_letters(token) for token in rest)
    forced = any(token == "--force" or "f" in _short_flag_letters(token) for token in rest)
    return forced and not dry_run


def classify(command: str) -> str | None:
    """Return the denied category id, or None when the command is not in the deny set.

    Tokens that themselves contain whitespace (a quoted payload) are recursively
    re-analysed up to _MAX_EXPANSION_DEPTH. Without that step `bash -c 'git push -f'`
    would slip through while the equivalent unquoted spelling would be caught, i.e. the
    same semantic command would get two different verdicts. With it, both are caught.
    The cost is a deliberate fail-closed false positive: a command that merely *prints*
    a prohibited form (`echo 'git push -f'`) is denied too. Rephrasing is trivial; a
    silent force push is not.
    """
    return _classify_text(command, 0)


_MAX_EXPANSION_DEPTH = 3


def _classify_text(text: str, depth: int) -> str | None:
    mentions_push_like = False
    names_carrier_key = False

    for segment in _segments(text):
        tokens = _tokenize(segment)
        found = _classify_tokens(tokens, depth)
        if found is not None:
            return found
        # Two deliberately SHAPE-INDEPENDENT checks, both over TOKENS rather than the raw
        # string. Tokens are already quote-stripped by _tokenize, so `remote."origin".mirror`
        # is seen as the key it really is; and neither check depends on locating the
        # subcommand, so an unknown value-taking global option cannot hide them.
        if not names_carrier_key and any(_FORCE_CONFIG_KEY.search(t) for t in tokens):
            names_carrier_key = True
        if not mentions_push_like and any(t in _PUSH_LIKE for t in tokens):
            mentions_push_like = True

    # Key-injected force: a refs-updating subcommand plus a named force-carrier key.
    if mentions_push_like and names_carrier_key:
        return CATEGORY_PUSH_FORCE
    return None


def _classify_tokens(tokens: list[str], depth: int) -> str | None:
    for index, token in enumerate(tokens):
        if not _is_git_invocation(token):
            continue
        subcommand, rest = _split_subcommand(tokens, index)
        if subcommand is None:
            continue
        if subcommand in _PUSH_LIKE and _push_is_forced(tokens, rest):
            return CATEGORY_PUSH_FORCE
        if subcommand == "reset" and _reset_is_hard(rest):
            return CATEGORY_RESET_HARD
        if subcommand == "clean" and _clean_is_forced_without_dry_run(rest):
            return CATEGORY_CLEAN_FORCE

    if depth < _MAX_EXPANSION_DEPTH:
        for token in tokens:
            if any(ch.isspace() for ch in token):
                found = _classify_text(token, depth + 1)
                if found is not None:
                    return found
    return None


def _denial_payload(category: str) -> dict:
    reason = (
        f"{GUARD_ID}: {category}. This command form is prohibited by the repository hard "
        "invariants (no force push; no destructive workspace reset or clean). Use a "
        "non-destructive equivalent, or obtain explicit owner authorization for a scoped "
        "recovery path. The command text is intentionally not echoed."
    )
    return {
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }


def decide(payload: object) -> str | None:
    """Pure decision function: hook payload in, denied category or None out."""
    if not isinstance(payload, dict):
        return None
    event = str(payload.get("hook_event_name") or "")
    if event and event != "PreToolUse":
        return None
    if str(payload.get("tool_name") or "").lower() != "bash":
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return None
    return classify(command)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] == "--selfcheck":
        return 0 if _selfcheck() else 1

    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        payload = json.loads(raw)
        category = decide(payload)
        if category is None:
            return 0
        sys.stdout.write(json.dumps(_denial_payload(category), ensure_ascii=False))
        sys.stdout.flush()
        return DENY_EXIT_CODE
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - fail-open is a documented decision
        sys.stderr.write(
            f"{GUARD_ID}: internal error ({type(exc).__name__}); allowing the call. "
            "This is the documented fail-open path for an internal guard error.\n"
        )
        return 0


SELFCHECK_DENY = [
    "git push --force",
    "git push -f origin master",
    "git push origin master -f",
    "git push --force-with-lease origin feature",
    "git push --force-with-lease=origin/feature origin feature",
    "git push --mirror origin",
    "git -C /tmp/repo push -f origin master",
    "git --git-dir=/tmp/repo/.git push --force",
    "git -c remote.origin.mirror=true push origin",
    "git -c remote.origin.push=+refs/heads/master:refs/heads/master push origin",
    "git --config-env=remote.origin.mirror=V push origin",
    "git --config-env remote.origin.mirror=V push origin",
    "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.mirror GIT_CONFIG_VALUE_0=true git push origin",
    "git -c remote.\"origin\".mirror=true push origin",
    "git --attr-source HEAD push -f origin master",
    "git send-pack --force /tmp/origin.git refs/heads/master:refs/heads/master",
    "cd /tmp && git push -fu origin master",
    "git reset --hard",
    "git reset --hard HEAD~3",
    "git -C /tmp/x reset --hard",
    "git clean -fd",
    "git clean -df",
    "git clean -fdx",
    "git clean --force",
    "git clean -f -d",
]

SELFCHECK_ALLOW = [
    "git status",
    "git fetch origin",
    "git branch -a",
    "git push origin master",
    "git push -u origin feature",
    "git push --set-upstream origin feature",
    "git push --follow-tags origin master",
    "git push --dry-run origin master",
    "git push --force-if-includes origin master",
    # Measured NOT to force (see the module docstring). Asserted at deploy-verify time so the
    # removed false-positive deny rules cannot creep back in unnoticed.
    "git -c push.force=true push origin master",
    "GIT_PUSH_FORCE=1 git push origin master",
    "git rebase main",
    "git commit --amend --no-edit",
    "git reset --soft HEAD~1",
    "git reset HEAD -- file.txt",
    "git clean -n",
    "git clean -nd",
    "git clean --dry-run -fd",
    "git clean -X",
    "git log --oneline -n 5",
    "git diff --check",
    "ls -la",
]


def _selfcheck() -> bool:
    """Built-in matrix used by install.py VERIFY. Deterministic, no repository needed.

    Deliberately a strict subset of the unittest matrices; the tests assert that subset
    relation so a form cannot be added to one matrix and silently missed by the other.
    """
    for command in SELFCHECK_DENY:
        if classify(command) is None:
            sys.stderr.write(f"selfcheck FAIL: expected DENY for {command!r}\n")
            return False
    for command in SELFCHECK_ALLOW:
        found = classify(command)
        if found is not None:
            sys.stderr.write(f"selfcheck FAIL: expected ALLOW for {command!r}, got {found}\n")
            return False
    return True


if __name__ == "__main__":
    sys.exit(main())
