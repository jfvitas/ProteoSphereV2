from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_release_accession_action_queue_preview_reports_action_lanes(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "release_accession_action_queue_preview.json"
    output_md = tmp_path / "release_accession_action_queue_preview.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_release_accession_action_queue_preview.py"),
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
    rows = payload["rows"]

    assert payload["artifact_id"] == "release_accession_action_queue_preview"
    assert payload["status"] == "report_only"
    assert summary["action_row_count"] == 12
    assert summary["promotion_review_count"] == 2
    assert summary["support_only_hold_count"] == 7
    assert summary["source_fix_followup_count"] == 3
    assert summary["top_priority_accessions"][:2] == ["Q9NZD4", "P00387"]
    assert rows[0]["action_lane"] == "promotion_review"
    assert rows[0]["release_wide_blockers"] == [
        "runtime maturity",
        "source coverage depth",
        "provenance/reporting depth",
    ]
    assert output_md.exists()
