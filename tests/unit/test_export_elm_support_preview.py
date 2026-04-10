from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_elm_support_and_validation_previews(tmp_path: Path) -> None:
    support_json = tmp_path / "elm_support_preview.json"
    support_md = tmp_path / "elm_support_preview.md"
    validation_json = tmp_path / "elm_support_validation_preview.json"
    validation_md = tmp_path / "elm_support_validation_preview.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_elm_support_preview.py"),
            "--output-json",
            str(support_json),
            "--output-md",
            str(support_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_elm_support_validation_preview.py"),
            "--support-json",
            str(support_json),
            "--output-json",
            str(validation_json),
            "--output-md",
            str(validation_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    support = json.loads(support_json.read_text(encoding="utf-8"))
    validation = json.loads(validation_json.read_text(encoding="utf-8"))
    rows = {row["accession"]: row for row in support["rows"]}

    assert support["artifact_id"] == "elm_support_preview"
    assert support["status"] == "complete"
    assert support["summary"]["cohort_accession_count"] == 12
    assert support["summary"]["elm_class_catalog_count"] == 353
    assert support["summary"]["elm_interaction_row_count"] == 2797
    assert support["summary"]["supported_accessions"] == ["P04637", "P31749"]
    assert rows["P04637"]["interaction_overlap_count"] == 6
    assert rows["P31749"]["interaction_overlap_count"] == 17
    assert validation["artifact_id"] == "elm_support_validation_preview"
    assert validation["status"] == "aligned"
    assert validation["validation"]["issue_count"] == 0
    assert "ELM Support Preview" in support_md.read_text(encoding="utf-8")
    assert "ELM Support Validation Preview" in validation_md.read_text(encoding="utf-8")
