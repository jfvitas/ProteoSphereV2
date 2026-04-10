from __future__ import annotations

from pathlib import Path

from scripts.export_download_location_audit_preview import (
    build_download_location_audit_preview,
)
from scripts.export_procurement_source_completion_preview import (
    build_procurement_source_completion_preview,
)


def test_procurement_source_completion_preview_separates_string_and_uniprot(
    tmp_path: Path,
) -> None:
    manifest = {
        "sources": [
            {
                "id": "string",
                "name": "STRING v12",
                "category": "interaction_networks",
                "top_level_files": [
                    {
                        "filename": "protein.links.full.v12.0.txt.gz",
                        "url": "https://stringdb-downloads.org/download/protein.links.full.v12.0.txt.gz",
                    }
                ],
            },
            {
                "id": "uniprot",
                "name": "UniProt / UniRef / ID Mapping",
                "category": "sequence_reference_backbone",
                "top_level_files": [
                    {
                        "filename": "uniref100.xml.gz",
                        "url": "https://ftp.uniprot.org/pub/databases/uniprot/uniref/uniref100/uniref100.xml.gz",
                    }
                ],
            },
        ]
    }
    primary_root = tmp_path / "primary"
    overflow_root = tmp_path / "overflow"
    failed_root = tmp_path / "failed"

    (primary_root / "string").mkdir(parents=True)
    (primary_root / "string" / "protein.links.full.v12.0.txt.gz").write_text(
        "complete",
        encoding="utf-8",
    )

    (overflow_root / "uniprot").mkdir(parents=True)
    (overflow_root / "uniprot" / "uniref100.xml.gz.part").write_text(
        "partial",
        encoding="utf-8",
    )

    audit = build_download_location_audit_preview(
        manifest,
        primary_seed_root=primary_root,
        overflow_seed_root=overflow_root,
        failed_snapshot_root=failed_root,
    )
    payload = build_procurement_source_completion_preview(audit)

    assert payload["string_completion_status"] == "complete"
    assert payload["string_completion_ready"] is True
    assert payload["uniprot_completion_status"] == "active"
    assert payload["uniprot_completion_ready"] is False

    rows_by_source = {row["source_id"]: row for row in payload["source_completion"]}
    assert rows_by_source["string"]["primary_live_path"].endswith(
        "/primary/string/protein.links.full.v12.0.txt.gz"
    )
    assert rows_by_source["uniprot"]["primary_live_path"].endswith(
        "/overflow/uniprot/uniref100.xml.gz.part"
    )
    assert rows_by_source["string"]["completion_status"] == "complete"
    assert rows_by_source["uniprot"]["completion_status"] == "active"


def test_procurement_source_completion_preview_marks_completed_overflow_authority(
    tmp_path: Path,
) -> None:
    manifest = {
        "sources": [
            {
                "id": "uniprot",
                "name": "UniProt / UniRef / ID Mapping",
                "category": "sequence_reference_backbone",
                "top_level_files": [
                    {
                        "filename": "uniref100.xml.gz",
                        "url": "https://ftp.uniprot.org/pub/databases/uniprot/uniref/uniref100/uniref100.xml.gz",
                    }
                ],
            }
        ]
    }
    primary_root = tmp_path / "primary"
    overflow_root = tmp_path / "overflow"
    failed_root = tmp_path / "failed"

    (overflow_root / "uniprot").mkdir(parents=True)
    (overflow_root / "uniprot" / "uniref100.xml.gz").write_text("complete", encoding="utf-8")

    audit = build_download_location_audit_preview(
        manifest,
        primary_seed_root=primary_root,
        overflow_seed_root=overflow_root,
        failed_snapshot_root=failed_root,
    )
    payload = build_procurement_source_completion_preview(audit)

    uniprot = payload["source_completion_index"]["uniprot"]
    assert payload["uniprot_completion_status"] == "complete"
    assert payload["uniprot_completion_ready"] is True
    assert uniprot["completed_off_primary_root"] is True
    assert uniprot["authority_note"] == "completed_off_primary_root_intentionally_authoritative"
