"""Freeze-v2 contract tests; no worker/model execution."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
H2_REL = "experiments/v1.2/h2-lazy-disclosure"
H2 = ROOT / H2_REL
FZ = H2 / "freeze-v2"


def load(name):
    spec = importlib.util.spec_from_file_location(name, FZ / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def git(*args, root=ROOT):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          check=True).stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


class WrapperDelivery(unittest.TestCase):
    def test_both_arms_deliver_only_outside_clean_base_with_object_hashes(self):
        wrapper = load("wrapper_delivery")
        materials = git("rev-parse", "HEAD").decode().strip()
        task = json.loads(git("show", f"{materials}:{H2_REL}/admission/"
                             "freeze-v2-input/shortlist.json"))["shortlist"][0]
        routes = json.loads(git("show", f"{materials}:{H2_REL}/routes-h2.json"))["routes"]
        dests = sorted({r["destination"] for r in routes if r["surface"] == "S3"})
        with tempfile.TemporaryDirectory() as tmp:
            for arm in ("control", "variant"):
                run = Path(tmp) / arm
                try:
                    receipt = wrapper.prepare(ROOT, run, "f01", arm, materials)
                    self.assertEqual(receipt, json.loads((run / "receipt.json").read_text()))
                    self.assertEqual(task["BASE_SHA"], git("rev-parse", "HEAD",
                                                         root=run / "repo").decode().strip())
                    self.assertEqual(b"", git("status", "--porcelain", "--ignored",
                                              root=run / "repo"))
                    self.assertNotEqual(0, subprocess.run(
                        ["git", "-C", str(run), "rev-parse", "--show-toplevel"],
                        capture_output=True).returncode)
                    base_paths = set(git("ls-tree", "-r", "--name-only", task["BASE_SHA"])
                                     .decode().splitlines())
                    for path in (run / "repo").rglob("*"):
                        if path.name in {"AGENTS.md", "H2_RULES.md", "H2_WARM"}:
                            self.assertIn(path.relative_to(run / "repo").as_posix(), base_paths)
                    carrier = git("show", f"{materials}:{H2_REL}/carriers/H2_LEAN_BOOTSTRAP.md")
                    if arm == "control":
                        carrier = (git("show", f"{materials}:{H2_REL}/harness/control-carrier-header.md")
                                   + git("show", f"{materials}:AGENTS.md")
                                   + git("show", f"{materials}:{H2_REL}/harness/control-carrier-footer.md"))
                    self.assertEqual(carrier, (run / "AGENTS.md").read_bytes())
                    self.assertEqual(digest(carrier), receipt["carrier_sha256"])
                    self.assertEqual("control_full_v1" if arm == "control" else "variant_lean_v1",
                                     receipt["carrier_kind"])
                    if arm == "variant":
                        manifest = json.loads(git("show", f"{materials}:{H2_REL}/variant-manifest.json"))
                        self.assertEqual(manifest["freeze"]["VARIANT_HASH"], digest(carrier))
                    rules = git("show", f"{materials}:RULES.md")
                    self.assertEqual(rules, (run / "H2_RULES.md").read_bytes())
                    self.assertEqual(digest(rules), receipt["rules_sha256"])
                    lines = []
                    for dest in dests:
                        data = git("show", f"{materials}:{dest}")
                        self.assertEqual(data, (run / "H2_WARM" / dest).read_bytes())
                        lines.append(f"{dest} {digest(data)}")
                    self.assertEqual(digest("\n".join(lines).encode()), receipt["warm_bundle_sha256"])
                    self.assertEqual(digest((FZ / "wrapper_delivery.py").read_bytes()),
                                     receipt["program_sha256"])
                    self.assertEqual(("f01", arm, task["BASE_SHA"], materials),
                                     tuple(receipt[k] for k in
                                           ("task_id", "arm", "base_sha", "materials_commit")))
                finally:
                    if run.exists():
                        wrapper.cleanup(ROOT, run)
                self.assertFalse(run.exists())

    def test_stray_delivery_inside_repo_rolls_back_the_entire_allocation(self):
        wrapper = load("wrapper_delivery")
        real_git = wrapper.git
        before = git("worktree", "list", "--porcelain")
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "contaminated"

            def contaminate(root, *args, **kwargs):
                result = real_git(root, *args, **kwargs)
                if args[:2] == ("worktree", "add"):
                    stray = run / "repo" / "nested" / "H2_RULES.md"
                    stray.parent.mkdir()
                    stray.write_text("stray\n")
                return result

            with mock.patch.object(wrapper, "git", side_effect=contaminate):
                with self.assertRaisesRegex(ValueError, "DELIVERY_INSIDE_REPO"):
                    wrapper.prepare(ROOT, run, "f01", "variant", "HEAD")
            self.assertFalse(run.exists())
        self.assertEqual(before, git("worktree", "list", "--porcelain"))

    def test_ignored_stray_file_also_fails_closed(self):
        wrapper = load("wrapper_delivery")
        real_git = wrapper.git
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "ignored"

            def contaminate(root, *args, **kwargs):
                result = real_git(root, *args, **kwargs)
                if args[:2] == ("worktree", "add"):
                    cache = run / "repo" / "__pycache__"
                    cache.mkdir()
                    (cache / "stray.pyc").write_bytes(b"stray")
                return result

            with mock.patch.object(wrapper, "git", side_effect=contaminate):
                with self.assertRaisesRegex(ValueError, "REPO_NOT_CLEAN"):
                    wrapper.prepare(ROOT, run, "f01", "control", "HEAD")
            self.assertFalse(run.exists())

    def test_refuses_existing_or_in_repository_target_without_deleting_it(self):
        wrapper = load("wrapper_delivery")
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp)
            with self.assertRaises(ValueError):
                wrapper.prepare(ROOT, existing, "f01", "control", "HEAD")
            self.assertTrue(existing.exists())
        with self.assertRaisesRegex(ValueError, "RUN_DIR_INSIDE_REPOSITORY"):
            wrapper.prepare(ROOT, FZ / "forbidden-run", "f01", "control", "HEAD")
        self.assertFalse((FZ / "forbidden-run").exists())
