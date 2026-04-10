from __future__ import annotations

import pytest

from core.release.cohort_registry import ReleaseCohortEntry, ReleaseCohortRegistry


def test_release_cohort_entry_requires_reason_for_included_and_excluded_states() -> None:
    with pytest.raises(
        ValueError,
        match="included release cohort entries require an inclusion_reason",
    ):
        ReleaseCohortEntry(
            canonical_id="protein:P04637",
            record_type="protein",
            inclusion_status="included",
        )

    with pytest.raises(
        ValueError,
        match="excluded release cohort entries require an exclusion_reason",
    ):
        ReleaseCohortEntry(
            canonical_id="protein:P04637",
            record_type="protein",
            inclusion_status="excluded",
        )


def test_release_cohort_entry_marks_release_ready_only_when_frozen_and_unblocked() -> None:
    entry = ReleaseCohortEntry(
        canonical_id="pair:protein_protein:protein:P31749|protein:Q9Y6K9",
        record_type="protein_protein",
        inclusion_status="included",
        freeze_state="frozen",
        inclusion_reason="real curated pair evidence meets the RC cohort bar",
        blocker_ids=(),
        evidence_lanes=("intact", "structure_bridge"),
        packet_ready=True,
        benchmark_priority=2,
    )

    blocked_entry = ReleaseCohortEntry(
        canonical_id="protein:P04637",
        record_type="protein",
        inclusion_status="included",
        freeze_state="frozen",
        inclusion_reason="anchor accession retained for release evidence accounting",
        blocker_ids=("self_only_intact_slice",),
    )

    assert entry.is_included is True
    assert entry.is_blocked is False
    assert entry.release_ready is True
    assert blocked_entry.is_blocked is True
    assert blocked_entry.release_ready is False
    assert blocked_entry.to_dict()["release_ready"] is False


def test_release_cohort_registry_is_sorted_and_deterministic() -> None:
    registry = ReleaseCohortRegistry(
        registry_id="release-cohort:rc1",
        release_version="0.9.0-rc1",
        freeze_state="draft",
        entries=(
            ReleaseCohortEntry(
                canonical_id="protein:P31749",
                record_type="protein",
                inclusion_status="included",
                freeze_state="draft",
                inclusion_reason="AKT1 retained for pair-positive cohort coverage",
                benchmark_priority=2,
            ),
            ReleaseCohortEntry(
                canonical_id="protein:P04637",
                record_type="protein",
                inclusion_status="excluded",
                exclusion_reason="self-only evidence remains below RC bar",
            ),
        ),
        notes=("release cohort candidate registry",),
    )

    assert [entry.canonical_id for entry in registry.entries] == [
        "protein:P04637",
        "protein:P31749",
    ]
    assert registry.included_canonical_ids == ("protein:P31749",)
    assert len(registry.included_entries) == 1
    assert len(registry.excluded_entries) == 1
    assert len(registry.pending_entries) == 0
    assert registry.require("protein:P31749").benchmark_priority == 2


def test_release_cohort_registry_rejects_duplicates_and_round_trips() -> None:
    entry = ReleaseCohortEntry(
        canonical_id="protein:P69905",
        record_type="protein",
        inclusion_status="included",
        freeze_state="frozen",
        inclusion_reason="hemoglobin anchor retained for release benchmark continuity",
        evidence_lanes=("uniprot", "rcsb_pdbe", "alphafold"),
        source_manifest_ids=("uniprot:2026_03:download:abc123",),
        leakage_key="P69905",
        tags=("anchor", "benchmark"),
        metadata={"cohort_bucket": "anchor", "score": 10},
    )
    registry = ReleaseCohortRegistry(
        registry_id="release-cohort:ga1",
        release_version="1.0.0",
        freeze_state="frozen",
        entries=(entry,),
    )

    payload = registry.to_dict()
    rebuilt = ReleaseCohortRegistry.from_dict(payload)

    assert rebuilt.registry_id == "release-cohort:ga1"
    assert rebuilt.freeze_state == "frozen"
    assert rebuilt.require("protein:P69905").release_ready is True
    assert rebuilt.require("protein:P69905").metadata["cohort_bucket"] == "anchor"

    with pytest.raises(ValueError, match="duplicate release cohort entry"):
        ReleaseCohortRegistry(
            registry_id="release-cohort:bad",
            release_version="1.0.0",
            entries=(entry, entry),
        )
