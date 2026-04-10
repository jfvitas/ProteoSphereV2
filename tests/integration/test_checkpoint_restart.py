from __future__ import annotations

import execution.canonical_pipeline as canonical_pipeline
from connectors.rcsb.parsers import (
    RCSBAssemblyRecord,
    RCSBEntityRecord,
    RCSBEntryRecord,
    RCSBStructureBundle,
)
from connectors.uniprot.parsers import UniProtSequenceRecord
from core.canonical.ligand import CanonicalLigand
from core.canonical.registry import CanonicalEntityRegistry
from execution.canonical_pipeline import (
    CanonicalPipelineConfig,
    resume_canonical_pipeline,
    run_canonical_pipeline,
)
from execution.checkpoints.store import CheckpointStore
from execution.dag.node import DAGNodeStatus


def _registry() -> CanonicalEntityRegistry:
    return CanonicalEntityRegistry(
        proteins=(),
        ligands=(
            CanonicalLigand(
                ligand_id="bindingdb:120095",
                name="BindingDB ligand 120095",
                source="BindingDB",
                source_id="120095",
                smiles="CCO",
            ),
        ),
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


def _structure_bundle() -> RCSBStructureBundle:
    entry = RCSBEntryRecord(
        pdb_id="1ABC",
        title="Checkpoint restart bundle",
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
        sequence="ACDEFGHIK",
        sequence_length=9,
        chain_ids=("A",),
        uniprot_ids=("P28482",),
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


def test_checkpoint_resume_advances_the_ready_frontier_after_partial_failure(monkeypatch) -> None:
    store = CheckpointStore()

    def _fail_structure_ingest(*args, **kwargs):  # noqa: ANN001,ARG001
        raise ValueError("synthetic structure ingest failure")

    monkeypatch.setattr(
        canonical_pipeline,
        "ingest_structure_records",
        _fail_structure_ingest,
    )

    initial = run_canonical_pipeline(
        CanonicalPipelineConfig(
            run_id="restart-partial",
            sequence_records=(_sequence_record(),),
            structure_records=(_structure_bundle(),),
            assay_records=(_assay_row(),),
            registry=_registry(),
            checkpoint_store=store,
            acquired_at="2026-03-22T15:00:00Z",
            parser_version="1.0.0",
        )
    )

    assert initial.status == "failed"
    assert initial.run_checkpoint is not None
    assert initial.run_checkpoint.checkpoint_state["completed_nodes"] == ["ingest_sequences"]
    assert initial.node_states["ingest_structures"].status == DAGNodeStatus.FAILED

    resumed = resume_canonical_pipeline(
        CanonicalPipelineConfig(
            run_id="restart-partial",
            sequence_records=(_sequence_record(),),
            structure_records=(_structure_bundle(),),
            assay_records=(_assay_row(),),
            registry=_registry(),
            checkpoint_store=store,
            acquired_at="2026-03-22T15:00:00Z",
            parser_version="1.0.0",
        )
    )

    assert resumed.status == "failed"
    assert resumed.reason == (
        "ingest_structures failed: ValueError: synthetic structure ingest failure"
    )
    assert resumed.sequence_result is not None
    assert resumed.assay_result is not None
    assert resumed.structure_result is None
    assert resumed.run_checkpoint is not None
    assert resumed.run_checkpoint.version == 3
    assert resumed.run_checkpoint.checkpoint_state["completed_nodes"] == [
        "ingest_sequences",
        "ingest_assays",
    ]
    assert resumed.node_states["ingest_sequences"].status == DAGNodeStatus.SUCCEEDED
    assert resumed.node_states["ingest_assays"].status == DAGNodeStatus.SUCCEEDED
    assert resumed.node_states["ingest_structures"].status == DAGNodeStatus.FAILED
    assert resumed.blocked_nodes == ("assemble_canonical_layer",)
    assert resumed.ready_nodes == ()
    assert store.list_versions("restart-partial") == (1, 2, 3)
    assert store.list_versions("restart-partial", "ingest_sequences") == (1,)
    assert store.list_versions("restart-partial", "ingest_structures") == (1,)
    assert store.list_versions("restart-partial", "ingest_assays") == (1,)


def test_checkpoint_resume_keeps_completed_runs_closed() -> None:
    store = CheckpointStore()
    initial = run_canonical_pipeline(
        CanonicalPipelineConfig(
            run_id="restart-complete",
            sequence_records=(_sequence_record(),),
            structure_records=(_structure_bundle(),),
            assay_records=(_assay_row(),),
            registry=_registry(),
            checkpoint_store=store,
            acquired_at="2026-03-22T15:00:00Z",
            parser_version="1.0.0",
        )
    )

    assert initial.status == "ready"
    assert initial.run_checkpoint is not None
    assert initial.run_checkpoint.checkpoint_state["completed_nodes"] == [
        "ingest_sequences",
        "ingest_structures",
        "ingest_assays",
        "assemble_canonical_layer",
    ]

    resumed = resume_canonical_pipeline(
        CanonicalPipelineConfig(
            run_id="restart-complete",
            sequence_records=(_sequence_record(),),
            structure_records=(_structure_bundle(),),
            assay_records=(_assay_row(),),
            registry=_registry(),
            checkpoint_store=store,
            acquired_at="2026-03-22T15:00:00Z",
            parser_version="1.0.0",
        )
    )

    assert resumed.status == "ready"
    assert resumed.reason == "all_canonical_ingest_slices_resolved"
    assert resumed.ready_nodes == ()
    assert resumed.blocked_nodes == ()
    assert resumed.run_checkpoint is not None
    assert resumed.run_checkpoint.version == 4
    assert resumed.run_checkpoint.checkpoint_state["completed_nodes"] == [
        "ingest_sequences",
        "ingest_structures",
        "ingest_assays",
        "assemble_canonical_layer",
    ]
    assert resumed.sequence_result is not None
    assert resumed.structure_result is not None
    assert resumed.assay_result is not None
    assert store.list_versions("restart-complete") == (1, 2, 3, 4)
    assert store.list_versions("restart-complete", "ingest_sequences") == (1,)
    assert store.list_versions("restart-complete", "ingest_structures") == (1,)
    assert store.list_versions("restart-complete", "ingest_assays") == (1,)
    assert store.list_versions("restart-complete", "assemble_canonical_layer") == (1,)
