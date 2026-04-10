from __future__ import annotations

import json

from connectors.rcsb.parsers import (
    RCSBAssemblyRecord,
    RCSBEntityRecord,
    RCSBEntryRecord,
    RCSBStructureBundle,
)
from connectors.uniprot.parsers import UniProtSequenceRecord
from core.canonical.ligand import CanonicalLigand
from core.canonical.registry import CanonicalEntityRegistry
from execution.canonical_pipeline import CanonicalPipelineConfig, run_canonical_pipeline
from execution.checkpoints.store import CheckpointStore


def _registry() -> CanonicalEntityRegistry:
    return CanonicalEntityRegistry(
        ligands=[
            CanonicalLigand(
                ligand_id="bindingdb:120095",
                name="BindingDB ligand 120095",
                source="BindingDB",
                source_id="120095",
                smiles="CCO",
            )
        ]
    )


def _sequence_record() -> UniProtSequenceRecord:
    return UniProtSequenceRecord(
        accession="P28482",
        entry_name="MAPK1_HUMAN",
        protein_name="Mitogen-activated protein kinase 1",
        organism_name="Homo sapiens",
        gene_names=("MAPK1",),
        reviewed=True,
        sequence="ACDEFGHIK",
        sequence_length=9,
        source_format="test",
    )


def _resolved_structure_bundle() -> RCSBStructureBundle:
    return _structure_bundle(uniprot_ids=("P28482",), sequence="ACDEFGHIK")


def _conflicted_structure_bundle() -> RCSBStructureBundle:
    return _structure_bundle(uniprot_ids=("P12345", "Q99999"), sequence="ACDEFGHIK")


def _structure_bundle(
    *,
    uniprot_ids: tuple[str, ...],
    sequence: str,
) -> RCSBStructureBundle:
    entry = RCSBEntryRecord(
        pdb_id="1ABC",
        title="Provenance integrity bundle",
        experimental_methods=("X-RAY DIFFRACTION",),
        resolution=1.8,
        release_date="2026-03-01",
        assembly_ids=("1",),
        polymer_entity_ids=("1",),
        nonpolymer_entity_ids=(),
    )
    entity = RCSBEntityRecord(
        pdb_id="1ABC",
        entity_id="1",
        description="Example protein",
        polymer_type="polypeptide(L)",
        sequence=sequence,
        sequence_length=len(sequence),
        chain_ids=("A",),
        uniprot_ids=uniprot_ids,
        organism_names=("Homo sapiens",),
        taxonomy_ids=("9606",),
    )
    assembly = RCSBAssemblyRecord(
        pdb_id="1ABC",
        assembly_id="1",
        method="software defined",
        oligomeric_state="monomer",
        oligomeric_count=1,
        stoichiometry="A:1",
        chain_ids=("A",),
        polymer_entity_ids=("1",),
    )
    return RCSBStructureBundle(entry=entry, entities=(entity,), assemblies=(assembly,))


def _resolved_assay_row() -> dict[str, object]:
    return {
        "BindingDB Reactant_set_id": "RS123",
        "BindingDB MonomerID": "120095",
        "Target Name": "Mitogen-activated protein kinase 1",
        "UniProtKB/SwissProt": "P28482",
        "Affinity Type": "Ki",
        "affinity_value_nM": "2.18E+4 nM",
        "Assay Description": "Competitive inhibition",
        "Publication Date": "2022-03-25",
        "BindingDB Curation Date": "2022-04-01",
        "PMID": "12345",
    }


def _unresolved_assay_row() -> dict[str, object]:
    row = _resolved_assay_row().copy()
    row["BindingDB MonomerID"] = ""
    return row


def test_provenance_integrity_preserves_lineage_through_canonical_pipeline() -> None:
    store = CheckpointStore()
    result = run_canonical_pipeline(
        CanonicalPipelineConfig(
            run_id="run-001",
            sequence_records=(_sequence_record(),),
            structure_records=(_resolved_structure_bundle(),),
            assay_records=(_resolved_assay_row(),),
            registry=_registry(),
            checkpoint_store=store,
            acquired_at="2026-03-22T15:00:00Z",
            parser_version="1.0.0",
        )
    )

    assert result.status == "ready"
    assert result.reason == "all_canonical_ingest_slices_resolved"
    assert result.sequence_result is not None
    assert result.structure_result is not None
    assert result.assay_result is not None

    sequence_provenance = result.sequence_result.provenance_records[0]
    structure_source_provenance = result.structure_result.provenance_records[1]
    assay_provenance = result.assay_result.provenance_records[0]

    assert structure_source_provenance.parent_ids == (sequence_provenance.provenance_id,)
    assert result.structure_result.chains[0].provenance_refs == (
        structure_source_provenance.provenance_id,
    )
    assert result.structure_result.complexes[0].provenance_refs == (
        structure_source_provenance.provenance_id,
    )
    assert assay_provenance.run_id == "run-001"
    assert result.assay_result.canonical_assays[0].provenance == (
        assay_provenance.provenance_id,
    )
    assert result.registry.resolve("P28482", entity_type="protein").canonical_id == "protein:P28482"
    assert result.registry.canonical_reference(
        result.registry.resolve("bindingdb:120095", entity_type="ligand")
    ) == "ligand:bindingdb:120095"
    assert result.run_checkpoint is not None
    assert result.run_checkpoint.provenance["node_id"] == "assemble_canonical_layer"
    assert result.run_checkpoint.metadata["node_count"] == 4
    assert result.node_checkpoints[0].metadata["operation"] == (
        "execution.ingest.sequences.ingest_sequence_records"
    )
    assert result.node_checkpoints[-1].provenance["completed_nodes"] == [
        "ingest_sequences",
        "ingest_structures",
        "ingest_assays",
        "assemble_canonical_layer",
    ]
    assert result.unresolved_cases == ()
    assert result.conflicts == ()
    assert json.loads(json.dumps(result.to_dict()))["status"] == "ready"


def test_provenance_integrity_surfaces_conflicts_and_unresolved_cases() -> None:
    store = CheckpointStore()
    result = run_canonical_pipeline(
        CanonicalPipelineConfig(
            run_id="run-002",
            sequence_records=(_sequence_record(),),
            structure_records=(_conflicted_structure_bundle(),),
            assay_records=(_unresolved_assay_row(),),
            registry=_registry(),
            checkpoint_store=store,
            acquired_at="2026-03-22T15:00:00Z",
            parser_version="1.0.0",
        )
    )

    assert result.status == "conflict"
    assert result.reason == "one_or_more_ingest_slices_reported_conflicts"
    assert result.sequence_result is not None
    assert result.sequence_result.status == "ready"
    assert result.structure_result is not None
    assert result.structure_result.status == "conflict"
    assert result.structure_result.conflicts[0].kind == "identity_conflict"
    assert {ref.reason for ref in result.structure_result.unresolved_references} == {
        "ambiguous_accession_mapping",
        "ambiguous_protein_mapping",
    }
    assert result.assay_result is not None
    assert result.assay_result.status == "unresolved"
    assert result.assay_result.unresolved_cases[0].issues[0].kind == "missing_ligand_identifier"
    assert len(result.unresolved_cases) == 3
    assert len(result.conflicts) == 1
    assert result.run_checkpoint is not None
    assert result.run_checkpoint.checkpoint_state["status"] == "conflict"
    assert result.summary["status"] == "conflict"
    assert json.loads(json.dumps(result.to_dict()))["summary"]["status"] == "conflict"
