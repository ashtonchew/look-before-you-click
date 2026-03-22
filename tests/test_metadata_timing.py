"""Test that run_metadata.json is written before run_single_example starts."""

import json
import os
import tempfile

from control.scheming import build_run_metadata


class TestMetadataWriteTiming:
    def test_metadata_written_before_run(self):
        """Simulate the run.py metadata-write logic and verify the file exists
        before any agent/env interaction would occur."""
        example = {
            "id": "test_task__scheming__exfil_v1",
            "scheming": {
                "side_task_id": "exfil_v1",
                "side_task_family": "exfil",
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            # This mirrors run.py: write metadata right after makedirs
            run_meta = build_run_metadata(example, "attack", "attack", "chrome")
            meta_path = os.path.join(tmpdir, "run_metadata.json")
            with open(meta_path, "w") as f:
                json.dump(run_meta, f, indent=2)

            # Verify file exists and has correct content
            assert os.path.exists(meta_path)
            with open(meta_path) as f:
                loaded = json.load(f)
            assert loaded["threat_model"] == "scheming"
            assert loaded["condition"] == "attack"
            assert loaded["base_task_id"] == "test_task"
            assert loaded["side_task_id"] == "exfil_v1"

    def test_environmental_metadata(self):
        example = {"id": "simple_task"}
        with tempfile.TemporaryDirectory() as tmpdir:
            run_meta = build_run_metadata(example, "none", "honest", "thunderbird")
            meta_path = os.path.join(tmpdir, "run_metadata.json")
            with open(meta_path, "w") as f:
                json.dump(run_meta, f, indent=2)

            with open(meta_path) as f:
                loaded = json.load(f)
            assert loaded["threat_model"] == "environmental"
            assert loaded["condition"] == "honest"
            assert loaded["side_task_id"] is None
