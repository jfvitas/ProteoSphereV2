from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_release_grade_readiness_preview_reports_dataset_complete(tmp_path: Path) -> None:
    output_json = tmp_path / "release_grade_readiness_preview.json"
    output_md = tmp_path / "release_grade_readiness_preview.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_release_grade_readiness_preview.py"),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    summary = payload["summary"]

    assert payload["status"] == "report_only"
    assert summary["release_grade_status"] == "frozen_v1_bar_closed"
    assert summary["dataset_creation_complete_for_current_scope"] is True
    assert summary["final_dataset_bundle_present"] is True
    assert summary["blocker_count"] == 0
    assert summary["deferred_to_v2_count"] == 4
    assert len(payload["blocker_rows"]) == 0
