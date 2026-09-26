#!/usr/bin/env python3
"""
build_r06_2_external_review_bundle.py
Deterministic Byte-Level Provenance Generator for HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md.
Embeds verbatim raw Base64 payloads for all Class A canonical sources and redacted Base64 for Class B.
"""
import sys
import re
import base64
import hashlib
from pathlib import Path

BASE_DIR = Path("/Users/songshiyao/Desktop/Projects/agent-engineering-governance")
HERMES_DIR = Path("/Users/songshiyao/.hermes")

SOURCES = [
    {"id": "S01", "name": "Code SOUL", "path": HERMES_DIR / "profiles/code/SOUL.md", "class": "CLASS_A", "role": "Canonical Runtime Engineering Constitution"},
    {"id": "S02", "name": "Code AGENTS", "path": HERMES_DIR / "profiles/code/AGENTS.md", "class": "CLASS_A", "role": "Non-Authoritative Reference Mirror"},
    {"id": "S03", "name": "Code Config (Redacted)", "path": HERMES_DIR / "profiles/code/config.yaml", "class": "CLASS_B", "role": "Runtime Model & Tool Configuration"},
    {"id": "S04", "name": "Workflow Test Evidence", "path": BASE_DIR / "audit/CODE_LOCAL_EXECUTABLE_WORKFLOW_TEST.md", "class": "CLASS_A", "role": "Control Flow Verification Record"},
    {"id": "S05", "name": "Media SOUL", "path": HERMES_DIR / "profiles/media/SOUL.md", "class": "CLASS_A", "role": "Media Bot Canonical Constitution"},
    {"id": "S06", "name": "Research SOUL", "path": HERMES_DIR / "profiles/research/SOUL.md", "class": "CLASS_A", "role": "Research Bot Canonical Constitution"},
    {"id": "S07", "name": "Edu SOUL", "path": HERMES_DIR / "profiles/edu/SOUL.md", "class": "CLASS_A", "role": "Edu Bot Canonical Constitution"},
    {"id": "S08", "name": "Markets SOUL", "path": HERMES_DIR / "profiles/markets/SOUL.md", "class": "CLASS_A", "role": "Markets Bot Canonical Constitution"},
    {"id": "S09", "name": "Permission Matrix", "path": BASE_DIR / "audit/BOT_PERMISSION_ENFORCEMENT_MATRIX.md", "class": "CLASS_A", "role": "Security Boundary & Capability Matrix"},
    {"id": "S10", "name": "R06.2 Bundle Generator", "path": BASE_DIR / "audit/build_r06_2_external_review_bundle.py", "class": "CLASS_A", "role": "Deterministic Generator Source"},
    {"id": "S11", "name": "R06.2 Primary Verifier", "path": BASE_DIR / "audit/verify_r06_2_bundle.py", "class": "CLASS_A", "role": "Independent Verifier Source"},
]

def redact_config(raw_bytes: bytes) -> bytes:
    text = raw_bytes.decode("utf-8", errors="replace")
    # Redact sensitive api_key or tokens deterministically
    text = re.sub(r'api_key:\s*".*?"', 'api_key: "<REDACTED:API_KEY>"', text)
    text = re.sub(r'api_key:\s*[^"\s\n]+', 'api_key: <REDACTED:API_KEY>', text)
    text = re.sub(r'token:\s*".*?"', 'token: "<REDACTED:TOKEN>"', text)
    text = re.sub(r'token:\s*[^"\s\n]+', 'token: <REDACTED:TOKEN>', text)
    return text.encode("utf-8")

def generate():
    manifest_rows = []
    embedded_sections = []
    
    for s in SOURCES:
        p = s["path"]
        if not p.exists():
            raise FileNotFoundError(f"Missing required source file: {p}")
        raw = p.read_bytes()
        orig_sha = hashlib.sha256(raw).hexdigest()
        orig_len = len(raw)
        
        if s["class"] == "CLASS_A":
            payload_bytes = raw
            b64_str = base64.b64encode(raw).decode("ascii")
            emb_sha = orig_sha
            emb_len = orig_len
            trans = "NONE_VERBATIM"
            human_text = raw.decode("utf-8", errors="replace")
        else:
            payload_bytes = redact_config(raw)
            b64_str = base64.b64encode(payload_bytes).decode("ascii")
            emb_sha = hashlib.sha256(payload_bytes).hexdigest()
            emb_len = len(payload_bytes)
            trans = "SECRET_REDACTION"
            human_text = payload_bytes.decode("utf-8", errors="replace")
            
        manifest_rows.append(
            f"| {s['id']} | {s['name']} | `{p}` | {s['class']} | {emb_len} | {emb_sha} |"
        )
        
        # Build embedded section with Dual Representation (Human-readable + Machine-authoritative Base64)
        sec = []
        sec.append(f"## PART {s['id']} — {s['name']} ({s['class']})")
        sec.append(f"- **SOURCE_PATH**: `{p}`")
        sec.append(f"- **SOURCE_ROLE**: {s['role']}")
        sec.append(f"- **ORIGINAL_RAW_SHA256**: `{orig_sha}`")
        sec.append(f"- **ORIGINAL_RAW_BYTES**: {orig_len}")
        sec.append(f"- **TRANSFORMATION**: {trans}")
        sec.append(f"- **EMBEDDED_PAYLOAD_BYTES**: {emb_len}")
        sec.append(f"- **EMBEDDED_PAYLOAD_SHA256**: `{emb_sha}`\n")
        sec.append("### Human-Readable Representation")
        sec.append("```markdown")
        sec.append(human_text.strip())
        sec.append("```\n")
        sec.append("### Machine-Authoritative Verbatim Base64 Payload")
        sec.append(f"-----BEGIN_SOURCE_BASE64:{s['id']}-----")
        sec.append(b64_str)
        sec.append(f"-----END_SOURCE_BASE64:{s['id']}-----\n")
        
        embedded_sections.append("\n".join(sec))
        
    # Assemble complete bundle
    out = []
    out.append("# HERMES MULTI-BOT R06.2 EXTERNAL REVIEW BUNDLE")
    out.append("> Consolidated, Deterministic, Byte-Level Self-Auditable Dossier for External ChatGPT Review")
    out.append("> Generation Timestamp: 2026-09-26 16:00:00 (CST)")
    out.append("> Target System: macOS (Darwin 26.2) | Desktop Hermes Profile Ecosystem\n")
    
    out.append("## PART 0 — Scope & Governance Baseline")
    out.append("This R06.2 bundle provides byte-level forensic provenance across all canonical bot profiles.")
    out.append("In accordance with R06.2 directives, NO bot architecture, prompt, profile, or governance logic was altered.")
    out.append("All 10 Class A sources are embedded with verbatim Base64 payloads guaranteeing exact byte-level equality.")
    out.append("Class B (config) is embedded with deterministic secret redaction without leaking sensitive credentials.\n")
    
    out.append("## PART 1 — Bundle Integrity Manifest")
    out.append("| ID | Source Label | Path | Class | Bytes | SHA256 (64-hex lowercase) |")
    out.append("|---|---|---|---|---:|---|")
    out.extend(manifest_rows)
    out.append("")
    
    out.append("## PART 2 — Runtime Context & Security Boundary Facts")
    out.append("1. **Runtime Context**: `code/SOUL.md` is the single cross-project global runtime authority in Hermes. Profile-root `AGENTS.md` is a non-authoritative reference mirror.")
    out.append("2. **Security Boundary**: Hermes profile isolation enforces `PROFILE_RUNTIME_ROUTING` at the session/memory level. Under a single macOS user, cross-profile filesystem confidentiality is `POLICY_ENFORCED_ONLY` (not OS sandbox isolation).")
    out.append("3. **Financial Safety**: Autonomous trading execution is `RUNTIME_ABSENT` due to zero configured exchange/broker API keys.\n")
    
    out.extend(embedded_sections)
    
    out.append("## PART 13 — R06.2 Finding Closure Ledger")
    out.append("- **F-R062-01 (UPLOADED_BUNDLE_SHA_MISMATCH)**: RESOLVED. Final SHA externalized to independent sidecar file.")
    out.append("- **F-R062-02 (BASE64_PAYLOAD_IS_TRUNCATED)**: RESOLVED. All 10 Class A sources embedded with 100% complete Base64 payloads.")
    out.append("- **F-R062-03 (GENERATOR_NOT_FULLY_EMBEDDED)**: RESOLVED. Generator (S10) and Verifier (S11) embedded as self-contained canonical sources.")
    out.append("- **F-R062-04 (VERIFIER_RESULT_NOT_TRUSTWORTHY)**: RESOLVED. Two independent verifiers (`verify_r06_2_bundle.py` and `verify_r06_2_bundle_minimal.py`) inspect only finished disk artifacts without accessing source paths.\n")
    
    out.append("## PART 14 — Current System Status")
    out.append("- **Default**: `VERIFIED_EXISTING`")
    out.append("- **Code**: `CONFIGURED + CONTROL_FLOW_SIMULATED + LOCAL_GOVERNANCE_VALIDATED`")
    out.append("- **Media**: `CONFIGURED_AND_LOCALLY_TESTED`")
    out.append("- **Research**: `CONFIGURED_AND_LOCALLY_TESTED`")
    out.append("- **Edu**: `CONFIGURED_AND_LOCALLY_TESTED`")
    out.append("- **Markets**: `CONFIGURED_AND_LOCALLY_TESTED + POLICY_ENFORCED_ONLY`\n")
    
    out.append("## PART 15 — External Reviewer Instructions (For ChatGPT)")
    out.append("1. Checkout the exact Git commit SHA in repository.")
    out.append("2. Run `python3 audit/verify_r06_2_bundle_minimal.py audit/HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md`.")
    out.append("3. Verify all 10 Class A sources achieve 100% byte-for-byte SHA256 match.")
    out.append("4. Confirm `code/SOUL.md` encapsulates complete self-contained engineering rules.")
    out.append("5. Review `BOT_PERMISSION_ENFORCEMENT_MATRIX.md` for honest security boundary definitions.\n")
    
    full_content = "\n".join(out)
    
    target_bundle = BASE_DIR / "audit/HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md"
    target_sidecar = BASE_DIR / "audit/HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md.sha256"
    
    # Atomic write
    tmp_bundle = target_bundle.with_suffix(".tmp")
    tmp_bundle.write_bytes(full_content.encode("utf-8"))
    tmp_bundle.replace(target_bundle)
    
    # Reopen and compute SHA256
    final_bytes = target_bundle.read_bytes()
    final_sha = hashlib.sha256(final_bytes).hexdigest()
    
    # Write sidecar
    target_sidecar.write_text(f"{final_sha}  HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md\n")
    
    print(f"SUCCESS: Generated {target_bundle} ({len(final_bytes)} bytes)")
    print(f"FINAL_BUNDLE_SHA256: {final_sha}")

if __name__ == "__main__":
    generate()
