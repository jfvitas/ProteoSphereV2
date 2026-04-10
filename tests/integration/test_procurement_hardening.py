from __future__ import annotations

import json

from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)
from execution.acquire.alphafold_snapshot import (
    AlphaFoldSnapshotStatus,
    acquire_alphafold_snapshot,
)
from execution.acquire.evolutionary_snapshot import (
    acquire_evolutionary_snapshot,
    build_evolutionary_snapshot_manifest,
)


def _evolutionary_release_manifest(
    *,
    local_artifact_refs: tuple[str, ...],
    provenance: tuple[str, ...] = (),
) -> SourceReleaseManifest:
    return SourceReleaseManifest(
        source_name="Evolutionary / MSA corpus",
        release_version="2026_03",
        retrieval_mode="download",
        source_locator="https://example.org/evolutionary/corpus.json",
        local_artifact_refs=local_artifact_refs,
        provenance=provenance,
        reproducibility_metadata=("aligner=mmseqs2-15",),
    )


def test_procurement_hardening_validates_in_tree_evolutionary_acquisition_and_manifest_identity(
    tmp_path,
) -> None:
    corpus_path = tmp_path / "evolutionary_corpus.json"
    corpus_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "accession": "P12345",
                        "sequence_version": "2",
                        "sequence_hash": "sha256:abc123",
                        "sequence_length": 342,
                        "taxon_id": 9606,
                        "uniref_cluster_ids": ["UniRef90_P12345"],
                        "source_refs": ["raw/uniprot/P12345.fasta"],
                        "lazy_materialization_refs": ["cache/msas/P12345.a3m"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    manifest_a = build_evolutionary_snapshot_manifest(
        source_release=_evolutionary_release_manifest(
            local_artifact_refs=(str(corpus_path),),
            provenance=("pinned-corpus",),
        ),
        corpus_snapshot_id="corpus-2026_03",
        aligner_version="mmseqs2-15",
        source_layers=("UniProt/UniRef", "local MMseqs2"),
        parameters={"evalue": 1e-3},
    )
    manifest_b = build_evolutionary_snapshot_manifest(
        source_release=_evolutionary_release_manifest(
            local_artifact_refs=(str(corpus_path), str(tmp_path / "alt-corpus.json")),
            provenance=("pinned-corpus",),
        ),
        corpus_snapshot_id="corpus-2026_03",
        aligner_version="mmseqs2-15",
        source_layers=("UniProt/UniRef", "local MMseqs2"),
        parameters={"evalue": 1e-3},
    )

    result = acquire_evolutionary_snapshot(manifest_a, acquired_on="2026-03-22T12:00:00Z")

    assert result.status == "ok"
    assert result.succeeded is True
    assert result.snapshot is not None
    assert result.snapshot.records[0].accession == "P12345"
    assert result.provenance.record_count == 1
    assert result.manifest.manifest_id == (
        f"{manifest_a.source_release.manifest_id}:corpus-2026_03:mmseqs2-15"
    )
    assert manifest_a.source_release.manifest_id != manifest_b.source_release.manifest_id
    assert manifest_a.manifest_id != manifest_b.manifest_id


def test_procurement_hardening_preserves_alphafold_invalid_manifest_identity() -> None:
    result = acquire_alphafold_snapshot(
        {
            "source_release": {
                "source_name": "AlphaFold DB",
                "release_version": "2026_03",
                "retrieval_mode": "screen-scrape",
                "source_locator": "https://alphafold.ebi.ac.uk/api/openapi.json",
            },
            "qualifiers": ["Q9TEST"],
        }
    )

    assert result.status == AlphaFoldSnapshotStatus.BLOCKED
    assert result.manifest.qualifiers == ("Q9TEST",)
    assert result.manifest.source_release.source_name == "AlphaFold DB"
    assert result.manifest.source_release.release_version == "2026_03"
    assert result.manifest.source_release.retrieval_mode == "api"
    assert result.manifest.manifest_id.startswith("AlphaFold DB:2026_03:api:")
    assert result.manifest.metadata["requested_invalid_retrieval_mode"] == "screen-scrape"
    round_tripped = validate_source_release_manifest_payload(
        result.manifest.to_dict()["source_release"]
    )
    assert round_tripped.retrieval_mode == "api"
    assert "unsupported retrieval_mode" in result.blocker_reason
    assert "P69905" not in result.manifest.manifest_id
