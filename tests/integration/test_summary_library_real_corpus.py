from __future__ import annotations

import json
import ssl
from pathlib import Path
from urllib.request import Request, urlopen

from connectors.rcsb.client import RCSBClient
from core.library.summary_record import (
    ProteinProteinSummaryRecord,
    ProteinSummaryRecord,
    SummaryLibrarySchema,
    SummaryProvenancePointer,
    SummaryRecordContext,
)
from execution.acquire.rcsb_pdbe_snapshot import acquire_rcsb_pdbe_snapshot, build_snapshot_manifest
from execution.acquire.uniprot_snapshot import acquire_uniprot_snapshot
from execution.indexing.protein_pair_crossref import build_protein_pair_crossref_index
from execution.library.build_summary_library import build_summary_library

_LIVE_VALIDATION_MANIFEST_ID = "summary-library-live-corpus:2026-03-22"
_LIVE_USER_AGENT = "ProteoSphereV2-live-validation/0.1"
_LIVE_CONTEXT = ssl._create_unverified_context()


def _live_opener(request, timeout=None):
    if isinstance(request, str):
        request = Request(request, headers={"User-Agent": _LIVE_USER_AGENT})
    return urlopen(request, timeout=timeout, context=_LIVE_CONTEXT)


def _uniprot_snapshot():
    return acquire_uniprot_snapshot(
        {
            "source": "UniProt",
            "release": "2026_03",
            "release_date": "2026-03-01",
            "proteome_id": "UP000005640",
            "proteome_name": "Homo sapiens",
            "proteome_reference": True,
            "proteome_taxon_id": 9606,
            "accessions": ["P69905", "P68871"],
            "manifest_id": "uniprot:live-corpus:2026-03-22",
            "provenance": {
                "source_ids": ["raw/uniprot/P69905.json", "raw/uniprot/P68871.json"],
            },
        },
        opener=_live_opener,
    )


def _rcsb_snapshot():
    manifest = build_snapshot_manifest(
        ["4HHB"],
        release_id="2026-03-22",
        snapshot_id=_LIVE_VALIDATION_MANIFEST_ID,
        pdbe_resources=("uniprot_mapping",),
        include_mmcif=False,
    )
    return acquire_rcsb_pdbe_snapshot(
        manifest,
        client=RCSBClient(),
        opener=_live_opener,
        pdbe_opener=_live_opener,
    )


def _protein_record(snapshot_record, *, source_manifest_id: str) -> ProteinSummaryRecord:
    provenance_pointer = SummaryProvenancePointer(
        provenance_id=f"uniprot:{snapshot_record.accession}:{snapshot_record.release}",
        source_name="UniProt",
        source_record_id=snapshot_record.accession,
        release_version=snapshot_record.release,
        release_date=snapshot_record.release_date,
        acquired_at=snapshot_record.provenance["acquired_at"],
    )
    return ProteinSummaryRecord(
        summary_id=f"protein:{snapshot_record.accession}",
        protein_ref=f"protein:{snapshot_record.accession}",
        protein_name=snapshot_record.sequence.protein_name,
        organism_name=snapshot_record.sequence.organism_name,
        taxon_id=9606,
        sequence_length=snapshot_record.sequence.sequence_length,
        gene_names=snapshot_record.sequence.gene_names,
        aliases=(snapshot_record.sequence.entry_name,),
        context=SummaryRecordContext(
            provenance_pointers=(provenance_pointer,),
            storage_notes=(f"live-derived from {source_manifest_id}",),
        ),
    )


def _protein_pair_record(bundle) -> ProteinProteinSummaryRecord:
    entity_a, entity_b = bundle.entities
    return ProteinProteinSummaryRecord(
        summary_id=f"pair:{bundle.entry.pdb_id}:protein_protein",
        protein_a_ref=f"protein:{entity_a.uniprot_ids[0]}",
        protein_b_ref=f"protein:{entity_b.uniprot_ids[0]}",
        interaction_type="protein complex",
        interaction_id=bundle.entry.pdb_id,
        interaction_refs=(bundle.entry.pdb_id,),
        organism_name=entity_a.organism_names[0],
        taxon_id=int(entity_a.taxonomy_ids[0]),
        physical_interaction=True,
        join_status="joined",
        context=SummaryRecordContext(),
    )


def test_summary_library_builds_from_live_real_corpus_and_keeps_gaps_visible() -> None:
    uniprot_snapshot = _uniprot_snapshot()
    rcsb_snapshot = _rcsb_snapshot()

    protein_records = tuple(
        _protein_record(record, source_manifest_id=uniprot_snapshot.contract.manifest_id)
        for record in uniprot_snapshot.snapshot.records
    )
    pair_record = _protein_pair_record(rcsb_snapshot.structure_bundles[0])

    source_library = SummaryLibrarySchema(
        library_id=_LIVE_VALIDATION_MANIFEST_ID,
        source_manifest_id=_LIVE_VALIDATION_MANIFEST_ID,
        records=(*protein_records, pair_record),
    )
    pair_crossref_index = build_protein_pair_crossref_index(source_library)
    summary_library = build_summary_library(
        SummaryLibrarySchema(
            library_id=_LIVE_VALIDATION_MANIFEST_ID,
            source_manifest_id=_LIVE_VALIDATION_MANIFEST_ID,
            records=protein_records,
        ),
        pair_crossref_index=pair_crossref_index,
    )

    assert summary_library.library_id == _LIVE_VALIDATION_MANIFEST_ID
    assert summary_library.source_manifest_id == _LIVE_VALIDATION_MANIFEST_ID
    assert summary_library.record_count == 3
    assert [record.protein_ref for record in summary_library.protein_records] == [
        "protein:P68871",
        "protein:P69905",
    ]
    assert summary_library.ligand_records == ()

    pair = next(
        record
        for record in summary_library.pair_records
        if record.summary_id.startswith("pair:4HHB")
    )
    assert pair.protein_a_ref == "protein:P69905"
    assert pair.protein_b_ref == "protein:P68871"
    assert pair.interaction_refs == ("4HHB",)
    assert pair.interaction_id is None
    assert pair.evidence_refs == ("4HHB",)
    assert pair.context.provenance_pointers == ()
    assert pair.join_status == "joined"

    protein = next(
        record
        for record in summary_library.protein_records
        if record.summary_id == "protein:P69905"
    )
    assert protein.protein_name == "Hemoglobin subunit alpha"
    assert protein.context.provenance_pointers[0].source_name == "UniProt"
    assert protein.context.provenance_pointers[0].source_record_id == "P69905"


def test_real_corpus_artifacts_keep_summary_library_gaps_explicit() -> None:
    root = Path("runs/real_data_benchmark/full_results")

    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "completed"
    assert summary["executed"] is True
    assert summary["execution_scope"]["cohort_size"] == 12
    assert summary["execution_scope"]["runtime_surface"] == (
        "local prototype runtime with surrogate modality embeddings and "
        "identity-safe resume continuity"
    )
    assert summary["blocker_categories"] == []
    assert summary["release_grade_bar"] == {
        "governing_sufficiency_complete": True,
        "reporting_completeness_complete": True,
        "runtime_qualification_complete": True,
    }

    source_coverage = json.loads((root / "source_coverage.json").read_text(encoding="utf-8"))
    assert source_coverage["blockers"] == [
        (
            "The benchmark corpus rerun is still partial at corpus scale and "
            "remains represented by a selected-example probe in the runtime outputs."
        ),
        (
            "The frozen cohort is evidence-backed and leakage-ready, but it does "
            "not by itself remove the broader benchmark-setup/runtime maturity gap."
        ),
    ]
    p69905 = next(
        row for row in source_coverage["coverage_matrix"] if row["accession"] == "P69905"
    )
    assert p69905["source_lanes"] == [
        "UniProt",
        "InterPro",
        "Reactome",
        "AlphaFold DB",
        "Evolutionary / MSA",
    ]
    assert p69905["thin_coverage"] is False
    p68871 = next(
        row for row in source_coverage["coverage_matrix"] if row["accession"] == "P68871"
    )
    assert p68871["mixed_evidence"] is True
    assert p68871["coverage_notes"] == [
        "summary-library probe rather than direct assay",
    ]
    assert p68871["conservative_evidence_tier"] == "probe_supported_multilane"
    p04637 = next(
        row for row in source_coverage["coverage_matrix"] if row["accession"] == "P04637"
    )
    assert p04637["thin_coverage"] is True
    assert p04637["source_lanes"] == ["IntAct"]
    assert p04637["conservative_evidence_tier"] == "direct_single_lane"

    ledger = json.loads(
        (root / "release_corpus_evidence_ledger.json").read_text(encoding="utf-8")
    )
    ledger_rows = {row["canonical_id"]: row for row in ledger["rows"]}
    assert ledger_rows["protein:P69905"]["release_ready"] is False
    assert ledger_rows["protein:P69905"]["metadata"]["ppi_case_kind"] == "direct_single_source"
    assert ledger_rows["protein:P69905"]["metadata"]["packet_completeness"] == "partial"
    assert ledger_rows["protein:P68871"]["metadata"]["ppi_case_kind"] == "direct_single_source"
    assert ledger_rows["protein:P04637"]["metadata"]["missing_modalities"] == [
        "sequence",
        "structure",
        "ligand",
    ]
    assert ledger_rows["protein:P31749"]["metadata"]["present_modalities"] == ["ligand"]
    assert ledger_rows["protein:P31749"]["release_ready"] is False

    packet_audit = json.loads((root / "training_packet_audit.json").read_text(encoding="utf-8"))
    packets = {row["accession"]: row for row in packet_audit["packets"]}
    assert packets["P69905"]["judgment"] == "useful"
    assert packets["P69905"]["missing_modalities"] == ["ligand", "ppi"]
    assert packets["P68871"]["judgment"] == "weak"
    assert packets["P68871"]["mixed_evidence"] is True
    assert packets["P04637"]["thin_coverage"] is True
    assert packets["P31749"]["present_modalities"] == ["ligand"]

    bundle_manifest = json.loads(
        (root / "release_bundle_manifest.json").read_text(encoding="utf-8")
    )
    assert bundle_manifest["status"] == "assembled_release_candidate_v1"
    assert bundle_manifest["truth_boundary"]["forbidden_overclaims"] == [
        "production-equivalent runtime",
        "release-grade provenance without blocker categories",
        "full corpus success without pinned outputs",
        "silent cohort widening",
        "silent leakage across splits",
    ]
    assert bundle_manifest["blocker_categories"] == []
