# R06.1 Generator Root Cause & Forensic Failure Report
> Forensic audit on generator failure, false PASS generation, and byte divergence.

## 1. Ten Forensic Questions & Answers
1. **Read Mode**: The previous generator used text reading/splitting instead of raw byte streams, introducing newline normalization (`\r\n` vs `\n`).
2. **SHA Target**: The SHA was computed on decoded text or pre-wrap buffers, but Markdown fences and wrapping modified byte offsets.
3. **Embedded Representation**: Rather than byte-exact payloads, Markdown formatting, dedents, and partial excerpts were embedded.
4. **Transformations**: Splitlines, indentation, and strip operations silently altered payload byte lengths (e.g. 4712 down to 3747 bytes).
5. **Config Redaction**: Redaction happened in memory without distinguishing `ORIGINAL_RAW_SHA256` from `REDACTED_EMBEDDED_SHA256`.
6. **Canonical SHA Ambiguity**: Manifest conflated raw disk file SHA with redacted/transformed payload SHA.
7. **Consistency Check Timing**: PART 14 PASS was evaluated on pre-render memory variables, NEVER on the finalized output file re-opened from disk.
8. **Final Bundle SHA Timing**: Statically declared or computed prior to file finalization, creating self-referential hash paradox.
9. **Generator Self-Embedding**: The generator source was omitted from the bundle, preventing third-party auditing of the generation logic.
10. **False Positive Mechanism**: Hardcoded or pre-render string assertions passed in memory without re-parsing emitted payloads.

## 2. Correct Architecture for R06.1
- **Dual Representation**: Human-readable view for reviewers + Base64 raw bytes payload for machine hash verification.
- **Class A Sources (Verbatim)**: Raw bytes base64-encoded; decoded SHA256 must match `ORIGINAL_RAW_SHA256` 100%.
- **Class B Sources (Transformed/Redacted)**: Explicitly labeled with `REDACTION_APPLIED = YES` and verified against `REDACTED_EMBEDDED_SHA256`.
- **Self-Auditable Generator**: The complete generator source is embedded verbatim in the bundle.
- **Independent Verifier**: A separate script (`audit/verify_r06_1_bundle.py`) reads the final output from disk and re-verifies every hash.
- **Sidecar SHA**: Final bundle SHA is emitted as a `.sha256` sidecar file and terminal output, eliminating the self-hash paradox.


