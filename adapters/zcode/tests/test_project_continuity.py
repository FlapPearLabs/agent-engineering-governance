#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PROJECT_CONTINUITY_CONTRACT_V1 — synthetic test matrix (contract §12).

Runs the adapter hooks + project-state validator against throwaway synthetic
repos (temp dirs, deleted afterwards). Never touches any product repository.
Needs only git + python stdlib — the hooks never invoke CodeGraph themselves.

  PS1-PS15   project-state lifecycle       CG1-CG12   CodeGraph lifecycle
  PS12       = CROSS-AGENT RESTORE (Agent A flush → remote → fresh Agent B clone)

Run:  python adapters/zcode/tests/test_project_continuity.py
  or  python -m unittest discover -s adapters/zcode/tests
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOV_ROOT = HERE.parents[2]
HOOKS = HERE.parent / "hooks"
VALIDATOR = GOV_ROOT / "scripts" / "validate_project_state.py"

GUARD = str(HOOKS / "project_state_guard.py")
CG_STATE = str(HOOKS / "codegraph_state.py")
STOP_GUARD = str(HOOKS / "state_flush_guard.py")
GROUND_GUARD = str(HOOKS / "grounding_guard.py")


def git(args, cwd, timeout=30):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, errors="replace")


def hook_env(runtime_dir):
    env = os.environ.copy()
    env["ZCODE_RUNTIME_STATE_DIR"] = str(runtime_dir)
    env.pop("ZCODE_PROJECT_DIR", None)
    env.pop("ZCODE_TICKET_RISK", None)
    env.pop("STATE_FLUSH_COMPLETED", None)
    env.pop("PROJECT_STATE_SYNC_COMPLETED", None)
    return env


class ContinuityBase(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="pcc-test-"))
        self.runtime = self.base / "runtime-state"
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)

    # -- fixture helpers -------------------------------------------------------

    def mk_repo(self, name="repo", with_remote=False, docs=True, code=True):
        repo = self.base / name
        repo.mkdir(parents=True)
        git(["init", "-b", "main"], str(repo))
        git(["config", "user.email", "t@t.local"], str(repo))
        git(["config", "user.name", "t"], str(repo))
        if docs:
            d = repo / "docs" / "adr"
            d.mkdir(parents=True)
            (repo / "docs" / "target.md").write_text("target v1\n", encoding="utf-8")
            (repo / "docs" / "adr" / "ADR-001.md").write_text("adr v1\n", encoding="utf-8")
        if code:
            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text("def main():\n    pass\n", encoding="utf-8")
        if with_remote:
            bare = self.base / (name + "-remote.git")
            subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)],
                           capture_output=True, check=True)
            git(["remote", "add", "origin", str(bare)], str(repo))
        return repo

    def commit_all(self, repo, msg="c1"):
        git(["add", "-A"], str(repo))
        r = git(["commit", "-m", msg], str(repo))
        return git(["rev-parse", "HEAD"], str(repo)).stdout.strip()

    def write_state(self, repo, remote=None, head="", **overrides):
        state = {
            "contract_version": 1,
            "project_identity": {"name": repo.name, "description": "synthetic"},
            "remote": remote if remote is not None else "",
            "default_branch": "main",
            "canonical_documents": {
                "targets": ["docs/target.md"], "specs": ["NONE"],
                "architecture": ["NONE"], "adrs": ["docs/adr/ADR-001.md"],
                "spikes": ["NONE"], "environment": ["NONE"],
            },
            "execution_control_plane": {"type": "none", "tracker_location": "NONE"},
            "recovery_snapshot": {
                "last_verified_remote_sha": head,
                "last_state_flush_reason": "PROJECT_INITIALIZED",
                "last_state_flush_at": "2026-09-06T00:00:00Z",
                "legal_frontier_summary": "synthetic",
                "blocker_refs": [],
                "next_legal_action": "implement-next-ticket",
            },
            "codegraph_policy": {"applicability": "REQUIRED",
                                 "lifecycle": "INIT_ONCE_SYNC_CONTINUOUSLY", "notes": ""},
        }
        state.update(overrides)
        agent_dir = repo / ".agent"
        agent_dir.mkdir(exist_ok=True)
        (agent_dir / "project-state.json").write_text(
            json.dumps(state, indent=1), encoding="utf-8")
        return state

    def run_tool(self, script, args=(), repo=None, stdin_data="", expect=None):
        proc = subprocess.run(
            [sys.executable, script] + list(args), cwd=str(repo or self.base),
            input=stdin_data, capture_output=True, text=True, timeout=60,
            errors="replace", env=hook_env(self.runtime))
        if expect is not None:
            self.assertEqual(proc.returncode, expect,
                             "rc=%s stdout=%s stderr=%s" % (proc.returncode, proc.stdout, proc.stderr))
        return proc

    def hook(self, repo, file_path, tool="Edit"):
        payload = json.dumps({"tool_name": tool,
                              "tool_input": {"file_path": file_path},
                              "cwd": str(repo)})
        return self.run_tool(CG_STATE, ["--hook"], repo=repo, stdin_data=payload)

    def status(self, repo):
        return self.run_tool(CG_STATE, ["status"], repo=repo).stdout

    def guard(self, repo):
        return self.run_tool(GUARD, repo=repo, stdin_data=json.dumps({"cwd": str(repo)})).stdout

    def stop(self, repo):
        return self.run_tool(STOP_GUARD, repo=repo, stdin_data=json.dumps({"cwd": str(repo)})).stdout


class ProjectStateTests(ContinuityBase):
    # PS1 — new repo initialization
    def test_ps1_new_repo_initialization(self):
        repo = self.mk_repo(with_remote=True)
        head = self.commit_all(repo)
        self.write_state(repo, remote="https://example.org/org/repo.git", head=head)
        self.commit_all(repo, "persist state")
        p = self.run_tool(str(VALIDATOR), [str(repo)], repo=repo)
        self.assertEqual(p.returncode, 0, p.stdout)

    # PS2 — existing repo lazy adoption (docs preserved, index points to them)
    def test_ps2_existing_repo_lazy_adoption(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.assertIn("PROJECT_CONTINUITY_INITIALIZATION_REQUIRED", self.guard(repo))
        target_before = (repo / "docs" / "target.md").read_text(encoding="utf-8")
        adr_before = (repo / "docs" / "adr" / "ADR-001.md").read_text(encoding="utf-8")
        self.write_state(repo)  # adoption = index pointing at existing docs, nothing moved
        self.assertEqual((repo / "docs" / "target.md").read_text(encoding="utf-8"), target_before)
        self.assertEqual((repo / "docs" / "adr" / "ADR-001.md").read_text(encoding="utf-8"), adr_before)
        p = self.run_tool(str(VALIDATOR), [str(repo)], repo=repo)
        self.assertEqual(p.returncode, 0, p.stdout)

    # PS3/PS4 — TARGET / ADR change marks PROJECT_STATE_DIRTY
    def test_ps3_ps4_target_and_adr_changes_dirty(self):
        repo = self.mk_repo()
        self.write_state(repo)
        self.hook(repo, "docs/target.md")
        self.assertIn("PROJECT_STATE_DIRTY=YES", self.status(repo))
        self.run_tool(CG_STATE, ["record-state-sync"], repo=repo)
        self.hook(repo, "docs/adr/ADR-001.md")
        self.assertIn("PROJECT_STATE_DIRTY=YES", self.status(repo))

    # PS5/PS6/PS7 — ticket / PR / regression transitions mark dirty
    def test_ps5_to_ps7_execution_events_dirty(self):
        repo = self.mk_repo()
        self.write_state(repo)
        for event in ("TICKET_STARTED", "PR_CREATED_OR_UPDATED",
                      "IMPORTANT_DEFECT_FIXED_WITH_REGRESSION"):
            out = self.run_tool(CG_STATE, ["record-event", event], repo=repo).stdout
            self.assertIn("PROJECT_STATE_DIRTY=YES", out)
            self.assertIn(event, out)
            self.run_tool(CG_STATE, ["record-state-sync", "--event", event], repo=repo)
            self.assertIn("PROJECT_STATE_DIRTY=NO", self.status(repo))

    # PS8 — read-only session never marks dirty
    def test_ps8_read_only_session_no_dirty(self):
        repo = self.mk_repo()
        self.write_state(repo)
        self.hook(repo, "src/app.py", tool="Read")
        self.hook(repo, "docs/target.md", tool="Read")
        st = self.status(repo)
        self.assertIn("GRAPH_DIRTY=NO", st)
        self.assertIn("PROJECT_STATE_DIRTY=NO", st)

    # PS9 — Stop with dirty state and no receipt
    def test_ps9_stop_dirty_without_flush(self):
        repo = self.mk_repo()
        self.write_state(repo)
        self.commit_all(repo, "persist")
        self.run_tool(CG_STATE, ["record-event", "TARGET_CHANGED"], repo=repo)
        out = self.stop(repo)
        self.assertIn("DURABLE_STATE_SYNC_REQUIRED", out)
        self.assertIn("STATE_FLUSH_REQUIRED", out)

    # PS10 — successful State Flush clears the gate
    def test_ps10_successful_state_flush(self):
        repo = self.mk_repo()
        head = self.commit_all(repo)
        self.write_state(repo, head=head)
        self.commit_all(repo, "persist state")  # flush includes durable commit
        head2 = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        self.run_tool(CG_STATE, ["record-event", "TARGET_CHANGED"], repo=repo)
        self.run_tool(CG_STATE, ["record-state-sync", "--head", head2], repo=repo)
        out = self.stop(repo)
        self.assertIn("STATE_FLUSH_GUARD=PASS", out)

    # PS11 — remote unavailable: DEFERRED semantics, work never blocked
    def test_ps11_remote_unavailable_deferred(self):
        repo = self.mk_repo()  # no origin configured
        self.write_state(repo, remote="", head="")  # deferred-mode index
        p = self.run_tool(str(VALIDATOR), [str(repo)], repo=repo)
        self.assertEqual(p.returncode, 0, p.stdout)
        g = self.guard(repo)
        self.assertIn("PROJECT_CONTINUITY_INITIALIZED", g)
        self.assertIn("REMOTE_STATE_SYNC=DEFERRED", g)

    # PS12 — CROSS-AGENT RESTORE: fresh Agent B recovers from remote only
    def test_ps12_cross_agent_restore_from_remote(self):
        # Agent A: initialize, flush, push
        repo = self.mk_repo(with_remote=True)
        head = self.commit_all(repo)
        self.write_state(repo, remote="https://example.org/org/repo.git", head=head,
                         recovery_snapshot={
                             "last_verified_remote_sha": head,
                             "last_state_flush_reason": "HANDOFF",
                             "last_state_flush_at": "2026-09-06T00:00:00Z",
                             "legal_frontier_summary": "stage-1 merged",
                             "blocker_refs": [],
                             "next_legal_action": "stage-2-grounding-for-T2"})
        self.commit_all(repo, "persist state")
        git(["push", "-u", "origin", "main"], str(repo))
        pushed = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        # Agent B: fresh clone, restore without any human history replay
        clone = self.base / "agent-b-clone"
        subprocess.run(["git", "clone", str(self.base / "repo-remote.git"), str(clone)],
                       capture_output=True, check=True)
        g = self.run_tool(GUARD, repo=clone, stdin_data=json.dumps({"cwd": str(clone)})).stdout
        self.assertIn("PROJECT_CONTINUITY_INITIALIZED=YES", g)
        self.assertIn("CONTRACT_VERSION=1", g)
        # Agent B sees A's persisted recovery snapshot verbatim (no human replay):
        self.assertIn(head, g)  # LAST_VERIFIED_REMOTE_SHA survived the agent switch
        self.assertEqual(
            git(["rev-parse", "origin/main"], str(clone)).stdout.strip(), pushed)
        state = json.loads((clone / ".agent" / "project-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["recovery_snapshot"]["next_legal_action"],
                         "stage-2-grounding-for-T2")

    # PS13 — contract version migration semantics
    def test_ps13_contract_version_migration(self):
        repo = self.mk_repo()
        self.write_state(repo)
        agent = repo / ".agent" / "project-state.json"
        data = json.loads(agent.read_text(encoding="utf-8"))
        data["contract_version"] = 0  # older compatible → SAFE_MIGRATION
        agent.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("SAFE_MIGRATION", self.guard(repo))
        data["contract_version"] = 2  # unknown newer → never destroy silently
        agent.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("PROJECT_STATE_CONTRACT_MIGRATION_REQUIRED", self.guard(repo))

    # PS14 — local absolute paths rejected from committed state
    def test_ps14_absolute_path_rejection(self):
        repo = self.mk_repo()
        self.write_state(repo, canonical_documents={
            "targets": ["/home/dev/elsewhere/target.md"], "specs": ["NONE"],
            "architecture": ["NONE"], "adrs": ["NONE"], "spikes": ["NONE"],
            "environment": ["NONE"]})
        p = self.run_tool(str(VALIDATOR), [str(repo)], repo=repo)
        self.assertEqual(p.returncode, 1)
        self.assertIn("no-local-absolute-paths", p.stdout)

    # PS15 — secret-like fields rejected (RULES R2 layer 1)
    def test_ps15_secret_like_field_rejection(self):
        repo = self.mk_repo()
        fake = "ghp_" + "a" * 30  # built, never literal: keep the repo scanner-clean
        self.write_state(repo, codegraph_policy={
            "applicability": "REQUIRED", "lifecycle": "INIT_ONCE_SYNC_CONTINUOUSLY",
            "notes": "leaked " + fake})
        p = self.run_tool(str(VALIDATOR), [str(repo)], repo=repo)
        self.assertEqual(p.returncode, 1)
        self.assertIn("no-secret-like-fields", p.stdout)


class CodeGraphLifecycleTests(ContinuityBase):
    def fake_index(self, repo):
        (repo / ".codegraph").mkdir(exist_ok=True)

    # CG1 — healthy index, no change → no sync / no init
    def test_cg1_healthy_no_change(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        out = self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout
        self.assertIn("NO_SYNC", out)
        self.assertIn("NO_INIT_REQUIRED", out)
        self.assertNotIn("INIT_ONCE_ALLOWED", out)
        self.assertIn("GRAPH_DIRTY=NO", self.status(repo))

    # CG2/CG3 — edits mark dirty, repeatedly, without any sync
    def test_cg2_cg3_repeated_edits_dirty_only(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.hook(repo, "src/app.py")
        self.hook(repo, "src/app.py")
        st = self.run_tool(CG_STATE, ["status"], repo=repo).stdout
        self.assertIn("GRAPH_DIRTY=YES", st)
        # no sync bookkeeping was written by the dirty markers
        for line in st.splitlines():
            if line.startswith("LAST_SYNC_HEAD="):
                self.assertEqual(line, "LAST_SYNC_HEAD=")

    # CG4 — query while dirty → sync ONCE, then NO_SYNC
    def test_cg4_query_while_dirty_sync_once(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.hook(repo, "src/app.py")
        self.assertIn("CODEGRAPH_SYNC_REQUIRED_ONCE",
                      self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout)
        head = self.commit_all(repo)
        self.run_tool(CG_STATE, ["mark-graph-synced", "--head", head], repo=repo)
        out = self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout
        self.assertIn("NO_SYNC", out)

    # CG5 — missing index on a code repo → init allowed once
    def test_cg5_missing_index_init_once(self):
        repo = self.mk_repo()
        out = self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout
        self.assertIn("CODEGRAPH_INDEX_MISSING", out)
        self.assertIn("INIT_ONCE_ALLOWED", out)

    # CG6 — existing index → full init prohibited
    def test_cg6_existing_index_init_prohibited(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.hook(repo, "src/app.py")  # even dirty
        out = self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout
        self.assertIn("NO_INIT_REQUIRED", out)
        self.assertNotIn("INIT_ONCE_ALLOWED", out)

    # CG7 — branch switch means incremental sync, never init
    def test_cg7_branch_switch_incremental(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.commit_all(repo)
        git(["checkout", "-b", "feature/x"], str(repo))
        self.hook(repo, "src/app.py")
        out = self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout
        self.assertIn("CODEGRAPH_SYNC_REQUIRED_ONCE", out)
        self.assertNotIn("INIT_ONCE_ALLOWED", out)

    # CG8 — sync failure must not fall back to full init (stop guard stays honest)
    def test_cg8_sync_failure_no_full_init_fallback(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.hook(repo, "src/app.py")
        # agent attempts sync and it fails: flag stays dirty; re-check still incremental
        self.assertIn("CODEGRAPH_SYNC_REQUIRED_ONCE",
                      self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout)
        self.assertNotIn("INIT_ONCE_ALLOWED",
                         self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout)
        stop_out = self.stop(repo)
        self.assertIn("CODEGRAPH_SYNC_REQUIRED_BEFORE_STOP", stop_out)

    # CG9 — two worktrees have isolated dirty state
    def test_cg9_worktree_isolation(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        git(["worktree", "add", str(repo.parent / "wt2"), "-b", "wt2"], str(repo))
        wt2 = repo.parent / "wt2"
        self.hook(repo, "src/app.py")
        self.assertIn("GRAPH_DIRTY=YES", self.status(repo))
        self.assertIn("GRAPH_DIRTY=NO", self.status(wt2))
        self.hook(wt2, "src/other.py")
        self.assertIn("GRAPH_DIRTY=YES", self.status(wt2))
        self.run_tool(CG_STATE, ["mark-graph-synced"], repo=repo)
        self.assertIn("GRAPH_DIRTY=NO", self.status(repo))
        self.assertIn("GRAPH_DIRTY=YES", self.status(wt2))

    # CG10 — MEDIUM production write without grounding receipt → blocked
    def test_cg10_medium_write_without_grounding_blocked(self):
        repo = self.mk_repo()
        p = self.run_tool(GROUND_GUARD, ["--file", "src/app.py", "--risk", "MEDIUM"], repo=repo)
        self.assertEqual(p.returncode, 2)
        self.assertIn("GROUNDING_GUARD_DECISION=BLOCK", p.stdout)
        self.assertIn("CODEGRAPH_GROUNDING_REQUIRED", p.stdout)

    # CG11 — grounding receipt present → write allowed
    def test_cg11_grounding_present_write_allowed(self):
        repo = self.mk_repo()
        head = self.commit_all(repo)
        self.run_tool(CG_STATE, ["set-grounding", "--ticket", "T-1", "--risk", "MEDIUM",
                            "--base-sha", head, "--mode", "graph",
                            "--seam", "src/app.py"], repo=repo)
        p = self.run_tool(GROUND_GUARD, ["--file", "src/app.py", "--risk", "MEDIUM"], repo=repo)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("GROUNDING_GUARD_DECISION=ALLOW", p.stdout)

    # CG12 — CodeGraph unavailable → MANUAL grounding receipt unblocks (Mode C)
    def test_cg12_unavailable_manual_fallback(self):
        repo = self.mk_repo()
        head = self.commit_all(repo)
        self.run_tool(CG_STATE, ["set-grounding", "--ticket", "T-2", "--risk", "MEDIUM",
                            "--base-sha", head, "--mode", "manual"], repo=repo)
        p = self.run_tool(GROUND_GUARD, ["--file", "src/app.py", "--risk", "MEDIUM"], repo=repo)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("GROUNDING_GUARD_DECISION=ALLOW_MANUAL", p.stdout)
        self.assertIn("MANUAL_GROUNDING_RECEIPT", p.stdout)
        # stale base always blocks, even with a receipt
        self.run_tool(CG_STATE, ["set-grounding", "--ticket", "T-3", "--risk", "HIGH",
                            "--base-sha", "0" * 40, "--mode", "graph"], repo=repo)
        p = self.run_tool(GROUND_GUARD, ["--file", "src/app.py", "--risk", "HIGH"], repo=repo)
        self.assertEqual(p.returncode, 2)
        self.assertIn("GROUNDING_RECEIPT_STALE", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
