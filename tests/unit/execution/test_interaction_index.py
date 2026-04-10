from __future__ import annotations

from connectors.bindingdb.parsers import BindingDBAssayRecord
from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.intact_snapshot import IntActInteractionRecord
from execution.indexing.interaction_index import build_interaction_planning_index


def _intact_record() -> IntActInteractionRecord:
    return IntActInteractionRecord(
        interaction_ac="EBI-123456",
        imex_id="IM-12345-1",
        participant_a_ids=("uniprotkb:P12345",),
        participant_b_ids=("uniprotkb:Q99999",),
        participant_a_aliases=("P12345",),
        participant_b_aliases=("Q99999",),
        participant_a_primary_id="P12345",
        participant_b_primary_id="Q99999",
        participant_a_identity_namespace="uniprotkb",
        participant_b_identity_namespace="uniprotkb",
        participant_a_tax_id=9606,
        participant_b_tax_id=9606,
        interaction_type="physical association",
        detection_method="two hybrid",
        source_database="IntAct",
        publication_ids=("PMID:12345",),
        confidence_values=("MI:confidence score",),
        interaction_ids=("EBI-123456",),
        expanded_from_complex=True,
        native_complex=False,
        interaction_representation="binary_projection",
        provenance={
            "source_locator": "cache/raw/intact/247.tsv",
        },
        raw_row="EBI-123456\tP12345\tQ99999",
    )


def _bindingdb_record() -> BindingDBAssayRecord:
    return BindingDBAssayRecord(
        reactant_set_id="RS123",
        monomer_id="120095",
        ligand_smiles="CCO",
        ligand_inchi_key="InChIKey=ABCDEF",
        target_name="Mitogen-activated protein kinase 1",
        target_uniprot_ids=("P28482",),
        target_pdb_ids=("1ABC",),
        affinity_type="Ki",
        affinity_value_nM=21800.0,
        assay_description="Competitive inhibition",
        publication_date="2022-03-25",
        curation_date="2022-04-01",
        source="BindingDB",
        raw={"PMID": "12345", "DOI": "10.1/example"},
    )


def test_build_interaction_planning_index_preserves_ppi_projection_lineage() -> None:
    intact_release = SourceReleaseManifest(
        source_name="IntAct",
        release_version="247",
        retrieval_mode="download",
        source_locator="cache/raw/intact/247.tsv",
    )

    schema = build_interaction_planning_index(
        [
            {"record": _intact_record(), "source_release": intact_release},
        ]
    )

    assert schema.record_count == 1
    entry = schema.records[0]

    assert entry.planning_id == "interaction:protein_protein:protein:P12345|protein:Q99999"
    assert entry.join_status == "partial"
    assert entry.source_records[0].source_name == "IntAct"
    assert entry.source_records[0].manifest_id.startswith("IntAct:247:download")
    assert entry.source_records[0].release_stamp == "247"
    assert entry.coverage[0].coverage_kind == "source"
    assert entry.coverage[1].coverage_kind == "modality"
    assert entry.coverage[1].coverage_state == "partial"
    assert entry.lazy_materialization_pointers[0].materialization_kind == "table"
    assert entry.lazy_materialization_pointers[0].pointer == "cache/raw/intact/247.tsv"
    assert entry.metadata["supporting_source_refs"] == ("EBI-123456", "IM-12345-1")


def test_build_interaction_planning_index_handles_protein_ligand_rows() -> None:
    bindingdb_release = SourceReleaseManifest(
        source_name="BindingDB",
        release_version="2026.02",
        retrieval_mode="download",
        source_locator="cache/raw/bindingdb/2026_02.tsv",
    )

    schema = build_interaction_planning_index(
        [
            {"record": _bindingdb_record(), "source_release": bindingdb_release},
        ]
    )

    assert schema.record_count == 1
    entry = schema.records[0]

    assert entry.planning_id == "interaction:protein_ligand:protein:P28482|ligand:bindingdb:120095"
    assert entry.join_status == "candidate"
    assert entry.source_records[0].source_name == "BindingDB"
    assert entry.source_records[0].source_record_id == "RS123"
    assert entry.source_records[0].manifest_id.startswith("BindingDB:2026.02:download")
    assert entry.source_records[0].release_stamp == "2026.02"
    assert entry.lazy_materialization_pointers[0].selector == "RS123"
    assert entry.metadata["ligand_refs"] == (
        "ligand:bindingdb:120095",
        "ligand:inchikey:ABCDEF",
        "ligand:smiles:CCO",
    )
    assert entry.metadata["source_record"]["source_locator"] == "cache/raw/bindingdb/2026_02.tsv"


def test_build_interaction_planning_index_uses_chemical_ligand_keys() -> None:
    bindingdb_release = SourceReleaseManifest(
        source_name="BindingDB",
        release_version="2026.02",
        retrieval_mode="download",
        source_locator="cache/raw/bindingdb/2026_02.tsv",
    )

    chemical_only_record = BindingDBAssayRecord(
        reactant_set_id="RS999",
        monomer_id="",
        ligand_smiles="CCO",
        ligand_inchi_key="InChIKey=ABCDEF",
        target_name="Mitogen-activated protein kinase 1",
        target_uniprot_ids=("P28482",),
        target_pdb_ids=("1ABC",),
        affinity_type="Ki",
        affinity_value_nM=21800.0,
        assay_description="Competitive inhibition",
        publication_date="2022-03-25",
        curation_date="2022-04-01",
        source="BindingDB",
        raw={"PMID": "12345", "DOI": "10.1/example"},
    )

    schema = build_interaction_planning_index(
        [
            {"record": chemical_only_record, "source_release": bindingdb_release},
        ]
    )

    assert schema.record_count == 1
    entry = schema.records[0]

    assert entry.planning_id == "interaction:protein_ligand:protein:P28482|ligand:inchikey:ABCDEF"
    assert entry.join_status == "candidate"
    assert entry.source_records[0].manifest_id.startswith("BindingDB:2026.02:download")
    assert entry.metadata["ligand_refs"] == (
        "ligand:inchikey:ABCDEF",
        "ligand:smiles:CCO",
    )
    assert entry.metadata["source_record"]["source_locator"] == "cache/raw/bindingdb/2026_02.tsv"


def test_build_interaction_planning_index_round_trips_through_dict() -> None:
    schema = build_interaction_planning_index(
        [
            {
                "source_name": "BioGRID",
                "biogrid_interaction_id": "123456",
                "participant_a_ids": ("uniprotkb:P12345",),
                "participant_b_ids": ("uniprotkb:Q99999",),
                "interaction_type": "physical interaction",
                "source_locator": "cache/raw/biogrid/2026_03.tsv",
                "raw_artifact_refs": ("cache/raw/biogrid/2026_03.tsv",),
            }
        ]
    )

    payload = schema.to_dict()
    assert payload["record_count"] == 1
    assert payload["records"][0]["join_status"] == "candidate"
    assert payload["records"][0]["lazy_materialization_pointers"][0]["pointer"] == (
        "cache/raw/biogrid/2026_03.tsv"
    )
