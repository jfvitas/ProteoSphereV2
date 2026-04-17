from __future__ import annotations

from api.model_studio.reference_library import build_public_warning_banner
from core.storage.reference_warehouse import (
    ReferenceWarehouseEntityFamily,
    ReferenceWarehouseManifest,
    ReferenceWarehouseSourceDescriptor,
    ReferenceWarehouseValidation,
    validate_reference_warehouse_manifest_payload,
)


def test_reference_warehouse_manifest_round_trips_and_normalizes_aliases() -> None:
    manifest = ReferenceWarehouseManifest(
        warehouse_id="warehouse:test",
        warehouse_root="E:/ProteoSphere/reference_library",
        catalog_path="E:/ProteoSphere/reference_library/catalog/reference_library.duckdb",
        catalog_engine="duckdb",
        catalog_status="ready",
        source_descriptors=(
            ReferenceWarehouseSourceDescriptor(
                source_key="uniprot",
                source_name="UniProt",
                category="sequence",
                snapshot_id="uniprot-2026-04-10",
                retrieval_mode="api",
                license_scope="metadata_only",
                redistributable=True,
                public_export_allowed=True,
                location_verified=True,
                canonical_root="E:/ProteoSphere/reference_library/incoming_mirrors/uniprot/current",
                duplicate_roots=("C:/CSTEMP/ProteoSphereV2_overflow/protein_data_scope_seed/uniprot",),
                consolidation_status="verified",
                scope_tier="authoritative",
            ),
        ),
        entity_families=(
            ReferenceWarehouseEntityFamily(
                family_name="proteins",
                storage_format="jsonl",
                row_count=12,
                partition_glob="E:/ProteoSphere/reference_library/partitions/proteins/*.jsonl",
                public_export_allowed=True,
                truth_surface_fields=(
                    "raw_claims",
                    "derived_claims",
                    "scraped_claims",
                    "best_evidence_claims",
                    "conflict_summary",
                ),
                default_view="best_evidence",
            ),
        ),
        validation=ReferenceWarehouseValidation(
            state="warn",
            checks={"family_count": 1, "source_count": 1},
            warnings=("duckdb unavailable",),
        ),
        export_policy={"warning_banner": "metadata only"},
    )

    payload = manifest.to_dict()
    restored = validate_reference_warehouse_manifest_payload(payload)

    assert restored.source_descriptors[0].license_scope == "public_metadata"
    assert restored.source_descriptors[0].location_verified is True
    assert restored.source_descriptors[0].duplicate_roots
    assert restored.validation.state == "warning"
    assert restored.family_count == 1
    assert restored.source_count == 1
    assert restored.entity_families[0].default_view == "best_evidence"


def test_build_public_warning_banner_prefers_export_policy_text() -> None:
    banner = build_public_warning_banner(
        {
            "warehouse_id": "warehouse:test",
            "bundle_version": "2026.04.preview",
            "export_policy": {
                "warning_banner": "Metadata only. Raw corpora remain local-first."
            },
        }
    )

    assert "warehouse:test" in banner
    assert "2026.04.preview" in banner
    assert "Metadata only. Raw corpora remain local-first." in banner
