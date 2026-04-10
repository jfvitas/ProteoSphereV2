from __future__ import annotations

import pytest

from core.provenance.record import (
    ProvenanceRecord,
    ProvenanceSource,
    ReproducibilityMetadata,
)


def test_provenance_record_normalizes_and_serializes_conservative_fields() -> None:
    record = ProvenanceRecord(
        provenance_id=" prov-001 ",
        source=ProvenanceSource(
            source_name=" UniProt ",
            acquisition_mode="api",
            original_identifier=" P12345 ",
            release_version=" 2025_01 ",
            snapshot_id=" 2025-03-01 ",
        ),
        transformation_step=" canonicalize_protein ",
        acquired_at=" 2026-03-22T10:00:00Z ",
        parser_version=" 1.4.0 ",
        transformation_history=(" fetch ", " fetch ", " parse "),
        parent_ids=(" raw-1 ", "raw-1", " raw-2 "),
        child_ids=(" child-1 ", "child-1"),
        run_id=" run-001 ",
        confidence=0.85,
        checksum=" sha256:abc123 ",
        raw_payload_pointer=" s3://bucket/raw.json ",
        reproducibility=ReproducibilityMetadata(
            config_snapshot_id=" cfg-1 ",
            code_version=" git:deadbeef ",
            source_bundle_hash=" sha256:bundle ",
            environment_summary={"python": "3.14", "flags": ("deterministic", "amp")},
            library_versions={"torch": "2.6.0", "numpy": "2.2.0"},
            hardware_summary={"accelerators": ("cpu",), "threads": 8},
            rng_seeds={"python": 7, "torch": 11},
            dataset_version_ids=(" split-v1 ", "split-v1", " features-v2 "),
            split_artifact_id=" split-001 ",
            feature_schema_version=" features@2 ",
            model_schema_version=" model@1 ",
        ),
        metadata={"notes": ("kept", "stable"), "active": True},
    )

    assert record.provenance_id == "prov-001"
    assert record.source.source_name == "UniProt"
    assert record.source.release_version == "2025_01"
    assert record.source.snapshot_id == "2025-03-01"
    assert record.transformation_step == "canonicalize_protein"
    assert record.transformation_history == ("fetch", "parse")
    assert record.parent_ids == ("raw-1", "raw-2")
    assert record.child_ids == ("child-1",)
    assert record.run_id == "run-001"
    assert record.reproducibility.dataset_version_ids == ("split-v1", "features-v2")

    payload = record.to_dict()

    assert payload["source"]["source_name"] == "UniProt"
    assert payload["transformation_history"] == ["fetch", "parse"]
    assert payload["parent_ids"] == ["raw-1", "raw-2"]
    assert payload["reproducibility"]["environment_summary"] == {
        "python": "3.14",
        "flags": ["deterministic", "amp"],
    }
    assert payload["metadata"] == {"notes": ["kept", "stable"], "active": True}


def test_provenance_record_supports_parent_child_lineage_hooks() -> None:
    parent = ProvenanceRecord(
        provenance_id="prov-parent",
        source=ProvenanceSource(
            source_name="RCSB",
            acquisition_mode="bulk_download",
            snapshot_id="2026-03-20",
        ),
        transformation_step="extract_chain",
        run_id="run-002",
    )

    child = parent.spawn_child(
        provenance_id="prov-child",
        transformation_step="derive_features",
        metadata={"feature_set": "contacts"},
    )
    updated_parent = parent.with_child(child.provenance_id)

    assert child.source == parent.source
    assert child.parent_ids == ("prov-parent",)
    assert child.transformation_history == ("extract_chain",)
    assert child.run_id == "run-002"
    assert child.metadata == {"feature_set": "contacts"}
    assert updated_parent.child_ids == ("prov-child",)


def test_provenance_record_round_trips_from_serialized_payload() -> None:
    original = ProvenanceRecord(
        provenance_id="prov-roundtrip",
        source=ProvenanceSource(
            source_name="BindingDB",
            acquisition_mode="manual_curated",
            original_identifier="BDB-123",
            release_version="2026.02",
        ),
        transformation_step="normalize_assay",
        acquired_at="2026-03-22T12:30:00Z",
        parser_version="2.0.1",
        parent_ids=("raw-assay-1",),
        reproducibility=ReproducibilityMetadata(
            code_version="git:cafebabe",
            rng_seeds={"python": 5},
            dataset_version_ids=("dataset-v3",),
        ),
        metadata={"unit_policy": {"target": "nM"}},
    )

    restored = ProvenanceRecord.from_dict(original.to_dict())

    assert restored == original


def test_provenance_record_rejects_non_serializable_metadata_and_bad_confidence() -> None:
    with pytest.raises(TypeError, match="metadata"):
        ProvenanceRecord(
            provenance_id="prov-bad-metadata",
            source=ProvenanceSource(source_name="UniProt", acquisition_mode="api"),
            transformation_step="normalize",
            metadata={"bad": object()},
        )

    with pytest.raises(ValueError, match="confidence"):
        ProvenanceRecord(
            provenance_id="prov-bad-confidence",
            source=ProvenanceSource(source_name="UniProt", acquisition_mode="api"),
            transformation_step="normalize",
            confidence=1.5,
        )
