from __future__ import annotations

from pathlib import Path

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.biogrid_cohort_slice import (
    BioGRIDCohortSlice,
    build_biogrid_cohort_slice,
)
from execution.acquire.biogrid_snapshot import acquire_biogrid_snapshot


def test_build_biogrid_cohort_slice_keeps_download_surface_metadata_without_rows(
    tmp_path: Path,
) -> None:
    manifest = SourceReleaseManifest(
        source_name="BioGRID",
        release_version="5.0.255",
        release_date="2026-03-01",
        retrieval_mode="download",
        source_locator="https://downloads.thebiogrid.org/BIOGRID-ALL-5.0.255.tab3.zip",
        provenance=("release-note",),
    )

    cohort_slice = build_biogrid_cohort_slice(manifest)

    assert isinstance(cohort_slice, BioGRIDCohortSlice)
    assert cohort_slice.status == "surface_only"
    assert cohort_slice.surface_reachable is True
    assert cohort_slice.row_acquired is False
    assert cohort_slice.entry_count == 1
    assert cohort_slice.surface_entry_count == 1
    assert cohort_slice.row_entry_count == 0
    assert cohort_slice.entries[0].entry_kind == "surface"
    assert cohort_slice.entries[0].status == "candidate"
    assert cohort_slice.entries[0].planning_entry.join_status == "deferred"
    assert cohort_slice.entries[0].planning_entry.coverage[0].coverage_state == "partial"
    assert cohort_slice.entries[0].planning_entry.metadata["row_acquired"] is False
    assert cohort_slice.entries[0].planning_entry.metadata["surface_reachable"] is True


def test_build_biogrid_cohort_slice_materializes_rows_from_release_snapshot(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "biogrid.tsv"
    source_file.write_text(
        "#BioGRID Interaction ID\tBioGRID ID A\tBioGRID ID B\tExperimental System\t"
        "Experimental System Type\tPubmed ID\tUniProt A\tUniProt B\n"
        "12345\tBGI:1\tBGI:2\tTwo-hybrid\tphysical\t12345678\tP12345\tQ99999\n"
        "12346\tBGI:3\tBGI:4\tAffinity Capture-MS\tphysical\t22345678\tP54321\tQ88888\n",
        encoding="utf-8",
    )

    manifest = SourceReleaseManifest(
        source_name="BioGRID",
        release_version="5.0.255",
        release_date="2026-03-01",
        retrieval_mode="download",
        local_artifact_refs=(str(source_file),),
        provenance=("release-note",),
    )

    snapshot_result = acquire_biogrid_snapshot(
        manifest,
        acquired_on="2026-03-22T00:00:00+00:00",
    )
    cohort_slice = build_biogrid_cohort_slice(manifest, snapshot_result=snapshot_result)

    assert cohort_slice.status == "materialized"
    assert cohort_slice.surface_reachable is True
    assert cohort_slice.row_acquired is True
    assert cohort_slice.entry_count == 3
    assert cohort_slice.surface_entry_count == 1
    assert cohort_slice.row_entry_count == 2
    assert cohort_slice.selected_row_count == 2
    assert cohort_slice.source_record_count == 2
    surface_entry = cohort_slice.entries[0]
    assert surface_entry.entry_kind == "surface"
    assert surface_entry.planning_entry.metadata["row_acquired"] is True
    assert surface_entry.planning_entry.metadata["selected_row_count"] == 2
    row_entry = cohort_slice.entries[1]
    assert row_entry.entry_kind == "row"
    assert row_entry.row_acquired is True
    assert row_entry.status == "materialized"
    assert row_entry.source_record_id == "12345"
    assert row_entry.interaction_id == "12345"
    assert row_entry.planning_entry.join_status == "partial"
    assert row_entry.planning_entry.coverage[0].coverage_state == "present"
    assert (
        row_entry.planning_entry.source_records[0].source_keys["experimental_system"]
        == "Two-hybrid"
    )
    assert row_entry.planning_entry.source_records[0].source_keys["row_acquired"] == "true"


def test_build_biogrid_cohort_slice_keeps_empty_payload_explicit(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "biogrid-empty.tsv"
    source_file.write_text("", encoding="utf-8")

    manifest = SourceReleaseManifest(
        source_name="BioGRID",
        release_version="5.0.255",
        release_date="2026-03-01",
        retrieval_mode="download",
        local_artifact_refs=(str(source_file),),
        provenance=("release-note",),
    )

    snapshot_result = acquire_biogrid_snapshot(manifest)
    cohort_slice = build_biogrid_cohort_slice(manifest, snapshot_result=snapshot_result)

    assert cohort_slice.status == "empty"
    assert cohort_slice.surface_reachable is True
    assert cohort_slice.row_acquired is False
    assert cohort_slice.entry_count == 1
    assert cohort_slice.row_entry_count == 0
    assert cohort_slice.source_snapshot_status == "unavailable"
    assert cohort_slice.source_snapshot_reason == "biogrid_empty_payload"
    assert cohort_slice.entries[0].status == "candidate"
    assert (
        cohort_slice.entries[0].planning_entry.metadata["snapshot_reason"]
        == "biogrid_empty_payload"
    )
