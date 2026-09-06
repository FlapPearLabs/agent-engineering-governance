#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PROJECT_CONTINUITY_CONTRACT_V1 — synthetic test matrix (contract §12).

Runs the adapter hooks + project-state validator against throwaway synthetic
repos (temp dirs, deleted afterwards). Never touches any product repository.
Needs only git + python stdlib — the hooks never invoke CodeGraph themselves.

  PS1-PS18   project-state lifecycle (16 methods; PS3/PS4 and PS5-PS7 combined)
  CG1-CG14   CodeGraph lifecycle & grounding (13 methods)
  LC1-LC15   lifecycle decision surface (15 methods; init once / sync /
             grounding + blast radius / never re-init per session)
  → 44 tests total. PS12 = CROSS-AGENT RESTORE (Agent A flush → remote →
    fresh Agent B clone). Review-driven: F1 mode A/B lanes (LC11/LC12),
    F2 fail-closed blast radius (LC13), F3 edit-surface authority (LC14),
    F4 structural receipts (CG14), F5 durability ladder (PS17),
    F6 index shape validation (PS18), F7 record-init honesty (LC15).

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
LC = str(HOOKS / "codegraph_lifecycle.py")


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

    def full_ground(self, repo, ticket="T-1", risk="MEDIUM", mode="manual", base=None,
                    extra=None):
        """Store a structurally COMPLETE §7 receipt (review F4: every field must
        exist; NONE/UNKNOWN are honest-gap values). Returns (proc, base_sha)."""
        head = base if base else git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        fields = {
            "GRAPH_BASE_SHA": head, "TARGET_SEAM": "src/app.py",
            "DIRECT_TARGETS": "src/app.py", "UPSTREAM_PRODUCERS": "NONE",
            "CALLERS": "UNKNOWN", "CALLEES": "UNKNOWN", "DOWNSTREAM_CONSUMERS": "NONE",
            "IMPACT": "NONE", "AFFECTED": "src/app.py", "STATE_OWNER": "NONE",
            "IDENTITY_OWNER": "NONE", "VALIDATION_OWNER": "NONE",
            "EXPECTED_EDIT_SURFACE": "src/app.py", "OUT_OF_SCOPE": "docs/",
        }
        if extra:
            fields.update(extra)
        args = ["set-grounding", "--ticket", ticket, "--risk", risk,
                "--base-sha", head, "--mode", mode]
        for k, v in fields.items():
            args += ["--field", "%s=%s" % (k, v)]
        return self.run_tool(CG_STATE, args, repo=repo), head


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
        data["contract_version"] = 0  # pre-contract stub → SAFE_MIGRATION (regenerate)
        agent.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("SAFE_MIGRATION", self.guard(repo))
        data["contract_version"] = 2  # unknown newer → never destroy silently
        agent.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("PROJECT_STATE_CONTRACT_MIGRATION_REQUIRED", self.guard(repo))
        data["contract_version"] = -1  # nonsense int → not auto-migrated either
        agent.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("PROJECT_STATE_CONTRACT_MIGRATION_REQUIRED", self.guard(repo))
        data["contract_version"] = "1"  # wrong type → not trusted as supported
        agent.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("PROJECT_STATE_CONTRACT_MIGRATION_REQUIRED", self.guard(repo))
        data["contract_version"] = True  # JSON bool aliases int in Python — must not pass
        agent.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("PROJECT_STATE_CONTRACT_MIGRATION_REQUIRED", self.guard(repo))
        p = self.run_tool(str(VALIDATOR), [str(repo)], repo=repo)
        self.assertEqual(p.returncode, 1)
        self.assertIn("contract-version-supported", p.stdout)

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
        # backslash-form traversal is equally rejected
        self.write_state(repo, canonical_documents={
            "targets": ["docs\\..\\..\\elsewhere\\target.md"], "specs": ["NONE"],
            "architecture": ["NONE"], "adrs": ["NONE"], "spikes": ["NONE"],
            "environment": ["NONE"]})
        p = self.run_tool(str(VALIDATOR), [str(repo)], repo=repo)
        self.assertEqual(p.returncode, 1)
        self.assertIn("no-local-absolute-paths", p.stdout)

    # PS16 — recovery snapshot required keys cannot be silently omitted
    def test_ps16_recovery_snapshot_required_keys(self):
        repo = self.mk_repo()
        self.write_state(repo)
        agent = repo / ".agent" / "project-state.json"
        data = json.loads(agent.read_text(encoding="utf-8"))
        del data["recovery_snapshot"]["next_legal_action"]
        del data["recovery_snapshot"]["last_verified_remote_sha"]
        agent.write_text(json.dumps(data), encoding="utf-8")
        p = self.run_tool(str(VALIDATOR), [str(repo)], repo=repo)
        self.assertEqual(p.returncode, 1)
        self.assertIn("recovery-snapshot-required-keys", p.stdout)

    # PS14b — runtime-only state is rejected in ANY value shape (key-level scan)
    def test_ps14b_runtime_fields_rejected_any_shape(self):
        repo = self.mk_repo()
        self.write_state(repo)
        agent = repo / ".agent" / "project-state.json"
        data = json.loads(agent.read_text(encoding="utf-8"))
        data["recovery_snapshot"]["graph_dirty"] = True          # boolean shape
        data["recovery_snapshot"]["last_sync_head"] = 12345      # int shape
        agent.write_text(json.dumps(data), encoding="utf-8")
        p = self.run_tool(str(VALIDATOR), [str(repo)], repo=repo)
        self.assertEqual(p.returncode, 1)
        self.assertIn("no-runtime-only-fields", p.stdout)
        data["recovery_snapshot"] = {
            "last_verified_remote_sha": "", "last_state_flush_reason": "x",
            "last_state_flush_at": "", "legal_frontier_summary": "x",
            "blocker_refs": [], "next_legal_action": "x",
            "grounding_receipt": {"TICKET": "T-1", "RISK": "HIGH"}}  # dict shape
        agent.write_text(json.dumps(data), encoding="utf-8")
        p = self.run_tool(str(VALIDATOR), [str(repo)], repo=repo)
        self.assertEqual(p.returncode, 1)
        self.assertIn("no-runtime-only-fields", p.stdout)

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

    # PS17 — review F5: remote durability ladder + stale/unbound marker handling
    def test_ps17_remote_durability_ladder(self):
        repo = self.mk_repo(with_remote=True)
        head = self.commit_all(repo)
        self.write_state(repo, remote="https://example.org/org/repo.git", head=head)
        self.commit_all(repo, "persist")
        head2 = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        git(["push", "-u", "origin", "main"], str(repo))
        # (1) LOCAL_DURABLE only → the stop guard demands remote verification
        self.run_tool(CG_STATE, ["record-event", "TARGET_CHANGED"], repo=repo)
        self.run_tool(CG_STATE, ["record-state-sync", "--head", head2], repo=repo)
        out = self.stop(repo)
        self.assertIn("REMOTE_VERIFICATION_REQUIRED", out)
        self.assertNotIn("STATE_FLUSH_GUARD=PASS", out)
        # (2) REMOTE_VERIFIED bound to this HEAD → clean terminal
        self.run_tool(CG_STATE, ["record-state-sync", "--head", head2,
                                 "--remote-verified"], repo=repo)
        out = self.stop(repo)
        self.assertIn("STATE_FLUSH_GUARD=PASS", out)
        self.assertIn("REMOTE_VERIFIED=YES", out)
        # (3) a later meaningful transition invalidates the old receipt
        self.run_tool(CG_STATE, ["record-event", "ADR_CHANGED"], repo=repo)
        out = self.stop(repo)
        self.assertIn("DURABLE_STATE_SYNC_REQUIRED", out)
        # (4) DEFERRED is the other honest terminal
        self.run_tool(CG_STATE, ["record-state-sync", "--deferred"], repo=repo)
        out = self.stop(repo)
        self.assertIn("REMOTE_STATE_SYNC=DEFERRED", out)
        # (5) an UNBOUND env marker must not bypass a new transition (review F5)
        self.run_tool(CG_STATE, ["record-event", "SPEC_CHANGED"], repo=repo)
        env = hook_env(self.runtime)
        env["STATE_FLUSH_COMPLETED"] = "1"
        proc = subprocess.run([sys.executable, STOP_GUARD], cwd=str(repo),
                              input=json.dumps({"cwd": str(repo)}), capture_output=True,
                              text=True, timeout=60, errors="replace", env=env)
        self.assertIn("UNBOUND_FLUSH_MARKER", proc.stdout)
        self.assertIn("DURABLE_STATE_SYNC_REQUIRED", proc.stdout)
        # (6) a marker bound to a PREVIOUS HEAD is stale once HEAD moves
        self.run_tool(CG_STATE, ["record-state-sync", "--remote-verified"], repo=repo)
        git(["commit", "--allow-empty", "-m", "transition after flush"], str(repo))
        env["STATE_FLUSH_HEAD_SHA"] = head2
        proc = subprocess.run([sys.executable, STOP_GUARD], cwd=str(repo),
                              input=json.dumps({"cwd": str(repo)}), capture_output=True,
                              text=True, timeout=60, errors="replace", env=env)
        self.assertIn("STALE_FLUSH_MARKER", proc.stdout)
        self.assertNotIn("marker bound", proc.stdout)

    # PS18 — review F6: a current-version index missing normative fields is
    # INVALID — never PROJECT_CONTINUITY_INITIALIZED
    def test_ps18_invalid_current_contract_index(self):
        repo = self.mk_repo()
        # (1) missing required top key
        st = self.write_state(repo)
        del st["canonical_documents"]
        (repo / ".agent" / "project-state.json").write_text(
            json.dumps(st, indent=1), encoding="utf-8")
        g = self.guard(repo)
        self.assertIn("PROJECT_STATE_CONTRACT_INVALID", g)
        self.assertNotIn("PROJECT_CONTINUITY_INITIALIZED", g)
        # (2) missing required recovery-snapshot key
        st = self.write_state(repo)
        del st["recovery_snapshot"]["next_legal_action"]
        (repo / ".agent" / "project-state.json").write_text(
            json.dumps(st, indent=1), encoding="utf-8")
        self.assertIn("PROJECT_STATE_CONTRACT_INVALID", self.guard(repo))
        # (3) corrupt JSON → INVALID, never silently destroyed
        (repo / ".agent" / "project-state.json").write_text("{broken", encoding="utf-8")
        g = self.guard(repo)
        self.assertIn("PROJECT_STATE_CONTRACT_INVALID", g)
        self.assertIn("unparseable-json", g)


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

    # CG11 — grounding receipt present → write allowed (worker's own commits
    # after the receipt do NOT stale it: base stays an ancestor of HEAD)
    def test_cg11_grounding_present_write_allowed(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.full_ground(repo, ticket="T-1", risk="MEDIUM", mode="graph")
        p = self.run_tool(GROUND_GUARD, ["--file", "src/app.py", "--risk", "MEDIUM"], repo=repo)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("GROUNDING_GUARD_DECISION=ALLOW", p.stdout)
        self.commit_all(repo, "worker commit after grounding")  # HEAD descends from base
        p = self.run_tool(GROUND_GUARD, ["--file", "src/app.py", "--risk", "MEDIUM"], repo=repo)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("GROUNDING_GUARD_DECISION=ALLOW", p.stdout)

    # CG12 — CodeGraph unavailable → MANUAL grounding receipt unblocks (Mode C)
    def test_cg12_unavailable_manual_fallback(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.full_ground(repo, ticket="T-2", risk="MEDIUM", mode="manual")
        p = self.run_tool(GROUND_GUARD, ["--file", "src/app.py", "--risk", "MEDIUM"], repo=repo)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("GROUNDING_GUARD_DECISION=ALLOW_MANUAL", p.stdout)
        self.assertIn("MANUAL_GROUNDING_RECEIPT", p.stdout)
        # stale base always blocks, even with a receipt
        self.full_ground(repo, ticket="T-3", risk="HIGH", mode="graph", base="0" * 40)
        p = self.run_tool(GROUND_GUARD, ["--file", "src/app.py", "--risk", "HIGH"], repo=repo)
        self.assertEqual(p.returncode, 2)
        self.assertIn("GROUNDING_RECEIPT_STALE", p.stdout)

    # CG14 — review F4: a §7-incomplete receipt fails CLOSED even when the four
    # legacy keys are present (structural fields may be NONE/UNKNOWN, not absent)
    def test_cg14_structurally_incomplete_receipt_rejected(self):
        repo = self.mk_repo()
        head = self.commit_all(repo)
        self.run_tool(CG_STATE, ["set-grounding", "--ticket", "T-9", "--risk", "HIGH",
                                 "--base-sha", head, "--mode", "graph"], repo=repo)
        p = self.run_tool(GROUND_GUARD, ["--file", "src/app.py", "--risk", "HIGH"], repo=repo)
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn("GROUNDING_RECEIPT_INVALID", p.stdout)

    # CG13 — malformed receipts fail CLOSED; a real rebase (base leaving HEAD's
    # ancestry) stales an existing receipt
    def test_cg13_malformed_receipt_and_real_rebase(self):
        repo = self.mk_repo()
        head = self.commit_all(repo)
        # malformed receipt written straight into runtime state (hand-edit / drift)
        self.full_ground(repo, ticket="T-1", risk="MEDIUM", mode="graph")
        # truncate the receipt to make it malformed (missing required keys).
        # runtime_root() reads ZCODE_RUNTIME_STATE_DIR at call time, so point it
        # at the test's hermetic runtime dir — otherwise this writes into the
        # real ~/.zcode/runtime-state and breaks sandbox isolation.
        prev = os.environ.get("ZCODE_RUNTIME_STATE_DIR")
        os.environ["ZCODE_RUNTIME_STATE_DIR"] = str(self.runtime)

        def _restore():
            if prev is None:
                os.environ.pop("ZCODE_RUNTIME_STATE_DIR", None)
            else:
                os.environ["ZCODE_RUNTIME_STATE_DIR"] = prev
        self.addCleanup(_restore)

        sys.path.insert(0, str(HOOKS))
        import importlib
        cs = importlib.import_module("_continuity_state")
        sp = cs.state_path(str(repo))
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps({"grounding_receipt": {"TICKET": "T-1"}}), encoding="utf-8")
        p = self.run_tool(GROUND_GUARD, ["--file", "src/app.py", "--risk", "MEDIUM"], repo=repo)
        self.assertEqual(p.returncode, 2)
        self.assertIn("GROUNDING_RECEIPT_INVALID", p.stdout)
        # a valid receipt, then a real history rewrite (amend) → base leaves ancestry
        self.full_ground(repo, ticket="T-4", risk="MEDIUM", mode="graph")
        git(["commit", "--amend", "-m", "rewritten"], str(repo))
        p = self.run_tool(GROUND_GUARD, ["--file", "src/app.py", "--risk", "MEDIUM"], repo=repo)
        self.assertEqual(p.returncode, 2)
        self.assertIn("GROUNDING_RECEIPT_STALE", p.stdout)


class LifecycleDecisionTests(ContinuityBase):
    """LC1-LC15 — the single canonical lifecycle decision surface (contract §6.7).

    Rule under test:
        new repo → INIT_ONCE (once) / thereafter → INCREMENTAL_SYNC
        before editing → grounding + blast radius / after editing → mark dirty
        review/handoff/stop → incremental sync when needed
        never → a full init per session

    Review-driven semantics:
        F1  MODE A lanes reuse the canonical graph — no per-worktree full init;
            MODE B lanes own their graph and may init once per lane
        F2  blast radius fails CLOSED (UNRESOLVED blocks production writes)
        F3  untracked files cannot bypass the approved edit surface
        F7  record-init requires index health evidence
    """

    def fake_index(self, repo):
        (repo / ".codegraph").mkdir(exist_ok=True)

    def lc(self, repo, *args):
        return self.run_tool(LC, list(args), repo=repo).stdout

    def decide(self, repo, intent, **flags):
        args = ["decide", "--intent", intent]
        for k, v in flags.items():
            args += ["--" + k.replace("_", "-"), v]
        return self.lc(repo, *args)

    def ground(self, repo, ticket="T-1", risk="HIGH", mode="manual"):
        return self.full_ground(repo, ticket=ticket, risk=risk, mode=mode)[0]

    # LC1 — brand new repo: exactly one full init, then never again
    def test_lc1_new_repo_init_once_then_forbidden(self):
        repo = self.mk_repo()
        self.assertIn("CODEGRAPH_LIFECYCLE_DECISION=INIT_ONCE",
                      self.decide(repo, "session-start"))
        self.fake_index(repo)  # F7: record-init demands health evidence
        self.lc(repo, "record-init")
        self.assertIn("FULL_INIT_FORBIDDEN", self.decide(repo, "session-start",
                                                         request_full_init=""))
        # a second, unrelated session must not be offered a full init either
        out = self.decide(repo, "session-start")
        self.assertNotIn("INIT_ONCE", out)
        self.assertIn("NO_SYNC", out)

    # LC2 — session start on an initialized repo is never INIT_ONCE
    def test_lc2_session_start_never_reinits(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.lc(repo, "record-init")
        for _ in range(3):  # three consecutive sessions
            out = self.decide(repo, "session-start")
            self.assertNotIn("INIT_ONCE", out)
        self.assertIn("NO_SYNC", self.decide(repo, "session-start"))

    # LC3 — a pre-existing index is enough to refuse a requested full init
    def test_lc3_existing_index_refuses_full_init(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        out = self.decide(repo, "session-start", request_full_init="")
        self.assertIn("FULL_INIT_FORBIDDEN", out)
        self.assertNotIn("INIT_ONCE", out)

    # LC4 — before a MEDIUM/HIGH production write: grounding first
    def test_lc4_pre_edit_requires_grounding(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        out = self.decide(repo, "pre-edit", risk="HIGH", file="src/app.py")
        self.assertIn("GROUNDING_REQUIRED", out)
        # LOW risk on a production file stays allowed (no over-gating)
        self.assertIn("ALLOW_WRITE", self.decide(repo, "pre-edit", risk="LOW",
                                                 file="src/app.py"))

    # LC5 — grounded but no blast radius → blast radius required
    def test_lc5_pre_edit_requires_blast_radius(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.ground(repo)
        out = self.decide(repo, "pre-edit", risk="HIGH", file="src/app.py")
        self.assertIn("BLAST_RADIUS_REQUIRED", out)
        self.assertNotIn("ALLOW_WRITE", out)

    # LC6 — inside the blast radius: allowed; outside: expansion required
    def test_lc6_blast_radius_boundary(self):
        repo = self.mk_repo()
        (repo / "src" / "other.py").write_text("def h():\n    pass\n", encoding="utf-8")
        self.commit_all(repo)
        self.fake_index(repo)
        self.ground(repo)
        base = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        self.lc(repo, "blast-radius", "--base", base, "--target", "src/app.py")
        self.assertIn("ALLOW_WRITE", self.decide(repo, "pre-edit", risk="HIGH",
                                                 file="src/app.py"))
        out = self.decide(repo, "pre-edit", risk="HIGH", file="src/other.py")
        self.assertIn("BLAST_RADIUS_EXPANSION_REQUIRED", out)

    # LC7 — after editing: mark dirty only; sync deferred to a sync intent
    def test_lc7_post_edit_marks_dirty_only(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.assertIn("MARK_DIRTY", self.decide(repo, "post-edit"))
        self.hook(repo, "src/app.py")  # real PostToolUse marker
        self.assertIn("GRAPH_DIRTY=YES", self.status(repo))
        for intent in ("query", "review", "handoff", "stop"):
            self.assertIn("INCREMENTAL_SYNC_ONCE", self.decide(repo, intent))

    # LC8 — review/handoff/stop sync once, then the graph is clean again
    def test_lc8_sync_intents_sync_once_then_clean(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.hook(repo, "src/app.py")
        self.assertIn("INCREMENTAL_SYNC_ONCE", self.decide(repo, "handoff"))
        self.lc(repo, "record-sync-result", "--ok")
        self.assertIn("NO_SYNC", self.decide(repo, "review"))
        self.assertIn("GRAPH_DIRTY=NO", self.status(repo))

    # LC9 — a failed sync is reported honestly and never escalates to a full init
    def test_lc9_sync_failure_never_escalates_to_init(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.hook(repo, "src/app.py")
        self.lc(repo, "record-sync-result", "--fail")
        for intent in ("query", "review", "handoff", "stop"):
            out = self.decide(repo, intent)
            self.assertIn("SYNC_FAILED_DEFERRED", out)
            self.assertNotIn("INIT_ONCE", out)
        # and the invariant checker agrees
        self.assertEqual(0, self.run_tool(LC, ["verify"], repo=repo, expect=0).returncode)

    # LC10 — invariant self-check passes in both fresh and dirty/initialized states
    def test_lc10_invariants_hold(self):
        repo = self.mk_repo()
        p = self.run_tool(LC, ["verify"], repo=repo, expect=0)
        self.assertIn("LIFECYCLE_INVARIANTS=PASS", p.stdout)
        self.fake_index(repo)
        self.lc(repo, "record-init")
        self.hook(repo, "src/app.py")  # dirty + initialized
        p = self.run_tool(LC, ["verify"], repo=repo, expect=0)
        self.assertIn("LIFECYCLE_INVARIANTS=PASS", p.stdout)
        self.assertNotIn("VIOLATION", p.stdout)

    # LC11 — MODE A: the canonical graph is initialized once per REPO; ordinary
    # worktree lanes reuse the base graph + delta-by-diff (review F1)
    def test_lc11_mode_a_lane_never_reinits(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.fake_index(repo)
        self.lc(repo, "record-init")            # canonical record in the main checkout
        wt = self.base / "wt-b"
        git(["worktree", "add", "-b", "feature/lc", str(wt)], str(repo))
        out = self.decide(wt, "session-start")  # ordinary MODE A lane, no lane index
        self.assertNotIn("INIT_ONCE", out)
        self.assertIn("MODE A", out)
        self.assertIn("FULL_INIT_FORBIDDEN",
                      self.decide(wt, "session-start", request_full_init=""))

    # LC12 — MODE B (explicit candidate-exact): lane-local graph, init once per lane
    def test_lc12_mode_b_lane_init_once(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.fake_index(repo)
        self.lc(repo, "record-init")            # canonical registered
        wt = self.base / "wt-b"
        git(["worktree", "add", "-b", "feature/lcb", str(wt)], str(repo))
        # lane graph missing → the lane may init its own graph EXACTLY ONCE
        self.assertIn("INIT_ONCE", self.decide(wt, "session-start", lane_mode="B"))
        (wt / ".codegraph").mkdir(exist_ok=True)
        out = self.run_tool(LC, ["record-init", "--lane"], repo=wt).stdout
        self.assertIn("GRAPH_INIT_RECORDED scope=lane", out)
        # lane initialized → no more lane init offers
        self.assertIn("FULL_INIT_FORBIDDEN", self.decide(wt, "session-start", lane_mode="B"))
        # …while a fresh MODE B lane elsewhere would still legitimately INIT_ONCE
        wt2 = self.base / "wt-c"
        git(["worktree", "add", "-b", "feature/lcc", str(wt2)], str(repo))
        self.assertIn("INIT_ONCE", self.decide(wt2, "session-start", lane_mode="B"))

    # LC13 — blast radius fails CLOSED (review F2)
    def test_lc13_blast_radius_fail_closed(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.fake_index(repo)
        self.ground(repo)
        # (1) invalid / unresolvable BASE_SHA → UNRESOLVED recorded → write blocked
        out = self.lc(repo, "blast-radius", "--base", "deadbeef" * 5, "--target", "src/app.py")
        self.assertIn("mode=UNRESOLVED", out)
        self.assertIn("BLAST_RADIUS_REQUIRED",
                      self.decide(repo, "pre-edit", risk="HIGH", file="src/app.py"))
        # (2) git cannot see uncommitted changes → UNRESOLVED (in-process mock)
        sys.path.insert(0, str(HOOKS))
        import importlib
        cl = importlib.import_module("codegraph_lifecycle")
        orig_git = cl._git

        class Failing:
            returncode = 128
            stdout = ""

        cl._git = lambda args, cwd, timeout=10: (
            Failing() if args[:1] == ["status"] else orig_git(args, cwd, timeout))
        try:
            rec, err = cl.compute_blast_radius(str(repo), "HEAD")
        finally:
            cl._git = orig_git
        self.assertFalse(rec["resolved"])
        self.assertEqual("UNRESOLVED", rec["mode"])
        # (3) no base at all → nothing provable → UNRESOLVED
        rec2, _ = cl.compute_blast_radius(str(repo), "")
        self.assertFalse(rec2["resolved"])
        self.assertEqual("UNRESOLVED", rec2["mode"])

    # LC14 — untracked files cannot bypass the edit surface (review F3)
    def test_lc14_untracked_no_bypass(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.fake_index(repo)
        self.ground(repo)
        base = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        self.lc(repo, "blast-radius", "--base", base, "--target", "src/app.py")
        # brand-new UNTRACKED file outside the approved surface → BLOCK
        (repo / "src" / "unrelated.py").write_text("x = 1\n", encoding="utf-8")
        out = self.decide(repo, "pre-edit", risk="HIGH", file="src/unrelated.py")
        self.assertIn("BLAST_RADIUS_EXPANSION_REQUIRED", out)
        # explicitly expand the intended edit surface → recompute → ALLOW
        self.lc(repo, "blast-radius", "--base", base, "--target", "src/app.py",
                "--target", "src/expected_new.py")
        (repo / "src" / "expected_new.py").write_text("y = 2\n", encoding="utf-8")
        out = self.decide(repo, "pre-edit", risk="HIGH", file="src/expected_new.py")
        self.assertIn("ALLOW_WRITE", out)

    # LC15 — record-init honesty (review F7)
    def test_lc15_record_init_requires_index_evidence(self):
        repo = self.mk_repo()
        out = self.run_tool(LC, ["record-init"], repo=repo).stdout
        self.assertIn("ERROR=GRAPH_INIT_REJECTED", out)
        # the repo is NOT locked: the one-time init offer stays available
        self.assertIn("INIT_ONCE", self.decide(repo, "session-start"))
        self.fake_index(repo)
        self.assertIn("GRAPH_INIT_RECORDED",
                      self.run_tool(LC, ["record-init"], repo=repo).stdout)
        self.assertIn("FULL_INIT_FORBIDDEN",
                      self.decide(repo, "session-start", request_full_init=""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
