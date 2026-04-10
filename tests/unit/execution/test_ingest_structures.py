from __future__ import annotations

import json

from connectors.rcsb.parsers import (
    RCSBAssemblyRecord,
    RCSBEntityRecord,
    RCSBEntryRecord,
    RCSBStructureBundle,
)
from core.provenance.record import ProvenanceRecord, ProvenanceSource
from execution.ingest.structures import ingest_structure_bundle


def _provenance() -> ProvenanceRecord:
    return ProvenanceRecord(
        provenance_id="prov-root",
        source=ProvenanceSource(
            source_name="Test source",
            acquisition_mode="manual_curated",
            original_identifier="test-structure",
            release_version="2026-03-22",
        ),
        transformation_step="source_selection",
        acquired_at="2026-03-22T10:00:00Z",
    )


def _bundle(
    *,
    sequence: str,
    uniprot_ids: tuple[str, ...],
    assembly_id: str = "1",
) -> RCSBStructureBundle:
    entry = RCSBEntryRecord(
        pdb_id="1ABC",
        title="Example structure",
        experimental_methods=("X-RAY DIFFRACTION",),
        resolution=1.8,
        release_date="2026-03-01",
        assembly_ids=(assembly_id,),
        polymer_entity_ids=("1",),
        nonpolymer_entity_ids=(),
    )
    entity = RCSBEntityRecord(
        pdb_id="1ABC",
        entity_id="1",
        description="Example protein",
        polymer_type="polypeptide(L)",
        sequence=sequence,
        sequence_length=len(sequence) if sequence else None,
        chain_ids=("A",),
        uniprot_ids=uniprot_ids,
        organism_names=("Homo sapiens",),
        taxonomy_ids=("9606",),
    )
    assembly = RCSBAssemblyRecord(
        pdb_id="1ABC",
        assembly_id=assembly_id,
        method="software defined",
        oligomeric_state="monomer",
        oligomeric_count=1,
        stoichiometry="A:1",
        chain_ids=("A",),
        polymer_entity_ids=("1",),
    )
    return RCSBStructureBundle(entry=entry, entities=(entity,), assemblies=(assembly,))


def test_ingest_structure_bundle_materializes_conservative_canonical_records() -> None:
    result = ingest_structure_bundle(
        _bundle(sequence="MKT", uniprot_ids=("P12345",)), provenance=(_provenance(),)
    )

    assert result.status == "resolved"
    assert len(result.provenance_records) == 2
    assert result.provenance_records[0].provenance_id == "prov-root"
    assert result.provenance_records[1].source.source_name == "RCSB PDB"
    assert result.provenance_records[1].parent_ids == ("prov-root",)
    assert len(result.proteins) == 1
    assert len(result.chains) == 1
    assert len(result.complexes) == 1
    assert len(result.graph_edges) == 2

    protein = result.proteins[0]
    chain = result.chains[0]
    complex_record = result.complexes[0]

    assert protein.provenance_refs == (result.provenance_records[1].provenance_id,)
    assert chain.mapped_protein_internal_id == protein.protein_id_internal
    assert chain.sequence_alignment_to_canonical is not None
    assert chain.sequence_alignment_to_canonical.status == "resolved"
    assert complex_record.member_chain_ids == (chain.chain_id_internal,)
    assert json.loads(json.dumps(result.to_dict()))["status"] == "resolved"


def test_ingest_structure_bundle_exposes_ambiguous_accession_mapping() -> None:
    result = ingest_structure_bundle(
        _bundle(sequence="MKT", uniprot_ids=("P12345", "Q99999")),
        provenance=(_provenance(),),
    )

    assert result.status == "conflict"
    assert len(result.proteins) == 2
    assert len(result.unresolved_references) == 2

    chain = result.chains[0]
    conflict = result.conflicts[0]

    assert chain.mapped_protein_internal_id is None
    assert chain.sequence_alignment_to_canonical is not None
    assert chain.sequence_alignment_to_canonical.status == "ambiguous"
    assert chain.unresolved_protein_reference is not None
    assert chain.unresolved_protein_reference.reason == "ambiguous_protein_mapping"
    assert conflict.kind == "identity_conflict"
    assert conflict.observed_values["accessions"] == ("P12345", "Q99999")


def test_ingest_structure_bundle_marks_missing_sequence_as_unresolved() -> None:
    result = ingest_structure_bundle(
        _bundle(sequence="", uniprot_ids=("P12345",)),
        provenance=(_provenance(),),
    )

    assert result.status == "partial"
    assert result.proteins == ()
    assert {ref.reason for ref in result.unresolved_references} == {
        "missing_sequence",
        "missing_primary_identifier",
    }

    chain = result.chains[0]
    assert chain.mapped_protein_internal_id is None
    assert chain.unresolved_protein_reference is not None
    assert chain.unresolved_protein_reference.reason == "missing_primary_identifier"
