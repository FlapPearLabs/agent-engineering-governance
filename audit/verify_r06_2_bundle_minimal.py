#!/usr/bin/env python3
"""
verify_r06_2_bundle_minimal.py
Independent Minimal Verifier (<150 lines, standard library only).
Strictly parses only the final bundle and its sidecar; NEVER opens source files.
"""
import sys
import re
import base64
import hashlib
from pathlib import Path

def verify_bundle(bundle_path_str: str) -> bool:
    bundle_path = Path(bundle_path_str)
    if not bundle_path.exists():
        print(f"FAIL: Bundle not found: {bundle_path}")
        return False
    
    bundle_bytes = bundle_path.read_bytes()
    bundle_sha = hashlib.sha256(bundle_bytes).hexdigest()
    print(f"BUNDLE_PATH: {bundle_path}")
    print(f"BUNDLE_BYTES: {len(bundle_bytes)}")
    print(f"BUNDLE_SHA256: {bundle_sha}")
    
    # 1. Sidecar verification
    sidecar_path = Path(str(bundle_path) + ".sha256")
    if sidecar_path.exists():
        sc_text = sidecar_path.read_text().strip()
        sc_sha = sc_text.split()[0]
        if sc_sha.lower() != bundle_sha.lower():
            print(f"FAIL: Sidecar SHA ({sc_sha}) != Bundle SHA ({bundle_sha})")
            return False
        print("SIDECAR_CHECK: PASS")
    else:
        print("SIDECAR_CHECK: WARNING (sidecar missing)")

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
    print(f"MANIFEST_ENTRIES_PARSED: {len(manifest_map)}")
    
    # 3. Extract and verify each Base64 payload
    payload_pattern = re.compile(r"-----BEGIN_SOURCE_BASE64:(S\d+)-----\s*([A-Za-z0-9+/=\s]+?)\s*-----END_SOURCE_BASE64:\1-----")
    matches = payload_pattern.findall(content)
    if not matches:
        print("FAIL: No Base64 payloads extracted")
        return False
    
    found_sids = set()
    pass_count_a = 0
    pass_count_b = 0
    fail_count = 0
    
    for sid, b64_raw in matches:
        found_sids.add(sid)
        if sid not in manifest_map:
            print(f"FAIL: Payload {sid} not in manifest")
            fail_count += 1
            continue
        
        meta = manifest_map[sid]
        clean_b64 = re.sub(r"\s+", "", b64_raw)
        try:
            decoded = base64.b64decode(clean_b64, validate=True)
        except Exception as e:
            print(f"FAIL: Base64 decode error for {sid}: {e}")
            fail_count += 1
            continue
        
        dec_len = len(decoded)
        dec_sha = hashlib.sha256(decoded).hexdigest().lower()
        
        if dec_len != meta["bytes"]:
            print(f"FAIL {sid}: Byte count mismatch (decoded {dec_len} != manifest {meta['bytes']})")
            fail_count += 1
            continue
            
        if dec_sha != meta["sha"]:
            print(f"FAIL {sid}: Hash mismatch (decoded {dec_sha} != manifest {meta['sha']})")
            fail_count += 1
            continue
            
        if meta["class"] == "CLASS_A":
            pass_count_a += 1
            print(f"VERIFY {sid} ({meta['name']}): CLASS_A BYTES={dec_len} SHA={dec_sha[:16]}... PASS")
        else:
            pass_count_b += 1
            print(f"VERIFY {sid} ({meta['name']}): CLASS_B REDACTED BYTES={dec_len} SHA={dec_sha[:16]}... PASS")
            
    # Check completeness
    for sid in manifest_map:
        if sid not in found_sids:
            print(f"FAIL: Manifest entry {sid} has no corresponding payload in bundle")
            fail_count += 1

    print(f"TOTAL_SUMMARY: CLASS_A_PASS={pass_count_a} CLASS_B_PASS={pass_count_b} FAILS={fail_count}")
    return fail_count == 0

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "audit/HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md"
    ok = verify_bundle(target)
    sys.exit(0 if ok else 1)
