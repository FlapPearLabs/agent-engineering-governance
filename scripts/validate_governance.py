#!/usr/bin/env python3
"""Governance self-validation harness (minimal).

Verifies mechanical properties of the governance repository only:
  1. required canonical files exist
  2. markdown relative links resolve
  3. JSON files parse
  4. no secrets / machine-private paths in governance artifacts
  5. MEMORY pointer candidate within injection budget (<=3500 chars)
  6. no unrelated-platform shell requirements in RULES/AGENTS
  7. every reference declares its canonical owner
  8. skills manifest carries required fields
  9. no contradictory authority markers (V1 inversion phrases)

NOT a workflow engine. Exit 0 = all checks PASS; exit 1 = any FAIL.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "README.md", "AGENTS.md", "RULES.md",
    "references/execution-stage.md", "references/ticket-lane.md",
    "references/review-and-repair-saturation.md",
    "references/git-ci-integration.md",
    "references/codegraph-grounding.md",
    "references/skills-and-model-routing.md",
    "deployment/BOOTSTRAP_CONTRACT.md",
    "deployment/MEMORY_POINTER_CANDIDATE.md",
    "deployment/deployment-profile.md",
    "skills/README.md", "mcp/README.md", "mcp/example/mcp.example.json",
    "scripts/validate_governance.py",
    ".github/workflows/governance-ci.yml",
]

# Tier 1 (RULES R2 layer-1): credentials/secrets AND local OS/personal identity
# (e.g. host login username) — banned in EVERY file, designated files included.
# Note: repository/account identifiers (git author name, account handle,
# noreply email) are legitimate and NOT scanned here (R2 terminology, B2 fix).
CREDENTIAL_PATTERNS = [
    r"ghp_[A-Za-z0-9]{20,}",   # GitHub PAT
    r"github_pat_",
    r"sk-[A-Za-z0-9]{20,}",    # generic API key
    r"-----BEGIN [A-Z ]*PRIVATE KEY",
    r"(?i)cookie\s*=",
    r"(?i)password\s*=",
    r"songshiyao",             # local OS login identity of the current host
]
# Tier 2 (RULES R2 layer-2): host-specific facts — banned in general governance
# artifacts; allowed ONLY in designated deployment files carrying the marker
# "MACHINE-SPECIFIC ALLOWED" (private repo, purpose = machine recovery).
MACHINE_PATTERNS = [
    r"/Users/",
    r"127\.0\.0\.1:7897",
]
DESIGNATED_MARKER = "MACHINE-SPECIFIC ALLOWED"
DESIGNATED_DIR = "deployment"

PLATFORM_MARKERS = [
    r"(基线|baseline)\s*[=＝:：]\s*(macOS|PowerShell|Windows|pwsh|zsh)",
    r"必须使用\s*(PowerShell|pwsh|\.ps1|\.bat\b)",
    r"强制\s*(PowerShell|pwsh)",
    r"全局基线\s*[=＝]?\s*macOS",
]

INVERSION_MARKERS = [
    "不得弱化本文件",
    "项目级权威在其更严格处生效，但不得弱化",
    "全局硬规则（CANDIDATE V1）",
]

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def md_link_targets(text: str) -> list[str]:
    out = []
    for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
        target = m.group(1).strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        out.append(target.split("#")[0])
    return out


def main() -> int:
    # 1. required files
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    check("required-files-exist", not missing, f"missing={missing}")

    # 2. markdown relative links resolve
    bad_links: list[str] = []
    for md in ROOT.rglob("*.md"):
        if ".git" in md.parts:
            continue
        for target in md_link_targets(md.read_text(encoding="utf-8")):
            resolved = (md.parent / target).resolve()
            if not resolved.exists():
                bad_links.append(f"{md.relative_to(ROOT)} -> {target}")
    check("markdown-links-resolve", not bad_links, f"broken={bad_links[:5]}")

    # 3. JSON parses
    json_bad: list[str] = []
    for jf in ROOT.rglob("*.json"):
        if ".git" in jf.parts:
            continue
        try:
            json.loads(jf.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            json_bad.append(f"{jf.relative_to(ROOT)}: {exc}")
    check("json-parses", not json_bad, f"bad={json_bad}")

    # 4. secrets / machine-private paths (two-tier, RULES R2)
    #    The scanner itself is exempt: it embeds its own detection regexes.
    def is_designated(f: Path) -> bool:
        try:
            head = "\n".join(f.read_text(encoding="utf-8", errors="ignore").splitlines()[:10])
        except Exception:  # noqa: BLE001
            return False
        return DESIGNATED_MARKER in head and str(f.relative_to(ROOT)).startswith(DESIGNATED_DIR)

    cred_leaks: list[str] = []
    mach_leaks: list[str] = []
    scan_files = [p for p in ROOT.rglob("*")
                  if p.is_file() and p.suffix in {".md", ".json", ".py", ".sh", ".txt", ".yml", ".yaml"}
                  and ".git" not in p.parts
                  and p.name != "validate_governance.py"]
    for f in scan_files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        for pat in CREDENTIAL_PATTERNS:
            if re.search(pat, text):
                cred_leaks.append(f"{f.relative_to(ROOT)} matches {pat}")
        if not is_designated(f):
            for pat in MACHINE_PATTERNS:
                if re.search(pat, text):
                    mach_leaks.append(f"{f.relative_to(ROOT)} matches {pat}")
    check("no-credentials-anywhere", not cred_leaks, f"leaks={cred_leaks[:5]}")
    check("machine-facts-only-in-designated-files", not mach_leaks, f"leaks={mach_leaks[:5]}")

    # 5. MEMORY pointer budget
    pointer = ROOT / "deployment/MEMORY_POINTER_CANDIDATE.md"
    if pointer.is_file():
        text = pointer.read_text(encoding="utf-8")
        blocks = re.findall(r"```(?:markdown)?\n(.*?)```", text, re.S)
        body = max(blocks, key=len) if blocks else text
        n = len(body)
        check("memory-pointer-within-budget", n <= 3500, f"chars={n} (budget 3500)")
    else:
        check("memory-pointer-within-budget", False, "pointer file missing")

    # 6. platform injection hygiene in RULES/AGENTS (reference mentions allowed elsewhere)
    plat_hits: list[str] = []
    for name in ("RULES.md", "AGENTS.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for pat in PLATFORM_MARKERS:
            if re.search(pat, text):
                plat_hits.append(f"{name}: {pat}")
    check("no-unrelated-platform-requirements", not plat_hits, f"hits={plat_hits}")

    # 7. references declare canonical owner
    owner_missing: list[str] = []
    for ref in sorted((ROOT / "references").glob("*.md")):
        if "Canonical owner" not in ref.read_text(encoding="utf-8"):
            owner_missing.append(ref.name)
    check("references-declare-canonical-owner", not owner_missing, f"missing={owner_missing}")

    # 8. skills manifest required fields
    sk = ROOT / "skills/README.md"
    if sk.is_file():
        text = sk.read_text(encoding="utf-8")
        ok = all(k in text for k in ("SOURCE", "VERSION", "LICENSE", "REPRODUCIBILITY"))
        check("skills-manifest-fields-present", ok, "need SOURCE/VERSION/LICENSE/REPRODUCIBILITY")
    else:
        check("skills-manifest-fields-present", False, "skills/README.md missing")

    # 9. contradictory authority markers
    inv_hits: list[str] = []
    for name in ("AGENTS.md", "RULES.md", "README.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for marker in INVERSION_MARKERS:
            if marker in text:
                inv_hits.append(f"{name}: {marker!r}")
    check("no-authority-inversion-markers", not inv_hits, f"hits={inv_hits}")

    # report
    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
