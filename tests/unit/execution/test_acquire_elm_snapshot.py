from __future__ import annotations

from pathlib import Path

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.elm_snapshot import (
    ElmSnapshot,
    ElmSnapshotContract,
    ElmSnapshotResult,
    acquire_elm_snapshot,
)


def test_acquire_elm_snapshot_parses_classes_and_interaction_context(
    tmp_path: Path,
) -> None:
    classes_file = tmp_path / "elm_classes.tsv"
    classes_file.write_text(
        "#ELM_Classes_Download_Version: 1.4\n"
        "#ELM_Classes_Download_Date: 2026-03-30 06:31:04.917584\n"
        '#Origin: asimov\n'
        '#Type: tsv\n'
        '#Num_Classes: 1\n'
        '"Accession"\t"ELMIdentifier"\t"FunctionalSiteName"\t"Description"\t"Regex"\t"Probability"\t"#Instances"\t"#Instances_in_PDB"\n'
        '"ELME000321"\t"TEST_MOTIF"\t"Example motif"\t"Example motif class."\t"AA[ST]"\t"0.003"\t"41"\t"0"\n',
        encoding="utf-8",
    )
    interactions_file = tmp_path / "elm_interaction_domains.tsv"
    interactions_file.write_text(
        "Elm\tDomain\tinteractorElm\tinteractorDomain\tStartElm\tStopElm\tStartDomain\tStopDomain\tAffinityMin\tAffinityMax\tPMID\ttaxonomyElm\ttaxonomyDomain\n"
        "TEST_MOTIF\tPF00001\tQ12345\tPF00002\t5\t9\t20\t42\tNone\tNone\t12345678\t\"9606\"(Homo sapiens)\t\"9606\"(Homo sapiens)\n",
        encoding="utf-8",
    )

    manifest = SourceReleaseManifest(
        source_name="ELM",
        release_version="1.4",
        release_date="2026-03-30",
        retrieval_mode="download",
        local_artifact_refs=(str(classes_file), str(interactions_file)),
        provenance=("seed export",),
        reproducibility_metadata=("manual review pending",),
    )

    result = acquire_elm_snapshot(manifest, acquired_on="2026-03-30T00:00:00+00:00")

    assert isinstance(result, ElmSnapshotResult)
    assert result.status == "ok"
    assert result.succeeded is True
    assert isinstance(result.contract, ElmSnapshotContract)
    assert isinstance(result.snapshot, ElmSnapshot)
    assert result.contract.manual_review_required is True
    assert result.snapshot.release_version == "1.4"
    assert result.snapshot.record_count == 1
    assert result.snapshot.class_records[0].accession == "ELME000321"
    assert result.snapshot.class_records[0].interaction_domain_count == 1
    assert result.snapshot.class_records[0].interaction_domains == ("PF00002",)
    assert result.snapshot.interaction_records[0].pmids == ("12345678",)
    assert result.provenance["manual_review_required"] is True
    assert result.provenance["parser_version"] == "elm-tsv-v1"

    payload = result.to_dict()
    assert payload["snapshot"]["class_records"][0]["identifier"] == "TEST_MOTIF"
    assert payload["snapshot"]["interaction_records"][0]["domain"] == "PF00001"


def test_acquire_elm_snapshot_blocks_when_no_artifact_is_available() -> None:
    manifest = SourceReleaseManifest(
        source_name="ELM",
        release_version="1.4",
        retrieval_mode="download",
        provenance=("missing export",),
    )

    result = acquire_elm_snapshot(manifest)

    assert result.status == "blocked"
    assert result.contract is not None
    assert result.snapshot is None
    assert result.blocker_reason == "elm_manifest_needs_source_locator_or_local_artifact_refs"
    assert result.provenance["availability"] == "blocked"
