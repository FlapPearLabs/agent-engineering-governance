#!/usr/bin/env python3
"""
verify_r06_2_bundle.py
Primary Independent Verifier for HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md.
"""
import sys
import re
import base64
import hashlib
from pathlib import Path

DO_NOT_OPEN_SOURCE_PATHS = True

def verify_primary(bundle_path_str: str) -> bool:
    bundle_path = Path(bundle_path_str)
    if not bundle_path.exists():
        print(f"FAIL: Bundle not found: {bundle_path}")
        return False
        
    bundle_bytes = bundle_path.read_bytes()
    bundle_sha = hashlib.sha256(bundle_bytes).hexdigest()
    print(f"=== PRIMARY VERIFIER R06.2 ===")
    print(f"TARGET_BUNDLE: {bundle_path}")
    print(f"BUNDLE_BYTE_SIZE: {len(bundle_bytes)}")
    print(f"BUNDLE_SHA256: {bundle_sha}")
    
    # 1. Verify sidecar
    sidecar_path = Path(str(bundle_path) + ".sha256")
    if not sidecar_path.exists():
        print("FAIL: Sidecar file does not exist")
        return False
    sc_text = sidecar_path.read_text().strip()
    sc_sha = sc_text.split()[0]
    if sc_sha.lower() != bundle_sha.lower():
        print(f"FAIL: Sidecar SHA ({sc_sha}) != Bundle SHA ({bundle_sha})")
        return False
    print("SIDECAR_CHECK: PASS")
    
    content = bundle_bytes.decode("utf-8", errors="replace")
    
    # 2. Parse Manifest
    manifest_rows = re.findall(r"\|\s*(S\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(CLASS_[AB])\s*\|\s*(\d+)\s*\|\s*([a-f0-9]{64})\s*\|", content)
    if not manifest_rows:
        print("FAIL: No valid manifest rows found")
        return False
    
    manifest_map = {}
    for sid, name, path, sclass, bcount, sha in manifest_rows:
        manifest_map[sid] = {
            "name": name.strip(),
            "class": sclass.strip(),
            "bytes": int(bcount.strip()),
            "sha": sha.strip().lower()
        }
    print(f"MANIFEST_ENTRIES: {len(manifest_map)}")
    
    # 3. Extract and verify Base64
    payload_pattern = re.compile(r"-----BEGIN_SOURCE_BASE64:(S\d+)-----\s*([A-Za-z0-9+/=\s]+?)\s*-----END_SOURCE_BASE64:\1-----")
    matches = payload_pattern.findall(content)
    
    pass_a = 0
    pass_b = 0
    fails = 0
    seen = set()
    
    for sid, b64_raw in matches:
        seen.add(sid)
        if sid not in manifest_map:
            print(f"FAIL: Payload {sid} not in manifest")
            fails += 1
            continue
        meta = manifest_map[sid]
        clean_b64 = re.sub(r"\s+", "", b64_raw)
        try:
            decoded = base64.b64decode(clean_b64, validate=True)
        except Exception as e:
            print(f"FAIL: Base64 decode error {sid}: {e}")
            fails += 1
            continue
            
        dec_len = len(decoded)
        dec_sha = hashlib.sha256(decoded).hexdigest().lower()
        
        if dec_len != meta["bytes"]:
            print(f"FAIL {sid}: Byte count mismatch (decoded {dec_len} != manifest {meta['bytes']})")
            fails += 1
            continue
        if dec_sha != meta["sha"]:
            print(f"FAIL {sid}: Hash mismatch (decoded {dec_sha} != manifest {meta['sha']})")
            fails += 1
            continue
            
        if meta["class"] == "CLASS_A":
            pass_a += 1
            print(f"VERIFY {sid} [{meta['name']}]: CLASS_A {dec_len} bytes, SHA {dec_sha[:16]}... PASS")
        else:
            pass_b += 1
            print(f"VERIFY {sid} [{meta['name']}]: CLASS_B REDACTED {dec_len} bytes, SHA {dec_sha[:16]}... PASS")
            
    for sid in manifest_map:
        if sid not in seen:
            print(f"FAIL: Manifest entry {sid} missing from bundle")
            fails += 1
            
    print(f"PRIMARY_SUMMARY: CLASS_A={pass_a}/10 CLASS_B={pass_b}/1 FAILS={fails}")
    return fails == 0

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "audit/HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md"
    ok = verify_primary(target)
    sys.exit(0 if ok else 1)

