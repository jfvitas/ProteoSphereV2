from __future__ import annotations

from api.model_studio.reference_library import (
    build_entity_conflict_summary,
    extract_claim_view,
    normalize_source_family_name,
    resolve_materialization_route,
)


def test_extract_claim_view_prefers_best_evidence_and_supports_raw_and_derived() -> None:
    record = {
        "raw_claims": {"name": "raw"},
        "derived_claims": {"name": "derived"},
        "best_evidence_claims": {"name": "best"},
    }

    assert extract_claim_view(record)["name"] == "best"
    assert extract_claim_view(record, "raw")["name"] == "raw"
    assert extract_claim_view(record, "derived_or_scraped")["name"] == "derived"


def test_extract_claim_view_supports_scraped_lists_and_combines_with_derived() -> None:
    scraped_only = {
        "scraped_claims": [
            {"claim_id": "scrape:1", "source_url": "https://example.org/p53"},
        ]
    }
    combined = {
        "derived_claims": [{"claim_id": "derived:1"}],
        "scraped_claims": [{"claim_id": "scrape:1"}],
    }

    assert extract_claim_view(scraped_only, "derived_or_scraped")[0]["claim_id"] == "scrape:1"
    merged = extract_claim_view(combined, "derived_or_scraped")
    assert [row["claim_id"] for row in merged] == ["derived:1", "scrape:1"]


def test_build_entity_conflict_summary_normalizes_missing_fields() -> None:
    summary = build_entity_conflict_summary(
        {
            "conflict_summary": {
                "has_conflicts": True,
                "compared_surfaces": ["raw_claims", "derived_claims"],
                "conflict_fields": ["protein_name"],
            }
        }
    )

    assert summary["has_conflicts"] is True
    assert summary["selected_view"] == "best_evidence"
    assert summary["conflict_fields"] == ["protein_name"]


def test_build_entity_conflict_summary_understands_conflict_detected_alias() -> None:
    summary = build_entity_conflict_summary(
        {
            "conflict_summary": {
                "conflict_detected": True,
                "notes": ["raw and scraped differ"],
            }
        }
    )

    assert summary["has_conflicts"] is True
    assert summary["notes"] == ["raw and scraped differ"]


def test_extract_claim_view_wraps_summary_records_when_claim_surfaces_are_absent() -> None:
    payload = extract_claim_view({"protein_ref": "protein:P53", "entry_name": "P53_HUMAN"})

    assert payload["mode"] == "summary_record"
    assert payload["selected_view"] == "best_evidence"
    assert payload["summary_record"]["protein_ref"] == "protein:P53"


def test_resolve_materialization_route_uses_source_registry_anchor() -> None:
    resolution = resolve_materialization_route(
        {
            "route_id": "materialization:alphafold:A0A009IHW8",
            "pointer": "C:/Users/jfvit/Documents/bio-agent-lab/data_sources/alphafold/swissprot_pdb_v6.tar",
            "selector": "AF-A0A009IHW8-F1-model_v6.pdb.gz",
            "source_name": "alphafold",
            "snapshot_id": "20260323T002625Z",
        },
        {
            "records": [
                {
                    "source_family": "alphafold",
                    "snapshot_id": "20260323T002625Z",
                    "integration_status": "promoted",
                    "authoritative_root": "E:/ProteoSphere/reference_library/incoming_mirrors/alphafold/20260323T002625Z/20260323T002625Z",
                }
            ]
        },
    )

    assert resolution["resolution_mode"] == "source_registry_anchor"
    assert resolution["canonical_root"].startswith("E:/ProteoSphere/reference_library/incoming_mirrors/alphafold")


def test_resolve_materialization_route_prefers_library_asset_pack_pointer() -> None:
    resolution = resolve_materialization_route(
        {
            "route_id": "materialization:alphafold:A0A009IHW8",
            "pointer": "D:/ProteoSphere/reference_library/asset_packs/alphafold/current/alphafold_db/swissprot_pdb_v6.tar",
            "selector": "AF-A0A009IHW8-F1-model_v6.pdb.gz",
            "source_name": "AlphaFold DB",
            "snapshot_id": "current",
        },
        {
            "records": [
                {
                    "source_family": "alphafold",
                    "snapshot_id": "current",
                    "integration_status": "promoted",
                    "authoritative_root": "E:/ProteoSphere/reference_library/incoming_mirrors/alphafold/current/alphafold_db",
                    "asset_pack_root": "D:/ProteoSphere/reference_library/asset_packs/alphafold/current/alphafold_db",
                }
            ]
        },
    )

    assert resolution["resolution_mode"] == "library_owned_asset_pack_pointer"
    assert resolution["canonical_root"] == "D:/ProteoSphere/reference_library/asset_packs/alphafold/current/alphafold_db"
    assert resolution["asset_pack_root"] == "D:/ProteoSphere/reference_library/asset_packs/alphafold/current/alphafold_db"
    assert resolution["direct_pointer_is_external"] is False


def test_normalize_source_family_name_handles_display_names() -> None:
    assert normalize_source_family_name("AlphaFold DB") == "alphafold"
