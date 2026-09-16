"""Mutation tests for governance documentation wiring, NOT semantic gate tests."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "governance", ROOT / "scripts/validate_governance.py")
governance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(governance)


class TicketGateWiringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("RULES.md", "AGENTS.md", "references/execution-stage.md"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((ROOT / name).read_text(encoding="utf-8"), encoding="utf-8")

    def test_intact_wiring(self):
        self.assertEqual(governance.ticket_gate_wiring(self.root), [])

    def test_removed_required_routes_and_guards_fail(self):
        cases = (
            ("AGENTS.md", "PRE_TICKET_CONVERGENCE_GATE"),
            ("AGENTS.md", "POST_TICKET_COMPOSITION_GATE"),
            ("AGENTS.md", "INDEPENDENT_TICKET_CONFORMANCE_REVIEW"),
            ("RULES.md", "references/execution-stage.md"),
            ("references/execution-stage.md", "SPEC_OR_AUTHORITY_CONFLICT"),
            ("references/execution-stage.md", "FAST_PATH = VALID_EVIDENCE_REUSE"),
            ("references/execution-stage.md", "STRUCTURAL_VALIDATION != SEMANTIC_COMPATIBILITY"),
        )
        for name, marker in cases:
            with self.subTest(name=name, marker=marker):
                path = self.root / name
                original = path.read_text(encoding="utf-8")
                path.write_text(original.replace(marker, "REMOVED"), encoding="utf-8")
                self.assertIn(name + ": " + marker,
                              governance.ticket_gate_wiring(self.root))
                path.write_text(original, encoding="utf-8")

    def test_missing_owner_file_fails(self):
        (self.root / "references/execution-stage.md").unlink()
        self.assertIn("references/execution-stage.md: missing file",
                      governance.ticket_gate_wiring(self.root))

    def test_marker_presence_is_explicitly_not_semantic_validation(self):
        # A contradictory sentence can pass static presence checks. This test
        # documents the tool boundary; an independent reviewer must reject it.
        path = self.root / "references/execution-stage.md"
        with path.open("a", encoding="utf-8") as stream:
            stream.write("\nHypothetical contradiction: same session alone proves compatibility.\n")
        self.assertEqual(governance.ticket_gate_wiring(self.root), [])


if __name__ == "__main__":
    unittest.main()
