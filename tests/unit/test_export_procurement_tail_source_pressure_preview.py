from __future__ import annotations

from scripts.export_procurement_tail_source_pressure_preview import (
    build_procurement_tail_source_pressure_preview,
)


def test_tail_source_pressure_preview_reports_dominant_source() -> None:
    payload = build_procurement_tail_source_pressure_preview(
        {
            "rows": [
                {
                    "source_id": "uniprot",
                    "source_name": "UniProt / UniRef / ID Mapping",
                    "after_bytes": 90,
                    "delta_bytes": 9,
                },
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "after_bytes": 10,
                    "delta_bytes": 1,
                },
            ]
        }
    )

    assert payload["summary"]["pressure_state"] == "source_dominant"
    assert payload["summary"]["dominant_source_id"] == "uniprot"
    assert payload["summary"]["dominant_source_byte_share"] == 0.9


def test_tail_source_pressure_preview_handles_empty_rows() -> None:
    payload = build_procurement_tail_source_pressure_preview({})

    assert payload["summary"]["pressure_state"] == "no_tail_sources"
    assert payload["summary"]["source_count"] == 0
