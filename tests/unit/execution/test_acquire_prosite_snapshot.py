from __future__ import annotations

from pathlib import Path

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.prosite_snapshot import (
    PrositeSnapshot,
    PrositeSnapshotContract,
    PrositeSnapshotResult,
    acquire_prosite_snapshot,
)


def test_acquire_prosite_snapshot_parses_release_stamped_motif_records(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "prosite.dat"
    source_file.write_text(
        "CC   *************************************************************************\n"
        "CC   PROSITE motifs file\n"
        "CC   Release 2026_01 of 28-Jan-2026.\n"
        "CC   *************************************************************************\n"
        "//\n"
        "ID   EXAMPLE_MOTIF; PATTERN.\n"
        "AC   PS99999;\n"
        "DT   01-JAN-2026 CREATED; 02-JAN-2026 DATA UPDATE; 03-JAN-2026 INFO UPDATE.\n"
        "DE   Example motif.\n"
        "PA   A-x(2)-B.\n"
        "CC   /SITE=1,example;\n"
        "PR   PRU99999;\n"
        "DO   PDOC99999;\n"
        "//\n"
        "ID   SECOND_MOTIF; PATTERN.\n"
        "AC   PS99998;\n"
        "DT   04-JAN-2026 CREATED; 05-JAN-2026 DATA UPDATE; 06-JAN-2026 INFO UPDATE.\n"
        "DE   Second motif.\n"
        "PA   C-x-D.\n"
        "DO   PDOC99998;\n"
        "//\n",
        encoding="utf-8",
    )

    manifest = SourceReleaseManifest(
        source_name="PROSITE",
        release_version="2026_01",
        release_date="2026-01-28",
        retrieval_mode="download",
        local_artifact_refs=(str(source_file),),
        provenance=("seed export",),
        reproducibility_metadata=("sha256:seed",),
    )

    result = acquire_prosite_snapshot(manifest, acquired_on="2026-03-30T00:00:00+00:00")

    assert isinstance(result, PrositeSnapshotResult)
    assert result.status == "ok"
    assert result.succeeded is True
    assert isinstance(result.contract, PrositeSnapshotContract)
    assert isinstance(result.snapshot, PrositeSnapshot)
    assert result.contract.release_version == "2026_01"
    assert result.snapshot.release_date == "2026-01-28"
    assert result.snapshot.record_count == 2
    assert result.snapshot.records[0].accession == "PS99999"
    assert result.snapshot.records[0].created_date == "01-JAN-2026"
    assert result.snapshot.records[0].profile_accession == "PRU99999"
    assert result.snapshot.records[1].doc_accession == "PDOC99998"
    assert result.provenance["parser_version"] == "prosite-flatfile-v1"
    assert result.provenance["content_source"].startswith("local_artifact:")

    payload = result.to_dict()
    assert payload["snapshot"]["record_count"] == 2
    assert payload["snapshot"]["records"][0]["identifier"] == "EXAMPLE_MOTIF"


def test_acquire_prosite_snapshot_blocks_when_no_artifact_is_available() -> None:
    manifest = SourceReleaseManifest(
        source_name="PROSITE",
        release_version="2026_01",
        retrieval_mode="download",
        provenance=("missing export",),
    )

    result = acquire_prosite_snapshot(manifest)

    assert result.status == "blocked"
    assert result.contract is not None
    assert result.snapshot is None
    assert result.blocker_reason == "prosite_manifest_needs_source_locator_or_local_artifact_refs"
    assert result.provenance["availability"] == "blocked"
