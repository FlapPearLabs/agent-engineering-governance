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
  · IDENTITY: a record must name the corpus case it classifies, and its revision pair must EQUAL
    the pair the pinned corpora bind to that case (`experiments/v1.2/replay/cases.yaml` and, since
    2.8.2, `h2-lazy-disclosure/admission/corpus.yaml`; one case id per union). Without this, a record
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
  · the record's CLASS is bound to nothing recomputable BY IDENTITY — it is now bound by
    EXECUTION instead: the class claim is a state-transition claim, and the transition is
    recomputed by running the candidate revision's own acceptance surfaces against materialised
    base and candidate trees. The corpus's own measured dispositions are still not consulted;
  · the oracle-rewrite triggers fire on paths the delta REWRITES, not on paths it ADDS. An added
    acceptance cannot neuter an existing oracle, and is instead held to the recomputed transition
    (it must fail against the unfixed base) with its provenance disclosed and bound.

A PASS therefore means "internally consistent AND consistent with every fact this repository can
recompute". It is not a statement that the work happened.

Usage:  python3 check_task_class.py <classification.json> [repo_root]
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMA_ID = "ELIGIBILITY_SCHEMA_V2"
SCHEMA_VERSION = "2.8.3"
# The identity rule reads the replay corpora (below), and nothing else in this repository pins
# them: they are in no freeze hash and no other test checks their SHA values. A trust
# root anyone can rewrite is not a trust root, so its digest is pinned HERE as a literal,
# exactly as the material tests pin the freeze hashes — editing the corpus without updating
# this constant (and the test that asserts it) fails the validator, in review.
CORPUS_SHA256 = "5d898b1a6db8fb16116a3cbec58c7078d780e379dd58d6d54553645291cda731"
# Candidate Admission's anchors live in their OWN corpus, pinned the same way. They used to be
# appended to replay/cases.yaml, which is also H3's replay input: H3's loader then counted 24
# unreviewed H2 anchors as detector cases (fresh review of 4add2ca, finding 4). The identity root is
# the union of the two files; a case id may appear in only one of them.
H2_CORPUS = "experiments/v1.2/h2-lazy-disclosure/admission/corpus.yaml"
H2_CORPUS_SHA256 = "3c69a9d9eaa13fa43d87387a88d8840959ca6baa97f46ba748ec9da656151d5b"
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
ORACLE_AUTHORITIES = ("FRAMEWORK_FROZEN", "PENDING_FREEZE_V2",
                      "DELTA_AUTHORED_DISCRIMINATING")
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
CORPORA = ((CASES_YAML, "CORPUS_SHA256"), (H2_CORPUS, "H2_CORPUS_SHA256"))
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
        found = self.changed_paths_with_status(base, candidate)
        return None if found is None else [p for _, p in found]

    def changed_paths_with_status(self, base: str, candidate: str):
        """[(status, path)] for the pair; status is git's A / M / D / T / R / C.

        Read with `-z`: without it git QUOTES a non-ASCII path ("scripts/validate_\\346...py"),
        which matches no name rule, so a rewritten non-ASCII validator derived no trigger (fresh
        review of f2c48a0, finding 5 — the same class as F-A1c). A rename/copy entry carries two
        paths; the NEW one is reported, as before.
        """
        r = self.git("diff", "--no-ext-diff", "--name-status", "-z", base, candidate, "--")
        if r.returncode != 0:
            return None
        fields = r.stdout.split("\0")
        out, i = [], 0
        while i < len(fields) and fields[i]:
            status = fields[i]
            width = 2 if status[:1] in ("R", "C") else 1
            if i + width >= len(fields):
                return None                      # truncated record: fail closed
            out.append((status, fields[i + width]))
            i += 1 + width
        return out


def hashlib_digest_ok(path, constant: str = "CORPUS_SHA256") -> bool:
    """True iff the file's sha256 equals the pinned literal named by `constant` (read at call time,
    so a test that patches the module constant is honoured)."""
    return hashlib.sha256(path.read_bytes()).hexdigest() == globals()[constant]


def _parse_corpus(path: Path) -> tuple[dict[str, list[str]], set[str]]:
    """(case_id -> [base, candidate, repository], every case id named) for one corpus file.

    Scoped to the `cases:` list on purpose. The first parser kept whatever `case_id` it saw last,
    so the `not_replay_ready:` section further down (which has its own `base_sha:` under a
    `candidate_ref:` entry) OVERWROTE the last real case's pair — the validator caught it and
    refused, which is how it was found. Parsing stops at the first top-level key after the cases
    list and resets on any list item that is not a `case_id`.
    """
    out: dict[str, list[str]] = {}
    named: set[str] = set()
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
            named.add(current)
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
    return out, named


def _read_corpora(repo: Repo):
    """Parse every pinned corpus, or None when any is missing, off its pin, or two corpora name
    the same case (a duplicate id would let one file shadow the other's pair). Digests are checked
    BEFORE anything is parsed: without that the identity rule is only as strong as an unprotected
    write."""
    merged: dict[str, list[str]] = {}
    named: set[str] = set()
    for rel, constant in CORPORA:
        path = repo.root / rel
        if not path.is_file() or not hashlib_digest_ok(path, constant):
            return None
        pairs, ids = _parse_corpus(path)
        if ids & named:
            return None
        merged.update(pairs)
        named |= ids
    return merged, named


def corpus_pairs(repo: Repo) -> dict[str, tuple[str, str, str]]:
    """case_id -> (base_sha, candidate_sha, source_repository), read from the pinned corpora."""
    read = _read_corpora(repo)
    if read is None:
        return {}
    return {k: (v[0], v[1], v[2]) for k, v in read[0].items() if v[0] and v[1]}


def corpus_incomplete_cases(repo: Repo) -> set[str]:
    """Cases a corpus names but for which no complete pair could be parsed.

    Separated from `corpus_pairs` so the diagnosis can say WHICH of the two happened: a case id that
    is absent from the corpus is a different mistake from a case the corpus lists without a pair.
    """
    read = _read_corpora(repo)
    if read is None:
        return set()
    return read[1] - set(corpus_pairs(repo))


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
        errors.append(f"the replay corpora could not be read, a sha256 is off its pinned "
                      f"literal ({CASES_YAML}, {H2_CORPUS}), or two corpora name one case — the "
                      f"corpora are this scheme's identity root, so nothing here can be "
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


def derived_triggers(changed) -> dict[str, list[str]]:
    """Oracle-rewrite triggers, derived from the delta's own file list WITH status.

    Precision matters here, and the imprecise version was found by the positive control: a delta
    that ADDS an acceptance cannot neuter an oracle that already existed, so firing
    WORKER_MODIFIES_TEST_ORACLE / WORKER_MODIFIES_VALIDATOR on it made every real repair task
    unsatisfiable while protecting nothing. The triggers therefore fire on paths the delta
    REWRITES (present at the base, changed by the pair). A newly ADDED oracle is not free either:
    the recomputed transition must show it failing against the unfixed base, its provenance is
    disclosed, and `oracle_in_worker_scope` is bound to that recomputation.
    """
    derived: dict[str, list[str]] = {}
    for status, p in changed or []:
        if status in ("A", "D"):
            continue                 # an added path rewrites nothing; a deleted one judges nothing
        if TEST_PATH_RE.search(p):
            derived.setdefault("WORKER_MODIFIES_TEST_ORACLE", []).append(p)
        if VALIDATOR_PATH_RE.search(p):
            derived.setdefault("WORKER_MODIFIES_VALIDATOR", []).append(p)
    return derived


# ---- TRANSITION RECOMPUTATION -------------------------------------------------------------------
# A class claim asserts a STATE TRANSITION, so the transition is RECOMPUTED BY EXECUTION and never
# taken from the record. The acceptance is the CANDIDATE revision's own acceptance surface,
# discovered from that tree by the repository's own path conventions, and it is held byte-pinned
# while it is run against BOTH revisions — so a BASE verdict cannot be produced by editing the
# acceptance between the two runs. Its provenance is recomputed from the object database:
#
#   DELTA_FROZEN    the path exists at both revisions with identical bytes
#   DELTA_ADDED     the delta introduces the path
#   DELTA_MODIFIED  the delta rewrites the path
#
# A DELTA_MODIFIED acceptance is NEVER a basis for an admissible class: the delta rewrote the very
# thing that is supposed to judge it, which is the single shape a vacuity attack always takes (the
# measured `select = []` attack on r03 is exactly this shape). A DELTA_ADDED acceptance cannot
# neuter an oracle that already existed, and a DELTA_FROZEN one is attributable by construction;
# both may serve, and each is reported as what it is. `oracle_in_worker_scope` is BOUND to this
# recomputation instead of being believed on its own.
#
# Verdicts are process exit codes obtained from materialised trees. A missing or timed-out
# acceptance is NOT a pass; an uncomputable transition supports no admissible claim.

ACCEPTANCE_KINDS = ("VALIDATOR", "TEST")
ACCEPTANCE_TIMEOUT = 300
# A verdict exists only when a process produced one. 124 is a timeout inside run_acceptance and 127
# is "the surface is not there"; neither is evidence about the deliverable, and treating either as a
# failure would let an unrunnable acceptance manufacture the FAIL_TO_PASS shape.
UNMEASURED_RCS = (124, 127)


def acceptance_surfaces(root: Path) -> dict[str, str]:
    """The repository's own acceptance surfaces, discovered from a tree by path convention."""
    out: dict[str, str] = {}
    scripts = root / "scripts"
    if scripts.is_dir():
        for q in sorted(scripts.glob("validate_*.py")):
            out[q.relative_to(root).as_posix()] = "VALIDATOR"
    tests = scripts / "tests"
    if tests.is_dir():
        for q in sorted(tests.glob("test_*.py")):
            out[q.relative_to(root).as_posix()] = "TEST"
    return out


def acceptance_command(rel: str, kind: str, interpreter: str) -> list[str]:
    if kind == "TEST":
        return [interpreter, "-m", "unittest", "discover", "-s", "scripts/tests",
                "-p", Path(rel).name]
    return [interpreter, rel]


def run_acceptance(tree: Path, rel: str, kind: str, interpreter: str) -> int:
    """Exit code of one acceptance surface run inside a materialised tree."""
    if not (tree / rel).is_file():
        return 127                       # absent is unrunnable, and unrunnable is not a pass
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        r = subprocess.run(acceptance_command(rel, kind, interpreter), cwd=str(tree),
                           capture_output=True, text=True, env=env,
                           timeout=ACCEPTANCE_TIMEOUT)
        return r.returncode
    except (subprocess.TimeoutExpired, OSError):
        return 124                       # a timeout is not a pass either


def _worktree_add(repo: Repo, sha: str, path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    return repo.git("worktree", "add", "-q", "--detach", str(path), sha).returncode == 0


def _worktree_remove(repo: Repo, path: Path) -> None:
    repo.git("worktree", "remove", "--force", str(path))


def _materialise_mutation(repo: Repo, cand: str, mut_wt: Path, added_paths: list[str]) -> bool:
    """Turn the candidate worktree `mut_wt` into the controlled mutation, as a REVISION.

    The mutation is the candidate's own commit object with exactly one byte range changed: the
    `tree` header. Parents (so the parent count and HEAD^ — a merge stays a merge), author,
    committer, dates, any signature header and the message bytes are the candidate's, verbatim, so
    a surface that reads HEAD sees what it saw at the candidate. History of this rule, each step
    measured on a real pair:
      F-A1   unlinked files left in git's index -> index-reading surfaces crashed (0007bb3)
      F-A1b  a commit under a synthetic identity -> the HEAD-identity check failed everywhere
      F-A4   `git commit` on top of the candidate -> new parent, merges stopped being merges, and
             the HEAD-identity check failed on PR merge 6217cc0 (fresh review of 4add2ca)
      F-A5   `git rm <path>` reads a path as a glob, so `docs/[ab].md` also removed docs/a.md
    Postconditions (fail closed): clean tree, parents identical to the candidate's, and
    `git diff <cand> HEAD` is exactly one deletion per added path and nothing else.
    """
    mut = Repo(mut_wt)
    quiet = ("-c", "core.hooksPath=/dev/null")
    if mut.git(*quiet, "--literal-pathspecs", "rm", "-q", "--", *added_paths).returncode != 0:
        return False
    tree = mut.git("write-tree")
    raw = subprocess.run(["git", "-C", str(repo.root), "cat-file", "commit", cand],
                         capture_output=True)
    if tree.returncode != 0 or raw.returncode != 0 or not raw.stdout.startswith(b"tree "):
        return False
    header, _, rest = raw.stdout.partition(b"\n")
    obj = b"tree " + tree.stdout.strip().encode() + b"\n" + rest
    written = subprocess.run(["git", "-C", str(mut_wt), "hash-object", "-t", "commit", "-w",
                              "--stdin"], input=obj, capture_output=True)
    if written.returncode != 0:
        return False
    sha = written.stdout.decode().strip()
    if mut.git(*quiet, "update-ref", "--no-deref", "HEAD", sha).returncode != 0:
        return False
    parents = [mut.git("rev-parse", f"{rev}^@").stdout.split() for rev in (cand, "HEAD")]
    delta = mut.git("diff", "--no-ext-diff", "--no-renames", "--name-status", "-z", cand, "HEAD",
                    "--").stdout.split("\0")
    pairs = sorted(zip(delta[0::2], delta[1::2]))
    return (not mut.git("status", "--porcelain").stdout.strip()
            and parents[0] == parents[1]
            and pairs == sorted(("D", p) for p in added_paths))


def recompute_transition(repo: Repo, base: str, cand: str, cls: str) -> dict:
    """Recompute the pair's acceptance state transition by execution, for one class.

    Returns the facts the class rules read — including the lifecycle statuses the record declares,
    so the declaration is checked against a measurement instead of against itself. A missing,
    unrunnable, timed-out or uncomputable acceptance is never a pass.
    """
    inside = repo.git("rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return {"error": "NOT_A_WORKTREE"}
    interpreter = sys.executable or "python3"
    scratch = Path(tempfile.mkdtemp(prefix="h2-transition-"))
    base_wt, cand_wt, mut_wt = scratch / "base", scratch / "cand", scratch / "mut"
    facts: dict = {"base": base, "candidate": cand, "class": cls, "surfaces": []}
    try:
        for sha, wt in ((base, base_wt), (cand, cand_wt), (cand, mut_wt)):
            if not _worktree_add(repo, sha, wt):
                return {"error": "WORKTREE_MATERIALISATION_FAILED", "sha": sha}
        # the controlled mutation: the candidate tree with every path the delta ADDS removed.
        # Modified paths keep their candidate content on purpose — reverting them wholesale would
        # rebuild the base tree and make the mutation a no-op by construction.
        # The mutation is a coherent REVISION (index, tree and HEAD agree), not files unlinked under
        # an index that still lists them: an acceptance that enumerates `git ls-files` crashes on
        # such a tree, and that crash was counted as a bite (admission finding F-A1, measured on
        # 0007bb3). `-z` keeps paths raw — the quoted form of a non-ASCII path names no file, so
        # it used to be skipped silently and the mutation kept the very file it claimed to remove.
        added = repo.git("diff", "--no-ext-diff", "--name-only", "-z", "--diff-filter=A",
                         base, cand, "--")
        if added.returncode != 0:
            return {"error": "DELTA_UNREADABLE"}
        added_paths = [p for p in added.stdout.split("\0") if p]
        if added_paths and not _materialise_mutation(repo, cand, mut_wt, added_paths):
            return {"error": "MUTATION_MATERIALISATION_FAILED"}

        for rel, kind in acceptance_surfaces(cand_wt).items():
            cb, cc = base_wt / rel, cand_wt / rel
            if not cb.is_file():
                provenance = "DELTA_ADDED"
            elif cb.read_bytes() == cc.read_bytes():
                provenance = "DELTA_FROZEN"
            else:
                provenance = "DELTA_MODIFIED"
            rc_cand = run_acceptance(cand_wt, rel, kind, interpreter)
            rc_mut = (run_acceptance(mut_wt, rel, kind, interpreter)
                      if provenance == "DELTA_FROZEN" else None)
            # the candidate's own bytes are carried into the base tree, held identical
            saved = cb.read_bytes() if cb.is_file() else None
            cb.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(cc, cb)
                rc_base = run_acceptance(base_wt, rel, kind, interpreter)
            finally:
                if saved is None:
                    cb.unlink(missing_ok=True)
                else:
                    cb.write_bytes(saved)
            facts["surfaces"].append({"path": rel, "kind": kind, "provenance": provenance,
                                      "rc_base": rc_base, "rc_cand": rc_cand, "rc_mut": rc_mut})

        # Acceptance surfaces the delta DELETES are not in the candidate tree, so the loop above
        # never saw them — and derived_triggers() skips a deleted path. Deleting a green guard (or
        # deleting it and re-adding a weaker copy elsewhere) was therefore invisible to the
        # regression rule (fresh review of f2c48a0, finding 2; real case r29 / 5205e5b). Each one
        # is run with its BASE bytes against the base tree and, carried in, the candidate tree.
        cand_set = set(acceptance_surfaces(cand_wt))
        facts["deleted_surfaces"] = []
        for rel, kind in acceptance_surfaces(base_wt).items():
            if rel in cand_set:
                continue
            rc_base = run_acceptance(base_wt, rel, kind, interpreter)
            target = cand_wt / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(base_wt / rel, target)
            try:
                rc_cand = run_acceptance(cand_wt, rel, kind, interpreter)
            finally:
                target.unlink(missing_ok=True)
            facts["deleted_surfaces"].append({"path": rel, "kind": kind,
                                              "provenance": "DELTA_DELETED",
                                              "rc_base": rc_base, "rc_cand": rc_cand,
                                              "rc_mut": None})

        surfaces = facts["surfaces"]
        eligible = [e for e in surfaces if e["provenance"] != "DELTA_MODIFIED"]
        frozen = [e for e in surfaces if e["provenance"] == "DELTA_FROZEN"]
        facts["acceptance_count"] = len(surfaces)
        facts["frozen_count"] = len(frozen)
        facts["acceptance_surface_frozen"] = bool(frozen)
        facts["oracle_in_worker_scope"] = any(e["provenance"] != "DELTA_FROZEN"
                                              for e in surfaces)
        # A basis is an acceptance the class can stand on, i.e. one whose verdict MOVES in the
        # direction the class claims. A surface that fails identically at both revisions is not
        # evidence of anything (it is broken, in this environment, for both), so it can neither
        # support nor sink a claim.
        def measured(*rcs):
            return all(rc is not None and rc not in UNMEASURED_RCS for rc in rcs)

        unmeasured = [e for e in surfaces
                      if not measured(e["rc_base"], e["rc_cand"])
                      or (e["provenance"] == "DELTA_FROZEN" and not measured(e["rc_mut"]))]
        discriminating = [e for e in eligible
                          if measured(e["rc_base"], e["rc_cand"])
                          and e["rc_base"] != 0 and e["rc_cand"] == 0]
        # A guard bites only a state it PROTECTS: green at the base AND at the candidate, red under
        # a mutation that differs from the candidate. Without the candidate leg, a frozen surface
        # the candidate itself broke counted as a bite — and with no added path the "mutation" IS
        # the candidate (admission finding F-A3, measured on 825d390: t09 0/1/1 read as a bite).
        biting = ([e for e in frozen
                   if measured(e["rc_base"], e["rc_cand"], e["rc_mut"])
                   and e["rc_base"] == 0 and e["rc_cand"] == 0 and e["rc_mut"] != 0]
                  if added_paths else [])
        green_frozen = [e for e in frozen if measured(e["rc_base"]) and e["rc_base"] == 0]
        # A frozen surface the candidate turns from green to red is a REGRESSION the candidate
        # introduced. A regression-guard task protects a correct state, so a candidate that breaks
        # any frozen guard — biting one or not — cannot be one (F-A6, fresh review of 4add2ca:
        # r26 / 95667e8 breaks t09 0/1/1 while a link guard bit).
        guards = frozen + facts["deleted_surfaces"]
        regressed = [e for e in guards if measured(e["rc_base"], e["rc_cand"])
                     and e["rc_base"] == 0 and e["rc_cand"] != 0]
        # a base-green guard whose candidate verdict could not be measured (timeout / absent) is
        # not a pass: B fails closed on it (fresh review of f2c48a0, finding 1)
        guard_unmeasured = [e for e in guards if measured(e["rc_base"]) and e["rc_base"] == 0
                            and not measured(e["rc_cand"])]
        facts["guard_unmeasured"] = guard_unmeasured
        facts["unmeasured"] = unmeasured
        facts["discriminating"] = discriminating
        facts["biting"] = biting
        facts["regressed"] = regressed
        if cls == "B_REGRESSION_GUARD":
            facts["baseline_oracle_status"] = "PASS" if green_frozen else "FAIL"
            facts["mutation_oracle_status"] = "FAIL" if biting else "PASS"
            facts["mutation_touches_target_predicate"] = bool(biting)
            # FAIL iff the candidate regressed a frozen guard; a surface red at both revisions in
            # this environment says nothing about the candidate (it made every B record "FAIL").
            # N2.1 P3-A still holds: an unmeasured rc (124/127) is not a FAIL.
            facts["candidate_oracle_status"] = (
                "FAIL" if regressed
                else "UNMEASURED" if guard_unmeasured
                else "PASS")
        else:
            facts["baseline_oracle_status"] = "FAIL" if discriminating else "PASS"
            facts["candidate_oracle_status"] = "PASS" if discriminating else "FAIL"
            facts["mutation_oracle_status"] = "FAIL" if biting else "PASS"
            facts["mutation_touches_target_predicate"] = bool(biting)
        return facts
    finally:
        for wt in (base_wt, cand_wt, mut_wt):
            _worktree_remove(repo, wt)
        repo.git("worktree", "prune")
        shutil.rmtree(scratch, ignore_errors=True)


def transition_verdict(cls: str, facts: dict) -> tuple[bool, str]:
    """(is the class claim supported, the reason token). Empty extension is a refusal."""
    if "error" in facts:
        return False, facts["error"]
    if not facts.get("acceptance_count"):
        return False, "NO_ACCEPTANCE"
    if facts.get("unmeasured") and not (facts.get("discriminating") or facts.get("biting")):
        return False, "ACCEPTANCE_NOT_MEASURED"
    if cls == "A_REPAIR":
        if facts["discriminating"]:
            return True, "FAIL_TO_PASS"
        moved = [e for e in facts["surfaces"]
                 if (e["rc_base"], e["rc_cand"]) not in ((124, 124), (127, 127))
                 and e["rc_base"] != e["rc_cand"]
                 and 124 not in (e["rc_base"], e["rc_cand"])
                 and 127 not in (e["rc_base"], e["rc_cand"])]
        if not moved:
            return False, "BASE_EQUALS_CANDIDATE"
        return False, "NO_DISCRIMINATING_ACCEPTANCE"
    if cls == "B_REGRESSION_GUARD":
        if not facts["frozen_count"]:
            return False, "NO_FROZEN_ACCEPTANCE"
        if facts.get("regressed"):
            return False, "CANDIDATE_REGRESSES_A_FROZEN_GUARD"
        if facts.get("guard_unmeasured"):
            return False, "CANDIDATE_GUARD_UNMEASURED"
        if not facts["biting"]:
            return False, "MUTATION_DOES_NOT_BITE"
        return True, "PASS_TO_FAIL_UNDER_MUTATION"
    return False, "NOT_AN_ADMISSIBLE_CLASS"


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
    # Type the VALUES the cross-checks read. Those checks compare with `is False`, so a falsey
    # non-boolean ("false", "no", 0, [], "") silently disabled them: a record could assert a
    # disclosure the object database disproves and still validate.
    for _key in ("historical_delta_touched_oracle", "historical_delta_touched_validator"):
        if _key in disclosures and not isinstance(disclosures[_key], bool):
            err.append(f"{cid}: disclosures.{_key} must be a boolean when present (got "
                       f"{type(disclosures[_key]).__name__}: {disclosures[_key]!r}) — a falsey "
                       f"non-boolean would silently disable the cross-check that reads it")

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
            err.append(f"{cid}: corpus_case_id {case_id!r} is not a case in {CASES_YAML} or {H2_CORPUS}")
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
        changed = repo.changed_paths_with_status(base, cand)
        paths = [p for _, p in changed] if changed is not None else None
        if paths is None:
            err.append(f"{cid}: the changed-file list of the pair could not be read (failing closed)")
        else:
            for trig, trig_paths in derived_triggers(changed).items():
                # NOTE: this check must run BEFORE the `declared` short-circuit. Placed after
                # it, the rule was dead for every record that declared the trigger — i.e. exactly
                # the shape that carries the contradiction.
                if trig == "WORKER_MODIFIES_VALIDATOR" and \
                        disclosures.get("historical_delta_touched_validator") is False:
                    err.append(f"{cid}: disclosures say the delta did not touch a validator, but "
                               f"the delta provably rewrites {trig_paths} — the disclosure "
                               f"contradicts the object database")
                # F3 (round 7): the same contradiction on the ORACLE axis was unchecked.
                if trig == "WORKER_MODIFIES_TEST_ORACLE" and \
                        disclosures.get("historical_delta_touched_oracle") is False:
                    err.append(f"{cid}: disclosures say the delta did not touch the test oracle, but "
                               f"the delta provably rewrites {trig_paths} — the disclosure "
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
            # The lifecycle statuses are no longer asserted here: they are BOUND to the
            # recomputed transition further down (declared value must equal the measured one).
            # Asserting them from the record was the shape that masked the measurement, and it is
            # precisely what "no declared field may substitute the mechanical fact" excludes.
            for key in ("baseline_oracle_status", "candidate_oracle_status"):
                if req.get(key) not in ("FAIL", "PASS"):
                    err.append(f"{cid}: {key} must be 'FAIL' or 'PASS' (got {req.get(key)!r})")
            # `oracle_in_worker_scope` is no longer believed on its own. It must EQUAL the
            # provenance recomputed from the delta (below), where any acceptance the delta
            # introduced or rewrote makes the oracle worker-scoped. The old "must be false" could
            # only ever be satisfied by a self-declaration, which is the shape that was shown not
            # to bind anything; a DELTA_MODIFIED acceptance is now excluded from being a basis at
            # all, and a DELTA_ADDED one is declared as such and carries the trigger it implies.
            if not isinstance(req.get("oracle_in_worker_scope"), bool):
                err.append(f"{cid}: A_REPAIR requires oracle_in_worker_scope as a boolean "
                           f"(got {req.get('oracle_in_worker_scope')!r})")
            authority = req.get("oracle_authority")
            if authority not in ORACLE_AUTHORITIES:
                err.append(f"{cid}: oracle_authority must be one of {list(ORACLE_AUTHORITIES)} "
                           f"(got {authority!r})")
            if authority == "PENDING_FREEZE_V2" and not has_oracle_externalization(pending):
                err.append(f"{cid}: oracle_authority PENDING_FREEZE_V2 requires a pending "
                           f"requirement whose code is exactly {PENDING_PREFIX!r}")
            # DELTA_AUTHORED_DISCRIMINATING is not believed either: it is only accepted when
            # the recomputed basis is a DELTA_ADDED acceptance that demonstrably FAILS against the
            # unfixed base. That binding is applied with the transition below.
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
            # closed vocabulary for an optional declared status: "UNMEASURED" is a recomputed value
            # a declaration must never be able to equal (fresh review of 4add2ca, finding 3)
            if "candidate_oracle_status" in req and \
                    req.get("candidate_oracle_status") not in ("PASS", "FAIL"):
                err.append(f"{cid}: candidate_oracle_status must be 'PASS' or 'FAIL' when "
                           f"declared (got {req.get('candidate_oracle_status')!r})")

    # --- RECOMPUTED STATE TRANSITION (the class claim is a claim about a transition) -----------
    # Runs only for an admissible claim over a locally resolvable pair whose record is otherwise
    # well formed: a record already carrying errors is refused on those, and running three trees
    # of acceptances for it would change no verdict. Everything here READS: the declared statuses
    # are bound to recomputed values, and the verdict comes from transition_verdict().
    if cls in ADMISSIBLE_CLASSES and local_pair == (True, True) and not err:
        facts = recompute_transition(repo, base, cand, cls)
        ok, reason = transition_verdict(cls, facts)
        declared = req if isinstance(req, dict) else {}
        if "error" not in facts:
            for key in ("baseline_oracle_status", "candidate_oracle_status"):
                if key in declared and declared.get(key) != facts[key]:
                    err.append(f"{cid}: declared {key}={declared.get(key)!r} but the acceptance "
                               f"recomputed {facts[key]!r} over {facts['acceptance_count']} "
                               f"surface(s) at {base[:12]} and {cand[:12]}")
            for key, actual in (("oracle_in_worker_scope", facts["oracle_in_worker_scope"]),
                                ("acceptance_surface_frozen", facts["acceptance_surface_frozen"]),
                                ("mutation_oracle_status", facts["mutation_oracle_status"]),
                                ("mutation_touches_target_predicate",
                                 facts["mutation_touches_target_predicate"]),
                                # a validator the delta introduced or rewrote is worker-controlled
                                # by construction, so the flag stops being a free declaration
                                ("validator_not_worker_controlled",
                                 not any(e["provenance"] != "DELTA_FROZEN"
                                         for e in facts["surfaces"] if e["kind"] == "VALIDATOR"))):
                if key in declared and declared.get(key) != actual:
                    err.append(f"{cid}: declared {key}={declared.get(key)!r} but the "
                               f"recomputation gives {actual!r}")
            basis = (facts.get("discriminating") or [None])[0]
            if basis is not None and cls == "A_REPAIR":
                want = ("FRAMEWORK_FROZEN" if basis["provenance"] == "DELTA_FROZEN"
                        else "DELTA_AUTHORED_DISCRIMINATING")
                if declared.get("oracle_authority") != want:
                    err.append(f"{cid}: the accepted basis is {basis['path']} "
                               f"[{basis['provenance']}], so oracle_authority must be {want!r} "
                               f"(got {declared.get('oracle_authority')!r}) — the authority is "
                               f"derived from the acceptance provenance, not chosen")
        if not ok:
            detail = "; ".join(
                f"{e['path']} [{e['provenance']}] base={e['rc_base']} cand={e['rc_cand']}"
                for e in facts.get("surfaces", [])[:4]) or "no acceptance surface"
            err.append(f"{cid}: the {cls} state transition is not supported by execution "
                       f"({reason}) — recomputed, not read from the record: {detail}")
        else:
            candidates = ([e for e in facts["discriminating"]
                           if e["provenance"] in ("DELTA_FROZEN", "DELTA_ADDED")]
                          if cls == "A_REPAIR" else list(facts.get("biting") or []))
            if candidates:
                best = candidates[0]
                print(f"  TRANSITION {cid} class={cls} verdict={reason} basis={best['path']} "
                      f"provenance={best['provenance']} base_rc={best['rc_base']} "
                      f"cand_rc={best['rc_cand']} mut_rc={best.get('rc_mut')}")
            else:                                   # supported, yet no basis to name: impossible
                err.append(f"{cid}: the {cls} claim is reported as {reason} with no basis surface — "
                           f"refusing rather than reporting a transition nothing carried")

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
                if verdict == "SHAPE_SATISFIED_PENDING_MATERIALISATION" and not pending:
                    err.append(f"{cid}: the class_considered verdict says the shape is "
                               f"PENDING_MATERIALISATION while pending_requirements is empty — a "
                               f"record cannot describe its class as unmaterialised and list "
                               f"nothing outstanding")
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
