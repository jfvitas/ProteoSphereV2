from __future__ import annotations

from scripts.export_procurement_tail_completion_margin_preview import (
    GIB,
    build_procurement_tail_completion_margin_preview,
)


def test_completion_margin_preview_reports_sufficient_margin() -> None:
    payload = build_procurement_tail_completion_margin_preview(
        {
            "rows": [
                {
                    "source_id": "uniprot",
                    "filename": "uniref100.xml.gz",
                    "total_bytes_from_log": 1000,
                    "current_bytes_from_log": 700,
                    "match_state": "progress_line_parsed",
                },
                {
                    "source_id": "string",
                    "filename": "protein.links.full.v12.0.txt.gz",
                    "total_bytes_from_log": 2000,
                    "current_bytes_from_log": 1500,
                    "match_state": "progress_line_parsed",
                },
            ]
        },
        {
            "rows": [
                {"filename": "uniref100.xml.gz", "after_bytes": 700, "bytes_per_second": 10.0},
                {
                    "filename": "protein.links.full.v12.0.txt.gz",
                    "after_bytes": 1500,
                    "bytes_per_second": 20.0,
                },
            ]
        },
        {"summary": {"free_bytes": 50 * GIB}},
    )

    assert payload["summary"]["completion_state"] == "sufficient_margin_for_tail_completion"
    assert payload["summary"]["total_remaining_bytes"] == 800
    assert payload["rows"][0]["estimated_hours_to_completion_at_recent_rate"] is not None


def test_completion_margin_preview_reports_insufficient_margin() -> None:
    payload = build_procurement_tail_completion_margin_preview(
        {
            "rows": [
                {
                    "source_id": "string",
                    "filename": "protein.links.full.v12.0.txt.gz",
                    "total_bytes_from_log": 5000,
                    "current_bytes_from_log": 1000,
                    "match_state": "progress_line_parsed",
                }
            ]
        },
        {"rows": [{"filename": "protein.links.full.v12.0.txt.gz", "after_bytes": 1000}]},
        {"summary": {"free_bytes": 1000}},
    )

    assert payload["summary"]["completion_state"] == "insufficient_margin_for_tail_completion"
    assert payload["summary"]["projected_free_after_completion_bytes"] < 0
