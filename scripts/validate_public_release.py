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
                                     project identity (see
                                     PUBLIC_PROJECT_IDENTITY below)
        PRIVATE_MACHINE_RECOVERY  -> must stay local-only / git-ignored /
                                     external private storage

    IF REPOSITORY_VISIBILITY == PRIVATE
        MACHINE_FINGERPRINT is allowed ONLY inside a designated deployment
        profile (under `deployment/`, carrying the marker). Ordinary
        governance / audit / README files stay forbidden: private visibility
        is not a blanket exemption.

Design invariants (external audit F1 / F2):

  * NO whole-file scanner self-exemption. This file is scanned like any other
    file, in both tree and history mode. Detector regexes are written so their
    own source text cannot match them (a character class breaks the literal),
    and every synthetic fixture is composed at run time so no sensitive
    literal exists in this source. The incident this gate repairs was
    validator source leaking host identity; exempting validator source from
    the scan would reproduce that incident.
  * SECRET / LOCAL_IDENTITY detection is content-based, never gated on a file
    extension allowlist. Extensionless configuration, dotfiles, container and
    build recipes are exactly where credentials live.

Execution contract (one file, four modes):

    python3 scripts/validate_public_release.py                    # CURRENT_TREE_SCAN
    python3 scripts/validate_public_release.py --history          # GIT_HISTORY_SCAN
    python3 scripts/validate_public_release.py --commit-metadata  # HEAD identity gate
    python3 scripts/validate_public_release.py --selftest         # synthetic tests

Environment:

    PUBLIC_RELEASE=1   force public mode (deterministic, no GitHub API needed)
    PUBLIC_RELEASE=0   force private mode (designated exception available)
    unset              default PUBLIC (this repository is public)

Exit 0 = clean, 1 = violations found. Never prints a credential value, a host
login name, or a non-canonical account handle.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Content classification, replacing the former extension allowlist (F2).
MAX_SCAN_BYTES = 2 * 1024 * 1024          # blob size cap
BINARY_SNIFF_BYTES = 8192                 # bytes inspected for text/binary
NONTEXT_RATIO_LIMIT = 0.30
_NONTEXT_BYTES = bytes(range(0, 7)) + b"\x0b\x0c" + bytes(range(14, 32)) + b"\x7f"

# --------------------------------------------------------------------------
# Intentional public project identity (F4). Deliberately the ONLY identity
# concept in this file: this is a gate, not an identity-management framework.
# --------------------------------------------------------------------------
PUBLIC_PROJECT_IDENTITY = "FlapPearLabs"
NOREPLY_HOST = "users.noreply.github.com"
NOREPLY_RX = re.compile(
    r"(?:(?P<uid>\d+)\+)?(?P<handle>[A-Za-z0-9][A-Za-z0-9\-]{0,38})@"
    + NOREPLY_HOST.replace(".", r"\."),
    re.I,
)

# --------------------------------------------------------------------------
# TIER A — forbidden everywhere, in every visibility mode.
# Each regex is written so that its own source line cannot match it.
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
    # LOCAL_IDENTITY: concrete host login directories. A placeholder such as
    # /Users/<LOCAL_OS_USERNAME>/ deliberately does NOT match, because '<' is
    # outside the trailing character class.
    ("WIN_USER_HOME", re.compile(r"(?i)[A-Za-z]:[\\/]+Users[\\/]+[A-Za-z0-9._\-]+")),
    ("UNIX_USER_HOME", re.compile(r"/(?:Users|home)/[A-Za-z0-9._\-]+")),
]

SECRET_RULES = {
    "GITHUB_PAT", "GITHUB_FINE_GRAINED_PAT", "AWS_ACCESS_KEY", "SLACK_TOKEN",
    "OPENAI_STYLE_KEY", "GOOGLE_API_KEY", "PRIVATE_KEY_HEADER",
    "GENERIC_BEARER", "COOKIE_ASSIGNMENT", "PASSWORD_ASSIGNMENT",
}

# --------------------------------------------------------------------------
# TIER B — machine fingerprint. Forbidden in PUBLIC artifacts; in PRIVATE mode
# forbidden everywhere except a designated deployment profile.
# --------------------------------------------------------------------------
TIER_B_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("LOCALHOST_ENDPOINT", re.compile(r"(?:127\.0\.0\.1|localhost|0\.0\.0\.0):[0-9]{2,5}")),
    # `[b]` breaks the literal so this detector cannot match its own source.
    ("HOST_PACKAGE_PREFIX", re.compile(r"/opt/home[b]rew/")),
    # Requires an actual endpoint: a scheme or a host:port. A documented
    # template leaves nothing matchable after placeholder stripping.
    ("PROXY_ENV_VALUE",
     re.compile(r"(?i)\bhttps?_proxy\s*[=:]\s*(?:https?://|[\w.\-]+:\d+)\S*")),
]

# Generic / portable forms that are allowed documentation, never a host fact.
PLACEHOLDER_SPANS = [
    re.compile(r"<[A-Z][A-Z0-9_]{2,}>"),
    re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}"),
    re.compile(r"\$\([^)]*\)"),
]

# The historical private-repo escape hatch. Retained so that (a) private mode
# keeps its documented, NARROW semantics and (b) the test suite can prove it
# does not bypass public mode.
DESIGNATED_MARKER = "MACHINE-SPECIFIC ALLOWED"
DESIGNATED_DIR = "deployment"


def public_mode() -> bool:
    """Deterministic, offline: PUBLIC_RELEASE env wins, default PUBLIC."""
    raw = os.environ.get("PUBLIC_RELEASE")
    if raw is None:
        return True
    return raw.strip() not in ("0", "false", "False", "no")


# --------------------------------------------------------------------------
# Output safety: never emit a secret value, a real login name, or a
# non-canonical account handle.
# --------------------------------------------------------------------------
def _redact_noreply(m: re.Match[str]) -> str:
    if m.group("handle").lower() == PUBLIC_PROJECT_IDENTITY.lower():
        return m.group(0)
    return "<SECONDARY_GITHUB_HANDLE>@" + NOREPLY_HOST


def sanitize(text: str) -> str:
    text = re.sub(r"(/(?:Users|home)/)[A-Za-z0-9._\-]+",
                  r"\1<LOCAL_OS_USERNAME>", text)
    text = re.sub(r"(?i)([A-Za-z]:[\\/]+Users[\\/]+)[A-Za-z0-9._\-]+",
                  r"\1<LOCAL_OS_USERNAME>", text)
    return NOREPLY_RX.sub(_redact_noreply, text)


@dataclass
class Violation:
    severity: str      # SECRET | LOCAL_IDENTITY | MACHINE_FINGERPRINT
    rule: str
    path: str
    lineno: int
    excerpt: str       # already sanitized / redacted

    def render(self) -> str:
        return f"[{self.severity}/{self.rule}] {self.path}:{self.lineno} :: {self.excerpt}"


@dataclass
class Scope:
    """Honest accounting of what was actually inspected."""
    refs: int = 0
    objects_total: int = 0
    blobs_total: int = 0
    text_scanned: int = 0
    skipped_binary: int = 0
    skipped_oversize: int = 0
    notes: list[str] = field(default_factory=list)

    def render(self, kind: str) -> str:
        return (f"{kind}_SCOPE refs={self.refs} objects={self.objects_total} "
                f"blobs={self.blobs_total} text_scanned={self.text_scanned} "
                f"skipped_binary={self.skipped_binary} "
                f"skipped_oversize={self.skipped_oversize} "
                f"size_cap_bytes={MAX_SCAN_BYTES}")


def decode_if_text(data: bytes, scope: Scope | None = None) -> str | None:
    """Content-based text classification (F2). No extension allowlist."""
    if len(data) > MAX_SCAN_BYTES:
        if scope:
            scope.skipped_oversize += 1
        return None
    sniff = data[:BINARY_SNIFF_BYTES]
    if b"\x00" in sniff:
        if scope:
            scope.skipped_binary += 1
        return None
    if sniff:
        nontext = sum(sniff.count(b) for b in _NONTEXT_BYTES)
        if nontext / len(sniff) > NONTEXT_RATIO_LIMIT:
            if scope:
                scope.skipped_binary += 1
            return None
    if scope:
        scope.text_scanned += 1
    return data.decode("utf-8", "replace")


def strip_placeholders(line: str) -> str:
    for rx in PLACEHOLDER_SPANS:
        line = rx.sub(" ", line)
    line = line.replace("~", " ").replace("$HOME", " ")
    return line


def is_designated(path: str, text: str) -> bool:
    """Designated private machine-recovery profile: path AND header marker."""
    norm = path.replace("\\", "/")
    if norm.startswith("history:"):
        norm = norm.split(":", 2)[-1]
    head = "\n".join(text.splitlines()[:10])
    return norm.startswith(DESIGNATED_DIR + "/") and DESIGNATED_MARKER in head


def scan_text(path: str, text: str) -> list[Violation]:
    out: list[Violation] = []
    # F3: private visibility is not a blanket exemption. Tier B is skipped ONLY
    # for a designated deployment profile, and only when not in public mode.
    tier_b_exempt = (not public_mode()) and is_designated(path, text)
    for lineno, raw in enumerate(text.splitlines(), 1):
        # TIER A is unconditional: no placeholder, marker or visibility mode can
        # excuse a credential or a concrete local login directory.
        for rule, rx in TIER_A_PATTERNS:
            if rx.search(raw):
                if rule in SECRET_RULES:
                    sev, excerpt = "SECRET", "<REDACTED: value withheld>"
                else:
                    sev = "LOCAL_IDENTITY"
                    excerpt = sanitize(raw.strip())[:160]
                out.append(Violation(sev, rule, path, lineno, excerpt))
        if tier_b_exempt:
            continue
        probe = strip_placeholders(raw)
        for rule, rx in TIER_B_PATTERNS:
            if rx.search(probe):
                out.append(Violation("MACHINE_FINGERPRINT", rule, path, lineno,
                                     sanitize(probe.strip())[:160]))
    return out


def iter_scan_files(root: Path, scope: Scope | None = None):
    for p in sorted(root.rglob("*")):
        if p.is_symlink() or not p.is_file():
            continue
        if ".git" in p.parts:
            continue
        if scope:
            scope.blobs_total += 1
        try:
            data = p.read_bytes()
        except OSError:
            continue
        text = decode_if_text(data, scope)
        if text is None:
            continue
        yield str(p.relative_to(root)).replace("\\", "/"), text


def scan_tree(root: Path, scope: Scope | None = None) -> list[Violation]:
    out: list[Violation] = []
    for rel, text in iter_scan_files(root, scope):
        out += scan_text(rel, text)
    return out


def scan_history(root: Path, scope: Scope | None = None) -> list[Violation]:
    """GIT_HISTORY_SCAN over every blob in the reachable object store.

    Deliberately separate from CURRENT_TREE_SCAN: the tree scan is cheap and
    gates every commit, the history scan is expensive and runs on demand.
    Scope is recorded, not assumed: the caller reports how many refs/objects
    were actually inspected instead of claiming a universal clean bill.
    """
    scope = scope if scope is not None else Scope()
    refs = subprocess.run(["git", "-C", str(root), "for-each-ref", "--format=%(refname)"],
                          capture_output=True, text=True)
    scope.refs = len([r for r in refs.stdout.splitlines() if r.strip()])

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
        scope.objects_total += 1
        if otype != "blob":
            continue
        scope.blobs_total += 1
        text = decode_if_text(data, scope)
        if text is None:
            continue
        rel = paths.get(sha, f"unnamed-object/{sha[:8]}")
        out += scan_text(f"history:{sha[:8]}:{rel}", text)
    proc.wait()
    return out


# --------------------------------------------------------------------------
# F4 — CURRENT_HEAD_COMMIT_METADATA gate.
# --------------------------------------------------------------------------
def mask_name(value: str) -> str:
    return "<NON_CANONICAL_AUTHOR_NAME>" if value.strip() else "<EMPTY>"


def mask_email(value: str) -> str:
    value = value.strip()
    if not value:
        return "<EMPTY>"
    if NOREPLY_RX.search(value):
        return "<SECONDARY_GITHUB_HANDLE>@" + NOREPLY_HOST
    return "<NON_CANONICAL_EMAIL>"


def identity_problems(role: str, name: str, email: str) -> list[str]:
    """Minimal check: does this identity match the intentional public one?"""
    problems: list[str] = []
    if name.strip() != PUBLIC_PROJECT_IDENTITY:
        problems.append(f"{role}_name != PUBLIC_PROJECT_IDENTITY "
                        f"({mask_name(name)})")
    m = NOREPLY_RX.fullmatch(email.strip())
    if not m:
        problems.append(f"{role}_email is not a canonical noreply form of "
                        f"PUBLIC_PROJECT_IDENTITY ({mask_email(email)})")
    elif m.group("handle").lower() != PUBLIC_PROJECT_IDENTITY.lower():
        # The decisive rule: a matching display name must NOT launder a
        # different account handle into public commit metadata.
        problems.append(f"{role}_email handle != PUBLIC_PROJECT_IDENTITY "
                        f"({mask_email(email)})")
    return problems


def head_commit_metadata(root: Path) -> dict[str, str]:
    fmt = "%an%n%ae%n%cn%n%ce"
    proc = subprocess.run(["git", "-C", str(root), "log", "-1", f"--format={fmt}"],
                          capture_output=True, text=True)
    lines = proc.stdout.splitlines()
    if proc.returncode != 0 or len(lines) < 4:
        return {}
    return {"author_name": lines[0], "author_email": lines[1],
            "committer_name": lines[2], "committer_email": lines[3]}


def commit_metadata_gate(root: Path) -> int:
    meta = head_commit_metadata(root)
    print("### CURRENT_HEAD_COMMIT_METADATA")
    print(f"PUBLIC_PROJECT_IDENTITY={PUBLIC_PROJECT_IDENTITY}")
    if not meta:
        print("VIOLATIONS=1")
        print("  [IDENTITY/NO_HEAD_COMMIT] unable to read HEAD commit metadata")
        return 1
    problems = (identity_problems("author", meta["author_name"], meta["author_email"])
                + identity_problems("committer", meta["committer_name"],
                                    meta["committer_email"]))
    print(f"VIOLATIONS={len(problems)}")
    for p in problems:
        print(f"  [PUBLIC_ACCOUNT_IDENTITY] {p}")
    if not problems:
        print(f"  author=committer={PUBLIC_PROJECT_IDENTITY} "
              f"(canonical @{NOREPLY_HOST} form)")
    return 1 if problems else 0


def print_report(title: str, violations: list[Violation], scope: Scope | None = None,
                 scope_kind: str = "") -> None:
    print(f"### {title}")
    print(f"MODE={'PUBLIC' if public_mode() else 'PRIVATE'}")
    if scope is not None:
        print(scope.render(scope_kind or title))
    print(f"VIOLATIONS={len(violations)}")
    for v in violations:
        print("  " + v.render())
    print()


# --------------------------------------------------------------------------
# Synthetic self-tests. Every sensitive fixture is COMPOSED at run time so
# that no sensitive literal exists in this source (F1). Nothing is committed.
# --------------------------------------------------------------------------
def _syn_unix_home() -> str:
    return "/" + "Users" + "/" + "synthlogin" + "/project/x.md"


def _syn_win_home() -> str:
    return "C" + ":" + "\\" + "Users" + "\\" + "synthlogin" + "\\.zcode"


def _syn_proxy_endpoint() -> str:
    return "http://" + "127.0.0" + ".1" + ":" + "7897"


def _syn_brew_path() -> str:
    return "/opt/" + "homebrew" + "/bin/gh"


def _syn_pat() -> str:
    return "gh" + "p" + "_" + "A" * 30


def _syn_api_key() -> str:
    return "sk" + "-" + "B" * 24


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

    def private(fn):
        prev = os.environ.get("PUBLIC_RELEASE")
        os.environ["PUBLIC_RELEASE"] = "0"
        try:
            return fn()
        finally:
            if prev is None:
                os.environ.pop("PUBLIC_RELEASE", None)
            else:
                os.environ["PUBLIC_RELEASE"] = prev

    # ---- PUBLIC tier-A / tier-B behaviour -------------------------------
    v = scan_tmp({"a.md": f"path = {_syn_unix_home()}\n"})
    t("01-public-rejects-unix-user-home",
      any(x.rule == "UNIX_USER_HOME" for x in v), str([x.rule for x in v]))

    v = scan_tmp({"a.md": f"checkout = {_syn_win_home()}\n"})
    t("02-public-rejects-windows-user-home",
      any(x.rule == "WIN_USER_HOME" for x in v), str([x.rule for x in v]))

    v = scan_tmp({"a.md": f"| proxy | `{_syn_proxy_endpoint()}` | FACT |\n"})
    t("03-public-rejects-localhost-proxy-endpoint",
      any(x.rule == "LOCALHOST_ENDPOINT" for x in v), str([x.rule for x in v]))

    v = scan_tmp({"a.md": "| gh | `<PATH_TO_GH> <VERSION>` |\n"
                          "| proxy | `<LOCAL_PROXY_URL>` |\n"
                          "| home | `/Users/<LOCAL_OS_USERNAME>/x` |\n"})
    t("04-placeholders-allowed", not v, str([x.rule for x in v]))

    v = scan_tmp({"a.md": "export CFG=${HOME}/.workbuddy/mcp.json\n"
                          "export CFG2=$HOME/.config/app\n"})
    t("05-home-templates-allowed", not v, str([x.rule for x in v]))

    v = scan_tmp({"a.md": f"Owner: {PUBLIC_PROJECT_IDENTITY}; "
                          f"email: {PUBLIC_PROJECT_IDENTITY}@{NOREPLY_HOST}\n"})
    t("06-project-account-identity-not-secret", not v, str([x.rule for x in v]))

    v = scan_tmp({"a.md": f"token = {_syn_pat()}\nkey = {_syn_api_key()}\n"})
    t("07-credential-fixtures-fail",
      any(x.severity == "SECRET" for x in v), str([x.rule for x in v]))

    rendered = "\n".join(x.render() for x in v) + "\n".join(x.excerpt for x in v)
    t("08-no-credential-value-in-output",
      _syn_pat() not in rendered and _syn_api_key() not in rendered,
      "credential value leaked into output")

    v = scan_tmp({f"{DESIGNATED_DIR}/profile.md":
                  f"{DESIGNATED_MARKER}\n\n| proxy | {_syn_proxy_endpoint()} |\n"})
    t("09-designated-marker-cannot-bypass-public",
      any(x.rule == "LOCALHOST_ENDPOINT" for x in v), str([x.rule for x in v]))

    # ---- F1: no whole-file scanner self-exemption -----------------------
    t("10-no-self-exempt-or-suffix-allowlist",
      not any(n in globals() for n in ("SELF_EXEMPT", "SCAN_SUFFIXES")),
      "whole-file exemption / suffix allowlist still present")

    src = (root / "scripts" / "validate_public_release.py").read_text(encoding="utf-8")
    v = scan_tmp({"scripts/validate_public_release.py": src})
    t("11-scanner-source-is-scanned-and-clean", not v,
      "; ".join(x.render() for x in v[:4]))

    injected = src + "\n# recovered checkout: " + _syn_unix_home() + "\n"
    v = scan_tmp({"scripts/validate_public_release.py": injected})
    t("12-injected-identity-in-scanner-source-fails",
      any(x.rule == "UNIX_USER_HOME" for x in v), str([x.rule for x in v]))

    gsrc = (root / "scripts" / "validate_governance.py").read_text(encoding="utf-8")
    v = scan_tmp({"scripts/validate_governance.py": gsrc})
    t("13-governance-scanner-source-clean", not v,
      "; ".join(x.render() for x in v[:4]))

    v = scan_tmp({"scripts/validate_governance.py":
                  gsrc + "\n# " + _syn_win_home() + "\n"})
    t("14-injected-identity-in-governance-source-fails",
      any(x.rule == "WIN_USER_HOME" for x in v), str([x.rule for x in v]))

    # ---- F2: content-based, not extension-based ------------------------
    v = scan_tmp({".env": f"GITHUB_TOKEN={_syn_pat()}\n"})
    t("15-dotenv-credential-fails",
      any(x.severity == "SECRET" for x in v), str([x.rule for x in v]))

    v = scan_tmp({".env.local": f"OPENAI_API_KEY={_syn_api_key()}\n"})
    t("16-dotenv-local-credential-fails",
      any(x.severity == "SECRET" for x in v), str([x.rule for x in v]))

    v = scan_tmp({"Dockerfile": f"ENV OPENAI_API_KEY={_syn_api_key()}\n"})
    t("17-dockerfile-credential-fails",
      any(x.severity == "SECRET" for x in v), str([x.rule for x in v]))

    v = scan_tmp({"credentials": f"machine github.com login x {_syn_pat()}\n"})
    t("18-extensionless-credential-fails",
      any(x.severity == "SECRET" for x in v), str([x.rule for x in v]))

    v = scan_tmp({"Makefile": f"export HTTPS_PROXY={_syn_proxy_endpoint()}\n"})
    t("19-makefile-machine-fingerprint-fails",
      any(x.severity == "MACHINE_FINGERPRINT" for x in v), str([x.rule for x in v]))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        env = dict(os.environ,
                   GIT_AUTHOR_NAME="synthetic", GIT_AUTHOR_EMAIL="s@example.invalid",
                   GIT_COMMITTER_NAME="synthetic", GIT_COMMITTER_EMAIL="s@example.invalid")

        def g(*a):
            return subprocess.run(["git", "-C", str(base), *a],
                                  capture_output=True, text=True, env=env)

        g("init", "-q")
        (base / "credentials").write_text(f"token {_syn_pat()}\n", encoding="utf-8")
        (base / "Dockerfile").write_text(f"ENV K={_syn_api_key()}\n", encoding="utf-8")
        (base / "logo.bin").write_bytes(b"\x89PNG\x00\x00" + bytes(range(256)) * 4)
        g("add", "-A")
        g("commit", "-q", "-m", "synthetic fixture commit")
        hscope = Scope()
        hv = scan_history(base, hscope)
        t("20-history-scan-covers-extensionless-and-dockerfile",
          sum(1 for x in hv if x.severity == "SECRET") >= 2,
          f"secrets={[x.rule for x in hv]}")
        t("21-history-scan-classifies-binary-out",
          hscope.skipped_binary >= 1 and hscope.text_scanned >= 2,
          f"text={hscope.text_scanned} binary={hscope.skipped_binary}")

    # ---- F3: PRIVATE designated semantics are narrow -------------------
    v = private(lambda: scan_tmp({f"{DESIGNATED_DIR}/deployment-profile.md":
                                  f"{DESIGNATED_MARKER}\n\n| proxy | {_syn_proxy_endpoint()} |\n"}))
    t("22-private-designated-profile-allows-tier-b", not v, str([x.rule for x in v]))

    v = private(lambda: scan_tmp({"README.md": f"| proxy | {_syn_proxy_endpoint()} |\n"}))
    t("23-private-ordinary-readme-still-fails",
      any(x.severity == "MACHINE_FINGERPRINT" for x in v), str([x.rule for x in v]))

    v = private(lambda: scan_tmp({"audit/AS_IS.md": f"gh at {_syn_brew_path()}\n"}))
    t("24-private-ordinary-audit-still-fails",
      any(x.severity == "MACHINE_FINGERPRINT" for x in v), str([x.rule for x in v]))

    v = private(lambda: scan_tmp({f"{DESIGNATED_DIR}/notes.md":
                                  f"| proxy | {_syn_proxy_endpoint()} |\n"}))
    t("25-private-unmarked-deployment-file-still-fails",
      any(x.severity == "MACHINE_FINGERPRINT" for x in v), str([x.rule for x in v]))

    v = private(lambda: scan_tmp({f"{DESIGNATED_DIR}/deployment-profile.md":
                                  f"{DESIGNATED_MARKER}\n\npath {_syn_unix_home()}\n"}))
    t("26-private-designated-profile-still-rejects-tier-a",
      any(x.rule == "UNIX_USER_HOME" for x in v), str([x.rule for x in v]))

    # ---- F4: commit metadata / public account identity -----------------
    canon = PUBLIC_PROJECT_IDENTITY
    probs = identity_problems("author", canon, f"{canon}@{NOREPLY_HOST}")
    t("27-canonical-noreply-passes", not probs, str(probs))

    probs = identity_problems("author", canon, f"151931662+{canon}@{NOREPLY_HOST}")
    t("28-canonical-noreply-with-uid-passes", not probs, str(probs))

    other = "not" + "-the" + "-project-account"
    probs = identity_problems("author", canon, f"{other}@{NOREPLY_HOST}")
    t("29-different-noreply-handle-fails", bool(probs), "accepted a foreign handle")
    t("30-foreign-handle-not-printed",
      other not in " ".join(probs), "foreign handle leaked into output")

    probs = identity_problems("committer", "A Real Person", f"{canon}@{NOREPLY_HOST}")
    t("31-non-canonical-display-name-fails", bool(probs), "accepted a foreign name")
    t("32-non-canonical-name-not-printed",
      "A Real Person" not in " ".join(probs), "author name leaked into output")

    probs = identity_problems("author", canon, "dev@example.com")
    t("33-non-noreply-email-fails", bool(probs), "accepted a non-noreply address")

    # ---- current repository state ---------------------------------------
    tree_v = scan_tree(root)
    t("34-current-public-tree-clean", not tree_v,
      "; ".join(x.render() for x in tree_v[:8]))

    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}"
              + (f"  [{detail}]" if detail and not ok else ""))
    print(f"\n{len(results) - len(failed)}/{len(results)} public-release tests passed")
    return 1 if failed else 0


def main() -> int:
    args = sys.argv[1:]
    mode = "tree"
    for a in args:
        if a in ("--history", "--selftest", "--commit-metadata"):
            mode = a[2:]

    if mode == "selftest":
        return selftest(ROOT)

    if mode == "commit-metadata":
        return commit_metadata_gate(ROOT)

    if mode == "history":
        scope = Scope()
        v = scan_history(ROOT, scope)
        print_report("GIT_HISTORY_SCAN", v, scope, "HISTORY_SCAN")
        # MEASUREMENT, not a gate. Historical local-identity / machine-fingerprint
        # findings are a privacy-hygiene issue requiring an owner decision on
        # remediation; they must not auto-fail a scheduled job. A confirmed
        # credential in history is different: it demands rotation, so it fails.
        secrets = [x for x in v if x.severity == "SECRET"]
        ident = [x for x in v if x.severity == "LOCAL_IDENTITY"]
        mach = [x for x in v if x.severity == "MACHINE_FINGERPRINT"]
        print(f"HISTORY_SEVERITY SECRET={len(secrets)} "
              f"LOCAL_IDENTITY={len(ident)} MACHINE_FINGERPRINT={len(mach)}")
        print("CONFIRMED_SECRET_LEAKS="
              + ("NONE_FOUND_WITHIN_SCANNED_REACHABLE_TEXT_OBJECTS"
                 if not secrets else "FOUND_SEE_ABOVE"))
        print("HISTORY_REWRITE_REQUIRED=USER_DECISION_REQUIRED"
              if not secrets and (ident or mach) else
              "HISTORY_REWRITE_REQUIRED=STOP_OWNER_DECISION" if secrets else
              "HISTORY_REWRITE_REQUIRED=NO")
        return 1 if secrets else 0

    scope = Scope()
    v = scan_tree(ROOT, scope)
    print_report("CURRENT_TREE_SCAN", v, scope, "CURRENT_TREE")
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main())
