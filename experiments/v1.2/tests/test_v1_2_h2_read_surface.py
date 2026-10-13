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
        (self.ev / "report.md").write_text("worker report\n", encoding="utf-8")
        # present but NOT on the allowlist: the enforced surface must be narrower than the
        # directory, otherwise receipt.json / task.txt become readable and un-logged
        (self.ev / "receipt.json").write_text("{}\n", encoding="utf-8")
        (self.ev / "task.txt").write_text("task\n", encoding="utf-8")
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
        verdict, reason = self.classify("RUN_EVIDENCE/contract.md")
        self.assertEqual((verdict, reason), (rs.ALLOWED, "OK"))

    def test_REGRESSION_contract_compliant_template_read_is_allowed(self):
        """The Round-1 defect: the worker reads the report template that prepare placed in
        its OWN evidence dir. Under the Round-1 predicate this was rejected."""
        verdict, reason = self.classify("RUN_EVIDENCE/worker-report-template.md")
        self.assertEqual(
            (verdict, reason),
            (rs.ALLOWED, "OK"),
            "a contract-compliant read of the run's own report template must be accepted",
        )

    def test_absolute_path_is_refused_even_for_own_evidence(self):
        """Codex finding (7ba6361): the old predicate used os.path.join(worktree, target),
        which DISCARDS the worktree prefix for an absolute target, so any existing absolute
        path passed; and a host path in this log is published, which the public-data policy
        forbids. The form is now refused outright."""
        verdict, reason = self.classify(str(self.ev / "worker-report-template.md"))
        self.assertEqual((verdict, reason), ("REJECTED", "HOST_PATH_NOT_ALLOWED"))

    def test_bare_name_has_a_determinate_base(self):
        """A bare relative path resolves against the task worktree ONLY. It must never be
        probed against the evidence dir as well, or one recorded name would denote two
        different files depending on which root the checker happened to try."""
        verdict, reason = self.classify("worker-report-template.md")
        self.assertEqual(verdict, "REJECTED")
        self.assertEqual(reason, "OUTSIDE_ALLOWED_SURFACE")

    def test_evidence_namespace_rejects_non_allowlisted_file(self):
        """Codex finding (7ba6361, read_surface.py:83): the branch accepted EVERY regular
        file under the evidence dir, so receipt.json / task.txt were readable. The surface
        must be narrower than the directory."""
        for name in ("receipt.json", "task.txt", "carrier-recheck.txt"):
            with self.subTest(name=name):
                self.assertEqual(
                    self.classify(f"RUN_EVIDENCE/{name}"),
                    ("REJECTED", "UNKNOWN_EVIDENCE_NAMESPACE"),
                )

    def test_evidence_namespace_rejects_traversal_and_subdirs(self):
        self.assertEqual(
            self.classify("RUN_EVIDENCE/../materials/protocol.md"),
            ("REJECTED", "UNKNOWN_EVIDENCE_NAMESPACE"),
        )
        self.assertEqual(
            self.classify("RUN_EVIDENCE/sub/contract.md"),
            ("REJECTED", "UNKNOWN_EVIDENCE_NAMESPACE"),
        )


class NegativeControls(ReadSurfaceFixture):
    """PART 10 — NC1..NC5 plus the boundary cases they depend on."""

    def _expect(self, target: str, reason: str):
        verdict, got = self.classify(target)
        self.assertEqual(verdict, "REJECTED", f"probe did not trigger for {target!r}")
        self.assertEqual(got, reason, f"wrong rejection reason for {target!r}")

    def test_NC1_materials_root_read_rejected(self):
        # realistic vector: relative traversal out of the worktree into the materials tree
        self._expect("../../materials/protocol.md", "MATERIALS_ROOT_READ")

    def test_NC1b_materials_warm_owner_read_rejected(self):
        """A routed WARM owner must be read from the run's H2_WARM copy, not the materials
        tree — otherwise the WARM copy the experiment measures is bypassed."""
        self._expect("../../materials/references/ticket-lane.md", "MATERIALS_ROOT_READ")

    def test_NC2_cross_arm_carrier_read_rejected(self):
        self._expect(
            "../../materials/carriers/H2_LEAN_BOOTSTRAP.md", "CROSS_ARM_READ"
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
            "../../evidence/H2-R2-R02/worker-report-template.md", "OTHER_RUN_EVIDENCE_READ"
        )

    def test_outside_any_allowed_surface_rejected(self):
        verdict, reason = self.classify("../../elsewhere/hosts")
        self.assertEqual(verdict, "REJECTED")
        self.assertEqual(reason, "OUTSIDE_ALLOWED_SURFACE")

    def test_missing_file_inside_worktree_rejected(self):
        self._expect("does-not-exist.md", "OUTSIDE_ALLOWED_SURFACE")

    def test_prefix_confusion_sibling_directory_is_rejected(self):
        """Adversarial review NB4: replacing the component-wise containment test with a naive
        string-prefix test would pass the whole suite, so the distinction must be pinned.
        A sibling directory whose name merely STARTS WITH the evidence dir name is outside."""
        evil = self.tmp / "evidence" / f"{self.ev.name}-evil"
        evil.mkdir(parents=True, exist_ok=True)
        (evil / "worker-report-template.md").write_text("sibling\n", encoding="utf-8")
        # repo-relative traversal, consistent with every other negative control: an ABSOLUTE
        # path would be refused earlier as HOST_PATH_NOT_ALLOWED and would never reach the
        # containment logic this test is about.
        verdict, reason = rs.classify_read_target(
            f"../../evidence/{self.ev.name}-evil/worker-report-template.md",
            self.wt, self.ev, self.mat,
        )
        self.assertEqual(verdict, "REJECTED")
        # EXACT reason: a sibling evidence dir is not "inside" this run's dir. A prefix test
        # would classify it as inside, and would then still reject it for the wrong reason,
        # which an assertIn(reason, REJECT_REASONS) would happily accept.
        self.assertEqual(reason, "OTHER_RUN_EVIDENCE_READ")


class TraversalAndSymlinkControls(ReadSurfaceFixture):
    """Path-normalisation bypasses must fail closed."""

    def test_relative_traversal_out_of_worktree_rejected(self):
        verdict, reason = self.classify("../../materials/protocol.md")
        self.assertEqual(verdict, "REJECTED")
        self.assertEqual(reason, "MATERIALS_ROOT_READ")

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
        self.assertEqual(reason, "MATERIALS_ROOT_READ")

    def test_symlinked_template_in_own_evidence_rejected(self):
        """The per-run template must be a real file, not a link to the materials tree."""
        link = self.ev / "linked-template.md"
        try:
            link.symlink_to(self.mat / "references" / "ticket-lane.md")
        except OSError:
            self.skipTest("symlink creation unavailable")
        # F55-N2: the previous version passed only the relative name, which resolves against
        # the WORKTREE, so it merely rejected a nonexistent worktree file and never touched
        # the symlink. The real link path must be passed, and the reason asserted exactly.
        self.assertTrue(link.is_symlink(), "fixture must be a real symlink")
        verdict, reason = rs.classify_read_target(
            "RUN_EVIDENCE/linked-template.md", self.wt, self.ev, self.mat
        )
        self.assertEqual(verdict, "REJECTED")
        self.assertEqual(
            reason, "UNKNOWN_EVIDENCE_NAMESPACE",
            "a non-allowlisted evidence name must be refused on the name itself",
        )
        # and the namespace that IS allowlisted must still refuse a link pointing at materials
        (self.ev / "contract.md").unlink()
        (self.ev / "contract.md").symlink_to(self.mat / "protocol.md")
        verdict, reason = rs.classify_read_target(
            "RUN_EVIDENCE/contract.md", self.wt, self.ev, self.mat
        )
        self.assertEqual(verdict, "REJECTED")
        self.assertEqual(reason, "MATERIALS_ROOT_READ")


class TelemetryIntegration(ReadSurfaceFixture):
    """The batch predicate used by collect_run.sh must agree with the single-target one."""

    def test_batch_reports_only_disallowed_reads(self):
        lines = [
            "READ FULL H2_RULES.md",
            "READ FULL CODEBUDDY.md",
            "READ FULL RUN_EVIDENCE/worker-report-template.md",
            "ROUTE n/a  codegraph-grounding.md  SKIPPED",
        ]
        self.assertEqual(rs.classify_telemetry(lines, self.wt, self.ev, self.mat), [])

    def test_batch_reports_each_violation_with_its_reason(self):
        lines = [
            "READ FULL RUN_EVIDENCE/worker-report-template.md",
            "READ FULL ../../materials/protocol.md",
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


class NestedRunsRootLayout(unittest.TestCase):
    """Codex finding on 7b9251a (P1): when H2_RUNS_ROOT lives INSIDE the materials checkout the
    worktree and evidence dir are descendants of `mat`. Testing `mat` before the explicitly
    allowed roots made every compliant read classify as MATERIALS_ROOT_READ, so preparation
    succeeded and collection rejected the run after the worker episode had been spent."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="h2-nested-"))
        # runs root nested inside the materials checkout, exactly the documented non-/tmp case
        self.mat = self.tmp / "repo"
        self.wt = self.mat / ".workbuddy" / "h2-runs" / "worktrees" / "H2-R2-R01"
        self.ev = self.mat / ".workbuddy" / "h2-runs" / "evidence" / "H2-R2-R01"
        for d in (self.mat, self.wt, self.ev):
            d.mkdir(parents=True, exist_ok=True)
        (self.wt / "CODEBUDDY.md").write_text("carrier\n", encoding="utf-8")
        (self.ev / "worker-report-template.md").write_text("tpl\n", encoding="utf-8")
        (self.mat / "protocol.md").write_text("protocol\n", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _c(self, target):
        return rs.classify_read_target(target, self.wt, self.ev, self.mat)

    def test_compliant_worktree_read_is_allowed_in_nested_layout(self):
        self.assertEqual(self._c("CODEBUDDY.md"), (rs.ALLOWED, "OK"))

    def test_compliant_evidence_read_is_allowed_in_nested_layout(self):
        self.assertEqual(self._c("RUN_EVIDENCE/worker-report-template.md"), (rs.ALLOWED, "OK"))

    def test_materials_content_is_still_refused_in_nested_layout(self):
        """The reorder must not open the materials tree: content OUTSIDE the allowed roots but
        inside the nested checkout is still refused."""
        verdict, reason = rs.classify_read_target(
            "../../../../protocol.md", self.wt, self.ev, self.mat
        )
        self.assertEqual(verdict, "REJECTED")
        self.assertEqual(reason, "MATERIALS_ROOT_READ")


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
