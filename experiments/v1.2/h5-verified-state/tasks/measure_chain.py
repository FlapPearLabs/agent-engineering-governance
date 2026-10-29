"""Measure H5 task chainability from the frozen H2 registry (read-only).

The frozen registry owns every SHA: this program copies none by hand. For each ordered pair
of frozen tasks (i, j) it asks

  1. git: is `candidate_i` exactly `base_j`, or an ancestor of it?
  2. git: does task j's delta touch task i's oracle surface? (oracle dependence)
  3. the frozen gate: does `run_acceptance_v2.accept` still say ACCEPT for task i on the tree
     at `base_j`, with the base itself still failing?

A pair is a chain link only when (1) holds, (2) does not, and (3) does. Everything else is
unchainable, and a measurement error is never a link (fail closed).

The intermediate commits between `candidate_i` and `base_j` are counted and classified with
git but are not re-run individually: the prescribed measurement is the endpoint `base_j`.
Pairs whose interval touches neither task i's fix paths nor its oracle path are reported as
`NO_INTERMEDIATE_CHANGE`, the rest as `ENDPOINT_ONLY`.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FZ = ROOT / "experiments/v1.2/h2-lazy-disclosure/freeze-v3"
REGISTRY = FZ / "task-registry-v3.json"
PROGRAM_REL = Path(__file__).resolve().relative_to(ROOT).as_posix()
REGISTRY_REL = REGISTRY.relative_to(ROOT).as_posix()
# The frozen worker scope denies scripts/tests/ for every task (T10), so the delta a worker may
# produce is the base..commit diff with that directory removed.
SCOPE_EXCLUDE = ":!scripts/tests"


# --------------------------------------------------------------------------- frozen inputs

def load_tasks(registry: Path = REGISTRY) -> list[dict]:
    """The frozen task table: id, base SHA, candidate SHA and oracle surface, from the file."""
    frozen = json.loads(Path(registry).read_text(encoding="utf-8"))
    expected = frozen["expected"]
    tasks = []
    for task in frozen["tasks"]:
        task_id = task["task_id"]
        if task_id not in expected:
            raise ValueError(f"NO_CANDIDATE_SHA:{task_id}")
        tasks.append({
            "id": task_id,
            "base": task["base_sha"],
            "candidate": expected[task_id]["candidate_sha"],
            "oracle_surface": [task["oracle"]["path"]],
        })
    ids = [task["id"] for task in tasks]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("DUPLICATE_OR_EMPTY_TASK_IDS")
    return tasks


# --------------------------------------------------------------------------- git primitives

def git(repo: Path, *args: str, input_data: bytes | None = None, check: bool = True):
    result = subprocess.run(["git", "--no-replace-objects", "-C", str(repo), *args],
                            input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False)
    if check and result.returncode:
        raise RuntimeError(f"GIT_FAILED:{args[0]}:"
                           f"{result.stderr.decode('utf-8', 'replace').strip()[:200]}")
    return result


def head_of(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD").stdout.decode().strip()


def commit_exists(repo: Path, oid: str) -> bool:
    return git(repo, "cat-file", "-e", f"{oid}^{{commit}}", check=False).returncode == 0


def is_ancestor(repo: Path, first: str, second: str) -> bool:
    result = git(repo, "merge-base", "--is-ancestor", first, second, check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError("ANCESTRY_UNKNOWN")
    return result.returncode == 0


def touched(repo: Path, base: str, candidate: str) -> set[str]:
    out = git(repo, "diff", "--no-renames", "--name-only", "-z", base, candidate).stdout
    return {path for path in out.decode("utf-8").split("\0") if path}


def names_of(repo: Path, commit: str) -> set[str]:
    out = git(repo, "show", "--no-renames", "--name-only", "--format=", commit).stdout
    return {line for line in out.decode("utf-8").splitlines() if line}


def commits_between(repo: Path, first: str, second: str) -> list[str]:
    out = git(repo, "rev-list", "--reverse", f"{first}..{second}").stdout
    return [line for line in out.decode("utf-8").splitlines() if line]


# --------------------------------------------------------------------------- pair relations

def pair_relation(repo: Path, first: dict, second: dict) -> dict:
    """The git-only half of a link: identity, ancestry and oracle dependence."""
    overlap = sorted(touched(repo, second["base"], second["candidate"])
                     & set(first["oracle_surface"]))
    return {
        "from": first["id"],
        "to": second["id"],
        "equal": first["candidate"] == second["base"],
        "ancestor": is_ancestor(repo, first["candidate"], second["base"]),
        "oracle_overlap": overlap,
    }


def intermediate_census(repo: Path, first: dict, second: dict) -> dict:
    """Classify the commits strictly between candidate_i and base_j (git only, no re-runs)."""
    commits = commits_between(repo, first["candidate"], second["base"])
    fix_paths = touched(repo, first["base"], first["candidate"])
    oracle = set(first["oracle_surface"])
    touching_fix = sum(1 for commit in commits if names_of(repo, commit) & fix_paths)
    touching_oracle = sum(1 for commit in commits if names_of(repo, commit) & oracle)
    stable = bool(commits) and not touching_fix and not touching_oracle
    return {
        "commits": len(commits),
        "touching_fix_paths": touching_fix,
        "touching_oracle": touching_oracle,
        "measured": False,
        "stability": "NO_INTERMEDIATE_CHANGE" if stable else "ENDPOINT_ONLY",
    }


def judge(relation: dict, measurement: dict | None) -> tuple[bool, str]:
    """The decision rule. `measurement` is None when the git facts already settle the pair."""
    if relation["oracle_overlap"]:
        return False, "ORACLE_DEPENDENCE"
    if not (relation["equal"] or relation["ancestor"]):
        return False, "BROKEN_LINK"
    if measurement is None:
        return False, "UNMEASURED"
    if measurement.get("error"):
        return False, f"MEASUREMENT_ERROR:{measurement['error']}"
    if measurement.get("verdict") != "ACCEPT":
        return False, f"ORACLE_NOT_PRESERVED:{measurement.get('verdict')}"
    if measurement.get("base_passing"):
        # The oracle already passes on the untouched base, so "unchanged" proves nothing.
        return False, "ORACLE_ACCEPTS_THE_BASE"
    return True, "LINK"


# --------------------------------------------------------------------------- frozen gate

def load_frozen(name: str):
    """Resolve a freeze-v3 module the way experiments/v1.2/tests/test_v1_2_h2_freeze_v3.py does."""
    v2 = (FZ.parent / "freeze-v2").resolve()
    for key, module in list(sys.modules.items()):
        source = getattr(module, "__file__", None)
        if source and Path(source).resolve().is_relative_to(v2):
            del sys.modules[key]
    if str(FZ) in sys.path:
        sys.path.remove(str(FZ))
    sys.path.insert(0, str(FZ))
    spec = importlib.util.spec_from_file_location(name, FZ / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def make_accept_fn(materials: str):
    """`accept for task i on the tree at <commit>`, using the frozen gate unchanged."""
    wrapper = load_frozen("wrapper_delivery")
    acceptance = load_frozen("run_acceptance_v2")

    def accept_at(task: dict, commit: str) -> dict:
        scratch = Path(tempfile.mkdtemp(prefix="h5-chain-cell-"))
        run = scratch / "cell"
        try:
            wrapper.prepare(ROOT, run, task["id"], "control", materials)
            patch = git(ROOT, "diff", "--binary", task["base"], commit, "--",
                        SCOPE_EXCLUDE).stdout
            applied = subprocess.run(
                ["git", "--no-replace-objects", "-C", str(run / "repo"), "apply",
                 "--whitespace=nowarn"], input=patch, capture_output=True)
            if applied.returncode:
                raise RuntimeError("DELTA_DOES_NOT_APPLY")
            (run / "report.md").write_text("# report\n\nFilled.\n", encoding="utf-8")
            (run / ".h2-telemetry.log").write_text("READ FULL repo/RULES.md\n", encoding="utf-8")
            verdict = acceptance.accept(ROOT, run)
            base = verdict.get("oracle", {}).get("base", {})
            base_passing = bool(base) and any(
                style.get("rc") == 0 and not style.get("not_passing") for style in base.values())
            return {"verdict": verdict["verdict"], "base_passing": base_passing,
                    "reasons": verdict["reasons"][:6]}
        finally:
            if run.exists():
                wrapper.cleanup(ROOT, run)
            shutil.rmtree(scratch, ignore_errors=True)

    return accept_at


def measure_pair(repo: Path, first: dict, second: dict, accept_fn) -> dict:
    """One ordered pair, fail closed: the expensive gate runs only where git leaves the door open."""
    try:
        relation = pair_relation(repo, first, second)
    except Exception as exc:                                  # noqa: BLE001 - fail closed
        return {"from": first["id"], "to": second["id"], "chainable": False,
                "reason": f"MEASUREMENT_ERROR:{type(exc).__name__}", "error": str(exc)[:200]}
    result = dict(relation, chainable=False, reason=None, endpoint=None, intermediates=None)
    if relation["oracle_overlap"]:
        result["reason"] = "ORACLE_DEPENDENCE"
        return result
    if not (relation["equal"] or relation["ancestor"]):
        result["reason"] = "BROKEN_LINK"
        return result
    result["intermediates"] = intermediate_census(repo, first, second)
    try:
        measurement = accept_fn(first, second["base"])
    except Exception as exc:                                  # noqa: BLE001 - fail closed
        measurement = {"error": f"{type(exc).__name__}", "detail": str(exc)[:200]}
    result["endpoint"] = {key: value for key, value in measurement.items() if key != "detail"}
    chainable, reason = judge(relation, measurement)
    result["chainable"], result["reason"] = chainable, reason
    return result


# --------------------------------------------------------------------------- verdict

def longest_chain(links: list[dict], ids: list[str]) -> list[str]:
    """Longest path in the link graph (a link is i -> j); ties break on the frozen order."""
    out: dict[str, list[str]] = {task_id: [] for task_id in ids}
    for link in links:
        out[link["from"]].append(link["to"])
    best: dict[str, list[str]] = {}

    def walk(node: str) -> list[str]:
        if node in best:
            return best[node]
        best[node] = [node]                                # cycles cannot appear: links are ancestry
        tail = max((walk(nxt) for nxt in out[node]), key=len, default=[])
        best[node] = [node, *tail]
        return best[node]

    return max((walk(task_id) for task_id in ids), key=len, default=[])


def summarise(tasks: list[dict], pairs: list[dict], relations: list[dict]) -> dict:
    links = [pair for pair in pairs if pair["chainable"]]
    errors = [pair for pair in pairs if pair.get("reason", "").startswith("MEASUREMENT_ERROR")]
    chain = longest_chain(links, [task["id"] for task in tasks])
    measured = [pair for pair in pairs if pair.get("endpoint") is not None]
    verdict = "A" if len(links) >= 2 else "B"
    if errors:
        verdict = "INCONCLUSIVE"
    return {
        "tasks": len(tasks),
        "ordered_pairs": len(pairs),
        "pairs_measured_with_the_frozen_gate": len(measured),
        "links": len(links),
        "links_by_source": {task["id"]: sum(1 for l in links if l["from"] == task["id"])
                            for task in tasks},
        "longest_chain": chain,
        "longest_chain_length": len(chain),
        "two_task_chains": len(links),
        "broken_links": sum(1 for pair in pairs if pair["reason"] == "BROKEN_LINK"),
        "oracle_dependent_pairs": sum(1 for pair in pairs
                                      if pair["reason"] == "ORACLE_DEPENDENCE"),
        "measurement_errors": len(errors),
        "bases_that_are_not_ancestors_of_their_candidate": [
            relation["id"] for relation in relations if not relation["base_ancestor_candidate"]],
        "verdict": verdict,
    }


def render(report: dict) -> str:
    """Deterministic JSON: one line per task and per pair, so the output stays reviewable."""
    head = ("schema_version", "program", "source_sha", "registry", "registry_sha256",
            "measurement_repo_is_harness_head", "python")
    lines = ["{"]
    for key in head:
        lines.append(f"  {json.dumps(key)}: {json.dumps(report[key], sort_keys=True)},")
    for key in ("tasks", "base_to_candidate", "pairs"):
        lines.append(f"  {json.dumps(key)}: [")
        rows = [f"    {json.dumps(row, sort_keys=True)}" for row in report[key]]
        lines.append(",\n".join(rows))
        lines.append("  ],")
    lines.append(f"  {json.dumps('summary')}: "
                 f"{json.dumps(report['summary'], indent=2, sort_keys=True).replace(chr(10), chr(10) + '  ')}")
    lines.append("}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True,
                        help="checkout to measure; must sit at this program's own commit")
    parser.add_argument("--tasks", default="",
                        help="comma-separated task ids, for a scoped re-run (default: all)")
    args = parser.parse_args()
    repo = args.repo.resolve()
    try:
        tasks = load_tasks()
    except Exception as exc:                                  # noqa: BLE001 - fail closed
        print(json.dumps({"schema_version": 1, "program": PROGRAM_REL,
                          "error": f"FROZEN_INPUT_UNREADABLE:{type(exc).__name__}"}))
        return 2
    if args.tasks:
        wanted = {item.strip() for item in args.tasks.split(",") if item.strip()}
        tasks = [task for task in tasks if task["id"] in wanted]
        if not tasks:
            print(json.dumps({"schema_version": 1, "program": PROGRAM_REL,
                              "error": "NO_SUCH_TASK"}))
            return 2
    missing = [f"{task['id']}:{oid}" for task in tasks for oid in (task["base"], task["candidate"])
               if not commit_exists(repo, oid)]
    if missing:
        print(json.dumps({"schema_version": 1, "program": PROGRAM_REL,
                          "error": "FROZEN_COMMIT_MISSING", "missing": missing}))
        return 3
    harness_head = head_of(ROOT)
    source = head_of(repo)
    if harness_head != source:
        print(json.dumps({"schema_version": 1, "program": PROGRAM_REL,
                          "error": "MEASUREMENT_REPO_NOT_AT_HARNESS_HEAD",
                          "harness_head": harness_head, "repo_head": source}))
        return 4
    relations = []
    for task in tasks:
        relations.append({"id": task["id"],
                          "base_ancestor_candidate": is_ancestor(repo, task["base"],
                                                                 task["candidate"]),
                          "candidate_ancestor_base": is_ancestor(repo, task["candidate"],
                                                                 task["base"])})
    accept_fn = make_accept_fn(source)
    pairs = [measure_pair(repo, first, second, accept_fn)
             for first in tasks for second in tasks if first["id"] != second["id"]]
    report = {
        "schema_version": 1,
        "program": PROGRAM_REL,
        "source_sha": source,
        "registry": REGISTRY_REL,
        "registry_sha256": hashlib.sha256(Path(REGISTRY).read_bytes()).hexdigest(),
        "measurement_repo_is_harness_head": harness_head == source,
        "python": sys.version.split()[0],
        "tasks": tasks,
        "base_to_candidate": relations,
        "pairs": pairs,
        "summary": summarise(tasks, pairs, relations),
    }
    print(render(report))
    return 1 if report["summary"]["measurement_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
