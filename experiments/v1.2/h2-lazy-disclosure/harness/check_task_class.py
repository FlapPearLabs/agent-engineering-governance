#!/usr/bin/env python3
"""H2 eligibility — mechanical validator for ELIGIBILITY_SCHEMA_V2 classification records.

WHY THIS EXISTS
---------------
The schema revision is only worth anything if it is enforced by a program rather than by prose.
The failure it guards against is concrete and already measured twice in this repository's history:

  * a task can PASS because the worker authored the thing that decides the verdict
    (measured: `ruff check .` reports "All checks passed" under `select = []`);
  * a task can PASS because no gate observes the deliverable at all
    (measured: the r06 delta adds eight files while the only era gate stays item-for-item 23/23).

WHAT IS RECOMPUTED HERE (never read from the record)
----------------------------------------------------
  · IDENTITY: a record must name the replay-corpus case it classifies, and its revision pair must
    EQUAL the pair `experiments/v1.2/replay/cases.yaml` binds to that case. Without this, a record
    may borrow a real, local, ancestor-related revision pair from an unrelated case and assert any
    class it likes — the first fix round left exactly that hole open (demonstrated).
  · DERIVED TRIGGERS: the changed-file list of that pair is read from the object database, and
    every changed test file derives WORKER_MODIFIES_TEST_ORACLE while every changed
    validate_*/check_* file derives WORKER_MODIFIES_VALIDATOR. A record must either DECLARE a
    derived trigger or list every one of its paths in `externalized_paths` together with an
    ORACLE_EXTERNALIZATION pending requirement. The delta's file list is a git fact, so this cannot
    be talked away by editing the record.
  · ANCESTRY: for a claim of an admissible class, the candidate must descend from the base
    (`git merge-base --is-ancestor`), and the pair must not be degenerate (base == candidate).
  · EVIDENCE PATHS: every `evidence[].source` must resolve to an existing file.
  · The closed vocabularies, the per-class field equalities, the trigger/class consistency, the
    disclosure-to-authority binding, the C_REJECT "show which class you blocked" rule, the exact
    pending-code match, and the structural rules (unique ids, required schema_version, malformed
    records as structured errors).

WHAT IS **NOT** ENFORCED — and why this program does not call its verdict an admission
-------------------------------------------------------------------------------------
The TRUTH of `baseline_oracle_status` / `mutation_oracle_status` is never recomputed: this program
cannot re-run a candidate's oracle, so a record can still declare statuses that are false. That
limit is real and is stated rather than papered over, which is why:

    this program validates an ADMISSION REQUEST, it never grants an admission.
    `round_admission.verdict = REQUEST_VALID` means "every fact this repository can check agrees
    with this record". The grant is the round freeze plus independent review — nothing here.

Further limits, recorded here so that a reader of THIS FILE is not misled:
  · the derived-trigger rules are NAME-based (tests?/, .test., test_*.py, validate_*.py,
    check_*.sh|py) and therefore BLIND TO ROLE. NOT derived: ruff.toml, .github/workflows/**,
    conftest.py, Makefile, pyproject.toml, and any file that validates without matching those names
    — the corpus contains one, r02's scripts/review_evidence.py, a collect/validate CLI. A task whose
    verdict hangs on such a file must declare the trigger by hand; a role-aware rule would need a
    declared manifest, which is out of scope here;
  · a disclosure that contradicts the object database is refused INDEPENDENTLY of what the record
    declares: `historical_delta_touched_validator: false` alongside a delta that provably changes a
    validate_*/check_* file is an error whether or not the record declares the derived trigger
    (the check runs before the declaration short-circuit);
  · the pin on the corpus is a COUPLING, not a proof: it forces a corpus editor to also edit the
    digest constant and the per-case literals, which makes the edit review-visible; it cannot stop a
    determined author from making all three edits together;
  · externalisation that silences a derived trigger is an assertion, and for an externally bound
    pair the "path is in the delta" check cannot run at all;
  · the record's CLASS is bound to nothing recomputable, and the corpus's own measured dispositions
    are deliberately not consulted.

A PASS therefore means "internally consistent AND consistent with every fact this repository can
recompute". It is not a statement that the work happened.

Usage:  python3 check_task_class.py <classification.json> [repo_root]
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SCHEMA_ID = "ELIGIBILITY_SCHEMA_V2"
SCHEMA_VERSION = "2.7.0"
# The identity rule reads experiments/v1.2/replay/cases.yaml, and nothing else in this
# repository pins that file: it is in no freeze hash and no test checks its SHA values. A trust
# root anyone can rewrite is not a trust root, so its digest is pinned HERE as a literal,
# exactly as the material tests pin the freeze hashes — editing the corpus without updating
# this constant (and the test that asserts it) fails the validator, in review.
CORPUS_SHA256 = "5d898b1a6db8fb16116a3cbec58c7078d780e379dd58d6d54553645291cda731"
CLASSES = ("A_REPAIR", "B_REGRESSION_GUARD", "C_REJECT")
ADMISSIBLE_CLASSES = ("A_REPAIR", "B_REGRESSION_GUARD")
TRIGGER_CODES = (
    "WORKER_MODIFIES_VALIDATOR",
    "WORKER_MODIFIES_TEST_ORACLE",
    "ACCEPTANCE_SURFACE_IN_WORKER_SCOPE",
    "SELF_PROVING_HASH",
    "OBSERVATION_COVERAGE_UNPROVEN",
    "BASE_CANDIDATE_NOT_COMPARABLE",
)
ORACLE_AUTHORITIES = ("FRAMEWORK_FROZEN", "PENDING_FREEZE_V2")
# The verdict vocabulary for an entry describing a class the record CLAIMS. Closed on purpose: an
# open vocabulary let a record mark its own class "NOT_APPLICABLE" and still request admission.
AFFIRMATIVE_VERDICTS = ("SHAPE_SATISFIED", "SHAPE_SATISFIED_PENDING_MATERIALISATION")
ADMISSION_VERDICTS = ("REQUEST_VALID", "NOT_ADMITTED")
SHA_BINDINGS = ("LOCAL_REPO_VERIFIED", "EXTERNAL_UNVERIFIABLE_LOCALLY")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{3,}$")
PENDING_PREFIX = "ORACLE_EXTERNALIZATION"
# A changed file that holds assertions, versus one that decides a verdict.
TEST_PATH_RE = re.compile(r"(^|/)tests?/|\.test\.|(^|/)test_[^/]*\.py$")
VALIDATOR_PATH_RE = re.compile(r"(^|/)validate_[^/]*\.py$|(^|/)check_[^/]*\.(sh|py)$")
CASES_YAML = "experiments/v1.2/replay/cases.yaml"
REQUIRED_RECORD_KEYS = (
    "candidate_id", "corpus_case_id", "source_repository", "base_sha", "candidate_sha",
    "sha_binding", "class", "class_considered", "reject_triggers", "pending_requirements",
    "round_admission", "evidence",
)


class Repo:
    """Read-only view of the object database the validator runs inside."""

    def __init__(self, root: Path):
        self.root = root

    def git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(self.root), *args],
                              capture_output=True, text=True)

    def has_commit(self, sha: str) -> bool:
        return self.git("cat-file", "-e", f"{sha}^{{commit}}").returncode == 0

    def is_ancestor(self, base: str, candidate: str) -> bool:
        return self.git("merge-base", "--is-ancestor", base, candidate).returncode == 0

    def changed_paths(self, base: str, candidate: str):
        r = self.git("diff", "--no-ext-diff", "--name-only", base, candidate, "--")
        if r.returncode != 0:
            return None
        return [p for p in r.stdout.split() if p]


def hashlib_digest_ok(path) -> bool:
    """True iff the file's sha256 equals CORPUS_SHA256."""
    return hashlib.sha256(path.read_bytes()).hexdigest() == CORPUS_SHA256


def corpus_pairs(repo: Repo) -> dict[str, tuple[str, str, str]]:
    """case_id -> (base_sha, candidate_sha, source_repository), read from the replay corpus.

    The corpus digest is checked against CORPUS_SHA256 BEFORE anything is parsed out of it:
    without that, the identity rule would be only as strong as an unprotected write.

    Scoped to the `cases:` list on purpose. The first parser kept whatever `case_id` it saw last,
    so the `not_replay_ready:` section further down (which has its own `base_sha:` under a
    `candidate_ref:` entry) OVERWROTE the last real case's pair — the validator caught it and
    refused, which is how it was found. Parsing now stops at the first top-level key after the
    cases list and resets on any list item that is not a `case_id`.
    """
    path = repo.root / CASES_YAML
    if not path.is_file():
        return {}
    if not hashlib_digest_ok(path):
        return {}
    out: dict[str, list[str]] = {}
    current = None
    started = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^cases:\s*$", line):
            started = True
            continue
        if started and re.match(r"^[A-Za-z_]+:", line):     # a later top-level section
            break
        if not started:
            continue
        m = re.match(r"\s*-\s*case_id:\s*(\S+)\s*$", line)
        if m:
            current = m.group(1)
            out.setdefault(current, ["", "", ""])
            continue
        if re.match(r"\s*-\s*\S+:", line):                  # a different list item: stop scoping
            current = None
            continue
        m = re.match(r"\s+base_sha:\s*([0-9a-f]{40})\s*$", line)
        if m and current:
            out[current][0] = m.group(1)
            continue
        m = re.match(r"\s+candidate_sha:\s*([0-9a-f]{40})\s*$", line)
        if m and current:
            out[current][1] = m.group(1)
            continue
        m = re.match(r"\s+source_repository:\s*(\S+)\s*$", line)
        if m and current:
            out[current][2] = m.group(1)
    return {k: (v[0], v[1], v[2] if len(v) > 2 else "")
            for k, v in out.items() if v[0] and v[1]}


def corpus_incomplete_cases(repo: Repo) -> set[str]:
    """Cases the corpus names but for which no complete pair could be parsed.

    Separated from `corpus_pairs` so the diagnosis can say WHICH of the two happened: a case id that
    is absent from the corpus is a different mistake from a case the corpus lists without a pair.
    """
    path = repo.root / CASES_YAML
    if not path.is_file() or not hashlib_digest_ok(path):
        return set()
    named, complete = set(), set()
    current = None
    started = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^cases:\s*$", line):
            started = True
            continue
        if started and re.match(r"^[A-Za-z_]+:", line):
            break
        if not started:
            continue
        m = re.match(r"\s*-\s*case_id:\s*(\S+)\s*$", line)
        if m:
            current = m.group(1)
            named.add(current)
    complete = set(corpus_pairs(repo))
    return named - complete


def check_document(doc, repo: Repo, classification_dir: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["document is not a JSON object"]
    if doc.get("schema") != SCHEMA_ID:
        errors.append(f"schema is {doc.get('schema')!r}, expected {SCHEMA_ID!r}")
    if doc.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version is {doc.get('schema_version')!r}; this validator implements "
                      f"{SCHEMA_VERSION!r} — a record set written against another revision must not "
                      f"be validated by this one")
    records = doc.get("records")
    if not isinstance(records, list) or not records:
        errors.append("`records` is missing or empty")
        return errors

    corpus = corpus_pairs(repo)
    corpus_incomplete = corpus_incomplete_cases(repo)
    if not corpus:
        errors.append(f"the replay corpus could not be read, or its sha256 is not "
                      f"{CORPUS_SHA256[:12]}... at {CASES_YAML} — the corpus is this scheme's "
                      f"identity root and must match the pinned digest, so nothing here can be "
                      f"validated (failing closed)")

    seen: list[str] = []
    seen_cases: list[str] = []
    for rec in records:
        if not isinstance(rec, dict):
            errors.append(f"record {type(rec).__name__} is not an object — a malformed record is "
                          f"an error, not a skip")
            continue
        cid = rec.get("candidate_id")
        key = cid if isinstance(cid, str) and cid else f"<non-string id: {cid!r}>"
        if key in seen:
            errors.append(f"duplicate candidate_id {cid!r}")
        seen.append(key)
        case_key = rec.get("corpus_case_id")
        if isinstance(case_key, str) and case_key:
            if case_key in seen_cases:
                errors.append(f"two records classify the same corpus case {case_key!r} — a case is "
                              f"classified once, so a conflicting pair of records cannot leave one "
                              f"valid request standing next to a rejection")
            seen_cases.append(case_key)
        errors.extend(check_record(rec, repo, classification_dir, corpus, corpus_incomplete))
    return errors


def resolve_evidence(source, classification_dir: Path, repo: Repo):
    """Resolve an evidence citation, SCOPED TO THE REPOSITORY.

    A file outside the repository is not evidence a reviewer can reach from the repository, so
    absolute paths and parent traversal are refused rather than accepted (an earlier version
    accepted `/etc/hosts`).
    """
    if not isinstance(source, str) or not source:
        return None
    root = repo.root.resolve()
    for base in (classification_dir, root):
        candidate = (base / source).resolve()
        if candidate.is_file() and (candidate == root or root in candidate.parents):
            return candidate
    return None


def has_oracle_externalization(pending) -> bool:
    """True iff a pending requirement's CODE is exactly ORACLE_EXTERNALIZATION.

    The exact code matters: a bare `startswith` would accept ORACLE_EXTERNALIZATION_LATER for a
    different obligation, so the code must be followed by a delimiter or end the string.
    """
    for p in pending:
        if not isinstance(p, str) or not p.startswith(PENDING_PREFIX):
            continue
        rest = p[len(PENDING_PREFIX):]
        if rest == "" or rest[0] in (":", " "):
            return True
    return False


def derived_triggers(paths) -> dict[str, list[str]]:
    derived: dict[str, list[str]] = {}
    for p in paths or []:
        if TEST_PATH_RE.search(p):
            derived.setdefault("WORKER_MODIFIES_TEST_ORACLE", []).append(p)
        if VALIDATOR_PATH_RE.search(p):
            derived.setdefault("WORKER_MODIFIES_VALIDATOR", []).append(p)
    return derived


def check_record(rec: dict, repo: Repo, classification_dir: Path,
                 corpus: dict[str, tuple[str, str, str]],
                 corpus_incomplete: set[str] | None = None) -> list[str]:
    cid = rec.get("candidate_id") or "<unnamed record>"
    corpus_incomplete = corpus_incomplete or set()
    err: list[str] = []

    # A malformed field must produce a structured error, not a traceback: this read used to be an
    # unguarded `(rec.get("disclosures") or {}).get(...)`, so a string value raised AttributeError
    # and aborted the whole run with no diagnosis.
    disclosures = rec.get("disclosures")
    if disclosures is None:
        disclosures = {}
    elif not isinstance(disclosures, dict):
        err.append(f"{cid}: disclosures must be an object when present (got "
                   f"{type(disclosures).__name__})")
        disclosures = {}

    for key in REQUIRED_RECORD_KEYS:
        if key not in rec:
            err.append(f"{cid}: missing required key {key!r}")
    for key in ("base_sha", "candidate_sha"):
        value = rec.get(key)
        if not isinstance(value, str) or not SHA_RE.match(value):
            err.append(f"{cid}: {key} is not a 40-hex revision ({value!r})")
    if not isinstance(rec.get("source_repository"), str) or not rec.get("source_repository"):
        err.append(f"{cid}: source_repository must be a non-empty string")

    cls = rec.get("class")
    if cls not in CLASSES:
        # NOTE: do NOT return early — an unknown class used to mask every other defect in the
        # record, which makes a broken record look like a single-error record.
        err.append(f"{cid}: class is {cls!r}; it must be one of {list(CLASSES)} "
                   f"(an unclassified task is an error, never a silent pass)")
    admissible_claim = cls in ADMISSIBLE_CLASSES

    base, cand = rec.get("base_sha"), rec.get("candidate_sha")
    have_pair = (isinstance(base, str) and isinstance(cand, str)
                 and bool(SHA_RE.match(base)) and bool(SHA_RE.match(cand)))

    # --- IDENTITY: the record must name a corpus case, and the pair must be that case's pair ----
    case_id = rec.get("corpus_case_id")
    if not isinstance(case_id, str) or not case_id:
        err.append(f"{cid}: corpus_case_id is required — a record that names no case can assert any "
                   f"class over any revision pair it borrows")
    elif corpus and case_id not in corpus:
        if case_id in corpus_incomplete:
            err.append(f"{cid}: the corpus lists {case_id!r} but binds no complete revision pair "
                       f"to it (a case without a base/candidate pair cannot classify anything)")
        else:
            err.append(f"{cid}: corpus_case_id {case_id!r} is not a case in {CASES_YAML}")
    elif corpus and have_pair:
        want_base, want_cand, want_repo = corpus[case_id]
        if want_repo and rec.get("source_repository") != want_repo:
            err.append(f"{cid}: source_repository is {rec.get('source_repository')!r} while the "
                       f"corpus binds {want_repo!r} to {case_id!r} — identity covers the repository, "
                       f"not only the revisions")
        if (base, cand) != (want_base, want_cand):
            err.append(f"{cid}: the revision pair does not match the corpus case {case_id!r} "
                       f"(corpus binds {want_base[:12]} -> {want_cand[:12]}, record declares "
                       f"{base[:12]} -> {cand[:12]}) — identity is recomputed from the corpus, not "
                       f"taken from the record")

    # --- revision binding ----------------------------------------------------------------------
    binding = rec.get("sha_binding")
    if binding not in SHA_BINDINGS:
        err.append(f"{cid}: sha_binding must be one of {list(SHA_BINDINGS)} (got {binding!r})")
    local_pair = None
    if have_pair:
        local_pair = (repo.has_commit(base), repo.has_commit(cand))
        if local_pair == (True, True):
            if binding != "LOCAL_REPO_VERIFIED":
                err.append(f"{cid}: both revisions resolve in this repository, so sha_binding must "
                           f"be LOCAL_REPO_VERIFIED (got {binding!r})")
            if base == cand:
                err.append(f"{cid}: the pair is degenerate (base == candidate) — a revision is its "
                           f"own ancestor, so an equal pair would otherwise pass the ancestry test "
                           f"while describing no delta at all")
            elif admissible_claim and not repo.is_ancestor(base, cand):
                err.append(f"{cid}: a claim of {cls} requires the candidate to descend from the "
                           f"base, and {cand[:12]} does not descend from {base[:12]} — recomputed "
                           f"from the object database, not read from the record")
        elif True in local_pair:
            err.append(f"{cid}: exactly one of the two revisions resolves here — an inconsistent "
                       f"pair cannot be a basis for classification")
        else:
            if binding != "EXTERNAL_UNVERIFIABLE_LOCALLY":
                err.append(f"{cid}: neither revision resolves in this repository, so sha_binding "
                           f"must be EXTERNAL_UNVERIFIABLE_LOCALLY")
            if not rec.get("external_repository"):
                err.append(f"{cid}: an externally bound record must name external_repository")
            if not rec.get("external_verification"):
                err.append(f"{cid}: an externally bound record must record the external "
                           f"verification command (a claim with no stated verification locus is "
                           f"not evidence)")

    # --- DERIVED TRIGGERS: the delta's own file list, read from the object database -------------
    triggers = rec.get("reject_triggers")
    if not isinstance(triggers, list):
        err.append(f"{cid}: reject_triggers must be a list")
        triggers = []
    declared = set()
    for t in triggers:
        if not isinstance(t, dict):
            err.append(f"{cid}: every reject_triggers entry must be an object")
            continue
        code = t.get("trigger")
        if code not in TRIGGER_CODES:
            err.append(f"{cid}: unknown trigger code {code!r}")
            continue
        declared.add(code)
        if not CODE_RE.match(str(t.get("reason_code", ""))):
            err.append(f"{cid}: trigger {code} needs a reason_code in UPPER_SNAKE form "
                       f"(got {t.get('reason_code')!r})")
        if not isinstance(t.get("detail"), str) or not t.get("detail"):
            err.append(f"{cid}: trigger {code} needs a non-empty detail")

    pending = rec.get("pending_requirements")
    if not isinstance(pending, list):
        err.append(f"{cid}: pending_requirements must be a list")
        pending = []
    for p in pending:
        if not isinstance(p, str) or not p.strip():
            err.append(f"{cid}: every pending requirement must be a non-empty string")
        elif not CODE_RE.match(p.split(":", 1)[0].split(" ", 1)[0]):
            err.append(f"{cid}: pending requirement {p[:40]!r} must begin with an UPPER_SNAKE code")

    externalized = rec.get("externalized_paths") or []
    if externalized and not isinstance(externalized, list):
        err.append(f"{cid}: externalized_paths must be a list when present")
        externalized = []
    for path in externalized:
        if not isinstance(path, str) or not path:
            err.append(f"{cid}: every externalized_paths entry must be a non-empty path")
    if externalized and local_pair == (True, True):
        changed = repo.changed_paths(base, cand) or []
        bogus = [path for path in externalized if path not in changed]
        if bogus:
            err.append(f"{cid}: externalized_paths names {bogus} which the delta does not change — "
                       f"externalising a path the pair never touches asserts nothing")
    if local_pair == (True, True):
        paths = repo.changed_paths(base, cand)
        if paths is None:
            err.append(f"{cid}: the changed-file list of the pair could not be read (failing closed)")
        else:
            for trig, trig_paths in derived_triggers(paths).items():
                # NOTE: this check must run BEFORE the `declared` short-circuit. Placed after
                # it, the rule was dead for every record that declared the trigger — i.e. exactly
                # the shape that carries the contradiction.
                if trig == "WORKER_MODIFIES_VALIDATOR" and \
                        disclosures.get("historical_delta_touched_validator") is False:
                    err.append(f"{cid}: disclosures say the delta did not touch a validator, but "
                               f"the delta provably changes {trig_paths} — the disclosure "
                               f"contradicts the object database")
                # F3 (round 7): the same contradiction on the ORACLE axis was unchecked.
                if trig == "WORKER_MODIFIES_TEST_ORACLE" and \
                        disclosures.get("historical_delta_touched_oracle") is False:
                    err.append(f"{cid}: disclosures say the delta did not touch the test oracle, but "
                               f"the delta provably changes {trig_paths} — the disclosure "
                               f"contradicts the object database")
                if trig in declared:
                    continue
                uncovered = [p for p in trig_paths if p not in externalized]
                if not uncovered and has_oracle_externalization(pending):
                    continue
                err.append(f"{cid}: the delta of this pair changes {uncovered or trig_paths} so "
                           f"{trig} is DERIVED from the git diff — the record must declare it, or "
                           f"list every such path in externalized_paths together with an "
                           f"{PENDING_PREFIX} pending requirement")

    if admissible_claim and triggers:
        err.append(f"{cid}: claims {cls} while carrying {len(triggers)} rejection trigger(s) — "
                   f"a claim of an admissible class must have a clean trigger set")
    if cls == "C_REJECT" and not triggers:
        err.append(f"{cid}: C_REJECT requires at least one enumerated trigger")

    # --- per-class requirements ---------------------------------------------------------------
    req = rec.get("class_requirements")
    if cls == "A_REPAIR":
        if not isinstance(req, dict):
            err.append(f"{cid}: A_REPAIR requires class_requirements")
        else:
            if req.get("baseline_oracle_status") != "FAIL":
                err.append(f"{cid}: A_REPAIR baseline_oracle_status must be 'FAIL' "
                           f"(got {req.get('baseline_oracle_status')!r})")
            if req.get("candidate_oracle_status") != "PASS":
                err.append(f"{cid}: A_REPAIR candidate_oracle_status must be 'PASS' "
                           f"(got {req.get('candidate_oracle_status')!r})")
            if req.get("oracle_in_worker_scope") is not False:
                err.append(f"{cid}: A_REPAIR requires oracle_in_worker_scope false")
            authority = req.get("oracle_authority")
            if authority not in ORACLE_AUTHORITIES:
                err.append(f"{cid}: oracle_authority must be one of {list(ORACLE_AUTHORITIES)} "
                           f"(got {authority!r})")
            if authority == "PENDING_FREEZE_V2" and not has_oracle_externalization(pending):
                err.append(f"{cid}: oracle_authority PENDING_FREEZE_V2 requires a pending "
                           f"requirement whose code is exactly {PENDING_PREFIX!r}")
            if disclosures.get("historical_delta_touched_oracle") is True:
                if authority == "FRAMEWORK_FROZEN":
                    err.append(f"{cid}: oracle_authority cannot be FRAMEWORK_FROZEN while the "
                               f"record discloses that the historical delta touched the oracle")
                if not has_oracle_externalization(pending):
                    err.append(f"{cid}: a touched oracle requires a {PENDING_PREFIX} pending "
                               f"requirement")

    if cls == "B_REGRESSION_GUARD":
        if not isinstance(req, dict):
            err.append(f"{cid}: B_REGRESSION_GUARD requires class_requirements")
        else:
            if req.get("baseline_oracle_status") != "PASS":
                err.append(f"{cid}: B_REGRESSION_GUARD baseline_oracle_status must be 'PASS'")
            if req.get("mutation_oracle_status") != "FAIL":
                err.append(f"{cid}: B_REGRESSION_GUARD mutation_oracle_status must be 'FAIL'")
            for flag in ("mutation_touches_target_predicate", "acceptance_surface_frozen",
                         "validator_not_worker_controlled"):
                if req.get(flag) is not True:
                    err.append(f"{cid}: B_REGRESSION_GUARD requires {flag} true")

    considered = rec.get("class_considered")
    if not isinstance(considered, list) or not considered:
        err.append(f"{cid}: class_considered must be a non-empty list of "
                   f"{{class, verdict}} entries (every record states which classes it was "
                   f"considered under)")
    else:
        for c in considered:
            if not isinstance(c, dict) or c.get("class") not in CLASSES or \
                    not isinstance(c.get("verdict"), str) or not c.get("verdict"):
                err.append(f"{cid}: every class_considered entry needs a known class and a "
                           f"non-empty verdict (got {c!r})")
    if isinstance(considered, list) and cls in ADMISSIBLE_CLASSES:
        own = [c for c in considered if isinstance(c, dict) and c.get("class") == cls]
        if not own:
            err.append(f"{cid}: class_considered does not mention the record's own class {cls!r} — a "
                       f"record that was not considered under the class it claims is not internally "
                       f"consistent")
        else:
            for c in own:
                verdict = str(c.get("verdict", "")).strip()
                if verdict not in AFFIRMATIVE_VERDICTS:
                    err.append(f"{cid}: the class_considered entry for the record's own class {cls!r} "
                               f"reads {verdict!r}, which is not an affirmative claim (allowed: "
                               f"{list(AFFIRMATIVE_VERDICTS)}) — a record cannot request admission "
                               f"under a class it describes as unavailable, and the vocabulary is "
                               f"closed so a synonym cannot stand in for one")
    if cls == "C_REJECT":
        if not isinstance(considered, list) or not considered:
            err.append(f"{cid}: C_REJECT requires class_considered (a task may not be dumped into "
                       f"the reject class without showing which admissible class was blocked)")
        else:
            blocked = [c for c in considered
                       if isinstance(c, dict) and c.get("class") in ADMISSIBLE_CLASSES
                       and c.get("verdict") == "BLOCKED"]
            if not blocked:
                err.append(f"{cid}: C_REJECT requires at least one admissible class listed as "
                           f"BLOCKED in class_considered")
            for c in blocked:
                if not isinstance(c.get("reason"), str) or not c.get("reason").strip():
                    err.append(f"{cid}: the BLOCKED entry for {c.get('class')} needs a reason")

    # --- admission REQUEST (this program never grants) -----------------------------------------
    admission = rec.get("round_admission")
    if not isinstance(admission, dict):
        err.append(f"{cid}: round_admission must be an object")
    else:
        verdict = admission.get("verdict")
        if verdict not in ADMISSION_VERDICTS:
            err.append(f"{cid}: round_admission.verdict must be one of {list(ADMISSION_VERDICTS)}")
        elif verdict == "REQUEST_VALID":
            if not admissible_claim:
                err.append(f"{cid}: only {list(ADMISSIBLE_CLASSES)} may carry a valid request")
            if binding != "LOCAL_REPO_VERIFIED":
                err.append(f"{cid}: a valid request requires a locally verifiable revision pair — "
                           f"an EXTERNAL_UNVERIFIABLE_LOCALLY record can never carry one: the "
                           f"verdict would rest on a fact this repository cannot check, and the "
                           f"derived-trigger rule cannot even run for it")
            if triggers:
                err.append(f"{cid}: a valid request is forbidden while any rejection trigger is set")
            if pending:
                err.append(f"{cid}: a valid request is forbidden while pending requirements remain "
                           f"({len(pending)} open)")
            if isinstance(req, dict):
                authority_now = req.get("oracle_authority")
                if authority_now == "PENDING_FREEZE_V2":
                    err.append(f"{cid}: a valid request is forbidden while oracle_authority is "
                               f"still PENDING_FREEZE_V2")
        elif not isinstance(admission.get("reason_codes"), list) or \
                not admission.get("reason_codes") or \
                not all(isinstance(rc, str) and rc.strip() for rc in admission["reason_codes"]):
            err.append(f"{cid}: NOT_ADMITTED requires reason_codes as a non-empty list of "
                       f"non-empty strings")

    # --- evidence -----------------------------------------------------------------------------
    evidence = rec.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        err.append(f"{cid}: evidence is required (a classification without measured evidence is "
                   f"an opinion)")
    else:
        for i, e in enumerate(evidence):
            if not isinstance(e, dict) or not all(e.get(k) for k in ("claim", "measured", "source")):
                err.append(f"{cid}: evidence[{i}] needs claim + measured + source")
                continue
            sources = e["source"] if isinstance(e["source"], list) else [e["source"]]
            if not sources or not all(isinstance(s, str) and s.strip() for s in sources):
                err.append(f"{cid}: evidence[{i}].source must be a path or a non-empty list of "
                           f"paths")
                continue
            for s in sources:
                if resolve_evidence(s, classification_dir, repo) is None:
                    err.append(f"{cid}: evidence[{i}].source {s!r} does not resolve to an existing "
                               f"file — evidence must be reachable, not asserted")

    return err


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print("usage: check_task_class.py <classification.json> [repo_root]", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"TASK_CLASS_VERDICT = FAIL reason=NO_CLASSIFICATION_FILE path={path}")
        return 1
    repo_root = Path(argv[2]).resolve() if len(argv) == 3 else Path(__file__).resolve().parents[4]
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"TASK_CLASS_VERDICT = FAIL reason=UNREADABLE err={exc}")
        return 1

    repo = Repo(repo_root)
    errors = check_document(doc, repo, path.resolve().parent)

    records = doc.get("records") if isinstance(doc, dict) else []
    records = records if isinstance(records, list) else []
    requests = [r.get("candidate_id") for r in records
                if isinstance(r, dict)
                and isinstance(r.get("round_admission"), dict)
                and r["round_admission"].get("verdict") == "REQUEST_VALID"]
    for rec in records:
        if not isinstance(rec, dict):
            continue
        print(f"  {str(rec.get('candidate_id', '<unnamed>')):44s} class={str(rec.get('class')):20s} "
              f"binding={str(rec.get('sha_binding')):32s} "
              f"triggers={len(rec.get('reject_triggers') or [])} "
              f"request={((rec.get('round_admission') or {}).get('verdict'))}")

    if errors:
        for e in errors:
            print(f"  ERROR {e}")
        print(f"TASK_CLASS_VERDICT = FAIL records={len(records)} errors={len(errors)}")
        return 1
    print(f"TASK_CLASS_VERDICT = PASS records={len(records)} valid_requests={len(requests)} "
          f"rejected={len(records) - len(requests)} errors=0 "
          f"enforcement=IDENTITY+DERIVED_TRIGGERS+REPO_FACTS (a valid request is NOT an admission: "
          f"the grant is the round freeze plus review)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
