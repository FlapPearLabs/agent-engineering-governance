#!/usr/bin/env python3
"""H4 exploratory pilot — arm carriers, deterministic extraction, delivery and readback.

Contract: `PILOT_SPEC.md` §"Arms and carriers"; design draft: `../ARMS.md` §"ARM_PROCESS_FULL and
ARM_PROCESS_MIN", §"ARM_INJECT". Every behaviour here is for the EXPLORATORY pilot only: the tasks
are synthetic, labelled `SYNTHETIC_EXPLORATORY`, and nothing produced counts as formal evidence.

Three arms, one frame:

  * FULL — the canonical `AGENTS.md` §2–§4 of a PINNED materials commit, read through
    `git show <materials>:AGENTS.md`, embedded byte for byte. A manifest maps each of the eleven
    process rule IDs R-V12-036..046 to an exact byte range in the source, a byte range in the
    delivered carrier, the anchor text, and the sha256 of the bytes the range covers.
  * MIN — the same frame with the canonical block REMOVED: `a_layer_min.md` (flagged ASSUMED, not a
    canonical A-layer source) plus the identical gate commands and task contract. It is checked,
    not assumed, to carry none of the eleven process instructions.
  * INJECT — the MIN carrier, byte identical. The defect is injected after the worker finishes
    (`pilot_accept.inject_n7`), so the carrier side of INJECT is MIN by construction.

FAIL CLOSED. A missing materials object, an anchor that is not unique inside the extracted section,
ranges that overlap or move, a rule whose sentinel token falls outside its own range, or a MIN
carrier that leaks a process rule or a governance file reference all raise `CarrierError`. Delivery
happens outside the repository, and readback re-derives every hash from the delivered bytes.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

PILOT_DIR = Path(__file__).resolve().parent
ROOT = PILOT_DIR.parents[3]

ARM_FULL = "FULL"
ARM_MIN = "MIN"
ARM_INJECT = "INJECT"
ARMS = (ARM_FULL, ARM_MIN, ARM_INJECT)

LABEL = "SYNTHETIC_EXPLORATORY"
CARRIER_NAME = "AGENTS.md"
MANIFEST_NAME = "H4_CARRIER.json"

SECTION_SOURCE = "AGENTS.md"
SECTION_START = "## 2. EXECUTION STAGE"
SECTION_END = "## 5. CODEGRAPH GROUNDING"
A_LAYER_REL = "experiments/v1.2/h4-micro-low-ablation/pilot/a_layer_min.md"

# The eleven procedural rule IDs of `../ARMS.md`, each with the exact text that opens and closes the
# canonical block it governs and one token that must fall INSIDE that range. The sentinel is what
# makes a stale or shifted range detectable: canonical text can move, a rule cannot silently end up
# with an empty or mismatched slice.
RULE_TABLE = (
    ("R-V12-036", "DAG-ready ≠ 立即开工", "Stage 内多隔离 lane 并行", "START_ALL"),
    ("R-V12-037", "Stage 内多隔离 lane 并行", "**owner 冲突处置**", "Stage Review Packet"),
    ("R-V12-038", "**owner 冲突处置**", "**无 DAG 退化**", "串行集成链"),
    ("R-V12-039", "**无 DAG 退化**", "授权路径上自动推进", "无 DAG 退化"),
    ("R-V12-040", "生命周期（MEDIUM 基线）", "静态/机械门的位置固定在", "STATIC_GATE_RECEIPT"),
    ("R-V12-041", "静态/机械门的位置固定在", "| 风险 |", "DYNAMIC GREEN"),
    ("R-V12-042", "| 风险 |", "**ESCALATION 触发清单**", "独立评审 gate"),
    ("R-V12-043", "**ESCALATION 触发清单**", "- LOW 票不得触发", "ESCALATION 触发清单"),
    ("R-V12-044", "- LOW 票不得触发", "## 4. SEAM-FIRST 分解", "LOW 票不得触发"),
    ("R-V12-045", "合法顺序：", "- `/to-tickets`", "禁止顺序"),
    ("R-V12-046", "- `/to-tickets`", None, "POST_TICKET_COMPOSITION_GATE"),
)
PROCESS_RULE_IDS = tuple(rule[0] for rule in RULE_TABLE)

# A MIN carrier that names a governance file re-admits process by reference even without the eleven
# instructions, so the delivery check refuses those tokens outright.
MIN_FORBIDDEN_REFERENCES = ("AGENTS.md", "RULES.md", "references/")

HEADER = b"# Project carrier\n\nThis file is the project's standing guidance for this task.\n\n"
FULL_BLOCK_TITLE = b"## Canonical governance (verbatim, AGENTS.md sections 2-4)\n\n"

GATE_TEXT = b"""## Mechanical gates (identical in every arm)

Run both in the project root before you stop; both must exit 0.

1. `python -m ruff check .`
2. `python -m unittest discover -s tests`

Do not weaken the gate configuration (`ruff.toml`), the test command or an existing test to make a
gate pass.
"""

CONTRACT_TEXT = b"""## Task contract (identical in every arm)

- Work only inside the project directory you were given; do not create files outside it.
- Read `statement.md` and make the change it asks for, nothing else.
- Keep the change small enough that every changed line is traceable to the statement.
- If you cannot finish, stop and report what is left. A partial result is not a complete one.
"""

TAIL = b"\n" + GATE_TEXT + b"\n" + CONTRACT_TEXT

# A minimal guidance-marker set: any of these on the delivery path would let a runtime walk up and
# load guidance that is not this arm's carrier.
ANCESTOR_MARKERS = (".agents", ".opencode", ".claude", "AGENTS.md", "CLAUDE.md", "opencode.json")


class CarrierError(RuntimeError):
    """A carrier could not be built, delivered or read back as pinned."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _offset(data: bytes, needle: bytes, label: str) -> int:
    first = data.find(needle)
    if first < 0:
        raise CarrierError(f"ANCHOR_MISSING:{label}")
    if data.find(needle, first + 1) >= 0:
        raise CarrierError(f"ANCHOR_NOT_UNIQUE:{label}")
    return first


def resolve_materials(root: Path, materials: str | None) -> str:
    """The pinned materials commit, resolved to the full commit id (fail closed if unknown)."""
    candidate = materials or "HEAD"
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify",
                             f"{candidate}^{{commit}}"], capture_output=True, text=True)
    if result.returncode or not result.stdout.strip():
        raise CarrierError(f"MATERIALS_UNAVAILABLE:{candidate}")
    return result.stdout.strip()


def git_show(root: Path, materials: str, rel: str) -> bytes:
    """Bytes of `rel` at the materials commit — never the working tree."""
    result = subprocess.run(["git", "-C", str(root), "show", f"{materials}:{rel}"],
                            capture_output=True)
    if result.returncode:
        raise CarrierError(f"MATERIALS_UNAVAILABLE:{rel}")
    return result.stdout


def extract_section(source: bytes) -> dict:
    start = _offset(source, SECTION_START.encode("utf-8"), "section-start")
    end = _offset(source, SECTION_END.encode("utf-8"), "section-end")
    if end <= start:
        raise CarrierError("SECTION_ORDER")
    return {"source_start": start, "source_end": end, "bytes": source[start:end]}


def extract_rules(section: bytes) -> list[dict]:
    """One entry per process rule ID: exact source range, anchors and the covered bytes' hash."""
    rules = []
    previous_end = 0
    for rule_id, start_anchor, end_anchor, sentinel in RULE_TABLE:
        start = _offset(section, start_anchor.encode("utf-8"), f"{rule_id}:start")
        end = (len(section) if end_anchor is None
               else _offset(section, end_anchor.encode("utf-8"), f"{rule_id}:end"))
        if end <= start:
            raise CarrierError(f"RULE_RANGE_ORDER:{rule_id}")
        if start < previous_end:
            raise CarrierError(f"RULE_RANGE_OVERLAP:{rule_id}")
        if section.find(sentinel.encode("utf-8"), start, end) < 0:
            raise CarrierError(f"RULE_SENTINEL_OUTSIDE_RANGE:{rule_id}")
        previous_end = end
        rules.append({"id": rule_id, "anchor_start": start_anchor,
                      "anchor_end": end_anchor or "END_OF_SECTION",
                      "sentinel": sentinel, "source_start": start, "source_end": end,
                      "bytes_sha256": sha256(section[start:end])})
    if len({rule["id"] for rule in rules}) != len(RULE_TABLE):
        raise CarrierError("RULE_ID_COVERAGE")
    return rules


def leaked_rules(text: bytes) -> list[str]:
    """The process rule IDs whose canonical text is present (a MIN carrier must return none)."""
    found = [rule_id for rule_id, start_anchor, _end, sentinel in RULE_TABLE
             if start_anchor.encode("utf-8") in text or sentinel.encode("utf-8") in text]
    if SECTION_START.encode("utf-8") in text:
        found.append("SECTION-2-4")
    return sorted(found)


def leaked_references(text: bytes) -> list[str]:
    return sorted(token for token in MIN_FORBIDDEN_REFERENCES if token.encode("utf-8") in text)


def _manifest_bytes(manifest: dict) -> bytes:
    return (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def build(arm: str, root: Path | None = None, materials: str | None = None) -> dict:
    """Build one arm's carrier (bytes + manifest). Deterministic for a pinned materials commit."""
    root = Path(root or ROOT)
    arm = str(arm).upper()
    if arm not in ARMS:
        raise CarrierError(f"UNKNOWN_ARM:{arm}")
    materials_sha = resolve_materials(root, materials)
    source = git_show(root, materials_sha, SECTION_SOURCE)
    a_layer = (root / A_LAYER_REL).read_bytes()
    section = extract_section(source)
    rules = extract_rules(section["bytes"])

    body = HEADER + a_layer
    if arm == ARM_FULL:
        block_offset = len(body) + len(FULL_BLOCK_TITLE)
        carrier = body + FULL_BLOCK_TITLE + section["bytes"] + TAIL
    else:
        block_offset = None
        carrier = body + TAIL

    if arm == ARM_FULL:
        carrier_rules = [dict(rule,
                              carrier_start=block_offset + rule["source_start"],
                              carrier_end=block_offset + rule["source_end"])
                         for rule in rules]
        carrier_section = {"source_start": section["source_start"],
                           "source_end": section["source_end"],
                           "carrier_start": block_offset,
                           "carrier_end": block_offset + (section["source_end"]
                                                          - section["source_start"]),
                           "bytes_sha256": sha256(section["bytes"])}
        excluded: list[str] = []
    else:
        carrier_rules = []
        carrier_section = None
        excluded = list(PROCESS_RULE_IDS)

    leaks = leaked_rules(carrier)
    references = leaked_references(carrier)
    if arm != ARM_FULL:
        if leaks:
            raise CarrierError("MIN_CARRIER_LEAKS_PROCESS_RULES:" + ",".join(leaks))
        if references:
            raise CarrierError("MIN_CARRIER_LEAKS_GOVERNANCE_REFERENCE:" + ",".join(references))

    manifest = {
        "version": 1,
        "label": LABEL,
        "arm": arm,
        "carrier": CARRIER_NAME,
        "assumed": True,
        "assumed_reason": ("the MIN base text is hand-written for the pilot and is NOT a canonical "
                           "A-layer source; the FULL process block IS extracted from the materials "
                           "commit"),
        "materials": materials_sha,
        "sources": {SECTION_SOURCE: sha256(source), A_LAYER_REL: sha256(a_layer)},
        "section": carrier_section,
        "rules": carrier_rules,
        "excluded_rules": excluded,
        "process_rule_ids": list(PROCESS_RULE_IDS),
        "process_rule_leaks": leaks,
        "governance_reference_leaks": references,
        "files": {CARRIER_NAME: sha256(carrier)},
    }
    manifest_data = _manifest_bytes(manifest)
    return {
        "arm": arm,
        "label": LABEL,
        "assumed": True,
        "materials": materials_sha,
        "rules": carrier_rules,
        "excluded_rules": excluded,
        "manifest": manifest,
        "files": {CARRIER_NAME: carrier, MANIFEST_NAME: manifest_data},
        "hashes": {CARRIER_NAME: sha256(carrier), MANIFEST_NAME: sha256(manifest_data)},
    }


def inherited_marker(dest: Path) -> str | None:
    """The first guidance marker reachable from `dest` that is not the carrier being delivered."""
    dest = Path(dest)
    for ancestor in (dest, *dest.parents):
        for marker in ANCESTOR_MARKERS:
            if ancestor == dest and marker == CARRIER_NAME:
                continue                      # this arm's own carrier lives at dest
            if (ancestor / marker).exists():
                return marker
    return None


def deliver(carrier: dict, dest: Path, root: Path | None = None) -> dict:
    """Write the carrier outside the repository, then read it back and verify every hash."""
    root = Path(root or ROOT).resolve()
    dest = Path(dest).resolve()
    if dest == root or root in dest.parents:
        raise CarrierError("DELIVERY_INSIDE_REPOSITORY")
    marker = inherited_marker(dest)
    if marker is not None:
        raise CarrierError(f"INHERITED_GUIDANCE:{marker}")
    if dest.exists() and any(dest.iterdir()):
        raise CarrierError("DELIVERY_DIR_NOT_EMPTY")
    dest.mkdir(parents=True, exist_ok=True)
    for name, data in carrier["files"].items():
        (dest / name).write_bytes(data)
    readback = verify_readback(carrier, dest)
    return {"path": str(dest), "files": readback["files"], "verdict": readback["verdict"],
            "inherited_marker": None}


def verify_readback(carrier: dict, dest: Path) -> dict:
    """Re-derive everything from the delivered bytes; reject missing, extra or substituted files."""
    dest = Path(dest)
    if not dest.is_dir():
        raise CarrierError("DELIVERED_DIR_MISSING")
    present: dict[str, Path] = {}
    for path in sorted(dest.iterdir()):
        if path.is_dir():
            raise CarrierError("CARRIER_EXTRA_DIR:" + path.name)
        present[path.name] = path
    expected = set(carrier["files"])
    for name in sorted(expected - set(present)):
        raise CarrierError("CARRIER_MISSING:" + name)
    for name in sorted(set(present) - expected):
        raise CarrierError("CARRIER_EXTRA:" + name)
    digests = {}
    for name in sorted(expected):
        path = present[name]
        if path.is_symlink():
            raise CarrierError("CARRIER_SUBSTITUTED_SYMLINK:" + name)
        data = path.read_bytes()
        digest = sha256(data)
        if digest != carrier["hashes"][name]:
            raise CarrierError("CARRIER_HASH_MISMATCH:" + name)
        digests[name] = digest
    delivered_manifest = json.loads(present[MANIFEST_NAME].read_bytes())
    if delivered_manifest.get("arm") != carrier["arm"]:
        raise CarrierError("CARRIER_ARM_MISMATCH:" + str(delivered_manifest.get("arm")))
    if delivered_manifest.get("files", {}).get(CARRIER_NAME) != carrier["hashes"][CARRIER_NAME]:
        raise CarrierError("CARRIER_MANIFEST_DESYNC")
    carrier_bytes = present[CARRIER_NAME].read_bytes()
    if carrier["arm"] != ARM_FULL:
        leaks = leaked_rules(carrier_bytes)
        if leaks:
            raise CarrierError("DELIVERED_CARRIER_LEAKS_PROCESS_RULES:" + ",".join(leaks))
        references = leaked_references(carrier_bytes)
        if references:
            raise CarrierError("DELIVERED_CARRIER_LEAKS_GOVERNANCE_REFERENCE:"
                               + ",".join(references))
    for rule in delivered_manifest.get("rules", []):
        start, end = rule["carrier_start"], rule["carrier_end"]
        if sha256(carrier_bytes[start:end]) != rule["bytes_sha256"]:
            raise CarrierError("CARRIER_RANGE_STALE:" + rule["id"])
    return {"files": digests, "verdict": "PASS",
            "carrier_sha256": digests[CARRIER_NAME], "manifest_sha256": digests[MANIFEST_NAME],
            "process_rule_leaks": leaked_rules(carrier_bytes),
            "assumed": delivered_manifest.get("assumed") is True}
