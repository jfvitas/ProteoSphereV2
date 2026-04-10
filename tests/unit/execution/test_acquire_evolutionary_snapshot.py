from __future__ import annotations

import json

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.evolutionary_snapshot import (
    acquire_evolutionary_snapshot,
    build_evolutionary_snapshot_manifest,
)


def test_manifest_normalizes_corpus_metadata() -> None:
    manifest = build_evolutionary_snapshot_manifest(
        source_release=SourceReleaseManifest(
            source_name="Evolutionary / MSA corpus",
            release_version="2026_03",
            retrieval_mode="download",
            source_locator="https://example.org/evolutionary/corpus.json",
        ),
        corpus_snapshot_id=" corpus-2026_03 ",
        aligner_version=" mmseqs2-15 ",
        source_layers=("UniProt/UniRef", "InterPro", "UniProt/UniRef"),
        parameters={"evalue": 1e-3, "max_depth": 512},
    )

    assert manifest.manifest_id == (
        f"{manifest.source_release.manifest_id}:corpus-2026_03:mmseqs2-15"
    )
    assert manifest.source_layers == ("UniProt/UniRef", "InterPro")
    assert manifest.parameters["evalue"] == 0.001
    assert manifest.parameters["max_depth"] == 512


def test_acquire_evolutionary_snapshot_reads_local_corpus_and_preserves_provenance(
    tmp_path,
) -> None:
    corpus_path = tmp_path / "evolutionary_corpus.json"
    corpus_payload = {
        "records": [
            {
                "accession": "P12345",
                "sequence_version": "2",
                "sequence_hash": "sha256:abc123",
                "sequence_length": 342,
                "taxon_id": 9606,
                "uniref_cluster_ids": ["UniRef90_P12345"],
                "orthogroup_ids": ["OG0001"],
                "alignment_depth": 128,
                "neff": 12.5,
                "gap_fraction": 0.08,
                "quality_flags": ["pinned", "family-aware"],
                "source_refs": ["raw/uniprot/p12345.fasta"],
                "lazy_materialization_refs": ["cache/msas/P12345.a3m"],
            },
            {
                "uniprot_accession": "Q99999",
                "sequence_version": "1",
                "sequence_hash": "sha256:def456",
                "taxon_id": 9606,
                "uniref_clusters": "UniRef50_Q99999",
                "alignment_coverage": 0.92,
                "flags": "local msa",
            },
        ]
    }
    corpus_path.write_text(json.dumps(corpus_payload), encoding="utf-8")

    manifest = build_evolutionary_snapshot_manifest(
        source_release=SourceReleaseManifest(
            source_name="Evolutionary / MSA corpus",
            release_version="2026_03",
            retrieval_mode="download",
            local_artifact_refs=(str(corpus_path),),
            provenance=("pinned-corpus",),
            reproducibility_metadata=("aligner=mmseqs2-15", "parameters=evalue:1e-3"),
        ),
        corpus_snapshot_id="corpus-2026_03",
        aligner_version="mmseqs2-15",
        source_layers=("UniProt/UniRef", "InterPro", "local MMseqs2"),
        parameters={"evalue": 1e-3, "coverage": 0.8},
    )

    result = acquire_evolutionary_snapshot(manifest, acquired_on="2026-03-22T12:00:00Z")

    assert result.status == "ok"
    assert result.succeeded is True
    assert result.manifest.manifest_id == (
        f"{result.manifest.source_release.manifest_id}:corpus-2026_03:mmseqs2-15"
    )
    assert result.provenance.record_count == 2
    assert result.provenance.raw_payload_sha256.startswith("sha256:")
    assert result.snapshot is not None
    assert result.snapshot.records[0].accession == "P12345"
    assert result.snapshot.records[0].uniref_cluster_ids == ("UniRef90_P12345",)
    assert result.snapshot.records[0].lazy_materialization_refs == ("cache/msas/P12345.a3m",)
    assert result.snapshot.records[1].accession == "Q99999"
    assert result.snapshot.records[1].uniref_cluster_ids == ("UniRef50_Q99999",)
    assert result.snapshot.records[0].metadata["source_record_index"] == 0
    assert result.snapshot.records[1].metadata["source_layers"] == (
        "UniProt/UniRef",
        "InterPro",
        "local MMseqs2",
    )


def test_acquire_evolutionary_snapshot_accepts_multi_record_corpus_and_remains_conservative(
    tmp_path,
) -> None:
    corpus_path = tmp_path / "evolutionary_corpus_multi.json"
    corpus_payload = {
        "records": [
            {
                "accession": "P69905",
                "sequence_version": "1",
                "sequence_hash": "sha256:alpha",
                "sequence_length": 142,
                "taxon_id": 9606,
                "uniref_cluster_ids": ["UniRef90_P69905"],
                "orthogroup_ids": ["OG_HUMAN_GLOBIN"],
                "alignment_depth": 64,
                "quality_flags": ["anchor", "live-derived"],
                "source_refs": ["uniprotkb:P69905"],
                "lazy_materialization_refs": ["msas/P69905.a3m"],
            },
            {
                "accession": "P68871",
                "sequence_version": "3",
                "sequence_hash": "sha256:beta",
                "sequence_length": 147,
                "taxon_id": 9606,
                "uniref_cluster_ids": ["UniRef90_P68871"],
                "orthogroup_ids": ["OG_HUMAN_GLOBIN"],
                "alignment_depth": 48,
                "alignment_coverage": 0.91,
                "quality_flags": ["paired-lane", "live-derived"],
                "source_refs": ["uniprotkb:P68871"],
                "lazy_materialization_refs": ["msas/P68871.a3m"],
            },
        ]
    }
    corpus_path.write_text(json.dumps(corpus_payload), encoding="utf-8")

    manifest = build_evolutionary_snapshot_manifest(
        source_release=SourceReleaseManifest(
            source_name="Evolutionary / MSA corpus",
            release_version="2026_03",
            retrieval_mode="download",
            local_artifact_refs=(str(corpus_path),),
            provenance=("multi-record-smoke",),
        ),
        corpus_snapshot_id="corpus-2026_03",
        aligner_version="mmseqs2-15",
        source_layers=("UniProt/UniRef", "InterPro", "live smoke"),
        parameters={"evalue": 1e-3, "coverage": 0.8},
    )

    result = acquire_evolutionary_snapshot(manifest, acquired_on="2026-03-22T13:00:00Z")

    assert result.status == "ok"
    assert result.reason == "evolutionary_snapshot_acquired"
    assert result.provenance.record_count == 2
    assert result.snapshot is not None
    assert tuple(record.accession for record in result.snapshot.records) == (
        "P69905",
        "P68871",
    )
    assert result.snapshot.records[0].quality_flags == ("anchor", "live-derived")
    assert result.snapshot.records[1].quality_flags == ("paired-lane", "live-derived")
    assert result.snapshot.records[0].lazy_materialization_refs == ("msas/P69905.a3m",)
    assert result.snapshot.records[1].lazy_materialization_refs == ("msas/P68871.a3m",)
    assert result.snapshot.records[0].metadata["source_record_index"] == 0
    assert result.snapshot.records[1].metadata["source_record_index"] == 1
    assert result.snapshot.records[0].metadata["source_layers"] == (
        "UniProt/UniRef",
        "InterPro",
        "live smoke",
    )
    assert result.snapshot.records[1].metadata["source_layers"] == (
        "UniProt/UniRef",
        "InterPro",
        "live smoke",
    )


def test_acquire_evolutionary_snapshot_handles_missing_or_empty_payloads(
    tmp_path,
) -> None:
    missing_manifest = build_evolutionary_snapshot_manifest(
        source_release=SourceReleaseManifest(
            source_name="Evolutionary / MSA corpus",
            release_version="2026_03",
            retrieval_mode="download",
            local_artifact_refs=(str(tmp_path / "missing.json"),),
        ),
        corpus_snapshot_id="corpus-2026_03",
        aligner_version="mmseqs2-15",
        source_layers=("UniProt/UniRef",),
        parameters={"evalue": 1e-3},
    )

    missing_result = acquire_evolutionary_snapshot(missing_manifest)
    assert missing_result.status == "blocked"
    assert missing_result.reason == "evolutionary_snapshot_payload_unavailable"

    empty_path = tmp_path / "empty.json"
    empty_path.write_text(json.dumps({"records": []}), encoding="utf-8")
    empty_manifest = build_evolutionary_snapshot_manifest(
        source_release=SourceReleaseManifest(
            source_name="Evolutionary / MSA corpus",
            release_version="2026_03",
            retrieval_mode="download",
            local_artifact_refs=(str(empty_path),),
        ),
        corpus_snapshot_id="corpus-2026_03",
        aligner_version="mmseqs2-15",
        source_layers=("UniProt/UniRef",),
        parameters={"evalue": 1e-3},
    )

    empty_result = acquire_evolutionary_snapshot(empty_manifest)
    assert empty_result.status == "unavailable"
    assert empty_result.reason == "evolutionary_snapshot_no_records"
