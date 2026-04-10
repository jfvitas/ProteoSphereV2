from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "artifacts" / "status" / "release_cohort_registry.json"
LEDGER = (
    ROOT
    / "runs"
    / "real_data_benchmark"
    / "full_results"
    / "release_corpus_evidence_ledger.json"
)
REPORT = ROOT / "docs" / "reports" / "p16_release_corpus_gate.md"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_release_corpus_gate_keeps_current_frozen_cohort_blocked() -> None:
    registry = _read_json(REGISTRY)
    ledger = _read_json(LEDGER)

    assert registry["registry_id"] == "release-cohort:prototype-frozen-12"
    assert registry["entry_count"] == 12
    assert registry["included_count"] == 12
    assert registry["blocked_count"] == 12
    assert registry["release_ready_count"] == 0

    assert ledger["summary"]["entry_count"] == 12
    assert ledger["summary"]["included_count"] == 12
    assert ledger["summary"]["blocked_count"] == 12
    assert ledger["summary"]["release_ready_count"] == 0
    assert ledger["summary"]["grade_counts"] == {"blocked": 12}


def test_release_corpus_gate_preserves_strongest_row_without_overclaiming() -> None:
    ledger = _read_json(LEDGER)
    rows_by_id = {row["canonical_id"]: row for row in ledger["rows"]}

    p69905 = rows_by_id["protein:P69905"]
    p31749 = rows_by_id["protein:P31749"]
    q9ucm0 = rows_by_id["protein:Q9UCM0"]

    assert p69905["grade"] == "blocked"
    assert p69905["release_ready"] is False
    assert p69905["score"] == 69
    assert p69905["blocker_ids"] == [
        "packet_not_materialized",
        "modalities_incomplete",
    ]

    assert p31749["grade"] == "blocked"
    assert "ligand:assay_linked" in p31749["evidence_lanes"]
    assert "thin_coverage" in p31749["blocker_ids"]

    assert q9ucm0["grade"] == "blocked"
    assert "ppi_gap" in q9ucm0["blocker_ids"]
    assert "ligand_gap" in q9ucm0["blocker_ids"]


def test_release_corpus_gate_report_matches_current_rc_verdict() -> None:
    report = REPORT.read_text(encoding="utf-8")

    assert "Status: `blocked`" in report
    assert "The frozen 12-accession cohort is not RC-capable yet." in report
    assert "0/12 rows are release-ready" in report
    assert "packet materialization is still partial for all 12 rows" in report
    assert "Phase 17 should treat this as an evidence-backed blocked gate" in report
