#!/usr/bin/env python3
import pathlib
import hashlib
import base64
import re
import sys

print("test_fixture.py initialized")

def run_test():
    d = pathlib.Path(__file__).parent
    c_bin = d / "c.bin"
    if not c_bin.exists():
        c_bin.write_bytes(bytearray(range(256)) * 4)
    
    files = ["a.txt", "b.md", "c.bin"]
    results = []
    for f in files:
        p = d / f
        raw = p.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        b64 = base64.b64encode(raw).decode('ascii')
        
        # Simulate container document embedding
        container = f"PREFIX\n-----BEGIN_SOURCE_BASE64:{f}-----\n{b64}\n-----END_SOURCE_BASE64:{f}-----\nSUFFIX"
        
        # Extract from container
        m = re.search(rf"-----BEGIN_SOURCE_BASE64:{f}-----\s*([A-Za-z0-9+/=\s]+?)\s*-----END_SOURCE_BASE64:{f}-----", container)
        assert m is not None, f"Regex failed for {f}"
        clean_b64 = re.sub(r"\s+", "", m.group(1))
        decoded = base64.b64decode(clean_b64, validate=True)
        
        assert decoded == raw, f"Byte mismatch for {f}"
        assert len(decoded) == len(raw), f"Length mismatch for {f}"
        assert hashlib.sha256(decoded).hexdigest() == sha, f"Hash mismatch for {f}"
        results.append(f"{f}: {len(raw)} bytes, SHA {sha} -> 100% BYTE EQUALITY PASS")
    
    for r in results:
        print(r)
    print("FIXTURE_TOTAL = 3/3 PASS")

if __name__ == "__main__":
    run_test()

