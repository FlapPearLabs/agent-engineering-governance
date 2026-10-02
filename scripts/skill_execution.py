#!/usr/bin/env python3
"""Read-only task-bound Skill receipt checks; semantic owner is routing §1.

Record validity never proves semantic application, message delivery or host deny.
No sourceRef, report text or trace is an execution/network authority. Stdlib only.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.review_evidence import PLACEHOLDER, schema_violations

SCHEMA = Path(__file__).resolve().parents[1] / "schemas/skill-execution.schema.json"
MAX_BYTES = 1024 * 1024
SAFE_RETRIEVAL_AVAILABLE = (os.open in os.supports_dir_fd
                           and all(hasattr(os, flag) for flag in
                                   ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")))


class SafeRetrievalUnavailable(RuntimeError):
    """The host cannot provide descriptor-relative, no-follow retrieval."""


def safe_artifact_read(root: Path, parts: list[str]) -> bytes:
    """Anchor directory handles; path swaps cannot redirect a read outside root."""
    if not SAFE_RETRIEVAL_AVAILABLE:
        raise SafeRetrievalUnavailable()
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current = os.open(root.anchor, directory_flags)
    try:
        # Anchor the caller's root too: swapping one of its parents into a
        # symlink must not redirect root acquisition between precheck and open.
        for part in list(root.parts[1:]) + parts[:-1]:
            child = os.open(part, directory_flags, dir_fd=current)
            os.close(current)
            current = child
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                       dir_fd=current)
        try:
            info = os.fstat(leaf)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise ValueError("not a bounded regular file")
            chunks = []
            size = 0
            while size <= MAX_BYTES:
                chunk = os.read(leaf, min(65536, MAX_BYTES + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("size cap exceeded")
            return b"".join(chunks)
        finally:
            os.close(leaf)
    finally:
        os.close(current)


def bounded_read(path: Path) -> bytes:
    """Reject non-regular/oversize sources before opening; bound growing files too."""
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
        raise ValueError("not a bounded regular file")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("size cap exceeded")
    return data


def envelope(findings):
    # Never echo raw producer values (including malformed shape values).
    clean = [{"reason": item["reason"], "path": item["path"]} for item in findings]
    return {"recordValid": not clean, "findings": clean,
            "semanticApplicationVerified": False, "hostEnforcementVerified": False}


def unfinished_text(value):
    if isinstance(value, str):
        return not value.strip() or PLACEHOLDER.fullmatch(value.strip()) is not None
    if isinstance(value, dict):
        return any(unfinished_text(item) for item in value.values())
    if isinstance(value, list):
        return any(unfinished_text(item) for item in value)
    return False


def validate_receipt(receipt, *, expected_subject, required_skills, evidence_root,
                     no_required_reason=None):
    """Verify declared records/attachments against independent consumer inputs."""
    findings = []

    def fail(reason, path):
        findings.append({"reason": reason, "path": path})

    try:
        schema = json.loads(bounded_read(SCHEMA))
        shape = schema_violations(receipt, schema)
    except (OSError, ValueError, TypeError, RecursionError):
        fail("SCHEMA_UNAVAILABLE", "$schema")
        return envelope(findings)
    if shape:
        return envelope(shape)
    if unfinished_text(receipt):
        fail("UNFINISHED_RECORD_TEXT", "$")
    expected_shape = schema_violations(expected_subject, schema["properties"]["subject"])
    if expected_shape or receipt["subject"] != expected_subject:
        fail("SUBJECT_MISMATCH", "$.subject")
    if not required_skills and (not isinstance(no_required_reason, str)
                               or unfinished_text(no_required_reason)):
        fail("REQUIREMENT_INPUT_REQUIRED", "consumer.required_skills")
    if required_skills and no_required_reason is not None:
        fail("REQUIREMENT_INPUT_CONFLICT", "consumer.required_skills")
    if any(not isinstance(name, str) or unfinished_text(name) for name in required_skills):
        fail("REQUIREMENT_INPUT_INVALID", "consumer.required_skills")
    names = [row["name"] for row in receipt["skills"]]
    if len(names) != len(set(names)):
        fail("DUPLICATE_SKILL", "$.skills")
    for required in required_skills:
        if required not in names:
            fail("REQUIRED_SKILL_MISSING", "$.skills")

    content = {}
    declared = set()
    # The consumer supplied a boundary, not permission to adopt a link target.
    # Lexical absolute conversion does not dereference any path component.
    root = Path(os.path.abspath(evidence_root))
    for index, artifact in enumerate(receipt["artifacts"]):
        location = artifact["location"]
        at = f"$.artifacts[{index}]"
        if location in declared:
            fail("DUPLICATE_ARTIFACT", at)
        declared.add(location)
        # Refuse schemes, drives, backslash/absolute paths and parent traversal.
        parts = location.split("/")
        if (":" in location or "\\" in location or "\x00" in location
                or location.startswith("/") or any(p in ("", ".", "..") for p in parts)):
            fail("ARTIFACT_PATH_FORBIDDEN", at)
            continue
        try:
            data = safe_artifact_read(root, parts)
        except SafeRetrievalUnavailable:
            fail("SAFE_RETRIEVAL_UNAVAILABLE", at)
            continue
        except OSError as exc:
            reason = "ARTIFACT_PATH_FORBIDDEN" if exc.errno in (errno.ELOOP, errno.ENOTDIR) \
                else "ARTIFACT_UNREADABLE"
            fail(reason, at)
            continue
        except (ValueError, RuntimeError):
            fail("ARTIFACT_UNREADABLE", at)
            continue
        if not data.strip():
            fail("ARTIFACT_EMPTY", at)
            continue
        if artifact["contentDigest"] != "sha256:" + hashlib.sha256(data).hexdigest():
            fail("ARTIFACT_DIGEST_MISMATCH", at)
            continue
        content[location] = data

    for index, row in enumerate(receipt["skills"]):
        at = f"$.skills[{index}]"
        if row["status"] == "UNVERIFIED":
            fail("SKILL_UNVERIFIED", at)
        if row["status"] == "APPLIED":
            if not row["readEvidenceRef"] or not row["sourceRef"] or not row["sourceRef"].strip():
                fail("FULL_READ_EVIDENCE_REQUIRED", at)
            if row["fallbackReason"] is not None:
                fail("APPLIED_FALLBACK_CONFLICT", at)
        elif row["status"] == "FALLBACK":
            if not row["fallbackReason"] or not row["fallbackReason"].strip():
                fail("FALLBACK_REASON_REQUIRED", at)
        refs = list(row["executionEvidenceRefs"]) + [row["reportRef"]]
        if row["readEvidenceRef"] is not None:
            refs.append(row["readEvidenceRef"])
        for ref in refs:
            if ref not in declared:
                fail("ARTIFACT_UNDECLARED", at)
            elif ref not in content:
                fail("ARTIFACT_NOT_VERIFIED", at)
        if row["reportRef"] not in content:
            continue
        try:
            report = json.loads(content[row["reportRef"]])
            report_schema = {"$ref": "#/$defs/report", "$defs": schema["$defs"]}
            report_shape = schema_violations(report, report_schema)
        except (ValueError, TypeError, RecursionError):
            fail("REPORT_NOT_JSON", at)
            continue
        if report_shape:
            fail("REPORT_STRUCTURE_INVALID", at)
            continue
        if unfinished_text(report):
            fail("UNFINISHED_REPORT_TEXT", at)
        if report["skill"] != row["name"] or report["status"] != row["status"]:
            fail("REPORT_MISMATCH", at)
        audience = "USER" if receipt["subject"]["role"] == "PARENT" else "PARENT"
        if report["audience"] != audience:
            fail("REPORT_AUDIENCE_MISMATCH", at)
        needed = set(row["executionEvidenceRefs"])
        if row["status"] == "APPLIED" and row["readEvidenceRef"]:
            needed.add(row["readEvidenceRef"])
        if not needed.issubset(report["evidenceRefs"]):
            fail("REPORT_EVIDENCE_MISSING", at)
        if any(ref not in content for ref in report["evidenceRefs"]):
            fail("REPORT_ARTIFACT_NOT_VERIFIED", at)
    return envelope(findings)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    for flag in ("repo", "base-sha", "candidate-sha", "task", "phase", "role", "evidence-root"):
        parser.add_argument("--" + flag, required=True)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--required-skill", action="append")
    choice.add_argument("--no-required-skills-reason")
    args = parser.parse_args(argv)
    subject = {"repo": args.repo, "baseSha": args.base_sha, "candidateSha": args.candidate_sha,
               "task": args.task, "phase": args.phase, "role": args.role}
    try:
        receipt = json.loads(bounded_read(args.receipt))
        result = validate_receipt(receipt, expected_subject=subject,
                                  required_skills=args.required_skill or [],
                                  evidence_root=args.evidence_root,
                                  no_required_reason=args.no_required_skills_reason)
    except (OSError, ValueError, TypeError, RecursionError, RuntimeError):
        result = envelope([{"reason": "RECEIPT_UNREADABLE", "path": "$"}])
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["recordValid"] else 1


if __name__ == "__main__":
    sys.exit(main())
