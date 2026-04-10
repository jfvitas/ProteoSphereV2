from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE_MANIFEST = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)
SOURCE_COVERAGE = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "source_coverage.json"
)
LEAKAGE_AUDIT = ROOT / "runs" / "real_data_benchmark" / "full_results" / "leakage_audit.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_release_bundle_pins_schema_as_required_artifact() -> None:
    payload = _read_json(BUNDLE_MANIFEST)
    schema_entry = next(item for item in payload["release_artifacts"] if item["role"] == "schema")

    assert payload["status"] == "assembled_with_blockers"
    assert schema_entry["present"] is True
    assert schema_entry["required"] is True
    assert "schema.json" in schema_entry["path"]
    assert "schema.json is a required release artifact" in (
        ROOT / "docs" / "reports" / "release_benchmark_bundle.md"
    ).read_text(encoding="utf-8")


def test_source_coverage_is_conservative_inventory_not_release_validation() -> None:
    payload = _read_json(SOURCE_COVERAGE)
    summary = payload["summary"]
    semantics = payload["semantics"]
    mixed_row = next(row for row in payload["coverage_matrix"] if row["accession"] == "P68871")

    assert semantics["coverage_not_validation"] is True
    assert semantics["release_grade_corpus_validation"] is False
    assert semantics["mixed_evidence_rows_are_conservative"] is True
    assert summary["total_accessions"] == 12
    assert summary["resolved_accessions"] == 12
    assert summary["unresolved_accessions"] == 0
    assert "P68871" in summary["mixed_evidence_accessions"]
    assert mixed_row["mixed_evidence"] is True
    assert mixed_row["conservative_evidence_tier"] == "probe_supported_multilane"


def test_leakage_audit_remains_accession_level_clean() -> None:
    payload = _read_json(LEAKAGE_AUDIT)
    audit = payload["audit"]

    assert audit["accession_level_only"] is True
    assert audit["cross_split_accessions"] == []
    assert audit["cross_split_leakage_keys"] == []
    assert audit["total_rows"] == 12
    assert audit["unique_accessions"] == 12
    assert audit["unique_leakage_keys"] == 12
