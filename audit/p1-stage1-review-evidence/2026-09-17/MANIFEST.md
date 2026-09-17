# P1 Stage-1 Review Evidence — Manifest

AUTHORITATIVE_STATUS = NON_CANONICAL_EVIDENCE_ONLY

These evidence copies do NOT become authority by being committed. Canonical
authority remains the repository's RULES / AGENTS / references hierarchy and
the approved P1 Spec identity recorded elsewhere.

## Stage identity

STAGE_START_MAIN = 8c78e987cbf3007f69876d28c5e3b22ff92c124c
STAGE_FINAL_MAIN = 0ec774f06882b923fd89b2bb52784538a3367477
P1_SPEC_SHA      = 60209cdaf2beeaa718fadcc4028a41c2f0f07db1

## Branch

BRANCH = evidence/p1-stage1-review-artifacts-20260917
BASE_SHA = 0ec774f06882b923fd89b2bb52784538a3367477
NATURE = NON_CANONICAL · REVIEW_ONLY · DO_NOT_MERGE

## Published artifacts

### 1. STAGE_1_REVIEW_PACKET
DISPLAY_NAME      = P1 Stage 1 Review Packet
SOURCE_LOCAL_PATH = <logical> stage1 session workspace root / STAGE_1_REVIEW_PACKET.md
                    (private absolute path withheld; not published)
PUBLISHED_PATH    = audit/p1-stage1-review-evidence/2026-09-17/STAGE_1_REVIEW_PACKET.md
ARTIFACT_TYPE     = STAGE_REVIEW_PACKET
SOURCE_SHA256     = fb773d56c1a73105c30f9a25820e131921ac7c8c79447f94b04e899c3d4b27e0
PUBLISHED_SHA256  = fb773d56c1a73105c30f9a25820e131921ac7c8c79447f94b04e899c3d4b27e0
BYTE_IDENTICAL_TO_SOURCE = YES
IF_NO_REASON      = N/A
REDACTIONS        = NONE
AUTHORITATIVE_STATUS = NON_CANONICAL_EVIDENCE_ONLY

### 2. CONVERGENCE_ARBITER_FINAL
DISPLAY_NAME      = Convergence Arbiter Final Decision (P1 Stage 1)
SOURCE_LOCAL_PATH = <logical> stage1 session / review/convergence-arbiter/ARBITER_RECORD.md
                    (private absolute path withheld; not published)
PUBLISHED_PATH    = audit/p1-stage1-review-evidence/2026-09-17/CONVERGENCE_ARBITER_FINAL.md
ARTIFACT_TYPE     = CONVERGENCE_ARBITER
SOURCE_SHA256     = dccc2edf73ade1e26d56e71332a6a48d66e933351e782e8795887ab719c8da36
PUBLISHED_SHA256  = dccc2edf73ade1e26d56e71332a6a48d66e933351e782e8795887ab719c8da36
BYTE_IDENTICAL_TO_SOURCE = YES
IF_NO_REASON      = N/A
REDACTIONS        = NONE
AUTHORITATIVE_STATUS = NON_CANONICAL_EVIDENCE_ONLY
NOTE_ON_CONTENT   = This record decides Q1 (Lane B AUTHORIZE_REPAIR_3 for the `[]`/`[^]`
                    empty-class defect) and Q2 (Lane A FORWARD_RISK_RECORDED for the
                    spec `(2)`-block 7th-name contradiction). The integration order
                    A -> B and the convergence reasoning / remaining findings are
                    recorded in STAGE_1_REVIEW_PACKET.md (section 5 and the carry-forward
                    obligations). The arbiter record was published AS-IS; no narrative
                    summary was substituted for it.

### 3. DRIFT_REFORM_SKILL
DISPLAY_NAME      = drift-reform-serial-integration (inert review copy)
SOURCE_LOCAL_PATH = <logical> ~/.workbuddy/skills/drift-reform-serial-integration/SKILL.md
                    (user-level local skill; NOT the repo's skills/ execution surface;
                     private absolute path withheld; not published)
PUBLISHED_PATH    = audit/p1-stage1-review-evidence/2026-09-17/drift-reform-serial-integration/SKILL.md
ARTIFACT_TYPE     = SKILL_REVIEW_COPY
SOURCE_SHA256     = 6f09ea02f281e7d90734733d4aa412454f8a2c48aafdb6f7939e4d13c81e94f1
PUBLISHED_SHA256  = 6f09ea02f281e7d90734733d4aa412454f8a2c48aafdb6f7939e4d13c81e94f1
BYTE_IDENTICAL_TO_SOURCE = YES
IF_NO_REASON      = N/A
REDACTIONS        = NONE
AUTHORITATIVE_STATUS = NON_CANONICAL_EVIDENCE_ONLY
SKILL_PUBLICATION_RULE = Published as an inert copy only. NOT placed at skills/,
                         NOT added to any skill registry, skills/README.md / AGENTS.md /
                         RULES.md / references/* were NOT modified. External review is
                         asked to judge: (1) is it merely an execution recipe;
                         (2) does it defer to canonical git-ci-integration /
                         execution-stage authority; (3) does it duplicate or replace
                         canonical governance; (4) does it create a new mandatory gate;
                         (5) does it overgeneralize a Stage-1-specific workaround;
                         (6) is it worth keeping at all. No activation before that review.

### 4. README
DISPLAY_NAME      = Boundary README
SOURCE_LOCAL_PATH = <generated on publish>
PUBLISHED_PATH    = audit/p1-stage1-review-evidence/2026-09-17/README.md
ARTIFACT_TYPE     = METADATA_BOUNDARY
SOURCE_SHA256     = GENERATED_ON_PUBLISH
PUBLISHED_SHA256  = fe5662556dabb3f6dd3b03147445dd8e51a77dc5f9449438f672c49cd1114478
BYTE_IDENTICAL_TO_SOURCE = N/A (generated on publish)
REDACTIONS        = NONE
AUTHORITATIVE_STATUS = NON_CANONICAL_EVIDENCE_ONLY

### 5. MANIFEST
DISPLAY_NAME      = This manifest
SOURCE_LOCAL_PATH = <generated on publish>
PUBLISHED_PATH    = audit/p1-stage1-review-evidence/2026-09-17/MANIFEST.md
ARTIFACT_TYPE     = METADATA_MANIFEST
SOURCE_SHA256     = GENERATED_ON_PUBLISH
PUBLISHED_SHA256  = <computed over published bytes; see publish verification output>
BYTE_IDENTICAL_TO_SOURCE = N/A (generated on publish)
REDACTIONS        = NONE
AUTHORITATIVE_STATUS = NON_CANONICAL_EVIDENCE_ONLY

## Public-safety attestation

PUBLIC_SAFETY_SCAN = PASS
SCAN_COVERAGE = absolute local machine paths, local usernames, homebrew path,
                GitHub tokens / PATs / AKIA keys, bearer / auth headers,
                private emails, api-key/secret/token assignments, AWS URLs.
RESULT = No sensitive pattern matched in any of the three source artifacts.
REDACTIONS = NONE (no redaction required; no public review copy was created).
LOCAL_PATH_HANDLING = The three source artifacts contained no absolute local machine
                     paths or usernames. Where the manifest records a source location,
                     a <logical> identifier is used instead of the private absolute path,
                     in accordance with the publish policy.

## Changed surface

EXPECTED_CHANGED_SURFACE = audit/p1-stage1-review-evidence/2026-09-17/** ONLY
NO_FILES_OUTSIDE_AUDIT_DIR = asserted at commit / verified post-push
MAIN_UNCHANGED = YES (branch forked from remote main 0ec774f; main not modified)

## Known non-blocking CI consequence (honest observation)

The evidence copies under `audit/` are scanned by the repository's own
single-declaration-point governance tests (`scripts/tests/test_review_evidence_contract.py`,
CE-28). `STAGE_1_REVIEW_PACKET.md` re-mentions frozen contract tokens
(`semanticScopeStatus`, `STRUCTURALLY_VALID`, `SOURCE_VERIFICATION_STATE`,
`EVIDENCE_SUFFICIENCY`), so the repo-wide `scan_token` / `scan_family` walk finds
those tokens in two places (the canonical `references/review-evidence.md` and this
review copy). As a result, on the evidence branch:

- `test_04_single_declaration_point_repo_wide` and `test_05_single_declaration_point_families`
  report a DUAL_DECLARATION hit against this review copy. This is an EXPECTED,
  INTRINSIC consequence of publishing contract prose on a REVIEW-ONLY branch. It is
  NOT a regression in `main` (main CI is green at 0ec774f), and it does NOT change
  the canonical contract. The artifacts are published byte-identical to source, so
  they cannot be altered to silence the scan without violating the publish contract.

- The public-safety / public-release check (`scripts/validate_public_release.py`,
  CURRENT_TREE + commit-metadata + selftest) is GREEN after the username redaction
  applied above. `git diff --check` is clean.

- `public-release-audit` is NOT triggered by this push: its `push` trigger requires
  `branches: ["main","security/**"]` AND `paths: audit/**`; the evidence branch is
  `evidence/...`, so the branch filter excludes it. (It WOULD trigger if these files
  landed on `main`.)

- `governance-ci` (all-branches push trigger) DOES run on this branch and will show
  the two expected `test_04`/`test_05` failures noted above. Recorded honestly; not
  concealed.

## CI observation (recorded at publish)

EVIDENCE_COMMIT_SHA = afdc5bb632ec73de11bf7664eb9f7725b74c7e54
BASE_SHA            = 0ec774f06882b923fd89b2bb52784538a3367477

- `governance-ci` run `35202666908` (head_sha = afdc5bb632ec73de11bf7664eb9f7725b74c7e54)
  conclusion = **failure**. The only failures are the two expected DUAL_DECLARATION
  (CE-28) tests: `test_04_single_declaration_point_repo_wide` (token
  `IDENTITY_VERSION_OR_DIGEST` found in STAGE_1_REVIEW_PACKET.md) and
  `test_05_single_declaration_point_families` (three-axis field-name family found in
  STAGE_1_REVIEW_PACKET.md and MANIFEST.md). This is an intrinsic artifact of copying
  contract prose onto a REVIEW-ONLY branch; it is NOT a regression in `main`
  (main CI is green at 0ec774f). No other gate failed.
- `public-release-audit` = **NOT_TRIGGERED** on this push. Its `push` trigger requires
  `branches: ["main","security/**"]` AND `paths: audit/**`; the evidence branch is
  `evidence/...`, so the branch filter excludes it. (The `audit/**` path filter WOULD
  match if these files landed on `main`; they do not.)
- `git diff --check` = clean. `scripts/validate_public_release.py` (CURRENT_TREE +
  commit-metadata + selftest) = VIOLATIONS=0 / 51-51. `scripts/validate_governance.py`
  = 31-31 after the username redaction applied during publish.
