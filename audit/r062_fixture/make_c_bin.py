#!/usr/bin/env python3
import pathlib

# Generate deterministic binary bytes
data = bytearray(range(256)) * 4  # 1024 bytes with all 0x00-0xFF bytes
p = pathlib.Path(__file__).parent / "c.bin"
p.write_bytes(data)
print(f"c.bin generated: {len(data)} bytes")
