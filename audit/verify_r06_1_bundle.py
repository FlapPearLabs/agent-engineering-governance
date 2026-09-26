#!/usr/bin/env python3
"""
verify_r06_1_bundle.py
Independent Verifier for HERMES_MULTI_BOT_R06_1_EXTERNAL_REVIEW_BUNDLE.md.
"""
import sys
import re
import hashlib
import base64
from pathlib import Path

def verify_bundle(bundle_path_str: str) -> bool:
    bundle_path = Path(bundle_path_str).resolve()
    if not bundle_path.exists():
        print(f"[FAIL] Bundle not found: {bundle_path}")
        return False

    raw_bytes = bundle_path.read_bytes()
    computed_bundle_sha = hashlib.sha256(raw_bytes).hexdigest()
    print(f"[INFO] Bundle Size: {len(raw_bytes)} bytes")
    print(f"[INFO] Computed Bundle SHA256: {computed_bundle_sha}")

    sidecar_path = bundle_path.with_suffix(".md.sha256")
    if sidecar_path.exists():
        sidecar_content = sidecar_path.read_text().strip().split()
        if sidecar_content:
            sidecar_sha = sidecar_content[0].lower()
            if sidecar_sha != computed_bundle_sha:
                print(f"[FAIL] Sidecar SHA mismatch: sidecar={sidecar_sha} vs computed={computed_bundle_sha}")
                return False
            print(f"[PASS] Sidecar SHA match: {sidecar_sha}")
        else:
            print(f"[FAIL] Sidecar empty: {sidecar_path}")
            return False
    else:
        print(f"[WARN] Sidecar file not found: {sidecar_path}")

    text = raw_bytes.decode('utf-8', errors='replace')

    manifest_matches = re.findall(r'\|\s*(S\d+)\s*\|\s*([^|]+)\|\s*(CLASS_[AB])\s*\|\s*(\d+)\s*\|\s*`([0-9a-fA-F]{64})`\s*\|\s*([^|]+)\|\s*`([0-9a-fA-F]{64})`\s*\|\s*([^|]+)\|', text)
    if not manifest_matches:
        print("[FAIL] Could not parse Manifest table in Bundle!")
        return False

    manifest_data = {}
    for sid, label, sclass, size, raw_sha, trans, emb_sha, sec in manifest_matches:
        manifest_data[sid] = {
            "label": label.strip(),
            "class": sclass.strip(),
            "size": int(size.strip()),
            "raw_sha256": raw_sha.strip().lower(),
            "trans": trans.strip(),
            "emb_sha256": emb_sha.strip().lower()
        }
    print(f"[INFO] Parsed {len(manifest_data)} sources from Manifest.")

    b64_blocks = re.findall(r'-----BEGIN_SOURCE_BASE64:(S\d+)-----\s*([A-Za-z0-9+/=\s]+)\s*-----END_SOURCE_BASE64:\1-----', text)
    extracted_b64 = {}
    for sid, b64_payload in b64_blocks:
        clean_b64 = re.sub(r'\s+', '', b64_payload)
        extracted_b64[sid] = base64.b64decode(clean_b64)

    class_a_count = 0
    class_a_pass = 0
    for sid, m in manifest_data.items():
        if m["class"] == "CLASS_A":
            class_a_count += 1
            if sid not in extracted_b64:
                print(f"[FAIL] Missing Base64 block for Class A source: {sid} ({m['label']})")
                return False
            decoded_bytes = extracted_b64[sid]
            decoded_sha = hashlib.sha256(decoded_bytes).hexdigest()
            decoded_size = len(decoded_bytes)

            if decoded_size != m["size"]:
                print(f"[FAIL] Size mismatch on {sid}: manifest={m['size']} vs decoded={decoded_size}")
                return False
            if decoded_sha != m["raw_sha256"]:
                print(f"[FAIL] SHA mismatch on {sid}: manifest={m['raw_sha256']} vs decoded={decoded_sha}")
                return False
            print(f"[PASS] {sid} {m['label']}: {decoded_size} bytes, SHA256 verified match ({decoded_sha})")
            class_a_pass += 1
        elif m["class"] == "CLASS_B":
            print(f"[INFO] {sid} {m['label']}: CLASS_B Redacted, embedded_sha={m['emb_sha256']}")

    print(f"\n[SUMMARY] Class A Verbatim Hash Match: {class_a_pass}/{class_a_count} PASS")
    return class_a_pass == class_a_count and class_a_count > 0

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "/Users/songshiyao/Desktop/Projects/agent-engineering-governance/audit/HERMES_MULTI_BOT_R06_1_EXTERNAL_REVIEW_BUNDLE.md"
    success = verify_bundle(target)
    sys.exit(0 if success else 1)

