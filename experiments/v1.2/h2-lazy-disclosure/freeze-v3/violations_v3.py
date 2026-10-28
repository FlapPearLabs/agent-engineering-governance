"""Collect per-process macOS sandbox denial evidence from unified logging."""
import json
import re
import subprocess
from pathlib import Path

PREDICATE = 'subsystem == "com.apple.sandbox.reporting"'
DENIAL = re.compile(r"Sandbox: (.+?)\((\d+)\) deny(?:\(\d+\))?\s+(\S+)(?:\s+(.*))?$")


def collect_violations(start_ts, end_ts, pids: set[int], out_path) -> int:
    """Write matching denial events as JSONL; malformed log entries are ignored."""
    try:
        result = subprocess.run(["/usr/bin/log", "show", "--start", str(start_ts),
                                 "--end", str(end_ts), "--style", "ndjson",
                                 "--predicate", PREDICATE], capture_output=True,
                                text=True, timeout=30, check=False)
        lines = result.stdout.splitlines()
    except (OSError, subprocess.SubprocessError, UnicodeError):
        lines = []
    records = []
    for line in lines:
        try:
            item = json.loads(line)
            match = DENIAL.search(item.get("eventMessage", ""))
            if not match or int(match[2]) not in pids:
                continue
            records.append({"ts": item.get("timestamp"), "pid": int(match[2]),
                            "process": match[1], "operation": match[3],
                            "path": match[4] or ""})
        except (ValueError, TypeError, AttributeError):
            continue
    Path(out_path).write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
    return len(records)
