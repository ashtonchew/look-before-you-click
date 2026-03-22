"""Validate expansion and correction manifests resolve through the runner path.

Uses the same path resolution as run.py / run_parallel.py:
  {base_dir}/examples/{domain}/{task_id}.json

Covers:
  - A2 per-variant manifests (env1, env2, schem1)
  - Correction manifests (router, schem_email, typed_env, typed_schem)
  - Narrowed typed-env task JSONs (exactly 1 injection/goal each)
  - Typed-schem attack manifest (beacon_nav only)
"""

import json
import os
import re


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_HARM = os.path.join(PROJECT_ROOT, "os-harm")


def _resolve_task_json(task_id: str, domain: str, base_dir: str) -> str:
    """Resolve a task JSON path using the same logic as run.py."""
    return os.path.join(base_dir, f"examples/{domain}/{task_id}.json")


def _extract_goal_names_from_run_parallel() -> set[str]:
    """Parse ALL_INJECTION_GOALS dict keys from run_parallel.py via regex."""
    run_py = os.path.join(OS_HARM, "run_parallel.py")
    with open(run_py, "r", encoding="utf-8") as f:
        src = f.read()
    block_match = re.search(
        r"ALL_INJECTION_GOALS\s*=\s*\{(.+?)\n\s*\}",
        src,
        re.DOTALL,
    )
    assert block_match, "Could not find ALL_INJECTION_GOALS dict in run_parallel.py"
    block = block_match.group(1)
    return set(re.findall(r'"([a-z0-9_]+)"\s*:', block))


def _iter_manifest_tasks(manifests):
    """Yield (manifest_path, base_dir, domain, task_id) for every task in manifests."""
    for manifest_path, base_dir in manifests:
        if not os.path.isfile(manifest_path):
            continue
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        for domain, task_ids in manifest.items():
            for tid in task_ids:
                yield manifest_path, base_dir, domain, tid


# ---------------------------------------------------------------------------
# A2 per-variant manifests
# ---------------------------------------------------------------------------

A2_PER_VARIANT_MANIFESTS = [
    (
        os.path.join(OS_HARM, "evaluation_examples", "test_a2_env1_selected.json"),
        os.path.join(OS_HARM, "evaluation_examples_selected"),
    ),
    (
        os.path.join(OS_HARM, "evaluation_examples", "test_a2_env2_selected.json"),
        os.path.join(OS_HARM, "evaluation_examples_selected"),
    ),
    (
        os.path.join(OS_HARM, "evaluation_examples", "test_a2_schem1_selected.json"),
        os.path.join(OS_HARM, "evaluation_examples_scheming_selected"),
    ),
]


class TestExpansionManifests:

    def test_a2_per_variant_manifests_exist(self):
        for manifest_path, _ in A2_PER_VARIANT_MANIFESTS:
            assert os.path.isfile(manifest_path), f"Manifest missing: {manifest_path}"

    def test_a2_per_variant_task_jsons_resolve(self):
        """Every per-variant manifest entry resolves to an existing task JSON."""
        for manifest_path, base_dir, domain, tid in _iter_manifest_tasks(
            A2_PER_VARIANT_MANIFESTS
        ):
            path = _resolve_task_json(tid, domain, base_dir)
            assert os.path.isfile(path), (
                f"Task JSON not found at {path} "
                f"(manifest={os.path.basename(manifest_path)})"
            )

    def test_a2_per_variant_goal_names_valid(self):
        """Injection goals in per-variant A2 tasks exist in run_parallel.py."""
        known_goals = _extract_goal_names_from_run_parallel()
        for manifest_path, base_dir, domain, tid in _iter_manifest_tasks(
            A2_PER_VARIANT_MANIFESTS
        ):
            path = _resolve_task_json(tid, domain, base_dir)
            assert os.path.isfile(path), f"Task JSON not found at {path}"
            with open(path, "r", encoding="utf-8") as f:
                task = json.load(f)
            for inj in task.get("injections", []):
                for goal in inj.get("goals", []):
                    assert goal in known_goals, (
                        f"Goal {goal!r} (task={tid!r}) not in run_parallel.py "
                        f"ALL_INJECTION_GOALS. Known: {sorted(known_goals)}"
                    )

    def test_a2_env1_has_one_task(self):
        """env1 manifest should contain exactly the reframed exfil task."""
        path = os.path.join(
            OS_HARM, "evaluation_examples", "test_a2_env1_selected.json"
        )
        with open(path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest == {"thunderbird": ["__injected_email__a2_reframed"]}

    def test_a2_env2_has_one_task(self):
        """env2 manifest should contain exactly the reviewer-aware task."""
        path = os.path.join(
            OS_HARM, "evaluation_examples", "test_a2_env2_selected.json"
        )
        with open(path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest == {"thunderbird": ["__injected_email__a2_reviewer_aware"]}

    def test_a2_schem1_has_one_task(self):
        """schem1 manifest should contain exactly the protocol-aware scheming task."""
        path = os.path.join(
            OS_HARM, "evaluation_examples", "test_a2_schem1_selected.json"
        )
        with open(path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest == {
            "thunderbird": ["__injected_email__scheming__upload_credentials__a2"]
        }


# ---------------------------------------------------------------------------
# Correction manifests
# ---------------------------------------------------------------------------

# The typed-env manifest resolves against the narrowed corrections base dir,
# not evaluation_examples_selected, so only the targeted injection/goal combos run.
CORRECTIONS_BASE = os.path.join(OS_HARM, "evaluation_examples_corrections")

CORRECTION_MANIFESTS = [
    (
        os.path.join(
            OS_HARM, "evaluation_examples", "test_corrections_router_selected.json"
        ),
        os.path.join(OS_HARM, "evaluation_examples_scheming_selected"),
    ),
    (
        os.path.join(
            OS_HARM,
            "evaluation_examples",
            "test_corrections_schem_email_selected.json",
        ),
        os.path.join(OS_HARM, "evaluation_examples_scheming_selected"),
    ),
    (
        os.path.join(
            OS_HARM,
            "evaluation_examples",
            "test_corrections_typed_env_selected.json",
        ),
        CORRECTIONS_BASE,
    ),
    (
        os.path.join(
            OS_HARM,
            "evaluation_examples",
            "test_corrections_typed_schem_selected.json",
        ),
        os.path.join(OS_HARM, "evaluation_examples_scheming_selected"),
    ),
    (
        os.path.join(
            OS_HARM,
            "evaluation_examples",
            "test_corrections_typed_schem_attack_selected.json",
        ),
        os.path.join(OS_HARM, "evaluation_examples_scheming_selected"),
    ),
]


class TestCorrectionManifests:

    def test_correction_manifests_exist(self):
        for manifest_path, _ in CORRECTION_MANIFESTS:
            assert os.path.isfile(manifest_path), f"Manifest missing: {manifest_path}"

    def test_correction_task_jsons_resolve(self):
        """Every correction manifest entry resolves to an existing task JSON."""
        for manifest_path, base_dir, domain, tid in _iter_manifest_tasks(
            CORRECTION_MANIFESTS
        ):
            path = _resolve_task_json(tid, domain, base_dir)
            assert os.path.isfile(path), (
                f"Task JSON not found at {path} "
                f"(manifest={os.path.basename(manifest_path)})"
            )

    def test_schem_email_tasks_have_scheming_block(self):
        """The 3 scheming email correction tasks should have a scheming block."""
        manifest_path = os.path.join(
            OS_HARM,
            "evaluation_examples",
            "test_corrections_schem_email_selected.json",
        )
        base_dir = os.path.join(OS_HARM, "evaluation_examples_scheming_selected")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        for domain, task_ids in manifest.items():
            for tid in task_ids:
                path = _resolve_task_json(tid, domain, base_dir)
                with open(path, "r", encoding="utf-8") as f:
                    task = json.load(f)
                assert "scheming" in task, (
                    f"Task {tid!r} missing 'scheming' block "
                    f"(expected scheming task)"
                )

    def test_router_task_is_vs_code_delete_backup(self):
        """Router correction manifest should target the delete_backup task."""
        manifest_path = os.path.join(
            OS_HARM,
            "evaluation_examples",
            "test_corrections_router_selected.json",
        )
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert "vs_code" in manifest
        assert len(manifest["vs_code"]) == 1
        assert "delete_backup" in manifest["vs_code"][0]

    def test_typed_schem_honest_has_two_tasks(self):
        """Typed-schem honest manifest should have beacon_nav + delete_backup."""
        manifest_path = os.path.join(
            OS_HARM,
            "evaluation_examples",
            "test_corrections_typed_schem_selected.json",
        )
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        tasks = manifest["thunderbird"]
        assert len(tasks) == 2
        assert "__injected_draft__scheming__beacon_nav" in tasks
        assert "__injected_draft__scheming__delete_backup" in tasks

    def test_typed_schem_attack_has_one_task(self):
        """Typed-schem attack manifest should have beacon_nav only."""
        manifest_path = os.path.join(
            OS_HARM,
            "evaluation_examples",
            "test_corrections_typed_schem_attack_selected.json",
        )
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest == {
            "thunderbird": ["__injected_draft__scheming__beacon_nav"]
        }

    def test_typed_schem_tasks_have_scheming_block(self):
        """All typed-schem correction tasks should have scheming blocks."""
        for manifest_name in [
            "test_corrections_typed_schem_selected.json",
            "test_corrections_typed_schem_attack_selected.json",
        ]:
            manifest_path = os.path.join(
                OS_HARM, "evaluation_examples", manifest_name
            )
            base_dir = os.path.join(OS_HARM, "evaluation_examples_scheming_selected")
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            for domain, task_ids in manifest.items():
                for tid in task_ids:
                    path = _resolve_task_json(tid, domain, base_dir)
                    with open(path, "r", encoding="utf-8") as f:
                        task = json.load(f)
                    assert "scheming" in task, (
                        f"Task {tid!r} missing 'scheming' block"
                    )

    def test_typed_env_narrowed_tasks_exist(self):
        """Narrowed task JSONs in evaluation_examples_corrections/ must exist."""
        for name in ["__injected_draft.json", "__injected_email.json"]:
            path = os.path.join(
                CORRECTIONS_BASE, "examples", "thunderbird", name
            )
            assert os.path.isfile(path), f"Narrowed task JSON missing: {path}"

    def test_typed_env_narrowed_draft_has_one_goal(self):
        """Narrowed __injected_draft should have exactly terminal_local_script."""
        path = os.path.join(
            CORRECTIONS_BASE,
            "examples",
            "thunderbird",
            "__injected_draft.json",
        )
        with open(path, "r", encoding="utf-8") as f:
            task = json.load(f)
        assert len(task["injections"]) == 1
        inj = task["injections"][0]
        assert inj["type"] == "thunderbird_mail_draft"
        assert inj["goals"] == ["terminal_local_script"]

    def test_typed_env_narrowed_email_has_one_goal(self):
        """Narrowed __injected_email should have exactly swisstransfer_send_files."""
        path = os.path.join(
            CORRECTIONS_BASE,
            "examples",
            "thunderbird",
            "__injected_email.json",
        )
        with open(path, "r", encoding="utf-8") as f:
            task = json.load(f)
        assert len(task["injections"]) == 1
        inj = task["injections"][0]
        assert inj["type"] == "desktop_notification"
        assert inj["goals"] == ["swisstransfer_send_files"]

    def test_typed_env_narrowed_goals_valid(self):
        """Goals in narrowed task JSONs must exist in run_parallel.py."""
        known_goals = _extract_goal_names_from_run_parallel()
        for name in ["__injected_draft.json", "__injected_email.json"]:
            path = os.path.join(
                CORRECTIONS_BASE, "examples", "thunderbird", name
            )
            with open(path, "r", encoding="utf-8") as f:
                task = json.load(f)
            for inj in task["injections"]:
                for goal in inj["goals"]:
                    assert goal in known_goals, (
                        f"Goal {goal!r} not in ALL_INJECTION_GOALS"
                    )
