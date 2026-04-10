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
RELEASE_REPORT = ROOT / "docs" / "reports" / "release_artifact_hardening.md"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_release_bundle_manifest_requires_schema_and_keeps_blockers() -> None:
    payload = _read_json(BUNDLE_MANIFEST)

    schema_entry = next(item for item in payload["release_artifacts"] if item["role"] == "schema")

    assert payload["status"] == "assembled_with_blockers"
    assert payload["truth_boundary"]["allowed_statuses"] == [
        "assembled_with_blockers",
        "blocked",
    ]
    assert schema_entry["present"] is True
    assert schema_entry["required"] is True
    assert payload["blocker_categories"] == [
        "runtime maturity",
        "source coverage depth",
        "provenance/reporting depth",
    ]


def test_source_coverage_semantics_remain_conservative() -> None:
    payload = _read_json(SOURCE_COVERAGE)
    semantics = payload["semantics"]
    summary = payload["summary"]
    mixed_row = next(row for row in payload["coverage_matrix"] if row["accession"] == "P68871")

    assert semantics["artifact_kind"] == "conservative_source_coverage_inventory"
    assert semantics["coverage_not_validation"] is True
    assert semantics["release_grade_corpus_validation"] is False
    assert semantics["mixed_evidence_rows_are_conservative"] is True
    assert summary["total_accessions"] == 12
    assert summary["resolved_accessions"] == 12
    assert summary["unresolved_accessions"] == 0
    assert summary["mixed_evidence_accessions"] == ["P68871"]
    assert mixed_row["mixed_evidence"] is True
    assert mixed_row["conservative_evidence_tier"] == "probe_supported_multilane"


def test_leakage_audit_and_report_match_the_release_posture() -> None:
    audit = _read_json(LEAKAGE_AUDIT)["audit"]
    report = RELEASE_REPORT.read_text(encoding="utf-8")

    assert audit["accession_level_only"] is True
    assert audit["cross_split_accessions"] == []
    assert audit["cross_split_leakage_keys"] == []
    assert audit["total_rows"] == 12
    assert "launchable as a truthful artifact set" in report
    assert "not a production-equivalent release claim" in report
