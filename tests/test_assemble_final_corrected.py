"""Validate the assembly corrections mapping and expected overlay counts.

Reads configs/assembly_corrections_map.json (single source of truth)
and checks structural invariants without running the shell script.
"""

import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_PATH = os.path.join(PROJECT_ROOT, "configs", "assembly_corrections_map.json")
HISTORICAL_ROOT = os.path.join(PROJECT_ROOT, "results_backup", "final_historical")


def _load_map():
    with open(MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Valid historical cohort names (the 8 original final-push groups)
VALID_COHORTS = {
    "final_env_b0_honest",
    "final_env_b0_attack",
    "final_env_b4_honest",
    "final_env_b4_attack",
    "final_schem_b0_honest",
    "final_schem_b0_attack",
    "final_schem_b4_honest",
    "final_schem_b4_attack",
}

# Expansion cohort names that must NOT appear
EXPANSION_COHORTS = {
    "final_env_b1_honest",
    "final_env_b1_attack",
    "final_env_b2_honest",
    "final_env_b2_attack",
    "final_env_b3_honest",
    "final_env_b3_attack",
    "final_a2_env1_b0",
    "final_a2_env1_b4",
    "final_a2_env2_b0",
    "final_a2_env2_b4",
    "final_a2_schem1_b0",
    "final_a2_schem1_b4",
}


class TestAssemblyMap:

    def test_map_file_exists(self):
        assert os.path.isfile(MAP_PATH), f"Mapping file missing: {MAP_PATH}"

    def test_map_is_valid_json(self):
        mapping = _load_map()
        assert "inner_prefix" in mapping
        assert "overlays" in mapping
        assert isinstance(mapping["overlays"], list)

    def test_inner_prefix_matches_runner(self):
        mapping = _load_map()
        assert mapping["inner_prefix"] == "pyautogui/screenshot_a11y_tree/o4-mini"

    def test_exactly_9_rerun_groups(self):
        mapping = _load_map()
        assert len(mapping["overlays"]) == 9

    def test_exactly_19_task_overlays(self):
        mapping = _load_map()
        total = sum(len(entry["tasks"]) for entry in mapping["overlays"])
        assert total == 19, f"Expected 19 task overlays, got {total}"

    def test_group_a_has_2_tasks(self):
        """Router coverage: 2 rerun groups x 1 task = 2."""
        mapping = _load_map()
        group_a = [e for e in mapping["overlays"] if e["group"] == "A"]
        total = sum(len(e["tasks"]) for e in group_a)
        assert len(group_a) == 2
        assert total == 2

    def test_group_b_has_12_tasks(self):
        """Scheming email: 4 rerun groups x 3 tasks = 12."""
        mapping = _load_map()
        group_b = [e for e in mapping["overlays"] if e["group"] == "B"]
        total = sum(len(e["tasks"]) for e in group_b)
        assert len(group_b) == 4
        assert total == 12

    def test_group_c_has_5_tasks(self):
        """Typed-prose: 3 rerun groups, 5 tasks total."""
        mapping = _load_map()
        group_c = [e for e in mapping["overlays"] if e["group"] == "C"]
        total = sum(len(e["tasks"]) for e in group_c)
        assert len(group_c) == 3
        assert total == 5

    def test_all_target_cohorts_are_valid(self):
        mapping = _load_map()
        for entry in mapping["overlays"]:
            assert entry["target_cohort"] in VALID_COHORTS, (
                f"Target cohort {entry['target_cohort']!r} is not a valid "
                f"historical cohort. Valid: {sorted(VALID_COHORTS)}"
            )

    def test_no_expansion_cohorts_referenced(self):
        mapping = _load_map()
        for entry in mapping["overlays"]:
            assert entry["target_cohort"] not in EXPANSION_COHORTS, (
                f"Target cohort {entry['target_cohort']!r} is an expansion "
                f"cohort -- must not be in corrections map"
            )
            assert entry["rerun_group"] not in EXPANSION_COHORTS, (
                f"Rerun group {entry['rerun_group']!r} looks like an expansion "
                f"cohort"
            )

    def test_no_duplicate_overlay_targets(self):
        mapping = _load_map()
        inner = mapping["inner_prefix"]
        seen = []
        for entry in mapping["overlays"]:
            for task in entry["tasks"]:
                path = f"{entry['target_cohort']}/{inner}/{task}"
                seen.append(path)
        assert len(seen) == len(set(seen)), (
            f"Duplicate overlay targets found: "
            f"{[p for p in seen if seen.count(p) > 1]}"
        )

    def test_no_empty_task_lists(self):
        mapping = _load_map()
        for entry in mapping["overlays"]:
            assert len(entry["tasks"]) > 0, (
                f"Rerun group {entry['rerun_group']!r} has zero tasks"
            )

    def test_all_rerun_group_names_start_with_final_rerun(self):
        mapping = _load_map()
        for entry in mapping["overlays"]:
            assert entry["rerun_group"].startswith("final_rerun_"), (
                f"Rerun group {entry['rerun_group']!r} should start with "
                f"'final_rerun_'"
            )

    def test_no_final_historical_in_rerun_groups(self):
        """Rerun groups must never reference final_historical paths."""
        mapping = _load_map()
        for entry in mapping["overlays"]:
            assert "final_historical" not in entry["rerun_group"]
            assert "final_historical" not in entry["target_cohort"]

    def test_target_task_dirs_exist_in_historical(self):
        """Every overlay target must correspond to a real dir in final_historical."""
        mapping = _load_map()
        inner = mapping["inner_prefix"]
        if not os.path.isdir(HISTORICAL_ROOT):
            return  # skip if historical not present (CI)
        for entry in mapping["overlays"]:
            cohort = entry["target_cohort"]
            cohort_dir = os.path.join(HISTORICAL_ROOT, cohort)
            if not os.path.isdir(cohort_dir):
                continue
            for task in entry["tasks"]:
                task_dir = os.path.join(cohort_dir, inner, task)
                assert os.path.isdir(task_dir), (
                    f"Historical task dir missing (overlay has nothing to "
                    f"replace): {task_dir}"
                )

    def test_rerun_groups_are_unique(self):
        mapping = _load_map()
        groups = [e["rerun_group"] for e in mapping["overlays"]]
        assert len(groups) == len(set(groups)), (
            f"Duplicate rerun group names: "
            f"{[g for g in groups if groups.count(g) > 1]}"
        )
