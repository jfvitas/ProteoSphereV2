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
from core.canonical.protein import CanonicalProtein
from core.canonical.registry import CanonicalEntityRegistry
from execution.canonical_pipeline import CanonicalPipelineConfig, run_canonical_pipeline
from execution.checkpoints.store import CheckpointStore


def _registry() -> CanonicalEntityRegistry:
    protein = CanonicalProtein(
        accession="P28482",
        sequence="ACDEFGHIK",
        name="Mitogen-activated protein kinase 1",
        organism="Homo sapiens",
        gene_names=("MAPK1",),
        description="Mitogen-activated protein kinase 1",
        aliases=("MAPK1_HUMAN",),
        annotations=("reviewed",),
    )
    ligand = CanonicalLigand(
        ligand_id="bindingdb:120095",
        name="BindingDB ligand 120095",
        source="BindingDB",
        source_id="120095",
        smiles="CCO",
    )
    return CanonicalEntityRegistry(proteins=[protein], ligands=[ligand])


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


def _structure_bundle(*, sequence: str, uniprot_ids: tuple[str, ...]) -> RCSBStructureBundle:
    entry = RCSBEntryRecord(
        pdb_id="1ABC",
        title="Canonical pipeline bundle",
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
        sequence_length=len(sequence) if sequence else None,
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


def _assay_row() -> dict[str, object]:
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


def test_canonical_pipeline_runs_full_graph_and_writes_checkpoints() -> None:
    store = CheckpointStore()
    result = run_canonical_pipeline(
        CanonicalPipelineConfig(
            run_id="run-001",
            sequence_records=(_sequence_record(),),
            structure_records=(_structure_bundle(sequence="ACDEFGHIK", uniprot_ids=("P28482",)),),
            assay_records=(_assay_row(),),
            registry=_registry(),
            checkpoint_store=store,
            acquired_at="2026-03-22T15:00:00Z",
            parser_version="1.0.0",
        )
    )

    assert result.status == "ready"
    assert result.reason == "all_canonical_ingest_slices_resolved"
    assert [node.node_id for node in result.scheduler.ordered_nodes] == [
        "ingest_sequences",
        "ingest_structures",
        "ingest_assays",
        "assemble_canonical_layer",
    ]
    assert result.node_states["ingest_sequences"].status.value == "succeeded"
    assert result.node_states["ingest_structures"].status.value == "succeeded"
    assert result.node_states["ingest_assays"].status.value == "succeeded"
    assert result.node_states["assemble_canonical_layer"].status.value == "succeeded"
    assert len(result.run_checkpoints) == 4
    assert store.list_versions("run-001") == (1, 2, 3, 4)
    assert store.list_versions("run-001", "ingest_sequences") == (1,)
    assert store.list_versions("run-001", "ingest_structures") == (1,)
    assert store.list_versions("run-001", "ingest_assays") == (1,)
    assert store.list_versions("run-001", "assemble_canonical_layer") == (1,)
    assert result.run_checkpoint is not None
    assert result.run_checkpoint.checkpoint_state["status"] == "ready"
    assert result.sequence_result is not None
    assert result.sequence_result.canonical_ids == ("protein:P28482",)
    assert result.structure_result is not None
    assert result.structure_result.chains[0].mapped_protein_internal_id is not None
    assert result.assay_result is not None
    assert result.assay_result.canonical_assays[0].target_id == "protein:P28482"
    assert result.assay_result.canonical_assays[0].ligand_id == "ligand:bindingdb:120095"
    assert result.unresolved_cases == ()
    assert result.conflicts == ()
    assert result.summary["blocked_nodes"] == []
    assert json.loads(json.dumps(result.to_dict()))["status"] == "ready"


def test_canonical_pipeline_preserves_unresolved_structure_cases() -> None:
    store = CheckpointStore()
    result = run_canonical_pipeline(
        CanonicalPipelineConfig(
            run_id="run-002",
            sequence_records=(_sequence_record(),),
            structure_records=(_structure_bundle(sequence="", uniprot_ids=("P28482",)),),
            assay_records=(_assay_row(),),
            registry=_registry(),
            checkpoint_store=store,
            acquired_at="2026-03-22T15:00:00Z",
            parser_version="1.0.0",
        )
    )

    assert result.status == "partial"
    assert result.structure_result is not None
    assert result.structure_result.status == "partial"
    assert {reference.reason for reference in result.structure_result.unresolved_references} == {
        "missing_sequence",
        "missing_primary_identifier",
    }
    assert result.sequence_result is not None
    assert result.sequence_result.status == "ready"
    assert result.assay_result is not None
    assert result.assay_result.status == "resolved"
    assert result.run_checkpoint is not None
    assert result.run_checkpoint.checkpoint_state["status"] == "partial"
    assert store.list_versions("run-002") == (1, 2, 3, 4)
    assert result.summary["structure"]["unresolved_references"] == 2
    assert json.loads(json.dumps(result.to_dict()))["summary"]["status"] == "partial"
