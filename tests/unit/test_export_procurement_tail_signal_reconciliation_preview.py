from __future__ import annotations

from scripts.export_procurement_tail_signal_reconciliation_preview import (
    build_procurement_tail_signal_reconciliation_preview,
)


def test_tail_signal_reconciliation_accepts_aligned_authoritative_tail_with_legacy_stale_state(
) -> None:
    payload = build_procurement_tail_signal_reconciliation_preview(
        board={
            "status": "attention",
            "summary": {"active_observed_download_count": 2},
            "procurement_supervisor": {
                "active_observed_download_count": 2,
                "observed_active_source": "remaining_transfer_status",
                "active_observed_downloads": [
                    {"task_id": "uniprot", "filename": "uniref100.xml.gz"},
                    {"task_id": "string", "filename": "protein.links.full.v12.0.txt.gz"},
                ],
            },
        },
        remaining_transfer_status={
            "status": "planning",
            "summary": {"active_file_count": 2, "remaining_source_count": 2},
        },
        process_diagnostics={
            "summary": {
                "authoritative_tail_file_count": 2,
                "raw_process_table_active_count": 10,
                "raw_process_table_duplicate_count": 8,
            },
            "authoritative_tail_files": [
                {"source_id": "uniprot", "filename": "uniref100.xml.gz"},
                {"source_id": "string", "filename": "protein.links.full.v12.0.txt.gz"},
            ],
        },
        supervisor_state={
            "status": "stale",
            "pending": ["chembl_rnacentral_bulk", "interpro_complexportal_resolver_small"],
            "observed_active": [{"pid": 1}],
        },
    )

    assert (
        payload["summary"]["reconciliation_state"]
        == "authoritative_tail_aligned_with_legacy_stale_signal"
    )
    assert payload["summary"]["authoritative_counts_aligned"] is True
    assert payload["summary"]["authoritative_tail_file_count"] == 2
    assert payload["summary"]["raw_process_table_active_count"] == 10


def test_tail_signal_reconciliation_flags_drift_when_authoritative_counts_disagree() -> None:
    payload = build_procurement_tail_signal_reconciliation_preview(
        board={
            "status": "attention",
            "summary": {"active_observed_download_count": 2},
            "procurement_supervisor": {
                "active_observed_download_count": 2,
                "active_observed_downloads": [
                    {"task_id": "uniprot", "filename": "uniref100.xml.gz"},
                    {"task_id": "string", "filename": "protein.links.full.v12.0.txt.gz"},
                ],
            },
        },
        remaining_transfer_status={
            "status": "planning",
            "summary": {"active_file_count": 1, "remaining_source_count": 2},
        },
        process_diagnostics={
            "summary": {
                "authoritative_tail_file_count": 2,
                "raw_process_table_active_count": 3,
                "raw_process_table_duplicate_count": 1,
            },
            "authoritative_tail_files": [
                {"source_id": "uniprot", "filename": "uniref100.xml.gz"},
                {"source_id": "string", "filename": "protein.links.full.v12.0.txt.gz"},
            ],
        },
        supervisor_state={"status": "stale", "pending": []},
    )

    assert payload["summary"]["reconciliation_state"] == "tail_signal_drift_requires_review"
    assert payload["summary"]["authoritative_counts_aligned"] is False
    assert payload["summary"]["remaining_transfer_active_file_count"] == 1
