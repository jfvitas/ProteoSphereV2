from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_release_grade_runbook_preview(tmp_path: Path) -> None:
    output_json = tmp_path / "release_grade_runbook_preview.json"
    output_md = tmp_path / "release_grade_runbook_preview.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_release_grade_runbook_preview.py"),
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
    steps = payload["steps"]

    assert payload["artifact_id"] == "release_grade_runbook_preview"
    assert payload["status"] == "report_only"
    assert summary["release_grade_status"] == "blocked_on_release_grade_bar"
    assert summary["command_count"] == 7
    assert summary["runtime_maturity_state"] == "prototype_runtime_resumable"
    assert summary["coverage_depth_state"] == "thin_lane_heavy"
    assert summary["provenance_depth_state"] == "ledger_present_but_blocked"
    assert steps[0]["step_id"] == "refresh_release_surfaces"
    assert steps[-1]["step_id"] == "hold_release_claim"
    assert output_md.exists()
