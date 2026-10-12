"""H2 read-surface regression + negative-control suite (PART 8/9/10).

Reproduces the Round-1 GLOBAL HARNESS CONTRACT DEFECT: a contract-compliant worker that read
the report template was rejected by TELEMETRY_TARGETS, because the template lived in the
frozen materials tree while the validator only accepted worktree-relative paths.

Design notes that keep the controls honest:
  * every negative control asserts on the stable REASON TOKEN, not merely "it failed";
  * every control asserts the probe actually TRIGGERED (verdict == REJECTED) rather than
    inferring it from a non-zero exit code;
  * no control uses unittest.TestCase.run(), which CAPTURES assertion failures instead of
    raising them and would silently turn a failing control into a passing one.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
H2 = ROOT / "experiments" / "v1.2" / "h2-lazy-disclosure"
HARNESS = H2 / "harness"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, HARNESS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rs = _load("read_surface")


class ReadSurfaceFixture(unittest.TestCase):
    """Builds a miniature runs root: materials tree, task worktree, two run evidence dirs."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="h2-read-surface-"))
        self.mat = self.tmp / "materials"
        self.wt = self.tmp / "worktrees" / "H2-R2-R01"
        self.ev = self.tmp / "evidence" / "H2-R2-R01"
        self.other_ev = self.tmp / "evidence" / "H2-R2-R02"
        for p in (
            self.mat / "carriers",
            self.mat / "references",
            self.wt,
            self.ev,
            self.other_ev,
        ):
            p.mkdir(parents=True, exist_ok=True)

        # frozen materials snapshot contents (the sensitive surface)
        (self.mat / "protocol.md").write_text("protocol internals\n", encoding="utf-8")
        (self.mat / "carriers" / "H2_LEAN_BOOTSTRAP.md").write_text("variant\n", encoding="utf-8")
        (self.mat / "references" / "ticket-lane.md").write_text("warm owner\n", encoding="utf-8")

        # task worktree contents, mirroring the real delivery surface
        (self.wt / "AGENTS.md").write_text("repo agents\n", encoding="utf-8")
        (self.wt / "CODEBUDDY.md").write_text("carrier\n", encoding="utf-8")
        (self.wt / "H2_RULES.md").write_text("rules copy\n", encoding="utf-8")
        (self.wt / ".h2-telemetry.log").write_text("", encoding="utf-8")
        warm = self.wt / "H2_WARM" / "references"
        warm.mkdir(parents=True, exist_ok=True)
        (warm / "ticket-lane.md").write_text("warm copy\n", encoding="utf-8")

        # the per-run copies prepare_run.sh is REQUIRED to place
        (self.ev / "contract.md").write_text("run contract\n", encoding="utf-8")
        (self.ev / "worker-report-template.md").write_text("report template\n", encoding="utf-8")
        (self.other_ev / "worker-report-template.md").write_text("other run\n", encoding="utf-8")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def classify(self, target: str):
        return rs.classify_read_target(target, self.wt, self.ev, self.mat)


class PositiveControl(ReadSurfaceFixture):
    """PART 9 — the happy path must pass."""

    def test_reads_inside_task_worktree_are_allowed(self):
        for target in ("AGENTS.md", "CODEBUDDY.md", ".h2-telemetry.log"):
            with self.subTest(target=target):
                verdict, reason = self.classify(target)
                self.assertEqual((verdict, reason), (rs.ALLOWED, "OK"))

    def test_read_of_own_evidence_run_contract_is_allowed(self):
        verdict, reason = self.classify(str(self.ev / "contract.md"))
        self.assertEqual((verdict, reason), (rs.ALLOWED, "OK"))

    def test_REGRESSION_contract_compliant_template_read_is_allowed(self):
        """The Round-1 defect: the worker reads the report template that prepare placed in
        its OWN evidence dir. Under the Round-1 predicate this was rejected."""
        verdict, reason = self.classify(str(self.ev / "worker-report-template.md"))
        self.assertEqual(
            (verdict, reason),
            (rs.ALLOWED, "OK"),
            "a contract-compliant read of the run's own report template must be accepted",
        )

    def test_absolute_path_to_own_evidence_template_is_allowed(self):
        verdict, reason = self.classify(str(self.ev / "worker-report-template.md"))
        self.assertEqual((verdict, reason), (rs.ALLOWED, "OK"))

    def test_bare_name_has_a_determinate_base(self):
        """A bare relative path resolves against the task worktree ONLY. It must never be
        probed against the evidence dir as well, or one recorded name would denote two
        different files depending on which root the checker happened to try."""
        verdict, reason = self.classify("worker-report-template.md")
        self.assertEqual(verdict, "REJECTED")
        self.assertEqual(reason, "OUTSIDE_ALLOWED_SURFACE")


class NegativeControls(ReadSurfaceFixture):
    """PART 10 — NC1..NC5 plus the boundary cases they depend on."""

    def _expect(self, target: str, reason: str):
        verdict, got = self.classify(target)
        self.assertEqual(verdict, "REJECTED", f"probe did not trigger for {target!r}")
        self.assertEqual(got, reason, f"wrong rejection reason for {target!r}")

    def test_NC1_materials_root_read_rejected(self):
        self._expect(str(self.mat / "protocol.md"), "MATERIALS_ROOT_READ")

    def test_NC1b_materials_warm_owner_read_rejected(self):
        """A routed WARM owner must be read from the run's H2_WARM copy, not the materials
        tree — otherwise the WARM copy the experiment measures is bypassed."""
        self._expect(str(self.mat / "references" / "ticket-lane.md"), "MATERIALS_ROOT_READ")

    def test_NC2_cross_arm_carrier_read_rejected(self):
        self._expect(
            str(self.mat / "carriers" / "H2_LEAN_BOOTSTRAP.md"), "CROSS_ARM_READ"
        )

    def test_NC4_unverifiable_abbreviated_path_rejected(self):
        """PART 8: an ellipsis path cannot be verified against any real file. It must not be
        pattern-matched into looking legitimate."""
        for target in (
            "h2-materials/.../worker-report-template.md",
            "foo/.../worker-report-template.md",
            "../.../x.md",
        ):
            with self.subTest(target=target):
                self._expect(target, "NON_CANONICAL_PATH")

    def test_NC4b_whitespace_padded_path_rejected(self):
        self._expect(" AGENTS.md", "NON_CANONICAL_PATH")

    def test_NC5_other_run_evidence_read_rejected(self):
        self._expect(
            str(self.other_ev / "worker-report-template.md"), "OTHER_RUN_EVIDENCE_READ"
        )

    def test_outside_any_allowed_surface_rejected(self):
        verdict, reason = self.classify("/etc/hosts")
        self.assertEqual(verdict, "REJECTED")
        self.assertIn(reason, rs.REJECT_REASONS)

    def test_missing_file_inside_worktree_rejected(self):
        self._expect("does-not-exist.md", "OUTSIDE_ALLOWED_SURFACE")

    def test_prefix_confusion_sibling_directory_is_rejected(self):
        """Adversarial review NB4: replacing the component-wise containment test with a naive
        string-prefix test would pass the whole suite, so the distinction must be pinned.
        A sibling directory whose name merely STARTS WITH the evidence dir name is outside."""
        evil = self.tmp / "evidence" / f"{self.ev.name}-evil"
        evil.mkdir(parents=True, exist_ok=True)
        (evil / "worker-report-template.md").write_text("sibling\n", encoding="utf-8")
        verdict, reason = rs.classify_read_target(
            str(evil / "worker-report-template.md"), self.wt, self.ev, self.mat
        )
        self.assertEqual(verdict, "REJECTED")
        self.assertIn(reason, rs.REJECT_REASONS)


class TraversalAndSymlinkControls(ReadSurfaceFixture):
    """Path-normalisation bypasses must fail closed."""

    def test_relative_traversal_out_of_worktree_rejected(self):
        verdict, reason = self.classify("../materials/protocol.md")
        self.assertEqual(verdict, "REJECTED")
        self.assertIn(reason, rs.REJECT_REASONS)

    def test_symlink_inside_worktree_pointing_into_materials_rejected(self):
        link = self.wt / "shortcut.md"
        try:
            link.symlink_to(self.mat / "protocol.md")
        except OSError:
            self.skipTest("symlink creation unavailable")
        verdict, reason = rs.classify_read_target(
            "shortcut.md", self.wt, self.ev, self.mat
        )
        self.assertEqual(verdict, "REJECTED", "a symlink must not launder a materials read")
        self.assertIn(reason, rs.REJECT_REASONS)

    def test_symlinked_template_in_own_evidence_rejected(self):
        """The per-run template must be a real file, not a link to the materials tree."""
        link = self.ev / "linked-template.md"
        try:
            link.symlink_to(self.mat / "references" / "ticket-lane.md")
        except OSError:
            self.skipTest("symlink creation unavailable")
        verdict, reason = rs.classify_read_target(
            "linked-template.md", self.wt, self.ev, self.mat
        )
        self.assertEqual(verdict, "REJECTED")
        self.assertIn(reason, rs.REJECT_REASONS)


class TelemetryIntegration(ReadSurfaceFixture):
    """The batch predicate used by collect_run.sh must agree with the single-target one."""

    def test_batch_reports_only_disallowed_reads(self):
        lines = [
            "READ FULL H2_RULES.md",
            "READ FULL CODEBUDDY.md",
            f"READ FULL {self.ev / 'worker-report-template.md'}",
            "ROUTE n/a  codegraph-grounding.md  SKIPPED",
        ]
        self.assertEqual(rs.classify_telemetry(lines, self.wt, self.ev, self.mat), [])

    def test_batch_reports_each_violation_with_its_reason(self):
        lines = [
            f"READ FULL {self.ev / 'worker-report-template.md'}",
            f"READ FULL {self.mat / 'protocol.md'}",
        ]
        problems = rs.classify_telemetry(lines, self.wt, self.ev, self.mat)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("MATERIALS_ROOT_READ", problems[0])

    def test_batch_rejects_the_round1_offending_event_shape(self):
        """The exact shape that invalidated Round 1: an abbreviated materials-tree path."""
        lines = ["READ FULL h2-materials/.../worker-report-template.md"]
        problems = rs.classify_telemetry(lines, self.wt, self.ev, self.mat)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("NON_CANONICAL_PATH", problems[0])


class InvariantTests(unittest.TestCase):
    def test_reason_tokens_are_stable(self):
        for token in (
            "NON_CANONICAL_PATH",
            "MATERIALS_ROOT_READ",
            "CROSS_ARM_READ",
            "OTHER_RUN_EVIDENCE_READ",
            "OUTSIDE_ALLOWED_SURFACE",
        ):
            self.assertIn(token, rs.REJECT_REASONS)

    def test_module_does_not_hardcode_a_machine_layout(self):
        """Paths must come from arguments; a hard-coded home prefix would silently stop
        classifying on another machine (the R2 sanitization lesson)."""
        src = (HARNESS / "read_surface.py").read_text(encoding="utf-8")
        self.assertNotIn("/Users/", src)
        self.assertNotIn(os.path.expanduser("~"), src.replace("\\", ""))


if __name__ == "__main__":
    unittest.main()
