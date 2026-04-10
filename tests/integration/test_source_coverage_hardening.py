from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "emit_source_coverage.py"
SOURCE_COVERAGE = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "source_coverage.json"
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _without_generated_at(payload: dict) -> dict:
    clone = dict(payload)
    clone.pop("generated_at", None)
    return clone


def test_source_coverage_hardening_re_emits_conservative_inventory(tmp_path) -> None:
    output = tmp_path / "source_coverage.json"

    subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        check=True,
        cwd=ROOT,
    )

    emitted = _read_json(output)
    committed = _read_json(SOURCE_COVERAGE)
    emitted_matrix = emitted["coverage_matrix"]
    verified_rows = [
        row for row in emitted_matrix if row["validation_class"] == "verified_accession"
    ]

    assert _without_generated_at(emitted) == _without_generated_at(committed)

    semantics = emitted["semantics"]
    summary = emitted["summary"]

    assert semantics["coverage_not_validation"] is True
    assert semantics["release_grade_corpus_validation"] is False
    assert semantics["mixed_evidence_rows_are_conservative"] is True
    assert summary["lane_depth_counts"] == {"1": 10, "2": 1, "5": 1}
    assert summary["verified_accession_accessions"] == ["P09105", "Q9UCM0"]
    assert summary["thin_coverage_accessions"] == [
        "P04637",
        "P31749",
        "Q9NZD4",
        "Q2TAC2",
        "P00387",
        "P02042",
        "P02100",
        "P69892",
        "P09105",
        "Q9UCM0",
    ]

    assert [row["accession"] for row in verified_rows] == ["P09105", "Q9UCM0"]
    for row in verified_rows:
        assert row["thin_coverage"] is True
        assert row["lane_depth"] == 1
        assert row["source_lanes"] == ["UniProt"]
        assert row["conservative_evidence_tier"] == "verified_accession_single_lane"
