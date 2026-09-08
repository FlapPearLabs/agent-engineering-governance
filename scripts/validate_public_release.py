#!/usr/bin/env python3
"""Public-release safety gate for this repository.

The repository is PUBLIC. It was originally designed with PRIVATE-repo
assumptions, the most visible one being the `MACHINE-SPECIFIC ALLOWED`
designated-deployment-file exception. That exception is DEFUNCT in public
release mode: a public repository cannot declare a file "machine-specific
allowed" and then commit host facts, because the file is world-readable.

Threat model (see RULES.md R2):

    IF REPOSITORY_VISIBILITY == PUBLIC
        SECRET / LOCAL_IDENTITY   -> forbidden everywhere
        MACHINE_FINGERPRINT       -> forbidden in committed public artifacts
                                     unless it is a generic placeholder or
                                     ${HOME}-relative portable documentation
        PUBLIC_ACCOUNT_IDENTITY   -> allowed only when intentionally part of
                                     project identity (e.g. FlapPearLabs)
        PRIVATE_MACHINE_RECOVERY  -> must stay local-only / git-ignored /
                                     external private storage

    IF REPOSITORY_VISIBILITY == PRIVATE
        the historical designated machine-recovery semantics may remain
        available if governance explicitly permits them.

Execution contract (three modes, one file):

    python3 scripts/validate_public_release.py              # CURRENT_TREE_SCAN
    python3 scripts/validate_public_release.py --history     # GIT_HISTORY_SCAN
    python3 scripts/validate_public_release.py --selftest    # synthetic tests

Environment:

    PUBLIC_RELEASE=1   force public mode (deterministic, no GitHub API needed)
    PUBLIC_RELEASE=0   force private mode (designated exceptions allowed)
    unset              default PUBLIC (this repository is public)

Exit 0 = clean, 1 = violations found. Never prints a credential value.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Files that define the detectors themselves. They necessarily contain the
# patterns as source text and are exempt from the scan, like the existing
# governance validator exempts itself.
SELF_EXEMPT = {"validate_governance.py", "validate_public_release.py"}

SCAN_SUFFIXES = {".md", ".json", ".py", ".sh", ".txt", ".yml", ".yaml", ".toml"}

# --------------------------------------------------------------------------
# TIER A — forbidden everywhere, in every visibility mode.
# --------------------------------------------------------------------------
TIER_A_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("GITHUB_PAT", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("GITHUB_FINE_GRAINED_PAT", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("AWS_ACCESS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("SLACK_TOKEN", re.compile(r"xox[abposr]-[A-Za-z0-9-]{10,}")),
    ("OPENAI_STYLE_KEY", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("GOOGLE_API_KEY", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("PRIVATE_KEY_HEADER", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY")),
    ("GENERIC_BEARER", re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}")),
    ("COOKIE_ASSIGNMENT", re.compile(r"(?i)cookie\s*=\s*[A-Za-z0-9._\-]{16,}")),
    ("PASSWORD_ASSIGNMENT", re.compile(r"(?i)password\s*=\s*\S{8,}")),
    # LOCAL_IDENTITY: concrete host login directories. Placeholders such as
    # /Users/<LOCAL_OS_USERNAME>/ deliberately do NOT match because '<' is
    # outside the character class.
    ("WIN_USER_HOME", re.compile(r"(?i)[A-Za-z]:[\\/]+Users[\\/]+[A-Za-z0-9._\-]+")),
    ("UNIX_USER_HOME", re.compile(r"/(?:Users|home)/[A-Za-z0-9._\-]+")),
]

# --------------------------------------------------------------------------
# TIER B — machine fingerprint. Forbidden in PUBLIC artifacts unless the
# occurrence is a placeholder or a portable ${HOME}/~/ documentation form.
# --------------------------------------------------------------------------
TIER_B_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("LOCALHOST_ENDPOINT", re.compile(r"(?:127\.0\.0\.1|localhost|0\.0\.0\.0):[0-9]{2,5}")),
    ("HOST_PACKAGE_PREFIX", re.compile(r"/opt/homebrew/")),
    # Requires an actual endpoint: a scheme or a host:port. A placeholder such
    # as `HTTPS_PROXY=<LOCAL_PROXY_URL>` leaves nothing matchable after
    # placeholder stripping, so documented templates stay legal.
    ("PROXY_ENV_VALUE",
     re.compile(r"(?i)\bhttps?_proxy\s*[=:]\s*(?:https?://|[\w.\-]+:\d+)\S*")),
]

# Generic / portable forms that are allowed documentation, never a host fact.
PLACEHOLDER_SPANS = [
    re.compile(r"<[A-Z][A-Z0-9_]{2,}>"),
    re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}"),
    re.compile(r"\$\([^)]*\)"),
]

# The historical private-repo escape hatch. Present so that (a) private mode
# keeps its documented semantics and (b) the test suite can prove it does NOT
# bypass public mode.
DESIGNATED_MARKER = "MACHINE-SPECIFIC ALLOWED"
DESIGNATED_DIR = "deployment"


def public_mode() -> bool:
    """Deterministic, offline: PUBLIC_RELEASE env wins, default PUBLIC."""
    raw = os.environ.get("PUBLIC_RELEASE")
    if raw is None:
        return True
    return raw.strip() not in ("0", "false", "False", "no")


# --------------------------------------------------------------------------
# Output safety: never emit a secret value, never emit a real login name.
# --------------------------------------------------------------------------
def sanitize(text: str) -> str:
    text = re.sub(r"(/(?:Users|home)/)[A-Za-z0-9._\-]+",
                  r"\1<LOCAL_OS_USERNAME>", text)
    text = re.sub(r"(?i)([A-Za-z]:[\\/]+Users[\\/]+)[A-Za-z0-9._\-]+",
                  r"\1<LOCAL_OS_USERNAME>", text)
    return text


@dataclass
class Violation:
    severity: str      # SECRET | LOCAL_IDENTITY | MACHINE_FINGERPRINT
    rule: str
    path: str
    lineno: int
    excerpt: str       # already sanitized / redacted

    def render(self) -> str:
        return f"[{self.severity}/{self.rule}] {self.path}:{self.lineno} :: {self.excerpt}"


def strip_placeholders(line: str) -> str:
    for rx in PLACEHOLDER_SPANS:
        line = rx.sub(" ", line)
    line = line.replace("~", " ").replace("$HOME", " ")
    return line


def scan_text(path: str, text: str) -> list[Violation]:
    out: list[Violation] = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        # TIER A is unconditional: no placeholder can excuse a credential or a
        # concrete local login directory.
        for rule, rx in TIER_A_PATTERNS:
            m = rx.search(raw)
            if m:
                if rule in ("GITHUB_PAT", "GITHUB_FINE_GRAINED_PAT", "AWS_ACCESS_KEY",
                            "SLACK_TOKEN", "OPENAI_STYLE_KEY", "GOOGLE_API_KEY",
                            "PRIVATE_KEY_HEADER", "GENERIC_BEARER",
                            "COOKIE_ASSIGNMENT", "PASSWORD_ASSIGNMENT"):
                    sev, excerpt = "SECRET", "<REDACTED: value withheld>"
                else:
                    sev = "LOCAL_IDENTITY"
                    excerpt = sanitize(raw.strip())[:160]
                out.append(Violation(sev, rule, path, lineno, excerpt))
        if not public_mode():
            continue
        probe = strip_placeholders(raw)
        for rule, rx in TIER_B_PATTERNS:
            if rx.search(probe):
                out.append(Violation("MACHINE_FINGERPRINT", rule, path, lineno,
                                     sanitize(probe.strip())[:160]))
    return out


def iter_scan_files(root: Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if ".git" in p.parts:
            continue
        if p.name in SELF_EXEMPT:
            continue
        if p.suffix not in SCAN_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        yield str(p.relative_to(root)), text


def scan_tree(root: Path) -> list[Violation]:
    out: list[Violation] = []
    for rel, text in iter_scan_files(root):
        out += scan_text(rel, text)
    return out


def scan_history(root: Path) -> list[Violation]:
    """GIT_HISTORY_SCAN over every blob in the object store.

    Deliberately separate from CURRENT_TREE_SCAN: the tree scan is cheap and
    gates every commit, the history scan is expensive and runs on demand.
    """
    paths: dict[str, str] = {}
    listing = subprocess.run(["git", "-C", str(root), "rev-list", "--objects", "--all"],
                             capture_output=True, text=True)
    for line in listing.stdout.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[1] and not parts[1].endswith("/"):
            paths.setdefault(parts[0], parts[1])

    out: list[Violation] = []
    proc = subprocess.Popen(
        ["git", "-C", str(root), "cat-file", "--batch-all-objects", "--batch"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    assert proc.stdout is not None
    while True:
        header = proc.stdout.readline().decode("utf-8", "replace").strip()
        if not header:
            break
        parts = header.split()
        if len(parts) < 3:
            continue
        sha, otype, size = parts[0], parts[1], int(parts[2])
        data = proc.stdout.read(size)
        proc.stdout.read(1)
        if otype != "blob":
            continue
        rel = paths.get(sha, f"objects/{sha[:8]}")
        if Path(rel).name in SELF_EXEMPT:
            continue
        if Path(rel).suffix not in SCAN_SUFFIXES:
            continue
        out += scan_text(f"history:{sha[:8]}:{rel}", data.decode("utf-8", "replace"))
    proc.wait()
    return out


def print_report(title: str, violations: list[Violation]) -> None:
    print(f"### {title}")
    print(f"MODE={'PUBLIC' if public_mode() else 'PRIVATE'}")
    print(f"VIOLATIONS={len(violations)}")
    for v in violations:
        print("  " + v.render())
    print()


# --------------------------------------------------------------------------
# Synthetic self-tests. Fixtures are built at run time, committed nowhere.
# --------------------------------------------------------------------------
def selftest(root: Path) -> int:
    results: list[tuple[str, bool, str]] = []

    def t(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    def scan_tmp(files: dict[str, str]) -> list[Violation]:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            for rel, content in files.items():
                fp = base / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(content, encoding="utf-8")
            return scan_tree(base)

    fake_pat = "ghp_" + "A" * 30          # built, never literal
    fake_sk = "sk-" + "B" * 24            # built, never literal

    v = scan_tmp({"a.md": "path = /Users/someuser/project/x.md\n"})
    t("1-public-rejects-unix-user-home",
      any(x.rule == "UNIX_USER_HOME" for x in v), str([x.rule for x in v]))

    v = scan_tmp({"a.md": 'checkout = C:\\Users\\someuser\\.zcode\\workspace\n'})
    t("2-public-rejects-windows-user-home",
      any(x.rule == "WIN_USER_HOME" for x in v), str([x.rule for x in v]))

    v = scan_tmp({"a.md": "| 出网代理 | `http://127.0.0.1:7897` | FACT |\n"})
    t("3-public-rejects-localhost-proxy-endpoint",
      any(x.rule == "LOCALHOST_ENDPOINT" for x in v), str([x.rule for x in v]))

    v = scan_tmp({"a.md": "| gh | `<PATH_TO_GH> <VERSION>` |\n"
                          "| proxy | `<LOCAL_PROXY_URL>` |\n"
                          "| home | `/Users/<LOCAL_OS_USERNAME>/x` |\n"})
    t("4-placeholders-allowed", not v, str([x.rule for x in v]))

    v = scan_tmp({"a.md": "export CFG=${HOME}/.workbuddy/mcp.json\n"
                          "export CFG2=$HOME/.config/app\n"})
    t("5-home-templates-allowed", not v, str([x.rule for x in v]))

    v = scan_tmp({"a.md": "Owner: FlapPearLabs; email: x@users.noreply.github.com\n"})
    t("6-project-account-identity-not-rejected", not v, str([x.rule for x in v]))

    v = scan_tmp({"a.md": f"token = {fake_pat}\nkey = {fake_sk}\n"})
    t("7-credential-fixtures-fail",
      any(x.severity == "SECRET" for x in v), str([x.rule for x in v]))

    rendered = "\n".join(x.render() for x in v) + "\n".join(x.excerpt for x in v)
    t("8-no-credential-value-in-output",
      fake_pat not in rendered and fake_sk not in rendered, "value leaked into output")

    v = scan_tmp({f"{DESIGNATED_DIR}/profile.md":
                  f"{DESIGNATED_MARKER}\n\n| proxy | http://127.0.0.1:7890 |\n"})
    t("9-designated-marker-cannot-bypass-public",
      any(x.rule == "LOCALHOST_ENDPOINT" for x in v), str([x.rule for x in v]))

    tree_v = scan_tree(root)
    t("10-current-public-tree-clean", not tree_v,
      "; ".join(x.render() for x in tree_v[:8]))

    os.environ["PUBLIC_RELEASE"] = "0"
    try:
        v = scan_tmp({f"{DESIGNATED_DIR}/profile.md":
                      f"{DESIGNATED_MARKER}\n\n| proxy | http://127.0.0.1:7890 |\n"})
        t("11-private-mode-keeps-designated-semantics", not v, str([x.rule for x in v]))
    finally:
        os.environ["PUBLIC_RELEASE"] = "1"

    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    print(f"\n{len(results) - len(failed)}/{len(results)} public-release tests passed")
    return 1 if failed else 0


def main() -> int:
    args = [a for a in sys.argv[1:]]
    mode = "tree"
    for a in args:
        if a in ("--history", "--selftest"):
            mode = a[2:]

    if mode == "selftest":
        return selftest(ROOT)

    if mode == "history":
        v = scan_history(ROOT)
        print_report("GIT_HISTORY_SCAN", v)
        # MEASUREMENT, not a gate. Historical local-identity / machine-fingerprint
        # findings are a privacy-hygiene issue requiring an owner decision on
        # remediation; they must not auto-fail a scheduled job. A confirmed
        # credential in history is different: it demands rotation, so it fails.
        secrets = [x for x in v if x.severity == "SECRET"]
        ident = [x for x in v if x.severity == "LOCAL_IDENTITY"]
        mach = [x for x in v if x.severity == "MACHINE_FINGERPRINT"]
        print(f"HISTORY_SEVERITY SECRET={len(secrets)} "
              f"LOCAL_IDENTITY={len(ident)} MACHINE_FINGERPRINT={len(mach)}")
        print("HISTORY_REWRITE_REQUIRED=USER_DECISION_REQUIRED"
              if not secrets and (ident or mach) else
              "HISTORY_REWRITE_REQUIRED=STOP_OWNER_DECISION" if secrets else
              "HISTORY_REWRITE_REQUIRED=NO")
        return 1 if secrets else 0

    v = scan_tree(ROOT)
    print_report("CURRENT_TREE_SCAN", v)
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main())
