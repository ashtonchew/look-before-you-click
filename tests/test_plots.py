"""Unit tests for analysis/plots.py failure taxonomy plot and concentration helpers."""

import os


from analysis.concentration import compute_failure_taxonomy, taxonomy_to_plot_data
from analysis.plots import write_failure_taxonomy_plot


class TestFailureTaxonomyPlot:

    def test_empty_dict_returns_none(self):
        assert write_failure_taxonomy_plot({}, "/tmp") is None

    def test_none_returns_none(self):
        assert write_failure_taxonomy_plot(None, "/tmp") is None

    def test_empty_threat_models_returns_none(self):
        assert write_failure_taxonomy_plot({"timing": {}}, "/tmp") is None

    def test_produces_file(self, tmp_path):
        counts = {
            "timing": {"environmental": 0, "scheming": 3},
            "router_gap": {"environmental": 1, "scheming": 0},
        }
        path = write_failure_taxonomy_plot(counts, str(tmp_path))
        assert path is not None
        assert os.path.isfile(path)
        assert path.endswith("failure_taxonomy.png")

    def test_all_zero_counts_returns_none(self):
        counts = {
            "timing": {"environmental": 0, "scheming": 0},
            "router_gap": {"environmental": 0},
        }
        assert write_failure_taxonomy_plot(counts, "/tmp") is None

    def test_mixed_zero_and_nonzero_produces_file(self, tmp_path):
        counts = {
            "timing": {"environmental": 0, "scheming": 1},
            "router_gap": {"environmental": 0, "scheming": 0},
        }
        path = write_failure_taxonomy_plot(counts, str(tmp_path))
        assert path is not None
        assert os.path.isfile(path)

    def test_single_threat_model(self, tmp_path):
        counts = {"boundary": {"environmental": 1}}
        path = write_failure_taxonomy_plot(counts, str(tmp_path))
        assert path is not None
        assert os.path.isfile(path)


class TestTaxonomyNoCrossThreadDoubleCount:
    """Regression: taxonomy must not double-count when a failure mode
    appears in both threat models."""

    def _ann(self, fm, outcome, tm, task_id="t"):
        return {"failure_mode": fm, "outcome": outcome, "threat_model": tm, "task_id": task_id}

    def test_shared_failure_mode_counts_separately(self):
        annotations = [
            self._ann("timing", "harm_blocked", "environmental"),
            self._ann("timing", "harm_blocked", "environmental"),
            self._ann("timing", "harm_blocked", "scheming"),
        ]
        taxonomy = compute_failure_taxonomy(annotations)
        plot = taxonomy_to_plot_data(taxonomy)
        assert plot["timing"]["environmental"] == 2
        assert plot["timing"]["scheming"] == 1

    def test_single_threat_model_no_duplication(self):
        annotations = [
            self._ann("router_gap", "harm_succeeded", "environmental"),
            self._ann("router_gap", "harm_succeeded", "environmental"),
        ]
        taxonomy = compute_failure_taxonomy(annotations)
        plot = taxonomy_to_plot_data(taxonomy)
        assert plot["router_gap"] == {"environmental": 2}

    def test_taxonomy_rows_have_scalar_threat_model(self):
        annotations = [
            self._ann("boundary", "harm_blocked", "environmental"),
            self._ann("boundary", "harm_blocked", "scheming"),
        ]
        taxonomy = compute_failure_taxonomy(annotations)
        for row in taxonomy:
            assert "," not in row["threat_model"]
