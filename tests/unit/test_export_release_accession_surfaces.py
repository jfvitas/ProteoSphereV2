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


def test_export_release_accession_closure_matrix_preview(tmp_path: Path) -> None:
    payload = _run(
        "export_release_accession_closure_matrix_preview.py",
        tmp_path / "release_accession_closure_matrix_preview.json",
        tmp_path / "release_accession_closure_matrix_preview.md",
    )
    summary = payload["summary"]
    rows = payload["rows"]
    assert payload["artifact_id"] == "release_accession_closure_matrix_preview"
    assert summary["accession_count"] == 12
    assert summary["closest_to_release_count"] == 2
    assert summary["blocked_pending_acquisition_count"] == 3
    assert rows[0]["closure_state"] == "closest_to_release"


def test_export_release_candidate_promotion_preview(tmp_path: Path) -> None:
    matrix_json = tmp_path / "release_accession_closure_matrix_preview.json"
    matrix_md = tmp_path / "release_accession_closure_matrix_preview.md"
    _run(
        "export_release_accession_closure_matrix_preview.py",
        matrix_json,
        matrix_md,
    )

    promotion_json = tmp_path / "release_candidate_promotion_preview.json"
    promotion_md = tmp_path / "release_candidate_promotion_preview.md"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_release_candidate_promotion_preview.py"),
            "--closure-matrix",
            str(matrix_json),
            "--output-json",
            str(promotion_json),
            "--output-md",
            str(promotion_md),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(promotion_json.read_text(encoding="utf-8"))
    summary = payload["summary"]
    assert payload["artifact_id"] == "release_candidate_promotion_preview"
    assert summary["candidate_count"] == 2
    assert summary["promotion_blocked"] is True
    assert summary["top_candidate_accessions"] == ["Q9NZD4", "P00387"]
