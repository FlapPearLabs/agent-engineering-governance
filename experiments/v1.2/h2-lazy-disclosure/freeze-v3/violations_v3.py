"""Collect per-process macOS sandbox denial evidence from unified logging."""
import datetime
import json
import re
import subprocess
from pathlib import Path

PREDICATE = 'subsystem == "com.apple.sandbox.reporting"'
DENIAL = re.compile(r"Sandbox: (.+?)\((\d+)\) deny(?:\(\d+\))?\s+(\S+)(?:\s+(.*))?$")
# The one timestamp spelling `log show --start/--end` accepted in the live measurement (T51d).
LOG_FORMAT = "%Y-%m-%d %H:%M:%S%z"


def stamp(moment=None) -> str:
    """A `log show` timestamp: local time with a numeric offset.

    The driver stamps a launch with `run_h2r2.now()` (ISO-8601, UTC), so its value is converted
    here instead of being handed to `log` in a spelling the live test did not prove. A value that
    cannot be parsed is passed through unchanged rather than silently replaced by another time.
    """
    if moment is None:
        return datetime.datetime.now().astimezone().strftime(LOG_FORMAT)
    if isinstance(moment, datetime.datetime):
        parsed = moment
    else:
        try:
            parsed = datetime.datetime.fromisoformat(str(moment))
        except ValueError:
            return str(moment)
    return parsed.astimezone().strftime(LOG_FORMAT)


def collect_violations(start_ts, end_ts, pids: set[int], out_path) -> int:
    """Write matching denial events as JSONL; malformed log entries are ignored.

    `pids` is the launch's observed process set and is a LOWER BOUND: a process that started and
    exited between two observations of the driver is not attributed. A `log show` failure raises,
    so the caller records it as an error instead of an empty (falsely clean) log.
    """
    result = subprocess.run(["/usr/bin/log", "show", "--start", stamp(start_ts),
                                 "--end", stamp(end_ts), "--style", "ndjson",
                                 "--predicate", PREDICATE], capture_output=True,
                            text=True, timeout=30, check=True)
    lines = result.stdout.splitlines()
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
