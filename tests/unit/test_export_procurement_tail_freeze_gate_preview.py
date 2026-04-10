from __future__ import annotations

from scripts.export_procurement_tail_freeze_gate_preview import (
    build_procurement_tail_freeze_gate_preview,
)


def test_build_procurement_tail_freeze_gate_preview_blocks_until_zero_gap() -> None:
    payload = build_procurement_tail_freeze_gate_preview(
        {
            "summary": {"file_coverage_percent": 98.1},
            "sources": [
                {"source_id": "string", "status": "partial"},
                {"source_id": "uniprot", "status": "partial"},
            ],
        },
        {
            "summary": {"total_gap_files": 3},
            "gap_files": [
                {
                    "source_id": "string",
                    "filename": "protein.links.full.v12.0.txt.gz",
                    "gap_kind": "partial",
                },
                {
                    "source_id": "uniprot",
                    "filename": "uniref100.xml.gz",
                    "gap_kind": "partial",
                },
            ],
        },
        {"summary": {"active_file_count": 3, "not_yet_started_file_count": 0}},
    )

    assert payload["gate_status"] == "blocked_pending_zero_gap"
    assert payload["remaining_gap_file_count"] == 3
    assert payload["freeze_conditions"]["remaining_gap_files_zero"] is False
    assert payload["freeze_conditions"]["not_yet_started_file_count_zero"] is True
    assert payload["freeze_conditions"]["string_complete"] is False
    assert payload["freeze_conditions"]["uniprot_complete"] is False


def test_build_procurement_tail_freeze_gate_preview_only_unlocks_on_full_completion() -> None:
    payload = build_procurement_tail_freeze_gate_preview(
        {
            "summary": {"file_coverage_percent": 100.0},
            "sources": [
                {"source_id": "string", "status": "complete"},
                {"source_id": "uniprot", "status": "complete"},
            ],
        },
        {"summary": {"total_gap_files": 0}, "gap_files": []},
        {"summary": {"active_file_count": 0, "not_yet_started_file_count": 0}},
    )

    assert payload["gate_status"] == "ready_to_freeze_complete_mirror"
    assert payload["remaining_gap_file_count"] == 0
    assert payload["freeze_conditions"]["remaining_gap_files_zero"] is True
    assert payload["freeze_conditions"]["not_yet_started_file_count_zero"] is True
    assert payload["freeze_conditions"]["string_complete"] is True
    assert payload["freeze_conditions"]["uniprot_complete"] is True
