# HERMES MULTI-BOT R06.2 AUDIT REPOSITORY EVIDENCE

## 1. Purpose & Scope
This audit branch hosts the byte-level self-auditable external review bundle (`HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md`) and its deterministic verifiers for the Hermes Multi-Bot / Multi-Profile architecture.
All Class A canonical sources are embedded with verbatim Base64 payloads ensuring exact byte-for-byte equality.

## 2. Key Files
- `HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md`: The single-file external review bundle.
- `HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md.sha256`: Sidecar SHA256 checksum.
- `build_r06_2_external_review_bundle.py`: Deterministic bundle generator.
- `verify_r06_2_bundle.py`: Primary independent verifier.
- `verify_r06_2_bundle_minimal.py`: Minimal second-opinion verifier (<150 lines).
- `r062_fixture/`: 3-file byte verification fixture test.

## 3. How to Verify
Run the minimal second-opinion verifier (zero external dependencies, standard library only):
```bash
python3 audit/verify_r06_2_bundle_minimal.py audit/HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md
```

Run the primary verifier:
```bash
python3 audit/verify_r06_2_bundle.py audit/HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md
```

Verify sidecar checksum:
```bash
shasum -a 256 -c audit/HERMES_MULTI_BOT_R06_2_EXTERNAL_REVIEW_BUNDLE.md.sha256
```

## 4. Expected Results
- Class A: 10/10 PASS (100% byte count & SHA256 match)
- Class B: 1/1 PASS (Redacted config match)
- Sidecar: PASS
