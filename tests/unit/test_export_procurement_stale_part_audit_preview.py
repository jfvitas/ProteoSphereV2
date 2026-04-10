from __future__ import annotations

from scripts.export_procurement_stale_part_audit_preview import (
    build_procurement_stale_part_audit_preview,
)


def test_build_procurement_stale_part_audit_preview_classifies_stale_and_live_rows(
    monkeypatch,
) -> None:
    string_final = (
        "D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed/string/"
        "protein.links.full.v12.0.txt.gz"
    )
    string_part = (
        "D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed/string/"
        "protein.links.detailed.v12.0.txt.gz.part"
    )
    uniprot_part = (
        "C:/CSTEMP/ProteoSphereV2_overflow/protein_data_scope_seed/uniprot/"
        "uniref100.xml.gz.part"
    )
    download_location_audit_preview = {
        "rows": [
            {
                "source_id": "string",
                "filename": "protein.links.detailed.v12.0.txt.gz",
                "final_locations": [
                    {
                        "path": string_final,
                    }
                ],
                "in_process_locations": [
                    {
                        "path": string_part,
                    }
                ],
            },
            {
                "source_id": "uniprot",
                "filename": "uniref100.xml.gz",
                "final_locations": [],
                "in_process_locations": [
                    {
                        "path": uniprot_part,
                    }
                ],
            },
        ]
    }

    sizes = {
        string_part.replace("/", "\\"): iter([1024, 1024]),
        uniprot_part.replace("/", "\\"): iter([2048, 4096]),
    }
    monkeypatch.setattr(
        "scripts.export_procurement_stale_part_audit_preview._path_size",
        lambda path_text: next(sizes[path_text]),
    )

    payload = build_procurement_stale_part_audit_preview(
        download_location_audit_preview,
        sample_seconds=0,
    )

    rows_by_filename = {row["filename"]: row for row in payload["rows"]}
    assert rows_by_filename["protein.links.detailed.v12.0.txt.gz"]["classification"] == (
        "stale_residue_after_final"
    )
    assert rows_by_filename["uniref100.xml.gz"]["classification"] == "live_transfer"
    assert payload["summary"]["stale_residue_count"] == 1
    assert payload["summary"]["live_transfer_count"] == 1
