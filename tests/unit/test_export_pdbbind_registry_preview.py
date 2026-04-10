from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_pdbbind_registry_and_validation_previews(tmp_path: Path) -> None:
    registry_json = tmp_path / "pdbbind_registry_preview.json"
    registry_md = tmp_path / "pdbbind_registry_preview.md"
    validation_json = tmp_path / "pdbbind_validation_preview.json"
    validation_md = tmp_path / "pdbbind_validation_preview.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_pdbbind_registry_preview.py"),
            "--output-json",
            str(registry_json),
            "--output-md",
            str(registry_md),
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
            str(REPO_ROOT / "scripts" / "export_pdbbind_validation_preview.py"),
            "--registry-json",
            str(registry_json),
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

    registry = json.loads(registry_json.read_text(encoding="utf-8"))
    validation = json.loads(validation_json.read_text(encoding="utf-8"))

    assert registry["artifact_id"] == "pdbbind_registry_preview"
    assert registry["status"] == "complete"
    assert registry["summary"]["row_count"] == 23010
    assert registry["summary"]["class_count"] == 4
    assert registry["summary"]["files_present"] == {
        "PL": True,
        "PP": True,
        "PN": True,
        "NL": True,
    }
    assert len(registry["class_samples"]) == 4
    assert validation["artifact_id"] == "pdbbind_validation_preview"
    assert validation["status"] == "aligned"
    assert validation["validation"]["issue_count"] == 0
    assert "PDBbind Registry Preview" in registry_md.read_text(encoding="utf-8")
    assert "PDBbind Validation Preview" in validation_md.read_text(encoding="utf-8")
