"""Material-integrity checks for the V1.2 mechanization-gap analysis slice.

SCOPE (deliberately narrow, same discipline as `test_material.py` and
`test_h1_material.py`): verify the N6 ARTIFACTS are internally consistent and
that their self-declared boundaries are the boundaries they actually keep.

What is checked here is *material integrity* and *boundary honesty* only. NOT
checked, on purpose:

  * no assertion about whether the analysis is *correct* — whether a rule really
    can move to a mechanical gate is a judgement for review, not for a test.
  * no quota on how many rules must be classified a particular way. The
    distribution is a finding of this round, not a target.
  * no assertion that any proposed mechanism is implemented. This slice
    explicitly does NOT implement anything (`NO_IMPLEMENTATION` below).

Kept (real integrity):

  * every rule id is unique, well-formed, and contiguous;
  * the inventory and the migration matrix cover EXACTLY the same rule set
    (a rule that exists in one and not the other is a dropped obligation);
  * every target-layer value is inside the declared seven-value vocabulary;
  * every HOT-removal candidate carries a replacement argument, and no rule is
    marked removable-now without one (MECHANIZATION_MUST_REPLACE);
  * every external claim carries an evidence-level marker, and the OpenAI
    material is not silently promoted to a first-hand source;
  * tree-ledger node ids are unique and the declared total matches the tree;
  * the branch's COMMITTED change set stays inside `experiments/v1.2/`;
  * the referenced local paths in the new documents resolve.

Stdlib only. Run with:
    python3 -m unittest discover -s experiments/v1.2/tests -v
"""
from __future__ import annotations

from collections import Counter
import re
import subprocess
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
V12 = ROOT / "experiments" / "v1.2"
GAP = V12 / "mechanization-gap"

TREE_LEDGER = V12 / "TREE_LEDGER.md"
README = GAP / "README.md"
INVENTORY = GAP / "rule-inventory.md"
LONGHORIZON = GAP / "longhorizon-mechanism-map.md"
FAILURES = GAP / "failure-mechanism-map.md"
MATRIX = GAP / "rule-migration-matrix.md"
PROTOCOLS = GAP / "experiment-protocols.md"

DECLARED_ARTIFACTS = (
    TREE_LEDGER,
    README,
    INVENTORY,
    LONGHORIZON,
    FAILURES,
    MATRIX,
    PROTOCOLS,
)

RULE_ID_RE = re.compile(r"R-V12-(\d{3})")
TARGET_LAYERS = {"A", "B", "C", "D", "E", "F", "G"}
EVIDENCE_LEVELS = {
    "E3_LOCAL_REPRODUCIBLE",
    "E2_LOCAL_SINGLE",
    "E1_LOCAL_ATTESTED",
    "HYPOTHESIS_NO_LOCAL",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestArtifactsExist(unittest.TestCase):
    def test_every_declared_artifact_exists(self):
        for path in DECLARED_ARTIFACTS:
            with self.subTest(artifact=str(path.relative_to(ROOT))):
                self.assertTrue(path.is_file(), f"missing artifact: {path}")


class TestRuleIdsAreWellFormedAndUnique(unittest.TestCase):
    """A duplicated or malformed rule id silently merges two obligations into one."""

    def setUp(self):
        self.text = _read(INVENTORY)
        self.numbers = [int(m.group(1)) for m in RULE_ID_RE.finditer(self.text)]

    def test_ids_are_contiguous_from_one(self):
        unique = sorted(set(self.numbers))
        self.assertEqual([], [n for n in unique if n < 1 or n > 999])
        self.assertEqual(
            list(range(1, max(unique) + 1)),
            unique,
            "rule ids must be contiguous; a gap means a rule was dropped",
        )

    def test_declared_total_matches_the_id_space(self):
        unique = sorted(set(self.numbers))
        self.assertIn(
            f"CURRENT_RULE_COUNT        = {len(unique)}",
            self.text,
            "the inventory must declare the rule count it actually contains",
        )


class TestInventoryAndMatrixCoverTheSameRules(unittest.TestCase):
    """Every inventoried rule must be classified, and vice versa.

    A rule present in the inventory but absent from the matrix is an
    un-dispositioned obligation; a rule in the matrix that was never
    inventoried is an ungrounded claim.
    """

    def test_rule_sets_are_identical(self):
        inv = {int(m.group(1)) for m in RULE_ID_RE.finditer(_read(INVENTORY))}
        mat = {int(m.group(1)) for m in RULE_ID_RE.finditer(_read(MATRIX))}
        self.assertEqual(
            sorted(inv - mat), [], "inventoried but not classified in the matrix"
        )
        self.assertEqual(
            sorted(mat - inv), [], "classified in the matrix but never inventoried"
        )


class TestTargetLayersAreInsideTheVocabulary(unittest.TestCase):
    """The matrix declares a seven-value target vocabulary; nothing may escape it.

    Rows are parsed by splitting on runs of 2+ spaces — the table's column
    separator. Two columns legitimately contain single spaces (the current
    mechanical owner, and annotations), so a whitespace-token parse would
    silently drop rows.
    """

    COLUMNS = 7  # ID | CUR | TGT | FORGET | PRED | MECH_TODAY | RM

    def _rows(self) -> list[list[str]]:
        rows = []
        for line in _read(MATRIX).splitlines():
            stripped = line.strip()
            if not stripped.startswith("R-V12-"):
                continue
            cols = [c.strip() for c in re.split(r"\s{2,}", stripped)]
            if len(cols) == self.COLUMNS:
                rows.append(cols)
        return rows

    def test_every_inventoried_rule_has_exactly_one_matrix_row(self):
        rows = self._rows()
        inventory_count = len(
            {int(m.group(1)) for m in RULE_ID_RE.finditer(_read(INVENTORY))}
        )
        self.assertEqual(
            inventory_count, len(rows),
            f"parsed {len(rows)} matrix rows for {inventory_count} inventoried rules "
            "— a rule with no row is an un-dispositioned obligation",
        )
        ids = [r[0] for r in rows]
        self.assertEqual(sorted(ids), sorted(set(ids)), "duplicate matrix row")

    def test_every_row_declares_a_legal_target_layer(self):
        rows = self._rows()
        self.assertTrue(rows, "no matrix rows parsed; the table format drifted")
        for cols in rows:
            with self.subTest(rule=cols[0]):
                self.assertIn(cols[2], TARGET_LAYERS)

    def test_declared_distribution_adds_up_to_the_rule_count(self):
        text = _read(MATRIX)
        block = text.split("**统计**", 1)[-1]
        counts = {}
        for m in re.finditer(r"^([A-G])\s+\S[^\n=]*=\s*(\d+)", block, re.M):
            counts[m.group(1)] = int(m.group(2))
        self.assertEqual(
            set(TARGET_LAYERS), set(counts),
            f"the distribution must declare all seven layers; found {sorted(counts)}",
        )
        inventory_count = len(
            {int(m.group(1)) for m in RULE_ID_RE.finditer(_read(INVENTORY))}
        )
        self.assertEqual(
            inventory_count, sum(counts.values()),
            f"layer distribution {counts} does not sum to {inventory_count}",
        )

    def test_distribution_matches_the_rows_actually_tabled(self):
        """The declared histogram must equal the histogram of the table itself."""
        declared = {}
        block = _read(MATRIX).split("**统计**", 1)[-1]
        for m in re.finditer(r"^([A-G])\s+\S[^\n=]*=\s*(\d+)", block, re.M):
            declared[m.group(1)] = int(m.group(2))
        actual = Counter(r[2] for r in self._rows())
        self.assertEqual(declared, dict(actual))

    def test_declared_current_layer_histogram_matches_the_rows(self):
        """The §4.1 counts are copied by hand from the table; recompute them.

        They were wrong once already (declared 76/34/11/31 against a table that
        says 86/52/3/2/16/13), which is exactly the kind of drift a declared
        number acquires when nothing compares it to its source.
        """
        block = _read(MATRIX).split("### 4.1 计数", 1)[-1].split("### 4.2", 1)[0]
        declared = {
            m.group(1): int(m.group(2))
            for m in re.finditer(
                r"(HOT_AUTO_MEMORY|HOT_AUTO_PARTIAL|HOT_NOT_DELIVERED|HOT_READ"
                r"|HOT_AUTO|EXPERIMENT_ONLY)\s*=\s*(\d+)",
                block,
            )
        }
        actual = Counter(r[1] for r in self._rows())
        for layer, count in sorted(actual.items()):
            with self.subTest(layer=layer):
                self.assertEqual(
                    count, declared.get(layer),
                    f"{layer}: table has {count}, §4.1 declares {declared.get(layer)}",
                )

    def test_removal_flags_are_inside_the_declared_vocabulary(self):
        allowed = {"YES", "NO", "NOT_YET", "N/A"}
        for cols in self._rows():
            with self.subTest(rule=cols[0]):
                self.assertIn(cols[6], allowed)


class TestMechanizationMustReplace(unittest.TestCase):
    """No rule may be marked removable-from-HOT without a replacement argument.

    This is the one rule the whole analysis rests on, so it is the one rule the
    material suite enforces on itself.
    """

    def test_every_now_removable_rule_appears_in_the_replacement_section(self):
        matrix = _read(MATRIX)
        removable = []
        for line in matrix.splitlines():
            stripped = line.strip()
            if not stripped.startswith("R-V12-"):
                continue
            cols = [c.strip() for c in re.split(r"\s{2,}", stripped)]
            if len(cols) == 7 and cols[6] == "YES":
                removable.append(cols[0])
        self.assertTrue(removable, "expected at least one rule removable now")
        replacement_section = matrix.split("## 3.", 1)[1] if "## 3." in matrix else ""
        self.assertTrue(replacement_section, "no replacement section found")
        for rule in removable:
            with self.subTest(rule=rule):
                self.assertIn(
                    rule, replacement_section,
                    f"{rule} is marked removable but has no replacement argument",
                )

    def test_replacement_section_answers_all_four_questions(self):
        """MECHANIZATION_MUST_REPLACE = WHAT / WHERE / HOW IT FAILS / LOAD-BEARING."""
        section = _read(MATRIX).split("## 3.", 1)[1]
        for marker in (
            "WHAT NOW ENFORCES IT",
            "WHERE =",
            "HOW IT FAILS",
            "HOW WE KNOW IT IS LOAD-BEARING",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, section)


class TestExternalClaimsCarryEvidenceLevels(unittest.TestCase):
    """E1 must never be presented as an established local fact."""

    def test_mechanism_entries_declare_adopt_disposition(self):
        text = _read(LONGHORIZON)
        # restrict to the mechanism-registration section: the summary block below
        # also writes "ADOPT_CONCEPT = ..." lines and would double-count them
        body = text.split("## 1. 机制登记", 1)[-1].split("## 2.", 1)[0]
        ids = {m.group(1) for m in re.finditer(r"^### (M-\d{2})\b", body, re.M)}
        self.assertGreaterEqual(len(ids), 10, "expected the full mechanism set")
        adopt = re.findall(r"^ADOPT_CONCEPT = (\w+)", body, re.M)
        self.assertEqual(
            len(ids), len(adopt),
            "every mechanism must declare exactly one ADOPT_CONCEPT disposition",
        )
        for value in adopt:
            with self.subTest(value=value):
                self.assertIn(value, {"YES", "EXPERIMENT", "NO"})

    def test_openai_material_is_not_promoted_to_first_hand(self):
        text = _read(LONGHORIZON)
        self.assertIn("SECONDARY_MENTION", text)
        self.assertIn("不支撑任何判定", text)

    def test_rejected_external_shapes_are_recorded(self):
        text = _read(LONGHORIZON)
        rejects = re.findall(r"^REJECT-(\d{2})\b", text, re.M)
        self.assertGreaterEqual(len(rejects), 5, "rejection list shrank unexpectedly")


class TestFailureMapSeparatesFactFromHypothesis(unittest.TestCase):
    """A hypothesised failure must not be written as one that happened.

    The evidence level is the field a downstream consumer would read, so it must
    be *machine-parseable*: `EVIDENCE_LEVEL = <LEVEL>` optionally followed by
    `  # <note>`. Free-form annotations attached without a separator break the
    parse (this happened once in this very slice and is why the check is strict).
    """

    LEVEL_LINE_RE = re.compile(
        r"^EVIDENCE_LEVEL = (?:"
        + "|".join(sorted(EVIDENCE_LEVELS))
        + r")(?:  # \S.*)?$",
        re.M,
    )

    def test_every_failure_declares_exactly_one_parseable_level(self):
        text = _read(FAILURES)
        ids = {m.group(1) for m in re.finditer(r"^### (F-\d{3})\b", text, re.M)}
        levels = self.LEVEL_LINE_RE.findall(text)
        self.assertEqual(
            len(ids), len(levels),
            f"{len(ids)} failures but {len(levels)} parseable EVIDENCE_LEVEL lines",
        )

    def test_no_evidence_level_line_is_unparseable(self):
        text = _read(FAILURES)
        all_lines = re.findall(r"^EVIDENCE_LEVEL = .*$", text, re.M)
        parsed = self.LEVEL_LINE_RE.findall(text)
        self.assertEqual(
            sorted(all_lines), sorted(parsed),
            "some EVIDENCE_LEVEL lines are not machine-parseable "
            "(value must be one of the four levels, optional '  # note' only)",
        )

    def test_declared_statistics_match_the_entries(self):
        text = _read(FAILURES)
        ids = {m.group(1) for m in re.finditer(r"^### (F-\d{3})\b", text, re.M)}
        for level in sorted(EVIDENCE_LEVELS):
            with self.subTest(level=level):
                declared = int(re.search(rf"{level}\s*=\s*(\d+)", text).group(1))
                actual = len(re.findall(rf"^EVIDENCE_LEVEL = {level}(?:  #.*)?$", text, re.M))
                self.assertEqual(
                    declared, actual, f"{level}: declared {declared}, found {actual}"
                )
        declared_total = int(re.search(r"合计\s*=\s*(\d+)", text).group(1))
        self.assertEqual(len(ids), declared_total)


class TestTreeLedgerIsConsistent(unittest.TestCase):
    """Node identity and the declared total must agree with the tree itself."""

    NODE_DEF_RE = re.compile(r"^#### (N\d+(?:\.\d+)?) ", re.M)
    EXPECTED_NODES = (
        {"N0"}
        | {f"N{i}" for i in range(1, 14)}
        | {f"N6.{i}" for i in range(1, 6)}
    )

    def test_every_declared_node_has_its_own_definition(self):
        """A node with no block of its own has no ENTRY/EXIT/STATUS fields."""
        defined = set(self.NODE_DEF_RE.findall(_read(TREE_LEDGER)))
        self.assertEqual(
            sorted(self.EXPECTED_NODES - defined), [],
            "these nodes are declared in the tree but have no definition block",
        )

    def test_node_ids_are_unique(self):
        defined = self.NODE_DEF_RE.findall(_read(TREE_LEDGER))
        self.assertEqual(
            sorted(defined), sorted(set(defined)),
            "a node is defined twice; the ledger would be ambiguous",
        )

    def test_declared_total_matches_the_tree(self):
        text = _read(TREE_LEDGER)
        declared = int(re.search(r"TREE_NODES_TOTAL\s*=\s*(\d+)", text).group(1))
        self.assertEqual(len(self.EXPECTED_NODES), declared)

    def test_every_definition_block_carries_the_required_fields(self):
        """PART 2 lists the fields each node must record; spot-check the critical ones."""
        text = _read(TREE_LEDGER)
        blocks = re.split(r"^#### (N\d+(?:\.\d+)?) ", text, flags=re.M)
        seen = 0
        for i in range(1, len(blocks), 2):
            node, body = blocks[i], blocks[i + 1]
            seen += 1
            with self.subTest(node=node):
                self.assertIn("STATUS =", body, f"{node} declares no STATUS")
        self.assertEqual(len(self.EXPECTED_NODES), seen)

    def test_no_new_top_level_nodes_were_added_without_a_recorded_reason(self):
        """PART 21: ordinary findings must not expand the main tree."""
        text = _read(TREE_LEDGER)
        self.assertIn("ADDED_NODES", text)
        self.assertIn("REASON", text)
        # check for node DEFINITIONS, not prose mentions of the names
        extra = set(self.NODE_DEF_RE.findall(text)) - self.EXPECTED_NODES
        self.assertEqual(
            sorted(extra), [],
            f"node(s) {sorted(extra)} appeared with no TREE_CHANGE to authorise them",
        )


class TestNoImplementationSlippedIn(unittest.TestCase):
    """This slice is analysis-only. It must not have touched canonical or added code."""

    def _merge_base(self) -> str:
        for candidate in ("origin/main", "main"):
            proc = subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet", candidate],
                capture_output=True, text=True, check=False,
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                continue
            mb = subprocess.run(
                ["git", "-C", str(ROOT), "merge-base", "HEAD", candidate],
                capture_output=True, text=True, check=False,
            )
            if mb.returncode == 0 and mb.stdout.strip():
                return mb.stdout.strip()
        self.fail("no base ref available; refusing to pass vacuously")

    def test_committed_change_set_stays_inside_the_experiment_directory(self):
        base = self._merge_base()
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--name-only", f"{base}..HEAD"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, proc.returncode, proc.stderr[-2000:])
        changed = [p for p in proc.stdout.splitlines() if p.strip()]
        outside = [p for p in changed if not p.startswith("experiments/v1.2/")]
        self.assertEqual(
            [], outside, f"changes outside experiments/v1.2/: {outside}"
        )

    def test_no_canonical_file_is_dirty_in_the_worktree(self):
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--",
             "AGENTS.md", "RULES.md", "references", "deployment", "scripts",
             "schemas", "templates", ".github", "adapters", "mcp", "audit", "docs",
             "ruff.toml", "requirements-dev.txt"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, proc.returncode, proc.stderr[-2000:])
        self.assertEqual("", proc.stdout.strip(), f"canonical surface modified:\n{proc.stdout}")

    def test_no_new_executable_code_added_by_this_slice(self):
        """The gap analysis must not ship mechanisms. Only .md plus this test file."""
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--name-only",
             f"{self._merge_base()}..HEAD"],
            capture_output=True, text=True, check=False,
        )
        changed = [p for p in proc.stdout.splitlines() if p.strip()]
        offenders = [
            p for p in changed
            if p.endswith((".py", ".sh", ".yml", ".yaml", ".json"))
            and p != "experiments/v1.2/tests/test_mechanization_gap_material.py"
        ]
        self.assertEqual(
            [], offenders,
            f"this slice must add no executable/schema artefacts, found: {offenders}",
        )


class TestReferencedPathsResolve(unittest.TestCase):
    """Referenced repo paths in the new documents must exist.

    Deliberately narrow: only backticked paths that look like repo-relative files
    with a known extension are checked, to avoid false positives from prose.
    """

    PATH_RE = re.compile(
        r"`((?:references|scripts|deployment|schemas|templates|adapters|audit|docs)"
        r"/[\w./-]+\.(?:md|py|json|yml|yaml))`"
    )

    def test_referenced_repo_paths_exist(self):
        seen = 0
        for doc in DECLARED_ARTIFACTS:
            text = _read(doc)
            for match in self.PATH_RE.finditer(text):
                seen += 1
                rel = match.group(1)
                with self.subTest(doc=doc.name, path=rel):
                    self.assertTrue(
                        (ROOT / rel).exists(),
                        f"{doc.name} references a path that does not exist: {rel}",
                    )
        self.assertGreater(seen, 0, "no repo paths parsed; the check would be vacuous")

    def test_external_source_paths_are_not_mistaken_for_local_ones(self):
        """The LongHorizon map quotes another repo's layout; those paths must be
        written so they cannot be read as paths in THIS repo."""
        text = _read(LONGHORIZON)
        self.assertIn("src/lh_harness/", text)
        for rel in ("adapters/base.py", "environment/base.py"):
            with self.subTest(rel=rel):
                self.assertNotRegex(
                    text, rf"(?<![\w/.\-])`{re.escape(rel)}`",
                    f"{rel} is written as if it were a path in this repo",
                )


if __name__ == "__main__":
    unittest.main()
