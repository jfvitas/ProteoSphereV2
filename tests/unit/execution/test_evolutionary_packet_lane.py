from __future__ import annotations

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.evolutionary_snapshot import (
    EvolutionarySnapshot,
    EvolutionarySnapshotProvenance,
    EvolutionarySnapshotRecord,
    EvolutionarySnapshotResult,
    build_evolutionary_snapshot_manifest,
)
from execution.materialization.evolutionary_packet_lane import (
    build_evolutionary_packet_lane,
)


def _evolutionary_snapshot_result(*, status: str = "ok") -> EvolutionarySnapshotResult:
    manifest = build_evolutionary_snapshot_manifest(
        source_release=SourceReleaseManifest(
            source_name="Evolutionary / MSA corpus",
            release_version="2026_03",
            retrieval_mode="download",
            source_locator="https://example.org/evolutionary/corpus.json",
            provenance=("pinned-evolutionary-corpus",),
        ),
        corpus_snapshot_id="corpus-2026_03",
        aligner_version="mmseqs2-15",
        source_layers=("UniProt/UniRef", "InterPro", "local MMseqs2"),
        parameters={"evalue": 1e-3, "coverage": 0.8},
    )
    provenance = EvolutionarySnapshotProvenance(
        corpus_snapshot_id=manifest.corpus_snapshot_id,
        manifest_id=manifest.manifest_id,
        release_version=manifest.source_release.release_version or "",
        release_date=manifest.source_release.release_date or "",
        retrieval_mode=manifest.source_release.retrieval_mode,
        source_locator=manifest.source_release.source_locator or "",
        source_layers=manifest.source_layers,
        parameters=manifest.parameters,
        raw_payload_sha256="sha256:abc123",
        byte_count=512,
        record_count=2,
        acquired_on="2026-03-22T12:00:00Z",
        availability="available" if status == "ok" else status,
        blocker_reason="" if status == "ok" else "evolutionary snapshot unavailable",
        manifest=manifest.to_dict(),
    )
    snapshot = None
    if status == "ok":
        snapshot = EvolutionarySnapshot(
            source_release=manifest.source_release.to_dict(),
            provenance=provenance,
            records=(
                EvolutionarySnapshotRecord(
                    accession="P69905",
                    sequence_version="1",
                    sequence_hash="sha256:alpha",
                    sequence_length=142,
                    taxon_id=9606,
                    uniref_cluster_ids=("UniRef90_P69905",),
                    orthogroup_ids=("OG_HUMAN_GLOBIN",),
                    alignment_depth=64,
                    alignment_coverage=0.98,
                    neff=12.4,
                    gap_fraction=0.05,
                    quality_flags=("pinned", "live-derived"),
                    source_refs=("uniprotkb:P69905",),
                    lazy_materialization_refs=("msas/P69905.a3m",),
                    metadata={
                        "source_record_index": 0,
                        "corpus_snapshot_id": "corpus-2026_03",
                        "aligner_version": "mmseqs2-15",
                        "source_layers": ("UniProt/UniRef", "InterPro", "local MMseqs2"),
                    },
                ),
                EvolutionarySnapshotRecord(
                    accession="P68871",
                    sequence_version="3",
                    sequence_hash="sha256:beta",
                    sequence_length=147,
                    taxon_id=9606,
                    uniref_cluster_ids=("UniRef90_P68871",),
                    orthogroup_ids=("OG_HUMAN_GLOBIN",),
                    alignment_depth=48,
                    alignment_coverage=0.92,
                    neff=11.1,
                    gap_fraction=0.07,
                    quality_flags=("paired-lane", "live-derived"),
                    source_refs=("uniprotkb:P68871",),
                    lazy_materialization_refs=("msas/P68871.a3m",),
                    metadata={
                        "source_record_index": 1,
                        "corpus_snapshot_id": "corpus-2026_03",
                        "aligner_version": "mmseqs2-15",
                        "source_layers": ("UniProt/UniRef", "InterPro", "local MMseqs2"),
                    },
                ),
            ),
        )
    return EvolutionarySnapshotResult(
        status=status,
        reason=(
            "evolutionary_snapshot_acquired"
            if status == "ok"
            else "evolutionary_snapshot_payload_unavailable"
        ),
        manifest=manifest,
        provenance=provenance,
        snapshot=snapshot,
        raw_payload='{"records": []}',
    )


def test_build_evolutionary_packet_lane_materializes_pinned_context_and_keeps_missing_explicit(
) -> None:
    result = build_evolutionary_packet_lane(
        ["P69905", "P68871", "Q2TAC2", "P69905"],
        snapshot_result=_evolutionary_snapshot_result(),
    )

    assert result.cohort_accessions == ("P69905", "P68871", "Q2TAC2")
    assert result.positive_accessions == ("P69905", "P68871")
    assert result.unresolved_accessions == ("Q2TAC2",)
    assert result.blocked_accessions == ()
    assert result.snapshot_status == "ok"
    assert result.snapshot_record_count == 2
    assert result.source_snapshot_id == "corpus-2026_03"
    assert result.aligner_version == "mmseqs2-15"
    assert result.source_layers == ("UniProt/UniRef", "InterPro", "local MMseqs2")

    assert tuple(lane.lane_state for lane in result.packet_lanes) == (
        "positive_hit",
        "positive_hit",
        "unresolved",
    )
    assert result.packet_lanes[0].sequence_hash == "sha256:alpha"
    assert result.packet_lanes[0].alignment_depth == 64
    assert result.packet_lanes[0].lazy_materialization_refs == ("msas/P69905.a3m",)
    assert result.packet_lanes[0].notes == ("pinned MSA-related context available",)
    assert result.packet_lanes[1].sequence_hash == "sha256:beta"
    assert result.packet_lanes[2].lane_depth == 0
    assert result.packet_lanes[2].notes == (
        "no evolutionary record materialized for this accession",
    )

    assert result.summary == {
        "cohort_accession_count": 3,
        "lane_count": 3,
        "positive_count": 2,
        "unresolved_count": 1,
        "blocked_count": 0,
        "materialized_count": 2,
        "snapshot_record_count": 2,
    }
    assert len(result.to_dict()["packet_lanes"]) == 3


def test_build_evolutionary_packet_lane_marks_blocked_snapshot_without_inference() -> None:
    result = build_evolutionary_packet_lane(
        ["P69905", "P68871"],
        snapshot_result=_evolutionary_snapshot_result(status="blocked"),
    )

    assert result.snapshot_status == "blocked"
    assert result.positive_accessions == ()
    assert result.unresolved_accessions == ()
    assert result.blocked_accessions == ("P69905", "P68871")
    assert tuple(lane.lane_state for lane in result.packet_lanes) == ("blocked", "blocked")
    assert result.packet_lanes[0].blocker_reason == "evolutionary_snapshot_payload_unavailable"
    assert result.packet_lanes[1].lane_depth == 0
    assert result.summary["blocked_count"] == 2
    assert result.summary["materialized_count"] == 0
