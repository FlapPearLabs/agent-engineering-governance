#!/usr/bin/env python3
"""Governance self-validation harness (minimal).

Verifies mechanical properties of the governance repository only. Check
families (the live count is whatever this file enforces — run it and require
all checks PASS; never hard-code an expected number in documentation):

  - required canonical files exist (incl. V1.1.1 references/setup docs)
  - markdown internal links resolve; JSON examples parse
  - two-tier secret scan (R2): credentials/local identity banned everywhere,
    machine-specific facts only in designated deployment files
  - MEMORY pointer candidate within injection budget
  - no unrelated-platform shell requirements in RULES/AGENTS
  - references declare canonical owners; skills guide carries V1 fields
  - canonical MCP set unchanged; agent-mail not canonical; connectors != MCP
  - AGENTS carries doctrine + CodeGraph Mode A/B/C semantics
  - no stale operational state (candidate headers / old check counts)
  - no vendored third-party skill source; skills statuses valid
  - no raw MEMORY archive under deployment/
  - PORTABLE_SETUP capability matrix present

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
    "references/static-analysis-and-code-intelligence.md",
    "references/engineering-memory.md",
    "references/project-state-persistence.md",
    "references/project-continuity-contract.md",
    "schemas/project-state.schema.json",
    "templates/project-state.json",
    "scripts/validate_project_state.py",
    "adapters/zcode/README.md",
    "adapters/zcode/hooks/governance_sync.py",
    "adapters/zcode/hooks/project_state_guard.py",
    "adapters/zcode/hooks/codegraph_state.py",
    "adapters/zcode/hooks/state_flush_guard.py",
    "adapters/zcode/hooks/grounding_guard.py",
    "adapters/zcode/hooks/codegraph_lifecycle.py",
    "adapters/zcode/hooks/_continuity_state.py",
    "adapters/zcode/tests/test_project_continuity.py",
    "deployment/BOOTSTRAP_CONTRACT.md",
    "deployment/MEMORY_POINTER_CANDIDATE.md",
    "deployment/deployment-profile.md",
    "deployment/PORTABLE_SETUP.md",
    "skills/README.md", "mcp/README.md", "mcp/example/mcp.example.json",
    "scripts/validate_governance.py",
    ".github/workflows/governance-ci.yml",
]

CANONICAL_MCP = ["codegraph", "context7", "gh_grep"]

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
    r"(?i)[a-z]:\\users\\",    # Windows-form host path (R2 layer 2, scanner-gap fix R1-A)
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

    # 8. skills guide: exists, no vendored third-party skill source (D2)
    vendored = [p.name for p in (ROOT / "skills").glob("**/SKILL.md")]
    check("no-vendored-skill-source", not vendored, f"vendored={vendored}")

    # 9. contradictory authority markers
    inv_hits: list[str] = []
    for name in ("AGENTS.md", "RULES.md", "README.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for marker in INVERSION_MARKERS:
            if marker in text:
                inv_hits.append(f"{name}: {marker!r}")
    check("no-authority-inversion-markers", not inv_hits, f"hits={inv_hits}")

    # 10. V1 portability: skills guide fields without vendoring/blocker
    sk = ROOT / "skills/README.md"
    sk_text = sk.read_text(encoding="utf-8") if sk.is_file() else ""
    sk_ok = all(k in sk_text for k in ("NAME", "PURPOSE", "SOURCE", "PRIMARY_TRIGGER", "IMPORTANT_BOUNDARY", "FALLBACK"))
    sk_blocked = ("REPRODUCIBILITY=INCOMPLETE" in sk_text) or ("deployment blocked" in sk_text) or ("DEPLOYMENT受阻" in sk_text) or ("deployment 受阻" in sk_text)
    check("skills-guide-v1-fields", sk_ok and not sk_blocked,
          f"fields_ok={sk_ok} stale_blocker={sk_blocked}")

    # 11. V1 portability: canonical MCP set exactly; agent-mail not canonical; connectors not MCP
    mcp_text = (ROOT / "mcp/README.md").read_text(encoding="utf-8")
    required_section = mcp_text.split("# PLATFORM CONNECTORS")[0]
    mcp_ok = all(name in required_section for name in CANONICAL_MCP) \
        and "OPTIONAL_PLATFORM_CONNECTOR" in mcp_text \
        and "不是 MCP" in mcp_text and "元数据字段" in mcp_text
    agentmail_canonical = "agent-mail" in required_section
    check("mcp-canonical-set-v1", mcp_ok and not agentmail_canonical,
          f"ok={mcp_ok} agentmail_in_required_section={agentmail_canonical}")

    # 12. V1 portability: AGENTS CodeGraph summary carries Mode A/B/C semantics
    ag_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    doctrine_ok = "ENGINEERING DOCTRINE" in ag_text and "AUTO-ADVANCE UNTIL REAL AUTHORITY UNCERTAINTY" in ag_text
    modes_ok = "MODE A — BASE + DIFF" in ag_text and "MODE B — LANE CANDIDATE-EXACT" in ag_text \
        and "MODE C — UNAVAILABLE" in ag_text and "CANDIDATE_GRAPH_COVERAGE" in ag_text
    check("agents-doctrine-and-codegraph-modes", doctrine_ok and modes_ok,
          f"doctrine={doctrine_ok} modes={modes_ok}")

    # 13. V1 portability: no stale operational state in README/skills/routing reference
    stale_state: list[str] = []
    for name in ("README.md", "skills/README.md", "references/skills-and-model-routing.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for phrase in ("等待外部", "送外部评审", "fresh governance review", "REPRODUCIBILITY=INCOMPLETE", "deployment 受阻"):
            if phrase in text:
                stale_state.append(f"{name}: {phrase!r}")
    readme_ok = "GOVERNANCE_CORE = PASS" in (ROOT / "README.md").read_text(encoding="utf-8")
    check("no-stale-operational-state", not stale_state and readme_ok,
          f"stale={stale_state} readme_core_pass={readme_ok}")

    # 14. V1 portability: PORTABLE_SETUP receipt schema present
    ps = ROOT / "deployment/PORTABLE_SETUP.md"
    ps_ok = ps.is_file() and all(k in ps.read_text(encoding="utf-8")
                                 for k in ("READY_FOR_ENGINEERING", "MISSING_SKILLS", "MISSING_MCP", "OVERRIDES"))
    check("portable-setup-receipt-schema", ps_ok, "PORTABLE_SETUP.md or receipt fields missing")

    # 15. V1.1: static-analysis reference + evidence routing doctrine
    sa_ok = (ROOT / "references/static-analysis-and-code-intelligence.md").is_file()
    ag = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    routing_ok = "ENGINEERING EVIDENCE ROUTING" in ag \
        and "DO_NOT_SPEND_REASONING_ON_MACHINE_PROVABLE_FACTS" in ag \
        and "DO_NOT_REPLACE_SEMANTIC_REASONING_WITH_STATIC_TOOL_OUTPUT" in ag
    check("static-analysis-and-routing-present", sa_ok and routing_ok,
          f"ref={sa_ok} routing={routing_ok}")

    # 16. V1.1: skills statuses valid (9 REQUIRED-at-trigger + 4 OPTIONAL; fallback principle present)
    skt = sk_text if sk_text else (ROOT / "skills/README.md").read_text(encoding="utf-8")
    n_req = skt.count("| CANONICAL | REQUIRED |")
    n_opt = skt.count("| CANONICAL | OPTIONAL |")
    missing_ok = "SKILL_MISSING != USER_MUST_COPY_FILES_MANUALLY" in skt
    check("skills-statuses-valid", n_req == 9 and n_opt == 4 and missing_ok,
          f"required={n_req} optional={n_opt} missing_principle={missing_ok}")

    # 17. V1.1: no raw MEMORY archive committed under deployment/
    raw_hits: list[str] = []
    dep = ROOT / "deployment"
    for f in dep.rglob("*"):
        if f.is_file():
            if f.stat().st_size > 8 * 1024:
                raw_hits.append(f"{f.relative_to(ROOT)} too large for a snapshot")
            elif f.suffix in {".md", ".txt"} and "TICKET LANE V2" in f.read_text(encoding="utf-8", errors="ignore"):
                raw_hits.append(f"{f.relative_to(ROOT)} looks like raw MEMORY body")
    check("no-raw-memory-archive", not raw_hits, f"hits={raw_hits}")

    # 18. V1.1: PORTABLE_SETUP capability matrix covers LSP/AST/static tooling
    ps_text = ps.read_text(encoding="utf-8") if ps.is_file() else ""
    cap_ok = all(k in ps_text for k in ("LSP", "AST", "formatter", "linter", "type checker", "test runner", "CAPABILITIES"))
    check("portable-setup-capability-matrix", cap_ok, "capability matrix fields missing")

    # 19. V1.1.1: no stale candidate/unactivated state in canonical runtime docs
    STALE_RUNTIME = [
        "CANDIDATE — 未激活",
        "状态：CANDIDATE",
        "等待外部治理评审",
        "pending external review",
        "CANDIDATE V2",
    ]
    stale_hits: list[str] = []
    runtime_files = [ROOT / n for n in ("README.md", "AGENTS.md", "RULES.md", "skills/README.md")]
    runtime_files += [p for p in (ROOT / "deployment").rglob("*.md")]
    runtime_files += [p for p in (ROOT / "references").rglob("*.md")]
    for f in runtime_files:
        text = f.read_text(encoding="utf-8")
        for phrase in STALE_RUNTIME:
            if phrase in text:
                stale_hits.append(f"{f.relative_to(ROOT)}: {phrase!r}")
    check("no-candidate-state-in-runtime-docs", not stale_hits, f"hits={stale_hits}")

    # 20. V1.1.1: no stale check-count claims in canonical docs (counts are execution evidence, not doctrine)
    count_hits: list[str] = []
    for f in runtime_files + [ROOT / "references" / "engineering-memory.md"]:
        text = f.read_text(encoding="utf-8")
        for phrase in ("10/10", "9/9", "10 项机械检查"):
            if phrase in text:
                count_hits.append(f"{f.relative_to(ROOT)}: {phrase!r}")
    version_ok = all("AGENT_ENGINEERING_GOVERNANCE_V1.1.1" in (ROOT / n).read_text(encoding="utf-8")
                     for n in ("README.md", "AGENTS.md", "RULES.md"))
    check("runtime-version-and-counts-sync", not count_hits and version_ok,
          f"counts={count_hits} version_sync={version_ok}")

    # 21. V1.1.2: project-state persistence wired into AGENTS + PORTABLE_SETUP
    ref = ROOT / "references/project-state-persistence.md"
    ref_text = ref.read_text(encoding="utf-8") if ref.is_file() else ""
    ps_text = ps_text if ps_text else (ps.read_text(encoding="utf-8") if ps.is_file() else "")
    ag2 = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    ps_integrated = all(k in ps_text for k in ("STATE_RESTORE", "REMOTE_DEFAULT_SHA", "CURRENT_LEGAL_FRONTIER", "READY_TO_CONTINUE"))
    ag_ok = all(k in ag2 for k in ("STATE_RESTORE", "STATE_FLUSH", "PROJECT_STATE_MUST_OUTLIVE_THE_AGENT", "project-state-persistence.md"))
    ref_ok = all(k in ref_text for k in ("PERSISTENCE_VALUE", "REMOTE_UNKNOWN != REMOTE_SYNCED", "STATE_FLUSH", "EPHEMERAL SCRATCH"))
    check("project-state-persistence-integrated", ref.is_file() and ps_integrated and ag_ok and ref_ok,
          f"ref={ref.is_file()} portable={ps_integrated} agents={ag_ok} ref_fields={ref_ok}")

    # 22. V1.1.2: memory stays non-authoritative; anti-bureaucracy present
    em = ROOT / "references/engineering-memory.md"
    em_text = em.read_text(encoding="utf-8") if em.is_file() else ""
    mem_ok = "MEMORY_IS_DISCOVERY_NOT_AUTHORITY" in em_text and "跨项目工程经验 → 本治理仓" in em_text
    anti_ok = "PERSISTENCE_VALUE" in ref_text and "不造官僚模板" in ref_text
    check("memory-non-authoritative-and-anti-bureaucracy", mem_ok and anti_ok,
          f"memory={mem_ok} anti_bureaucracy={anti_ok}")

    # 23. PROJECT_CONTINUITY_CONTRACT_V1: contract text is canonical and complete
    pcc = ROOT / "references/project-continuity-contract.md"
    pcc_text = pcc.read_text(encoding="utf-8") if pcc.is_file() else ""
    pcc_ok = all(k in pcc_text for k in (
        "PROJECT_CONTINUITY_CONTRACT_V1", ".agent/project-state.json",
        "ONE_FACT_ONE_CANONICAL_OWNER", "CODEGRAPH_INIT_ONCE_SYNC_CONTINUOUSLY",
        "GROUND_BEFORE_MEDIUM_HIGH_WRITE", "PROJECT_STATE_SYNC_RECEIPT",
        "REMOTE_STATE_SYNC = DEFERRED", "GROUNDING_RECEIPT", "DURABLE_STATE_SYNC_REQUIRED",
        "lazy adoption", "PROJECT_CONTINUITY_INITIALIZATION_REQUIRED",
    ))
    check("project-continuity-contract-present", pcc_ok, f"ok={pcc_ok}")

    # 24. project-state schema/template/validator trio is coherent
    schema = ROOT / "schemas/project-state.schema.json"
    template = ROOT / "templates/project-state.json"
    vps = ROOT / "scripts/validate_project_state.py"
    trio_ok = schema.is_file() and vps.is_file() and template.is_file()
    if trio_ok:
        tpl_text = template.read_text(encoding="utf-8")
        sch_text = schema.read_text(encoding="utf-8")
        vps_text = vps.read_text(encoding="utf-8")
        trio_ok = (
            tpl_text.count("${") >= 5                      # placeholder form (R2), no real values
            and '"contract_version"' in tpl_text
            and "project-state.schema.json" in sch_text
            and ".agent" in vps_text and "project-state.json" in vps_text
            and "secret" in vps_text.lower()
        )
    check("project-state-trio-coherent", trio_ok, f"ok={trio_ok}")

    # 25. ZCode adapter reference: hooks + runtime-state layout + tests present
    ad = ROOT / "adapters/zcode/README.md"
    ad_text = ad.read_text(encoding="utf-8") if ad.is_file() else ""
    ad_ok = all(k in ad_text for k in (
        "project_state_guard.py", "codegraph_state.py", "state_flush_guard.py",
        "grounding_guard.py", "runtime-state", "contract_version",
    ))
    check("zcode-adapter-reference-present", ad_ok, f"ok={ad_ok}")

    # 26. AGENTS carries the continuity contract pointer
    ag3 = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    ag3_ok = "project-continuity-contract.md" in ag3 \
        and ".agent/project-state.json" in ag3 \
        and "PROJECT_CONTINUITY_INITIALIZATION_REQUIRED" in ag3
    check("agents-continuity-wiring", ag3_ok, f"ok={ag3_ok}")

    # 27. CI runs the synthetic continuity matrix
    ci_text = (ROOT / ".github/workflows/governance-ci.yml").read_text(encoding="utf-8")
    ci_ok = "unittest discover -s adapters/zcode/tests" in ci_text
    check("ci-runs-continuity-matrix", ci_ok, f"ok={ci_ok}")

    # report
    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
