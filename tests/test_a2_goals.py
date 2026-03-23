"""Validate that all A2 task JSONs reference goal names that exist in run.py.

Uses the same path resolution as run.py (base_dir/examples/{domain}/{task_id}.json)
so mixed-base-dir issues are caught here, not at runtime.
"""

import json
import os
import re


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_HARM = os.path.join(PROJECT_ROOT, "os-harm")

# Each manifest is paired with the base dir that run.py would use.
MANIFESTS = [
    (
        os.path.join(OS_HARM, "evaluation_examples", "test_a2_env_selected.json"),
        os.path.join(OS_HARM, "evaluation_examples_selected"),
    ),
    (
        os.path.join(OS_HARM, "evaluation_examples", "test_a2_schem_selected.json"),
        os.path.join(OS_HARM, "evaluation_examples_scheming_selected"),
    ),
]


def _resolve_task_json(task_id: str, domain: str, base_dir: str) -> str:
    """Resolve a task JSON path using the same logic as run.py."""
    return os.path.join(base_dir, f"examples/{domain}/{task_id}.json")


def _extract_goal_names_from_run_py() -> set[str]:
    """Parse all_injection_goals dict keys from run.py via regex."""
    run_py = os.path.join(OS_HARM, "run.py")
    with open(run_py, "r", encoding="utf-8") as f:
        src = f.read()
    block_match = re.search(
        r"all_injection_goals\s*=\s*\{(.+?)\n\s*\}",
        src,
        re.DOTALL,
    )
    assert block_match, "Could not find all_injection_goals dict in run.py"
    block = block_match.group(1)
    return set(re.findall(r'"([a-z0-9_]+)"\s*:', block))


def _iter_manifest_tasks():
    """Yield (manifest_path, base_dir, domain, task_id) for every A2 task."""
    for manifest_path, base_dir in MANIFESTS:
        if not os.path.isfile(manifest_path):
            continue
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        for domain, task_ids in manifest.items():
            for tid in task_ids:
                yield manifest_path, base_dir, domain, tid


class TestA2GoalReferences:

    def test_manifests_exist(self):
        for manifest_path, _ in MANIFESTS:
            assert os.path.isfile(manifest_path), f"Manifest missing: {manifest_path}"

    def test_all_task_jsons_resolve(self):
        """Every manifest entry resolves via run.py's path construction."""
        for manifest_path, base_dir, domain, tid in _iter_manifest_tasks():
            path = _resolve_task_json(tid, domain, base_dir)
            assert os.path.isfile(path), (
                f"Task JSON not found at {path} "
                f"(manifest={os.path.basename(manifest_path)}, base_dir={os.path.basename(base_dir)})"
            )

    def test_all_goal_names_exist_in_run_py(self):
        known_goals = _extract_goal_names_from_run_py()
        for manifest_path, base_dir, domain, tid in _iter_manifest_tasks():
            path = _resolve_task_json(tid, domain, base_dir)
            assert os.path.isfile(path), f"Task JSON not found at {path}"
            with open(path, "r", encoding="utf-8") as f:
                task = json.load(f)
            for inj in task.get("injections", []):
                for goal in inj.get("goals", []):
                    assert goal in known_goals, (
                        f"Goal {goal!r} (task={tid!r}) not in run.py "
                        f"all_injection_goals. Known: {sorted(known_goals)}"
                    )
