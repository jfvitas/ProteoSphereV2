from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_export(script_name: str, tmp_path: Path) -> tuple[dict[str, object], str]:
    output_json = tmp_path / f"{script_name}.json"
    output_md = tmp_path / f"{script_name}.md"
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
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    return payload, markdown


def test_export_training_set_readiness_preview(tmp_path: Path) -> None:
    payload, markdown = _run_export("export_training_set_readiness_preview.py", tmp_path)

    assert payload["status"] == "report_only"
    assert payload["readiness_state"] == "package_ready_previewable"
    assert payload["summary"]["selected_count"] == 12
    assert payload["summary"]["governing_ready_count"] == 2
    assert payload["summary"]["blocked_pending_acquisition_count"] == 3
    assert payload["summary"]["package_ready"] is True
    assert payload["summary"]["blocked_reasons"] == []
    assert "Training Set Readiness Preview" in markdown

    rows = {row["accession"]: row for row in payload["readiness_rows"]}
    assert rows["P00387"]["training_set_state"] == "governing_ready"
    assert rows["Q9NZD4"]["training_set_state"] == "governing_ready"
    assert rows["Q2TAC2"]["training_set_state"] == "blocked_pending_acquisition"
    assert rows["P09105"]["recommended_next_step"].startswith("wait_for_source_fix:")


def test_export_cohort_compiler_preview(tmp_path: Path) -> None:
    payload, markdown = _run_export("export_cohort_compiler_preview.py", tmp_path)

    assert payload["status"] == "report_only"
    assert payload["row_count"] == 12
    assert payload["summary"]["selected_count"] == 12
    assert payload["summary"]["split_assignment_ready"] is True
    assert payload["summary"]["selected_split_counts"] == {"train": 8, "val": 2, "test": 2}
    assert "Cohort Compiler Preview" in markdown

    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P00387"]["training_set_state"] == "governing_ready"
    assert rows["Q9NZD4"]["training_set_state"] == "governing_ready"
    assert rows["Q9UCM0"]["training_set_state"] == "blocked_pending_acquisition"


def test_export_balance_diagnostics_preview(tmp_path: Path) -> None:
    payload, markdown = _run_export("export_balance_diagnostics_preview.py", tmp_path)

    assert payload["status"] == "report_only"
    assert payload["summary"]["selected_count"] == 12
    assert payload["summary"]["split_counts"] == {"train": 8, "val": 2, "test": 2}
    assert payload["summary"]["bucket_counts"] == {
        "rich_coverage": 4,
        "moderate_coverage": 4,
        "sparse_or_control": 4,
    }
    assert payload["summary"]["thin_coverage_count"] == 10
    assert payload["summary"]["mixed_evidence_count"] == 1
    assert "Balance Diagnostics Preview" in markdown

    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P00387"]["thin_coverage"] is True
    assert rows["Q9UCM0"]["missing_modalities"] == ["structure", "ligand", "ppi"]


def test_export_package_readiness_preview(tmp_path: Path) -> None:
    payload, markdown = _run_export("export_package_readiness_preview.py", tmp_path)

    assert payload["status"] == "report_only"
    assert payload["readiness_state"] == "ready_for_package"
    assert payload["summary"]["fold_export_ready"] is True
    assert payload["summary"]["cv_fold_export_unlocked"] is True
    assert payload["summary"]["final_split_committed"] is False
    assert payload["summary"]["blocker_count"] == 0
    assert payload["summary"]["blocked_reasons"] == []
    assert payload["summary"]["ready_for_package"] is True
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["non_governing"] is True
    assert "Package Readiness Preview" in markdown
