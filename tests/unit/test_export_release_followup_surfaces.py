from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(script_name: str, output_json: Path, output_md: Path) -> dict[str, object]:
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / script_name),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    return json.loads(output_json.read_text(encoding="utf-8"))


def test_export_release_promotion_gate_preview(tmp_path: Path) -> None:
    payload = _run(
        "export_release_promotion_gate_preview.py",
        tmp_path / "release_promotion_gate_preview.json",
        tmp_path / "release_promotion_gate_preview.md",
    )
    summary = payload["summary"]
    rows = payload["rows"]

    assert payload["artifact_id"] == "release_promotion_gate_preview"
    assert summary["candidate_count"] == 2
    assert summary["promotion_gate_state"] == "open_for_governing_review"
    assert summary["promotion_ready_now"] is True
    assert summary["top_candidate_accessions"][:2] == ["Q9NZD4", "P00387"]
    assert rows[0]["accession"] == "Q9NZD4"


def test_export_release_source_fix_followup_batch_preview(tmp_path: Path) -> None:
    payload = _run(
        "export_release_source_fix_followup_batch_preview.py",
        tmp_path / "release_source_fix_followup_batch_preview.json",
        tmp_path / "release_source_fix_followup_batch_preview.md",
    )
    summary = payload["summary"]
    rows = payload["rows"]

    assert payload["artifact_id"] == "release_source_fix_followup_batch_preview"
    assert summary["batch_row_count"] == 3
    assert summary["blocked_accession_count"] == 3
    assert summary["next_batch_state"] == "source_fix_followup_active"
    assert rows[0]["accession"] == "Q2TAC2"
