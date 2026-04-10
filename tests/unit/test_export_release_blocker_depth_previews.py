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


def test_export_release_runtime_maturity_preview(tmp_path: Path) -> None:
    payload = _run(
        "export_release_runtime_maturity_preview.py",
        tmp_path / "release_runtime_maturity_preview.json",
        tmp_path / "release_runtime_maturity_preview.md",
    )
    summary = payload["summary"]
    assert payload["artifact_id"] == "release_runtime_maturity_preview"
    assert summary["cohort_size"] == 12
    assert summary["resumed_run_processed_examples"] == 12
    assert summary["identity_safe_resume"] is True
    assert summary["runtime_maturity_state"] == "prototype_runtime_resumable"


def test_export_release_source_coverage_depth_preview(tmp_path: Path) -> None:
    payload = _run(
        "export_release_source_coverage_depth_preview.py",
        tmp_path / "release_source_coverage_depth_preview.json",
        tmp_path / "release_source_coverage_depth_preview.md",
    )
    summary = payload["summary"]
    assert payload["artifact_id"] == "release_source_coverage_depth_preview"
    assert summary["total_accessions"] == 12
    assert summary["thin_coverage_count"] == 10
    assert summary["direct_live_smoke_count"] == 3
    assert summary["coverage_depth_state"] == "thin_lane_heavy"


def test_export_release_provenance_depth_preview(tmp_path: Path) -> None:
    payload = _run(
        "export_release_provenance_depth_preview.py",
        tmp_path / "release_provenance_depth_preview.json",
        tmp_path / "release_provenance_depth_preview.md",
    )
    summary = payload["summary"]
    assert payload["artifact_id"] == "release_provenance_depth_preview"
    assert summary["ledger_entry_count"] == 12
    assert summary["ledger_blocked_count"] == 12
    assert summary["release_card_count"] == 3
    assert summary["provenance_depth_state"] == "ledger_present_but_blocked"
