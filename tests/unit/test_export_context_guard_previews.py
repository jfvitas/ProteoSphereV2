from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.export_bindingdb_dump_inventory_preview import (
    build_bindingdb_dump_inventory_preview,
)
from scripts.export_motif_domain_site_context_preview import (
    build_motif_domain_site_context_preview,
)
from scripts.export_sequence_redundancy_guard_preview import (
    build_sequence_redundancy_guard_preview,
)
from scripts.export_uniref_cluster_context_preview import (
    build_uniref_cluster_context_preview,
)


def test_build_bindingdb_dump_inventory_preview_reads_zip_inventory(tmp_path: Path) -> None:
    zip_path = tmp_path / "bindingdb.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "BDB-mySQL_All_202603.dmp",
            "CREATE TABLE `BindingDB`; CREATE TABLE `MonomerID`;",
        )

    payload = build_bindingdb_dump_inventory_preview(zip_path)

    assert payload["has_mysql_dump"] is True
    assert payload["summary"]["sampled_table_count"] == 2
    assert payload["sampled_create_tables"] == ["BindingDB", "MonomerID"]


def test_build_motif_domain_site_context_preview_summarizes_xrefs_and_features(
    monkeypatch,
) -> None:
    def fake_fetch_json(url: str) -> dict[str, object]:
        assert url.endswith("/P00387.json")
        return {
            "uniProtKBCrossReferences": [
                {
                    "database": "InterPro",
                    "id": "IPR001834",
                    "properties": [{"key": "EntryName", "value": "CBR-like"}],
                },
                {"database": "Pfam", "id": "PF0001", "properties": []},
            ],
            "features": [
                {"type": "Domain"},
                {"type": "Binding site"},
                {"type": "Motif"},
            ],
        }

    monkeypatch.setattr(
        "scripts.export_motif_domain_site_context_preview.fetch_json",
        fake_fetch_json,
    )

    payload = build_motif_domain_site_context_preview(
        {
            "rows": [
                {
                    "accession": "P00387",
                    "modality_readiness": {"motif_domain": "grounded preview-safe"},
                }
            ]
        }
    )

    row = payload["rows"][0]
    assert row["domain_database_counts"]["InterPro"] == 1
    assert row["domain_database_counts"]["Pfam"] == 1
    assert row["feature_type_counts"]["Domain"] == 1
    assert row["site_feature_total"] == 3
    assert row["interpro_entries"][0]["entry_name"] == "CBR-like"


def test_build_uniref_cluster_context_preview_reads_uniref_crossrefs(monkeypatch) -> None:
    def fake_fetch_json(url: str) -> dict[str, object]:
        assert url.endswith("/P00387.json")
        return {
            "uniProtKBCrossReferences": [
                {"database": "UniRef100", "id": "UniRef100_P00387"},
                {"database": "UniRef90", "id": "UniRef90_A0A000"},
                {"database": "UniRef50", "id": "UniRef50_A0A000"},
            ]
        }

    monkeypatch.setattr(
        "scripts.export_uniref_cluster_context_preview.fetch_json",
        fake_fetch_json,
    )

    payload = build_uniref_cluster_context_preview(
        {"rows": [{"accession": "P00387"}]},
        {"gate_status": "blocked_pending_zero_gap"},
    )

    row = payload["rows"][0]
    assert row["uniref100_cluster_id"] == "UniRef100_P00387"
    assert row["representative_member_candidate"] == "P00387"
    assert row["local_materialization_status"] == "pending_tail_completion"


def test_build_sequence_redundancy_guard_preview_flags_shared_clusters() -> None:
    payload = build_sequence_redundancy_guard_preview(
        {
            "rows": [
                {"accession": "P1", "uniref100_cluster_id": "UniRef100_A"},
                {"accession": "P2", "uniref100_cluster_id": "UniRef100_A"},
                {"accession": "P3", "uniref100_cluster_id": "UniRef100_B"},
            ]
        }
    )

    assert payload["summary"]["shared_cluster_accession_count"] == 2
    assert payload["summary"]["shared_cluster_group_count"] == 1
    statuses = {row["accession"]: row["redundancy_guard_status"] for row in payload["rows"]}
    assert statuses["P1"] == "shared_cluster_guard_required"
    assert statuses["P3"] == "crossref_present_no_in_scope_collision"
