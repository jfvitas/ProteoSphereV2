from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_release_grade_closure_queue_preview_reports_ranked_actions(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "release_grade_closure_queue_preview.json"
    output_md = tmp_path / "release_grade_closure_queue_preview.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_release_grade_closure_queue_preview.py"),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        check=True,
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    summary = payload["summary"]
    queue_rows = payload["queue_rows"]

    assert payload["artifact_id"] == "release_grade_closure_queue_preview"
    assert payload["status"] == "report_only"
    assert summary["release_grade_status"] == "frozen_v1_bar_closed"
    assert summary["queue_length"] == 0
    assert summary["ready_to_execute_count"] == 0
    assert summary["final_dataset_bundle_present"] is True
    assert summary["package_readiness_state"] == "ready_for_package"
    assert queue_rows == []
    assert output_md.exists()
