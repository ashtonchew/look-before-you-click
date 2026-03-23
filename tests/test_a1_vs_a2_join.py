"""Regression test for A1-vs-A2 environmental join logic.

Ensures _find_rows matches environmental A1 rows via inject_suffix (not task_id)
and that A2-env-2 matches only the substrate-specific Thunderbird received-email row.
"""

from analysis.a1_vs_a2_table import _find_rows


def _row(task_id, experiment, inject_suffix="", is_attack="True", baseline="B0"):
    return {
        "task_id": task_id,
        "experiment": experiment,
        "inject_suffix": inject_suffix,
        "is_attack": is_attack,
        "baseline": baseline,
    }


# Minimal A1 environmental rows mimicking final_corrected
A1_ROWS = [
    # swisstransfer target (env-1 base)
    _row("__injected_email", "final_env_b0_attack",
         "desktop_notification__swisstransfer_send_files", baseline="B0"),
    _row("__injected_email", "final_env_b4_attack",
         "desktop_notification__swisstransfer_send_files", baseline="B4"),
    # Thunderbird received-email url_query_params (env-2 base, correct substrate)
    _row("__injected_email", "final_env_b0_attack",
         "thunderbird_mail_received__url_query_params", baseline="B0"),
    _row("__injected_email", "final_env_b4_attack",
         "thunderbird_mail_received__url_query_params", baseline="B4"),
    # VS Code url_query_params (different domain, should NOT match env-2)
    _row("ec71221e", "final_env_b0_attack",
         "desktop_notification__url_query_params", baseline="B0"),
    # Thunderbird draft url_query_params (different substrate, should NOT match env-2)
    _row("__injected_draft", "final_env_b0_attack",
         "thunderbird_mail_draft__url_query_params", baseline="B0"),
]


def test_env1_finds_swisstransfer_by_inject_suffix():
    result = _find_rows(
        A1_ROWS, "final_env",
        "inject_suffix", "desktop_notification__swisstransfer_send_files",
        True, exact=True,
    )
    assert "B0" in result
    assert "B4" in result
    assert len(result["B0"]) == 1
    assert result["B0"][0]["task_id"] == "__injected_email"


def test_env2_matches_only_thunderbird_received_substrate():
    result = _find_rows(
        A1_ROWS, "final_env",
        "inject_suffix", "thunderbird_mail_received__url_query_params",
        True, exact=True,
    )
    assert "B0" in result
    assert len(result["B0"]) == 1
    assert result["B0"][0]["inject_suffix"] == "thunderbird_mail_received__url_query_params"
    # Must NOT include VS Code or draft substrate rows
    all_suffixes = [r["inject_suffix"] for bl_rows in result.values() for r in bl_rows]
    assert "desktop_notification__url_query_params" not in all_suffixes
    assert "thunderbird_mail_draft__url_query_params" not in all_suffixes


def test_old_task_id_match_would_miss_env_rows():
    """The old code matched task_id substring; verify it would find nothing."""
    result = _find_rows(
        A1_ROWS, "final_env",
        "task_id", "swisstransfer_send_files",
        True, exact=False,
    )
    # task_id is "__injected_email", doesn't contain "swisstransfer_send_files"
    assert len(result) == 0
