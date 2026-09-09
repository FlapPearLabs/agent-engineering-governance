#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PROJECT_CONTINUITY_CONTRACT_V1 — synthetic test matrix (contract §12).

Runs the adapter hooks + project-state validator against throwaway synthetic
repos (temp dirs, deleted afterwards). Never touches any product repository.
Needs only git + python stdlib — the hooks never invoke CodeGraph themselves.

  PS1-PS20   project-state lifecycle (18 methods; PS3/PS4 and PS5-PS7 combined)
  CG1-CG15   CodeGraph lifecycle & grounding (14 methods)
  LC1-LC21   lifecycle decision surface (21 methods; init once / sync /
             grounding + blast radius / never re-init per session)
  R6         convergence repair regressions (PR #5 review round 6):
             F1 stop marker is evidence not an issue / F2 record-init
             write-once + record-rebuild recovery path / F3 Bash pre-grounding
             allowlist + mechanical source delta / F4 approved vs observed
             surface / F5 Mode A base coherence / F6 corrupt-graph rebuild
             state / F7 receipt HEAD binding + NUL diff path exactness
  R61        final convergence patch (review round 6.1): Bash receipt
             validation (partial/stale BLOCK, complete fresh ALLOW) + trusted
             set-grounding bootstrap end-to-end / Mode A REVIEW coherence +
             MODE C escape + CODEGRAPH_UNAVAILABLE classification /
             UNAPPROVED_DELTA runtime gate on writes + review
  → 67 tests total (62 through R6 + 5 R6.1). PS12 = CROSS-AGENT RESTORE (Agent A flush → remote →
    fresh Agent B clone). Review-driven: F1 mode A/B lanes (LC11/LC12),
    F2 fail-closed blast radius (LC13), F3 edit-surface authority (LC14),
    F4 structural receipts (CG14), F5 durability ladder (PS17),
    F6 index shape validation (PS18), F7 record-init honesty (LC15);
    R4 single decision surface (CG15), all-intents lane invariant (LC16),
    health-proof + init scope (LC17), deferred authority + marker
    no-bypass (PS19); R5 graph-owner-head freshness (LC18 + LC-INV7),
    MODE A candidate-delta semantics (CG9/LC19), NUL-safe porcelain
    parsing (LC20), remote-required stop + receipt HEAD binding (PS10/
    PS11/PS20), record-init owner-SHA binding (LC21).

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
BASH_GUARD = str(HOOKS / "bash_preflight_guard.py")


def git(args, cwd, timeout=30):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, errors="replace")


def hook_env(runtime_dir):
    env = os.environ.copy()
    env["ZCODE_RUNTIME_STATE_DIR"] = str(runtime_dir)
    # review R4-D: the synthetic matrix mocks the record-init health probe
    # (production default = the real `codegraph status` CLI). The mock treats a
    # .codegraph/index.meta.json marker as health evidence, so an EMPTY
    # .codegraph directory is still honestly rejected in tests.
    env["ZCODE_CODEGRAPH_HEALTH_CMD"] = _HEALTHY_PROBE
    env.pop("ZCODE_PROJECT_DIR", None)
    env.pop("ZCODE_TICKET_RISK", None)
    env.pop("STATE_FLUSH_COMPLETED", None)
    env.pop("PROJECT_STATE_SYNC_COMPLETED", None)
    return env


_HEALTHY_PROBE_CODE = ("import sys, os; sys.exit(0 if os.path.isfile("
                       "os.path.join('.codegraph', 'index.meta.json')) else 1)")
_HEALTHY_PROBE = '"%s" -c "%s"' % (sys.executable, _HEALTHY_PROBE_CODE)


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

    def run_tool(self, script, args=(), repo=None, stdin_data="", expect=None,
                 extra_env=None):
        env = hook_env(self.runtime)
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, script] + list(args), cwd=str(repo or self.base),
            input=stdin_data, capture_output=True, text=True, timeout=60,
            errors="replace", env=env)
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

    def stop(self, repo, extra_env=None):
        return self.run_tool(STOP_GUARD, repo=repo, stdin_data=json.dumps({"cwd": str(repo)}),
                             extra_env=extra_env).stdout

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
        # review R6-F7a: a durability receipt binds the CURRENT git HEAD — the
        # repo must have at least one commit (resolvable HEAD) for
        # record-state-sync to record anything (fail-closed otherwise).
        self.commit_all(repo, "bootstrap HEAD")
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

    # PS10 — successful State Flush clears the gate (review R5-F4: remote
    # semantics — a governed repo ends REMOTE_VERIFIED, never "no remote → PASS")
    def test_ps10_successful_state_flush(self):
        repo = self.mk_repo(with_remote=True)
        head = self.commit_all(repo)
        self.write_state(repo, remote="https://example.org/org/repo.git", head=head)
        self.commit_all(repo, "persist state")  # flush includes durable commit
        head2 = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        git(["push", "-u", "origin", "main"], str(repo))
        self.run_tool(CG_STATE, ["record-event", "TARGET_CHANGED"], repo=repo)
        self.run_tool(CG_STATE, ["record-state-sync", "--head", head2], repo=repo)
        # LOCAL_DURABLE alone is not a clean stop (remote required)
        out = self.stop(repo)
        self.assertIn("REMOTE_VERIFICATION_REQUIRED", out)
        self.assertNotIn("STATE_FLUSH_GUARD=PASS", out)
        # remote-verified receipt bound to this HEAD → the honest clean terminal
        self.run_tool(CG_STATE, ["record-state-sync", "--head", head2,
                                 "--remote-verified"], repo=repo)
        out = self.stop(repo)
        self.assertIn("STATE_FLUSH_GUARD=PASS", out)
        self.assertIn("REMOTE_VERIFIED=YES", out)

    # PS11 — remote unavailable: DEFERRED semantics, work never blocked.
    # Review R5-F4: SessionStart AND Stop use the SAME remote semantics —
    # a no-remote Stop is NOT a PASS (REMOTE_REQUIRED); the honest terminal
    # is a no-remote DEFERRED failure receipt bound to HEAD.
    def test_ps11_remote_unavailable_deferred(self):
        repo = self.mk_repo()  # no origin configured
        self.write_state(repo, remote="", head="")  # deferred-mode index
        p = self.run_tool(str(VALIDATOR), [str(repo)], repo=repo)
        self.assertEqual(p.returncode, 0, p.stdout)
        g = self.guard(repo)
        self.assertIn("PROJECT_CONTINUITY_INITIALIZED", g)
        self.assertIn("REMOTE_STATE_SYNC=DEFERRED", g)
        # Stop side: same remote semantics
        self.commit_all(repo, "bootstrap")
        out = self.stop(repo)
        self.assertIn("REMOTE_REQUIRED", out)
        self.assertNotIn("STATE_FLUSH_GUARD=PASS", out)
        head = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        self.run_tool(CG_STATE, ["record-state-sync", "--deferred", "--head", head,
                                 "--remote-operation", "git push origin main",
                                 "--failure-class", "REMOTE_NOT_CONFIGURED",
                                 "--attempted-at", "2026-09-08T00:00:00Z"], repo=repo)
        out = self.stop(repo)
        self.assertIn("STATE_FLUSH_GUARD=PASS", out)
        self.assertIn("REMOTE_STATE_SYNC=DEFERRED", out)

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
        # (4) DEFERRED is the other honest terminal — WITH a failure receipt
        #     (review R4-A1: a naked --deferred is rejected outright, see PS19)
        self.run_tool(CG_STATE, ["record-state-sync", "--deferred", "--head", head2,
                                 "--remote-operation", "git push origin main",
                                 "--failure-class", "NETWORK_TIMEOUT",
                                 "--attempted-at", "2026-09-07T00:00:00Z"], repo=repo)
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

    # PS19 — review R4-A1/A2: DEFERRED needs a real failure receipt; a bound
    # flush marker is EVIDENCE, never a bypass
    def test_ps19_deferred_authority_and_marker_no_bypass(self):
        repo = self.mk_repo(with_remote=True)
        head = self.commit_all(repo)
        self.write_state(repo, remote="https://example.org/org/repo.git", head=head)
        self.commit_all(repo, "persist")
        head2 = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        git(["push", "-u", "origin", "main"], str(repo))
        self.run_tool(CG_STATE, ["record-event", "TARGET_CHANGED"], repo=repo)
        # (A1-1) naked --deferred on a REACHABLE remote → rejected, rc=2
        p = self.run_tool(CG_STATE, ["record-state-sync", "--deferred"], repo=repo, expect=2)
        self.assertIn("ERROR=REMOTE_DEFERRED_EVIDENCE_REQUIRED", p.stdout)
        # no deferred receipt was persisted (state untouched) → guard still blocks
        out = self.stop(repo)
        self.assertNotIn("REMOTE_STATE_SYNC=DEFERRED", out)
        self.assertIn("DURABLE_STATE_SYNC_REQUIRED", out)
        # (A1-2) a full failure receipt (HEAD_SHA/REMOTE_OPERATION/FAILURE_CLASS/
        # ATTEMPTED_AT) → DEFERRED accepted as the honest terminal
        self.run_tool(CG_STATE, ["record-state-sync", "--deferred", "--head", head2,
                                 "--remote-operation", "git push origin main",
                                 "--failure-class", "NETWORK_TIMEOUT",
                                 "--attempted-at", "2026-09-07T00:00:00Z"], repo=repo)
        self.assertIn("REMOTE_STATE_SYNC=DEFERRED", self.stop(repo))
        # (A2) a marker bound to the CURRENT HEAD is still NOT a bypass —
        # re-dirty the project state first, then flush-marker with exact binding
        self.run_tool(CG_STATE, ["record-event", "SPEC_CHANGED"], repo=repo)
        env = hook_env(self.runtime)
        env["STATE_FLUSH_COMPLETED"] = "1"
        env["STATE_FLUSH_HEAD_SHA"] = head2
        proc = subprocess.run([sys.executable, STOP_GUARD], cwd=str(repo),
                              input=json.dumps({"cwd": str(repo)}), capture_output=True,
                              text=True, timeout=60, errors="replace", env=env)
        self.assertIn("BOUND_FLUSH_MARKER", proc.stdout)
        self.assertIn("DURABLE_STATE_SYNC_REQUIRED", proc.stdout)
        self.assertNotIn("STATE_FLUSH_GUARD=PASS", proc.stdout)

    # PS20 — review R5-F4/F6: REMOTE IS REQUIRED, NOT OPTIONAL; terminal
    # durability receipts fail CLOSED on HEAD binding (missing binding or a
    # moved HEAD must never PASS — transient broken HEAD refs are realistic)
    def test_ps20_remote_required_and_receipt_head_binding(self):
        # (F4) no remote + no receipt → NOT a clean stop
        repo = self.mk_repo()  # no origin
        self.commit_all(repo)
        self.write_state(repo, remote="", head="")
        self.commit_all(repo, "persist")
        out = self.stop(repo)
        self.assertIn("REMOTE_REQUIRED", out)
        self.assertNotIn("STATE_FLUSH_GUARD=PASS", out)
        # (F6-1) remote-backed: a REMOTE_VERIFIED receipt WITHOUT a HEAD
        # binding (hand-edited / drifted state) must never PASS
        repo2 = self.mk_repo(name="repo2", with_remote=True)
        head = self.commit_all(repo2)
        self.write_state(repo2, remote="https://example.org/org/repo2.git", head=head)
        self.commit_all(repo2, "persist")
        head2 = git(["rev-parse", "HEAD"], str(repo2)).stdout.strip()
        git(["push", "-u", "origin", "main"], str(repo2))
        self.run_tool(CG_STATE, ["record-state-sync", "--head", head2,
                                 "--remote-verified"], repo=repo2)
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
        sp = cs.state_path(str(repo2))
        data = json.loads(sp.read_text(encoding="utf-8"))
        del data["remote_durability"]["head_sha"]  # strip the HEAD binding
        sp.write_text(json.dumps(data), encoding="utf-8")
        out = self.stop(repo2)
        self.assertIn("REMOTE_RECEIPT_INVALID", out)
        self.assertNotIn("STATE_FLUSH_GUARD=PASS", out)
        # (F6-2) a receipt bound to a HEAD that has since moved → INVALID
        self.run_tool(CG_STATE, ["record-state-sync", "--head", head2,
                                 "--remote-verified"], repo=repo2)
        git(["commit", "--amend", "-m", "rewritten"], str(repo2))
        out = self.stop(repo2)
        self.assertIn("REMOTE_RECEIPT_INVALID", out)
        self.assertNotIn("STATE_FLUSH_GUARD=PASS", out)


class CodeGraphLifecycleTests(ContinuityBase):
    def fake_index(self, repo):
        # review R4-D: health = directory + probe evidence (index.meta.json);
        # a bare directory alone is NOT a healthy index
        d = repo / ".codegraph"
        d.mkdir(exist_ok=True)
        (d / "index.meta.json").write_text('{"status": "synthetic-healthy"}',
                                           encoding="utf-8")

    # CG1 — healthy index, no change → no sync / no init (pre-query DELEGATES
    # to the lifecycle decision surface — review R4-B)
    def test_cg1_healthy_no_change(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        out = self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout
        self.assertIn("CODEGRAPH_LIFECYCLE_DECISION=NO_SYNC", out)
        self.assertNotIn("INIT_ONCE", out)
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
        self.assertIn("CODEGRAPH_LIFECYCLE_DECISION=INCREMENTAL_SYNC_ONCE",
                      self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout)
        head = self.commit_all(repo)
        self.run_tool(CG_STATE, ["mark-graph-synced", "--head", head], repo=repo)
        out = self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout
        self.assertIn("CODEGRAPH_LIFECYCLE_DECISION=NO_SYNC", out)

    # CG5 — missing index at the MAIN checkout → init allowed once
    # (a lane would be pointed at the main checkout instead — CG15)
    def test_cg5_missing_index_init_once(self):
        repo = self.mk_repo()
        out = self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout
        self.assertIn("CODEGRAPH_LIFECYCLE_DECISION=INIT_ONCE", out)

    # CG6 — existing index → full init prohibited
    def test_cg6_existing_index_init_prohibited(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.hook(repo, "src/app.py")  # even dirty
        out = self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout
        self.assertIn("INCREMENTAL_SYNC_ONCE", out)
        self.assertNotIn("INIT_ONCE", out)

    # CG7 — branch switch means incremental sync, never init
    def test_cg7_branch_switch_incremental(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.commit_all(repo)
        git(["checkout", "-b", "feature/x"], str(repo))
        self.hook(repo, "src/app.py")
        out = self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout
        self.assertIn("INCREMENTAL_SYNC_ONCE", out)
        self.assertNotIn("INIT_ONCE", out)

    # CG8 — sync failure must not fall back to full init (stop guard stays honest)
    def test_cg8_sync_failure_no_full_init_fallback(self):
        repo = self.mk_repo()
        self.fake_index(repo)
        self.hook(repo, "src/app.py")
        # agent attempts sync and it fails: flag stays dirty; re-check still incremental
        self.assertIn("INCREMENTAL_SYNC_ONCE",
                      self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout)
        self.assertNotIn("INIT_ONCE",
                         self.run_tool(CG_STATE, ["pre-query"], repo=repo).stdout)
        stop_out = self.stop(repo)
        self.assertIn("CODEGRAPH_SYNC_REQUIRED_BEFORE_STOP", stop_out)

    # CG9 — two worktrees have isolated runtime state (review R5-F2: a MODE A
    # lane edit is CANDIDATE DELTA, never lane graph dirty)
    def test_cg9_worktree_isolation(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        git(["worktree", "add", str(repo.parent / "wt2"), "-b", "wt2"], str(repo))
        wt2 = repo.parent / "wt2"
        self.hook(repo, "src/app.py")
        self.assertIn("GRAPH_DIRTY=YES", self.status(repo))
        self.assertIn("GRAPH_DIRTY=NO", self.status(wt2))
        self.hook(wt2, "src/other.py")
        st2 = self.status(wt2)
        self.assertIn("CANDIDATE_DELTA_DIRTY=YES", st2)   # MODE A lane: candidate delta
        self.assertIn("GRAPH_DIRTY=NO", st2)              # …never a lane graph dirty flag
        self.run_tool(CG_STATE, ["mark-graph-synced"], repo=repo)
        self.assertIn("GRAPH_DIRTY=NO", self.status(repo))
        self.assertIn("CANDIDATE_DELTA_DIRTY=YES", self.status(wt2))  # isolated state

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

    # CG15 — review R4-B: ONE LIFECYCLE → ONE DECISION SURFACE. The legacy
    # pre-query shortcut (".codegraph missing → INIT_ONCE_ALLOWED") is gone;
    # a MODE A lane without .codegraph must NEVER see INIT_ONCE.
    def test_cg15_pre_query_delegates_never_lane_init(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.fake_index(repo)
        self.run_tool(LC, ["record-init"], repo=repo)   # canonical MODE A graph initialized
        wt = self.base / "wt-b"
        git(["worktree", "add", "-b", "feature/cg15", str(wt)], str(repo))
        out = self.run_tool(CG_STATE, ["pre-query"], repo=wt).stdout
        self.assertNotIn("INIT_ONCE", out)              # old shortcut would have said INIT_ONCE_ALLOWED
        self.assertIn("CODEGRAPH_LIFECYCLE_DECISION=NO_SYNC", out)
        # canonical graph missing → the lane is pointed at the main checkout
        repo2 = self.mk_repo(name="repo2")
        self.commit_all(repo2)
        wt2 = self.base / "wt-c"
        git(["worktree", "add", "-b", "feature/cg15b", str(wt2)], str(repo2))
        out2 = self.run_tool(CG_STATE, ["pre-query"], repo=wt2).stdout
        self.assertNotIn("INIT_ONCE", out2)
        self.assertIn("CANONICAL_INIT_REQUIRED_AT_MAIN", out2)


class LifecycleDecisionTests(ContinuityBase):
    """LC1-LC21 — the single canonical lifecycle decision surface (contract §6.7).

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
        R5-F1  graph freshness tracks the GRAPH-OWNER HEAD (LC18, LC-INV7)
        R5-F2  MODE A lane edits are candidate delta, not lane syncs (LC19)
        R5-F3  NUL-safe porcelain parsing (LC20)
        R5-F5  record-init binds the graph owner's actual HEAD (LC21)
    """

    def fake_index(self, repo):
        # review R4-D: health = directory + probe evidence (index.meta.json)
        d = repo / ".codegraph"
        d.mkdir(exist_ok=True)
        (d / "index.meta.json").write_text('{"status": "synthetic-healthy"}',
                                           encoding="utf-8")

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
        self.fake_index(wt)
        out = self.run_tool(LC, ["record-init", "--lane"], repo=wt).stdout
        self.assertIn("GRAPH_INIT_RECORDED scope=lane", out)
        # lane initialized → no more lane init offers (R5-F1: the no-request
        # session-start answers the SYNC posture, not an init prohibition)
        self.assertIn("FULL_INIT_FORBIDDEN",
                      self.decide(wt, "session-start", lane_mode="B", request_full_init=""))
        self.assertIn("NO_SYNC", self.decide(wt, "session-start", lane_mode="B"))
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
        # R6.1-3: the unapproved observed delta is a RUNTIME GATE with two exits.
        # (a) REMOVE the unauthorized delta → recompute → coherent → continue
        (repo / "src" / "unrelated.py").unlink()
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

    # LC16 — review R4-C: the MODE A lane invariant covers ALL intents —
    # an ordinary worktree lane NEVER gets INIT_ONCE while the canonical
    # graph is missing; every init-offering intent points at the main checkout
    def test_lc16_mode_a_lane_all_intents_never_init(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        wt = self.base / "wt-b"
        git(["worktree", "add", "-b", "feature/lc16", str(wt)], str(repo))
        for intent in ("session-start", "query", "review", "blast-radius", "handoff", "stop"):
            out = self.decide(wt, intent)
            self.assertNotIn("INIT_ONCE", out)
            self.assertIn("CANONICAL_INIT_REQUIRED_AT_MAIN", out)
        # write intents never offer an init either
        self.assertNotIn("INIT_ONCE",
                         self.decide(wt, "pre-edit", risk="LOW", file="src/app.py"))
        self.assertIn("MARK_DIRTY", self.decide(wt, "post-edit"))
        # the mechanical invariant check agrees (LC-INV6, no violations)
        p = self.run_tool(LC, ["verify"], repo=wt, expect=0)
        self.assertIn("LIFECYCLE_INVARIANTS=PASS", p.stdout)
        self.assertNotIn("LC-INV6", p.stdout)

    # LC17 — review R4-D: real health evidence + canonical/lane scope separation
    def test_lc17_record_init_health_and_scope(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        # (1) a bare .codegraph directory is NOT health evidence → rejected
        (repo / ".codegraph").mkdir()
        out = self.run_tool(LC, ["record-init"], repo=repo).stdout
        self.assertIn("ERROR=GRAPH_INIT_REJECTED", out)
        self.assertIn("CODEGRAPH_HEALTH_UNPROVEN", out)
        # (2) the repo is NOT locked: no INIT_ONCE is offered (the directory
        # exists), and record-init remains retryable once health is real
        out2 = self.decide(repo, "session-start")
        self.assertNotIn("INIT_ONCE", out2)
        self.assertIn("register via record-init", out2)
        # (3) healthy evidence (mocked probe sees index.meta.json) → recorded
        (repo / ".codegraph" / "index.meta.json").write_text("{}", encoding="utf-8")
        out = self.run_tool(LC, ["record-init"], repo=repo).stdout
        self.assertIn("GRAPH_INIT_RECORDED scope=canonical", out)
        # (4) a healthy LANE index can NEVER satisfy the canonical record-init
        repo2 = self.mk_repo(name="repo2")
        self.commit_all(repo2)
        wt = self.base / "wt-r17"
        git(["worktree", "add", "-b", "feature/lc17", str(wt)], str(repo2))
        self.fake_index(wt)
        out = self.run_tool(LC, ["record-init"], repo=wt).stdout
        self.assertIn("ERROR=GRAPH_INIT_REJECTED", out)
        self.assertIn("INDEX_MISSING scope=canonical", out)
        # …while the lane's OWN graph records scope=lane
        out = self.run_tool(LC, ["record-init", "--lane"], repo=wt).stdout
        self.assertIn("GRAPH_INIT_RECORDED scope=lane", out)

    # LC18 — review R5-F1: graph freshness tracks the GRAPH-OWNER HEAD, not
    # only the PostToolUse dirty marker (pull / merge / fast-forward /
    # checkout / external commit never fire an Edit marker)
    def test_lc18_graph_owner_head_freshness(self):
        repo = self.mk_repo()
        self.commit_all(repo)                      # HEAD = A
        self.fake_index(repo)
        self.lc(repo, "record-init")               # index anchored at A
        # (1) HEAD advances to B with NO Edit hook → mechanical freshness wins
        (repo / "src" / "app.py").write_text("def main():\n    return 2\n", encoding="utf-8")
        self.commit_all(repo, "advance to B")
        out = self.decide(repo, "query")
        self.assertIn("INCREMENTAL_SYNC_ONCE", out)
        self.assertIn("R5-F1", out)
        self.assertNotIn("INIT_ONCE", out)
        self.assertIn("INCREMENTAL_SYNC_ONCE", self.decide(repo, "session-start"))
        self.lc(repo, "record-sync-result", "--ok")     # sync once → fresh again
        self.assertIn("NO_SYNC", self.decide(repo, "query"))
        # (2) a branch switch without any Edit hook → incremental sync
        git(["checkout", "-b", "feature/lc18"], str(repo))
        (repo / "src" / "other.py").write_text("x = 1\n", encoding="utf-8")
        self.commit_all(repo, "feature commit C")       # feature HEAD = C
        git(["checkout", "main"], str(repo))            # back to synced B
        self.assertIn("NO_SYNC", self.decide(repo, "query"))
        git(["checkout", "feature/lc18"], str(repo))    # HEAD moves to C, no marker
        out = self.decide(repo, "review")
        self.assertIn("INCREMENTAL_SYNC_ONCE", out)
        self.assertIn("R5-F1", out)
        # (3) same HEAD + no dirty → NO_SYNC (and the invariant checker agrees)
        self.lc(repo, "record-sync-result", "--ok")
        self.assertIn("NO_SYNC", self.decide(repo, "handoff"))
        p = self.run_tool(LC, ["verify"], repo=repo, expect=0)
        self.assertIn("LIFECYCLE_INVARIANTS=PASS", p.stdout)
        self.assertNotIn("LC-INV7", p.stdout)

    # LC19 — review R5-F2: a MODE A lane edit is CANDIDATE DELTA, never a lane
    # CodeGraph sync (review/handoff/stop must not demand an impossible lane
    # sync); a MODE B lane edit IS a lane graph sync. Mechanical git evidence
    # detects Bash-made edits with no Edit marker (JIT at boundaries, not
    # per-edit).
    def test_lc19_mode_a_candidate_delta_vs_mode_b_lane_sync(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.fake_index(repo)
        self.lc(repo, "record-init")               # canonical graph healthy
        # (1) MODE A lane: PostToolUse marker → candidate delta, NOT graph dirty
        wt = self.base / "wt-a19"
        git(["worktree", "add", "-b", "feature/lc19a", str(wt)], str(repo))
        self.hook(wt, "src/app.py")
        st = self.status(wt)
        self.assertIn("CANDIDATE_DELTA_DIRTY=YES", st)
        self.assertIn("GRAPH_DIRTY=NO", st)
        for intent in ("query", "review", "handoff", "stop"):
            out = self.decide(wt, intent)
            self.assertIn("NO_SYNC", out)
            self.assertNotIn("INCREMENTAL_SYNC_ONCE", out)
            self.assertIn("BASE_ONLY+DELTA_BY_DIFF", out)   # coverage stays explicit
        # (2) NO marker at all (worker used Bash) → git evidence still detects
        wt2 = self.base / "wt-a19b"
        git(["worktree", "add", "-b", "feature/lc19b", str(wt2)], str(repo))
        (wt2 / "src" / "bash_edit.py").write_text("x = 1\n", encoding="utf-8")
        out = self.decide(wt2, "handoff")
        self.assertIn("NO_SYNC", out)
        self.assertIn("CANDIDATE_DELTA_DIRTY=YES", out)     # marker=False git=True
        # (3) MODE B lane: the same edit IS a lane graph sync
        wtb = self.base / "wt-b19"
        git(["worktree", "add", "-b", "feature/lc19c", str(wtb)], str(repo))
        env = hook_env(self.runtime)
        env["ZCODE_CODEGRAPH_LANE_MODE"] = "B"
        payload = json.dumps({"tool_name": "Edit",
                              "tool_input": {"file_path": "src/app.py"},
                              "cwd": str(wtb)})
        proc = subprocess.run([sys.executable, CG_STATE, "--hook"], cwd=str(wtb),
                              input=payload, capture_output=True, text=True, timeout=60,
                              errors="replace", env=env)
        self.assertIn("CODEGRAPH_DIRTY=YES", proc.stdout)
        self.fake_index(wtb)
        self.lc(wtb, "record-init", "--lane")
        out = self.decide(wtb, "handoff", lane_mode="B")
        self.assertIn("INCREMENTAL_SYNC_ONCE", out)         # lane graph sync demanded

    # LC20 — review R5-F3: NUL-safe porcelain parsing — unstaged / staged /
    # untracked / rename / space-filename all resolve correctly; a parser
    # failure yields resolved=False (never wrong-path resolved evidence)
    def test_lc20_porcelain_parsing(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        # staged modification
        (repo / "src" / "app.py").write_text("def main():\n    return 3\n", encoding="utf-8")
        git(["add", "src/app.py"], str(repo))
        # unstaged tracked modification (the exact shape R4 parsing corrupted)
        (repo / "docs" / "target.md").write_text("target v2\n", encoding="utf-8")
        # untracked file
        (repo / "src" / "untracked.py").write_text("u = 1\n", encoding="utf-8")
        # staged rename (both endpoints belong to the delta)
        git(["mv", "docs/adr/ADR-001.md", "docs/adr/RENAMED-001.md"], str(repo))
        # tracked filename containing spaces, staged then modified unstaged
        spaced = repo / "docs" / "my notes file.md"
        spaced.write_text("notes v1\n", encoding="utf-8")
        git(["add", "docs/my notes file.md"], str(repo))
        spaced.write_text("notes v2\n", encoding="utf-8")
        sys.path.insert(0, str(HOOKS))
        import importlib
        cl = importlib.import_module("codegraph_lifecycle")
        files, resolved = cl.changed_files(str(repo), "")
        self.assertTrue(resolved)
        for expected in ("src/app.py", "docs/target.md", "src/untracked.py",
                         "docs/adr/ADR-001.md", "docs/adr/RENAMED-001.md",
                         "docs/my notes file.md"):
            self.assertIn(expected, files)
        # a record the parser cannot trust → resolved=False, no corrupt paths
        orig_git = cl._git

        class Corrupt:
            returncode = 0
            stdout = "R  docs/adr/RENAMED-001.md\x00"   # rename without its pair record

        cl._git = lambda args, cwd, timeout=10: (
            Corrupt() if args[:1] == ["status"] else orig_git(args, cwd, timeout))
        try:
            files2, resolved2 = cl.changed_files(str(repo), "")
        finally:
            cl._git = orig_git
        self.assertFalse(resolved2)
        self.assertNotIn("rc/app.py", files2)   # the historic corruption shape

    # LC21 — review R5-F5: record-init binds the GRAPH OWNER's actual HEAD —
    # canonical record-init invoked from a lane records the MAIN checkout's
    # HEAD; an explicit --head may never silently contradict the owner HEAD
    def test_lc21_record_init_binds_graph_owner_head(self):
        repo = self.mk_repo()
        self.commit_all(repo)                       # main HEAD = A
        self.fake_index(repo)
        wt = self.base / "wt-lc21"
        git(["worktree", "add", "-b", "feature/lc21", str(wt)], str(repo))
        (wt / "src" / "lane_only.py").write_text("x = 1\n", encoding="utf-8")
        git(["add", "-A"], str(wt))
        git(["commit", "-m", "lane B"], str(wt))    # lane HEAD = B ≠ A
        main_head = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        lane_head = git(["rev-parse", "HEAD"], str(wt)).stdout.strip()
        self.assertNotEqual(main_head, lane_head)
        # canonical record-init FROM the lane → binds the canonical owner HEAD
        out = self.run_tool(LC, ["record-init"], repo=wt).stdout
        self.assertIn("GRAPH_INIT_RECORDED scope=canonical", out)
        self.assertIn("head=%s" % main_head, out)
        # a lane index can never satisfy the canonical init, and an explicit
        # --head contradicting the owner HEAD is rejected outright
        self.fake_index(wt)
        out = self.run_tool(LC, ["record-init", "--lane", "--head", main_head],
                            repo=wt).stdout
        self.assertIn("ERROR=GRAPH_INIT_HEAD_MISMATCH", out)
        # lane record-init binds the LANE owner's own HEAD
        out = self.run_tool(LC, ["record-init", "--lane"], repo=wt).stdout
        self.assertIn("GRAPH_INIT_RECORDED scope=lane", out)
        self.assertIn("head=%s" % lane_head, out)


class R6ConvergenceTests(ContinuityBase):
    """R6 convergence repair regressions (PR #5 review round 6).

    F1  stop marker is evidence, not an issue (clean + BOUND marker → PASS)
    F2  graph init record is WRITE-ONCE (second record-init rejected; freshness
        only via incremental sync; record-rebuild is the separate recovery path)
    F3  shell/Bash cannot bypass MEDIUM/HIGH grounding (strict pre-grounding
        read-only allowlist; fail-closed UNKNOWN_BASH_MUTABILITY) + mechanical
        git source delta forces graph sync even with no marker and HEAD unchanged
    F4  authority (APPROVED_EDIT_SURFACE) separated from observation
        (OBSERVED_DELTA) and impact (IMPACT_SURFACE); unapproved delta never
        self-authorises on recompute
    F5  MODE A base/graph coherence (lane base must equal canonical graph base)
    F6  corrupt/partial index has an explicit CODEGRAPH_REBUILD_REQUIRED state
        (never auto delete / auto full init; manual grounding stays possible)
    F7  receipt HEAD binding (current HEAD is the default truth) + NUL diff
        path exactness (no .strip() on diff paths)
    """

    def fake_index(self, repo):
        d = repo / ".codegraph"
        d.mkdir(exist_ok=True)
        (d / "index.meta.json").write_text('{"status": "synthetic-healthy"}',
                                           encoding="utf-8")

    def ground(self, repo, ticket="T-1", risk="HIGH", mode="manual"):
        return self.full_ground(repo, ticket=ticket, risk=risk, mode=mode)[0]

    def in_process_state(self, repo):
        """The hermetic in-process runtime state for `repo` (same key the hook
        subprocesses use): ZCODE_RUNTIME_STATE_DIR must be pointed at the test
        runtime BEFORE importing _continuity_state, or the load lands in the
        real ~/.zcode/runtime-state instead of the synthetic one."""
        prev = os.environ.get("ZCODE_RUNTIME_STATE_DIR")
        os.environ["ZCODE_RUNTIME_STATE_DIR"] = str(self.runtime)
        self.addCleanup(self._restore_runtime_env, prev)
        sys.path.insert(0, str(HOOKS))
        import importlib
        return importlib.import_module("_continuity_state")

    @staticmethod
    def _restore_runtime_env(prev):
        if prev is None:
            os.environ.pop("ZCODE_RUNTIME_STATE_DIR", None)
        else:
            os.environ["ZCODE_RUNTIME_STATE_DIR"] = prev

    def lc(self, repo, *args):
        return self.run_tool(LC, list(args), repo=repo).stdout

    def decide(self, repo, intent, **flags):
        args = ["decide", "--intent", intent]
        for k, v in flags.items():
            args += ["--" + k.replace("_", "-"), v]
        return self.lc(repo, *args)

    def bash_guard(self, repo, command, risk="HIGH"):
        return self.run_tool(BASH_GUARD, ["--command", command, "--risk", risk],
                             repo=repo)

    # R6-F1 — clean valid BOUND_FLUSH_MARKER must reach the PASS branch
    def test_r6_f1_clean_bound_marker_is_pass(self):
        repo = self.mk_repo(with_remote=True)
        head = self.commit_all(repo)
        self.write_state(repo, remote="https://example.org/org/repo.git", head=head)
        self.commit_all(repo, "persist state")
        head2 = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        git(["push", "-u", "origin", "main"], str(repo))
        self.run_tool(CG_STATE, ["record-event", "TARGET_CHANGED"], repo=repo)
        self.run_tool(CG_STATE, ["record-state-sync", "--head", head2,
                                 "--remote-verified"], repo=repo)
        # before any marker: clean repo + REMOTE_VERIFIED receipt → PASS
        out = self.stop(repo)
        self.assertIn("STATE_FLUSH_GUARD=PASS", out)
        # with a bound marker: STILL PASS — the marker is evidence, never an
        # issue (the pre-R6 code path turned exactly this state into
        # STATE_FLUSH_REQUIRED). extra_env is required: hook_env() pops the
        # marker variables for every other test (hermetic default).
        out = self.stop(repo, extra_env={"STATE_FLUSH_COMPLETED": "1",
                                         "STATE_FLUSH_HEAD_SHA": head2})
        self.assertIn("STATE_FLUSH_GUARD=PASS", out)
        self.assertIn("BOUND_FLUSH_MARKER", out)
        self.assertNotIn("STATE_FLUSH_REQUIRED", out)

    # R6-F2 — record-init is WRITE-ONCE; freshness only via incremental sync
    def test_r6_f2_record_init_write_once(self):
        repo = self.mk_repo()
        self.commit_all(repo)                       # HEAD = A
        self.fake_index(repo)
        self.lc(repo, "record-init")                # graph indexed at A
        head_a = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        # HEAD moves to B with no sync
        (repo / "src" / "app.py").write_text("def main():\n    return 2\n", encoding="utf-8")
        self.commit_all(repo, "advance to B")
        head_b = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        self.assertNotEqual(head_a, head_b)
        # a second normal record-init must be REJECTED — never a freshness update
        out = self.lc(repo, "record-init")
        self.assertIn("ERROR=GRAPH_INIT_ALREADY_RECORDED", out)
        self.assertNotIn("GRAPH_INIT_RECORDED scope=canonical head=%s" % head_b, out)
        # query still detects the graph stale → incremental sync required
        out = self.decide(repo, "query")
        self.assertIn("INCREMENTAL_SYNC_ONCE", out)
        self.assertNotIn("INIT_ONCE", out)
        # freshness advances ONLY through record-sync-result --ok
        self.lc(repo, "record-sync-result", "--ok")
        out = self.decide(repo, "query")
        self.assertIn("NO_SYNC", out)
        # the recorded init head was NEVER mutated by the second record-init
        cs = self.in_process_state(repo)
        st = cs.load(str(repo))
        self.assertEqual(head_a, st["graph_init"]["head"])
        self.assertEqual(head_b, st["last_sync_head"])  # freshness, not init
        # the explicit rebuild path is separate and authority-gated
        self.assertIn("ERROR=CODEGRAPH_REBUILD_AUTHORITY_REQUIRED",
                      self.lc(repo, "record-rebuild"))
        self.assertIn("ERROR=CODEGRAPH_REBUILD_REQUIRES_EXISTING_RECORD",
                      self.lc(repo, "record-rebuild", "--authority",
                              "CODEGRAPH_REBUILD_AUTHORIZED",
                              "--lane"))

    # R6-F3 — shell/Bash cannot bypass MEDIUM/HIGH grounding pre-grounding
    def test_r6_f3_bash_preflight_allowlist(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        # HIGH + no receipt + read-only git status → ALLOW
        p = self.bash_guard(repo, "git status")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("BASH_PREFLIGHT_DECISION=ALLOW", p.stdout)
        p = self.bash_guard(repo, "git log --oneline -5")
        self.assertEqual(p.returncode, 0, p.stdout)
        p = self.bash_guard(repo, "rg -n 'def main' src")
        self.assertEqual(p.returncode, 0, p.stdout)
        p = self.bash_guard(repo, "git branch --show-current")
        self.assertEqual(p.returncode, 0, p.stdout)
        # HIGH + no receipt + Bash write / redirection / chaining → BLOCK
        for bad in ("echo x > src/app.py",
                    "cat in.txt >> src/app.py",
                    "git status && rm -rf src",
                    "python script.py",
                    "git commit -m x",
                    "mv a b",
                    "sed -i s/a/b/ src/app.py",
                    "git push origin main",
                    "ls | wc -l",
                    "curl https://example.org"):
            p = self.bash_guard(repo, bad)
            self.assertEqual(p.returncode, 2, "expected BLOCK for %r" % bad)
            self.assertIn("BASH_PREFLIGHT_DECISION=BLOCK", p.stdout)
            self.assertIn("UNKNOWN_BASH_MUTABILITY", p.stdout)
        # LOW risk below the threshold → ALLOW even pre-grounding
        p = self.bash_guard(repo, "npm test", risk="LOW")
        self.assertEqual(p.returncode, 0, p.stdout)
        # a valid grounding receipt exists → normal authorized Bash returns
        self.full_ground(repo, ticket="T-R6", risk="HIGH", mode="manual")
        p = self.bash_guard(repo, "npm test")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("normal Bash", p.stdout)

    # R6-F3 — canonical source changed via Bash (no marker, HEAD unchanged)
    #        → incremental sync required; MODE B same; MODE A lane → candidate
    #        delta only (no lane graph sync)
    def test_r6_f3_mechanical_delta_forces_graph_sync(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.fake_index(repo)
        self.lc(repo, "record-init")                # canonical graph healthy at HEAD
        self.assertIn("NO_SYNC", self.decide(repo, "query"))
        # Bash-made edit: write the file directly (no PostToolUse hook fires)
        (repo / "src" / "bash_edit.py").write_text("x = 1\n", encoding="utf-8")
        self.assertIn("GRAPH_DIRTY=NO", self.status(repo))
        out = self.decide(repo, "query")
        self.assertIn("INCREMENTAL_SYNC_ONCE", out)
        self.assertIn("R6-F3", out)
        # MODE B: the same mechanical evidence demands a LANE graph sync
        wtb = self.base / "wt-r6b"
        git(["worktree", "add", "-b", "feature/r6b", str(wtb)], str(repo))
        self.fake_index(wtb)
        self.lc(wtb, "record-init", "--lane")
        self.assertIn("NO_SYNC", self.decide(wtb, "review", lane_mode="B"))
        (wtb / "src" / "bash_edit2.py").write_text("y = 2\n", encoding="utf-8")
        out = self.decide(wtb, "review", lane_mode="B")
        self.assertIn("INCREMENTAL_SYNC_ONCE", out)
        self.assertIn("R6-F3", out)
        # MODE A ordinary lane: candidate delta detected → NO lane graph sync
        wta = self.base / "wt-r6a"
        git(["worktree", "add", "-b", "feature/r6a", str(wta)], str(repo))
        self.lc(repo, "record-sync-result", "--ok")  # canonical fresh again
        self.assertIn("NO_SYNC", self.decide(wta, "handoff"))
        (wta / "src" / "bash_edit3.py").write_text("z = 3\n", encoding="utf-8")
        out = self.decide(wta, "handoff")
        self.assertIn("NO_SYNC", out)
        self.assertIn("CANDIDATE_DELTA_DIRTY=YES", out)
        self.assertIn("BASE_ONLY+DELTA_BY_DIFF", out)

    # R6-F4 — authority vs observation: recompute never approves an
    #         already-changed file; explicit expansion is the only widening path
    def test_r6_f4_approved_vs_observed_surface(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.fake_index(repo)
        self.ground(repo)
        base = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        self.lc(repo, "blast-radius", "--base", base, "--target", "src/app.py")
        # Bash writes a file OUTSIDE the approved surface
        (repo / "src" / "unrelated.py").write_text("x = 1\n", encoding="utf-8")
        out = self.lc(repo, "blast-radius", "--base", base, "--target", "src/app.py")
        self.assertIn("BLAST_RADIUS=RECORDED", out)
        self.assertIn("UNAPPROVED_DELTA_DETECTED", out)
        self.assertIn("SURFACE_COHERENT=NO", out)
        cs = self.in_process_state(repo)
        st = cs.load(str(repo))
        self.assertNotIn("src/unrelated.py", st["blast_radius"]["approved_edit_surface"])
        # the file REMAINS unauthorized — recompute did not self-approve it
        out = self.decide(repo, "pre-edit", risk="HIGH", file="src/unrelated.py")
        self.assertIn("BLAST_RADIUS_EXPANSION_REQUIRED", out)
        # …and the invariant checker reports the breach (LC-INV8)
        p = self.run_tool(LC, ["verify"], repo=repo, expect=1)
        self.assertIn("LC-INV8", p.stdout)
        # explicit authority action: widen the surface → recompute → coherent
        self.lc(repo, "blast-radius", "--base", base, "--target", "src/app.py",
                "--target", "src/unrelated.py")
        out = self.lc(repo, "blast-radius", "--base", base, "--target", "src/app.py",
                      "--target", "src/unrelated.py")
        self.assertIn("SURFACE_COHERENT=YES", out)
        out = self.decide(repo, "pre-edit", risk="HIGH", file="src/unrelated.py")
        self.assertIn("ALLOW_WRITE", out)
        p = self.run_tool(LC, ["verify"], repo=repo, expect=0)
        self.assertIn("LIFECYCLE_INVARIANTS=PASS", p.stdout)

    # R6-F5 — Mode A base/graph coherence: lane base must equal the canonical
    #         graph base; a moved main/graph must NOT masquerade as the lane's
    #         base graph. R6.1-2: the coherence invariant is GRAPH-BACKED only
    #         — a manual (MODE C) receipt escapes it, so this regression is
    #         driven by a graph-backed receipt (mode="graph").
    def test_r6_f5_mode_a_base_coherence(self):
        repo = self.mk_repo()
        self.commit_all(repo)                        # HEAD = A
        self.fake_index(repo)
        self.lc(repo, "record-init")                 # canonical graph at A
        wt = self.base / "wt-r6f5"
        git(["worktree", "add", "-b", "feature/r6f5", str(wt)], str(repo))
        base_a = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        self.full_ground(wt, ticket="T-A", risk="HIGH", mode="graph", base=base_a)
        self.lc(wt, "blast-radius", "--base", base_a, "--target", "src/app.py")
        # lane base A + canonical graph A → MODE A valid
        self.assertIn("ALLOW_WRITE", self.decide(wt, "pre-edit", risk="HIGH",
                                                 file="src/app.py"))
        # main + canonical graph advance to B; the lane remains at A
        (repo / "src" / "app.py").write_text("def main():\n    return 9\n", encoding="utf-8")
        self.commit_all(repo, "main advances to B")
        self.lc(repo, "record-sync-result", "--ok")  # graph synced to B
        head_b = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        self.assertNotEqual(base_a, head_b)
        # the lane must NOT get a false BASE_ONLY + DELTA_BY_DIFF PASS
        out = self.decide(wt, "pre-edit", risk="HIGH", file="src/app.py")
        self.assertIn("BLAST_RADIUS_REQUIRED", out)
        self.assertIn("MODE_A_BASE_MISMATCH", out)
        self.assertNotIn("ALLOW_WRITE", out)
        # …and the honest answer on the lane is the reconcile instruction
        self.assertIn("MODE C", out)

    # R6-F6 — corrupt/partial index has an explicit recovery state
    def test_r6_f6_corrupt_graph_recovery_state(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.fake_index(repo)
        self.lc(repo, "record-init")                 # healthy registration
        self.assertIn("NO_SYNC", self.decide(repo, "query"))
        # the graph becomes unhealthy (probe now fails)
        (repo / ".codegraph" / "index.meta.json").unlink()
        out = self.decide(repo, "query")
        self.assertIn("CODEGRAPH_REBUILD_REQUIRED", out)
        self.assertNotIn("INIT_ONCE", out)
        self.assertNotIn("NO_SYNC", out)
        self.assertIn("NEVER auto-delete", out)
        self.assertIn("NEVER auto full init", out)
        # session-start agrees (no silent re-init either)
        self.assertIn("CODEGRAPH_REBUILD_REQUIRED", self.decide(repo, "session-start"))
        # no silent full rebuild: record-init is write-once → rejected with the
        # explicit rebuild pointer
        self.assertIn("ERROR=GRAPH_INIT_ALREADY_RECORDED", self.lc(repo, "record-init"))
        # the explicit rebuild path records the recovery once health is restored
        (repo / ".codegraph" / "index.meta.json").write_text("{}", encoding="utf-8")
        out = self.lc(repo, "record-rebuild", "--authority", "CODEGRAPH_REBUILD_AUTHORIZED",
                      "--reason", "INDEX_CORRUPTION")
        self.assertIn("GRAPH_REBUILD_RECORDED", out)
        self.assertIn("rebuild_count=1", out)
        self.assertIn("NO_SYNC", self.decide(repo, "query"))
        # manual grounding fallback remains possible while corrupt (MODE C)
        (repo / ".codegraph" / "index.meta.json").unlink()
        self.full_ground(repo, ticket="T-M", risk="HIGH", mode="manual")
        p = self.run_tool(GROUND_GUARD, ["--file", "src/app.py", "--risk", "HIGH"], repo=repo)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("ALLOW_MANUAL", p.stdout)
        # the invariant checker stays consistent in the recovery state: the
        # sync-posture invariants presuppose a healthy graph and must not fire
        # against CODEGRAPH_REBUILD_REQUIRED (verify PASS, no findings)
        p = self.run_tool(LC, ["verify"], repo=repo, expect=0)
        self.assertIn("LIFECYCLE_INVARIANTS=PASS", p.stdout)
        self.assertNotIn("LC-INV", p.stdout)

    # R6-F7a — a newly recorded durability receipt binds the CURRENT HEAD;
    #          an explicit --head contradicting it is rejected; a cached
    #          last_state_sync_head is never reused as default truth
    def test_r6_f7a_state_sync_receipt_head(self):
        repo = self.mk_repo(with_remote=True)
        self.commit_all(repo)
        self.write_state(repo, remote="https://example.org/org/repo.git",
                         head="x" * 40)
        self.commit_all(repo, "persist")
        head1 = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        # (1) an explicit --head contradicting current HEAD → rejected
        p = self.run_tool(CG_STATE, ["record-state-sync", "--head", "0" * 40],
                          repo=repo, expect=2)
        self.assertIn("ERROR=STATE_SYNC_HEAD_MISMATCH", p.stdout)
        # (2) no --head → CURRENT HEAD is the default truth (cached head NEVER)
        self.run_tool(CG_STATE, ["record-state-sync"], repo=repo)
        cs = self.in_process_state(repo)
        st = cs.load(str(repo))
        self.assertEqual(head1, st["remote_durability"]["head_sha"])
        self.assertEqual(head1, st["last_state_sync_head"])
        # (3) explicit --head == current HEAD → accepted
        self.run_tool(CG_STATE, ["record-state-sync", "--head", head1,
                                 "--remote-verified"], repo=repo)
        st = cs.load(str(repo))
        self.assertEqual(head1, st["remote_durability"]["head_sha"])
        self.assertEqual("REMOTE_VERIFIED", st["remote_durability"]["level"])

    # R6-F7b — git diff -z paths are preserved EXACTLY (no .strip()); leading /
    #          trailing space filenames survive; only empty NUL fields skipped.
    #          Note: the FILESYSTEM leg exercises leading spaces + rename pairs
    #          (Windows removes trailing spaces from names at creation, so the
    #          trailing-space exactness claim is proven by the SYNTHETIC diff
    #          leg below, which is where the old .strip() bug actually lived).
    def test_r6_f7b_nul_diff_path_exactness(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        # filename with a leading space (legal on NTFS/ext4)
        lead = repo / "src" / " lead-space.py"
        lead.write_text("a = 1\n", encoding="utf-8")
        git(["add", "-A"], str(repo))
        self.commit_all(repo, "space names")
        lead.write_text("a = 2\n", encoding="utf-8")
        sys.path.insert(0, str(HOOKS))
        import importlib
        cl = importlib.import_module("codegraph_lifecycle")
        files, resolved = cl.changed_files(str(repo), "")
        self.assertTrue(resolved)
        self.assertIn("src/ lead-space.py", files)
        # staged rename with spaces: both endpoints represented exactly.
        # The source must be COMMITTED first — git folds an add-then-rename of
        # a never-committed file into a plain "A new" record (the old endpoint
        # legitimately never existed in any revision).
        (repo / "docs").mkdir(exist_ok=True)
        spaced = repo / "docs" / "my notes file.md"
        spaced.write_text("n1\n", encoding="utf-8")
        git(["add", "docs/my notes file.md"], str(repo))
        self.commit_all(repo, "commit source name")
        git(["mv", "docs/my notes file.md", "docs/renamed notes file.md"], str(repo))
        files2, resolved2 = cl.changed_files(str(repo), "")
        self.assertTrue(resolved2)
        self.assertIn("docs/renamed notes file.md", files2)
        self.assertIn("docs/my notes file.md", files2)
        # SYNTHETIC probe (the exact F7b defect shape): diff lines with
        # leading/trailing spaces must survive byte-exact; empty NUL fields
        # are the ONLY thing skipped — no .strip(), no path mutation
        orig_git = cl._git

        class SpacyDiff:
            returncode = 0
            stdout = "src/ pad both.py\x00src/x.py \x00\x00"

        cl._git = lambda args, cwd, timeout=10: (
            SpacyDiff() if args[:2] == ["diff", "--name-only"] else orig_git(args, cwd, timeout))
        try:
            files3, resolved3 = cl.changed_files(str(repo), "HEAD")
        finally:
            cl._git = orig_git
        self.assertTrue(resolved3)
        self.assertIn("src/ pad both.py", files3)
        self.assertIn("src/x.py ", files3)
        self.assertNotIn("src/x.py", files3)  # exactness — no silent mutation


class R61FinalConvergenceTests(ContinuityBase):
    """R6.1 final convergence patch regressions (PR #5 review round 6.1).

    F1  Bash receipt validation — `{"BASE_SHA": ...}` alone is NOT grounding;
        the Bash preflight reuses grounding_guard's structural + freshness
        semantics (partial receipt BLOCKS; stale receipt BLOCKS; complete
        fresh receipt unlocks normal Bash)
    B   trusted receipt bootstrap — before grounding, EXACTLY the canonical
        `python <hooks>/codegraph_state.py set-grounding ...` command is
        narrowly allowed (exact script path, exact subcommand, flags only);
        chaining / redirection / arbitrary scripts stay BLOCKED; the REAL
        path readonly grounding → trusted set-grounding → receipt → normal
        Bash unlocks end to end
    F2  graph-backed Mode A coherence covers REVIEW (not only pre-edit): a
        long-lived lane with a moved canonical graph gets NO review PASS;
        MODE C (manual) genuinely escapes coherence; a MISSING tool is
        CODEGRAPH_UNAVAILABLE (MODE C) vs a running tool + broken index =
        CODEGRAPH_REBUILD_REQUIRED
    F3  UNAPPROVED_DELTA_DETECTED is a runtime gate: blocks further MEDIUM/HIGH
        writes AND review until the delta is removed or the surface is
        explicitly expanded; LC-INV8 stays as defense in depth
    """

    def fake_index(self, repo):
        d = repo / ".codegraph"
        d.mkdir(exist_ok=True)
        (d / "index.meta.json").write_text('{"status": "synthetic-healthy"}',
                                           encoding="utf-8")

    def ground(self, repo, ticket="T-1", risk="HIGH", mode="manual"):
        return self.full_ground(repo, ticket=ticket, risk=risk, mode=mode)[0]

    def in_process_state(self, repo):
        prev = os.environ.get("ZCODE_RUNTIME_STATE_DIR")
        os.environ["ZCODE_RUNTIME_STATE_DIR"] = str(self.runtime)
        self.addCleanup(self._restore_runtime_env, prev)
        sys.path.insert(0, str(HOOKS))
        import importlib
        return importlib.import_module("_continuity_state")

    @staticmethod
    def _restore_runtime_env(prev):
        if prev is None:
            os.environ.pop("ZCODE_RUNTIME_STATE_DIR", None)
        else:
            os.environ["ZCODE_RUNTIME_STATE_DIR"] = prev

    def lc(self, repo, *args):
        return self.run_tool(LC, list(args), repo=repo).stdout

    def decide(self, repo, intent, **flags):
        args = ["decide", "--intent", intent]
        for k, v in flags.items():
            args += ["--" + k.replace("_", "-"), v]
        return self.lc(repo, *args)

    def bash_guard(self, repo, command, risk="HIGH"):
        return self.run_tool(BASH_GUARD, ["--command", command, "--risk", risk],
                             repo=repo)

    def set_grounding_cmd(self, repo, extra=()):
        """The canonical trusted bootstrap command shape. The script path is
        quoted with FORWARD slashes: shlex.split(posix=True) is the guard's
        tokenizer and would eat Windows backslashes as escapes (a mechanical
        fact the guard itself documents)."""
        return 'python "%s" set-grounding --ticket T-B --risk HIGH --base-sha %s --mode manual %s' \
            % (str(HOOKS / "codegraph_state.py").replace("\\", "/"),
               git(["rev-parse", "HEAD"], str(repo)).stdout.strip(),
               " ".join(extra))

    # R6.1-1 — Bash receipt validation: partial / stale BLOCK, complete fresh ALLOW
    def test_r61_f1_bash_receipt_validation(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        cs = self.in_process_state(repo)
        sp = cs.state_path(str(repo))
        sp.parent.mkdir(parents=True, exist_ok=True)
        # (1) partial receipt {BASE_SHA: ...} only → normal Bash still BLOCKS
        sp.write_text(json.dumps({"grounding_receipt": {"BASE_SHA": "a" * 40}}),
                      encoding="utf-8")
        p = self.bash_guard(repo, "npm test")
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn("GROUNDING_RECEIPT_INVALID", p.stdout)
        # (2) structurally complete but STALE receipt → still BLOCKS
        self.full_ground(repo, ticket="T-S", risk="HIGH", mode="graph", base="0" * 40)
        p = self.bash_guard(repo, "npm test")
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn("GROUNDING_RECEIPT_STALE", p.stdout)
        # (3) complete + fresh receipt → normal Bash unlocks
        self.full_ground(repo, ticket="T-F", risk="HIGH", mode="manual")
        p = self.bash_guard(repo, "npm test")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("normal Bash", p.stdout)

    # R6.1-1 — trusted set-grounding bootstrap: exact shape ALLOW, everything
    #          else (chaining, redirection, arbitrary scripts) BLOCKED; then
    #          the REAL end-to-end path: readonly → trusted set-grounding →
    #          receipt exists → normal Bash unlocks
    def test_r61_f1_trusted_receipt_bootstrap_end_to_end(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        # (1) the canonical trusted command is the ONLY python-shaped ALLOW
        p = self.bash_guard(repo, self.set_grounding_cmd(repo))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("TRUSTED_RECEIPT_BOOTSTRAP", p.stdout)
        # (2) chaining / redirection / arbitrary python stay BLOCKED
        for bad in (
            self.set_grounding_cmd(repo) + " && echo pwned",
            self.set_grounding_cmd(repo) + " > out.txt",
            'python "%s" set-grounding --ticket X --risk HIGH --base-sha %s --mode manual'
            % (str(HOOKS / "nonexistent.py").replace("\\", "/"), "b" * 40),  # wrong script
            "python -c \"import os; os.remove('src/app.py')\"",
            "python script.py",
        ):
            p = self.bash_guard(repo, bad)
            self.assertEqual(p.returncode, 2, "expected BLOCK for %r" % bad)
            self.assertIn("UNKNOWN_BASH_MUTABILITY", p.stdout)
        # (3) REAL path end-to-end: no receipt → normal Bash BLOCKS; readonly
        #     grounding discovery ALLOWED; trusted set-grounding records the
        #     receipt; normal Bash unlocks
        p = self.bash_guard(repo, "npm test")
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn("UNKNOWN_BASH_MUTABILITY", p.stdout)
        p = self.bash_guard(repo, "rg -n 'def main' src")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("read-only allowlist pre-grounding", p.stdout)
        cmd = self.set_grounding_cmd(repo, extra=(
            "--field GRAPH_BASE_SHA=%s" % git(["rev-parse", "HEAD"], str(repo)).stdout.strip(),
            "--field TARGET_SEAM=src/app.py", "--field DIRECT_TARGETS=src/app.py",
            "--field UPSTREAM_PRODUCERS=NONE", "--field CALLERS=UNKNOWN",
            "--field CALLEES=UNKNOWN", "--field DOWNSTREAM_CONSUMERS=NONE",
            "--field IMPACT=NONE", "--field AFFECTED=src/app.py",
            "--field STATE_OWNER=NONE", "--field IDENTITY_OWNER=NONE",
            "--field VALIDATION_OWNER=NONE", "--field EXPECTED_EDIT_SURFACE=src/app.py",
            "--field OUT_OF_SCOPE=docs/"))
        # run the REAL command through the REAL guard (the hook would allow it;
        # here we also execute it so the receipt actually lands)
        p = self.bash_guard(repo, cmd)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("TRUSTED_RECEIPT_BOOTSTRAP", p.stdout)
        subprocess.run(cmd, shell=True, cwd=str(repo), capture_output=True, text=True,
                       timeout=60,
                       env={**os.environ, "ZCODE_RUNTIME_STATE_DIR": str(self.runtime)})
        cst = self.in_process_state(repo)
        st = cst.load(str(repo))
        self.assertIsInstance(st.get("grounding_receipt"), dict)
        self.assertIn("BASE_SHA", st["grounding_receipt"])
        p = self.bash_guard(repo, "npm test")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("normal Bash", p.stdout)

    # R6.1-2 — graph-backed Mode A coherence covers REVIEW; MODE C escapes it
    def test_r61_f2_mode_a_review_coherence_and_mode_c_escape(self):
        repo = self.mk_repo()
        self.commit_all(repo)                        # HEAD = A
        self.fake_index(repo)
        self.lc(repo, "record-init")                 # canonical graph at A
        wt = self.base / "wt-r61"
        git(["worktree", "add", "-b", "feature/r61", str(wt)], str(repo))
        base_a = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        # graph-backed receipt at base A (BASE_SHA == GRAPH_BASE_SHA)
        self.full_ground(wt, ticket="T-G", risk="HIGH", mode="graph", base=base_a)
        self.lc(wt, "blast-radius", "--base", base_a, "--target", "src/app.py")
        self.assertIn("NO_SYNC", self.decide(wt, "review"))
        # canonical graph advances A → B; the long-lived lane stays at A
        (repo / "src" / "app.py").write_text("def main():\n    return 9\n", encoding="utf-8")
        self.commit_all(repo, "main advances to B")
        self.lc(repo, "record-sync-result", "--ok")
        # review MUST NOT return a normal BASE_ONLY+DELTA_BY_DIFF PASS
        out = self.decide(wt, "review")
        self.assertIn("BLAST_RADIUS_REQUIRED", out)
        self.assertIn("MODE_A_BASE_MISMATCH", out)
        self.assertNotIn("NO_SYNC", out)
        # MODE C (manual receipt) genuinely escapes the coherence invariant
        self.full_ground(wt, ticket="T-M", risk="HIGH", mode="manual", base=base_a)
        out = self.decide(wt, "review")
        self.assertNotIn("MODE_A_BASE_MISMATCH", out)
        # handoff/stop are covered by the same review-time gate (still manual)
        self.assertIn("NO_SYNC", self.decide(wt, "handoff"))

    # R6.1-2 — tool unavailable vs corrupt index are DIFFERENT classifications
    def test_r61_f2_codegraph_unavailable_classification(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.fake_index(repo)
        self.lc(repo, "record-init")
        # healthy registered graph → NO_SYNC
        self.assertIn("NO_SYNC", self.decide(repo, "query"))
        # corrupt index under a RUNNING (mock) tool → CODEGRAPH_REBUILD_REQUIRED
        (repo / ".codegraph" / "index.meta.json").unlink()
        out = self.decide(repo, "query")
        self.assertIn("CODEGRAPH_REBUILD_REQUIRED", out)
        self.assertNotIn("CODEGRAPH_UNAVAILABLE", out)
        # the mock probe is REMOVED entirely → the TOOL itself is unreachable
        # → CODEGRAPH_UNAVAILABLE / MODE C (never a rebuild state).
        # hook_env() injects the mock probe into every subprocess, so the
        # probe-less leg must EXPLICITLY override it with a CLI that cannot
        # exist — the mechanical shape of "codegraph tool not installed".
        out2 = self.decide(repo, "query", **{
            "codegraph-health-cmd": "definitely-not-a-real-codegraph-cli-xyz status"})
        self.assertIn("CODEGRAPH_UNAVAILABLE", out2)
        self.assertNotIn("CODEGRAPH_REBUILD_REQUIRED", out2)
        self.assertIn("MODE C", out2)
        self.assertIn("never auto-init", out2)
        self.assertIn("never auto-rebuild", out2)

    # R6.1-3 — unapproved observed delta is a RUNTIME GATE on writes AND review;
    #          explicit expansion recomputes → coherent → continue
    def test_r61_f3_unapproved_delta_runtime_gate(self):
        repo = self.mk_repo()
        self.commit_all(repo)
        self.fake_index(repo)
        self.ground(repo)
        base = git(["rev-parse", "HEAD"], str(repo)).stdout.strip()
        self.lc(repo, "blast-radius", "--base", base, "--target", "src/app.py")
        # unauthorized unrelated.py ALREADY changed (outside approved surface)
        (repo / "src" / "unrelated.py").write_text("x = 1\n", encoding="utf-8")
        self.lc(repo, "blast-radius", "--base", base, "--target", "src/app.py")
        # (1) another approved-file write BLOCKS (runtime gate, not a note)
        out = self.decide(repo, "pre-edit", risk="HIGH", file="src/app.py")
        self.assertIn("BLAST_RADIUS_REQUIRED", out)
        self.assertIn("UNAPPROVED_DELTA_DETECTED", out)
        self.assertNotIn("ALLOW_WRITE", out)
        # (2) review BLOCKS too
        self.assertIn("BLAST_RADIUS_REQUIRED", self.decide(repo, "review"))
        self.assertIn("UNAPPROVED_DELTA_DETECTED", self.decide(repo, "review"))
        # (3) explicit authority expansion INCLUDING unrelated.py → recompute
        #     → coherent → writes and review continue
        self.lc(repo, "blast-radius", "--base", base, "--target", "src/app.py",
                "--target", "src/unrelated.py")
        self.assertIn("SURFACE_COHERENT=YES", self.lc(
            repo, "blast-radius", "--base", base, "--target", "src/app.py",
            "--target", "src/unrelated.py"))
        self.assertIn("ALLOW_WRITE", self.decide(repo, "pre-edit", risk="HIGH",
                                                 file="src/app.py"))
        self.assertIn("NO_SYNC", self.decide(repo, "review"))
        # LC-INV8 remains as defense in depth (no breach in the coherent state)
        p = self.run_tool(LC, ["verify"], repo=repo, expect=0)
        self.assertIn("LIFECYCLE_INVARIANTS=PASS", p.stdout)


class R62FindPreGroundingTests(ContinuityBase):
    """R6.2 single-blocker convergence regression (PR #5 review round 6.2).

    `find` is a traversal DSL, not a reader: -delete, -exec/-execdir/-ok … +
    and -fprint/-fprintf/-fls all mutate or execute, and a `+`-terminated
    -exec carries no chain marker at all — so one bare `find . -exec sh -c … +`
    runs an arbitrary command before grounding. No safe subset of find
    primaries is maintained at this gate.

    Pre-grounding (no valid receipt)  → every find form BLOCKS with
                                        UNKNOWN_BASH_MUTABILITY.
    Complete + fresh grounding receipt → normal Bash semantics return, so
                                        `find .` is ALLOW again.
    """

    def bash_guard(self, repo, command, risk="HIGH"):
        return self.run_tool(BASH_GUARD, ["--command", command, "--risk", risk],
                             repo=repo)

    def test_r62_find_is_not_pre_grounding(self):
        repo = self.mk_repo()
        self.commit_all(repo)

        find_forms = (
            "find .",
            'find . -name "*.py"',
            "find . -exec rm -rf {} +",
            "find . -execdir rm -rf {} +",
            "find . -exec sh -c id {} +",
            "find . -delete",
            "find . -ok rm {} +",
            "find . -fprintf out.txt %p",
            "find . -fls out.txt",
        )
        # (1) no grounding receipt → ALL find forms BLOCK, including the plain
        #     discovery forms and the `+`-terminated -exec that carries no
        #     chain marker.
        for cmd in find_forms:
            p = self.bash_guard(repo, cmd)
            self.assertEqual(p.returncode, 2,
                             "expected BLOCK for %r (got rc=%s): %s"
                             % (cmd, p.returncode, p.stdout))
            self.assertIn("BASH_PREFLIGHT_DECISION=BLOCK", p.stdout,
                          "missing BLOCK decision for %r: %s" % (cmd, p.stdout))
            self.assertIn("UNKNOWN_BASH_MUTABILITY", p.stdout,
                          "missing UNKNOWN_BASH_MUTABILITY for %r: %s"
                          % (cmd, p.stdout))

        # (2) the documented safe discovery alternatives still work
        #     pre-grounding — `find` is not the only way to look around.
        for cmd in ("git ls-files", "rg -n main src", "ls src", "cat src/app.py"):
            p = self.bash_guard(repo, cmd)
            self.assertEqual(p.returncode, 0,
                             "expected ALLOW for %r: %s" % (cmd, p.stdout))
            self.assertIn("BASH_PREFLIGHT_DECISION=ALLOW", p.stdout)

        # (3) complete + fresh grounding receipt → normal Bash semantics return
        #     and `find .` is ALLOW again (this gate is pre-grounding only).
        self.full_ground(repo, ticket="T-R62", risk="HIGH", mode="manual")
        p = self.bash_guard(repo, "find .")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("BASH_PREFLIGHT_DECISION=ALLOW", p.stdout)
        self.assertIn("normal Bash", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
