from __future__ import annotations

from execution.acquire.local_pair_ligand_bridge import (
    bridge_local_protein_ligand,
    bridge_local_protein_pair,
    bridge_local_record,
    canonical_pair_id,
)
from execution.acquire.local_source_registry import DEFAULT_LOCAL_SOURCE_REGISTRY


def test_bridge_local_protein_pair_resolves_accession_first_pair() -> None:
    source_entry = DEFAULT_LOCAL_SOURCE_REGISTRY.get("pdbbind_pp")
    assert source_entry is not None

    record = bridge_local_protein_pair(
        source_name="pdbbind_pp",
        source_record_id="1FC2",
        pdb_id="1FC2",
        receptor_accessions=("P01857",),
        partner_accessions=("P01636",),
        receptor_chain_ids=("C", "D"),
        partner_chain_ids=("E",),
        source_entry=source_entry,
    )

    assert record.status == "resolved"
    assert record.pair_canonical_id == canonical_pair_id(("P01857", "P01636"))
    assert record.protein_canonical_ids == ("protein:P01857", "protein:P01636")
    assert record.issues == ()


def test_bridge_local_protein_pair_keeps_ambiguous_mapping_unresolved() -> None:
    record = bridge_local_protein_pair(
        source_name="pdbbind_pp",
        source_record_id="ambiguous-ppi",
        receptor_accessions=("P69905", "P68871"),
        partner_accessions=("P02042",),
    )

    assert record.status == "unresolved"
    assert record.pair_canonical_id is None
    assert any(issue.code == "multiple_receptor_accessions" for issue in record.issues)


def test_bridge_local_protein_ligand_resolves_small_molecule_identity() -> None:
    source_entry = DEFAULT_LOCAL_SOURCE_REGISTRY.get("biolip")
    assert source_entry is not None

    record = bridge_local_protein_ligand(
        source_name="biolip",
        source_record_id="1BB0:0IV",
        pdb_id="1BB0",
        protein_accessions=("P00734",),
        protein_chain_ids=("A",),
        ligand_id="0IV",
        ligand_inchi_key="USNINKBPBVKHHZ-UHFFFAOYSA-N",
        ligand_smiles="CCO",
        ligand_role="small_molecule",
        source_entry=source_entry,
    )

    assert record.status == "resolved"
    assert record.protein_canonical_ids == ("protein:P00734",)
    assert record.ligands[0].canonical_id == "ligand:0IV"
    assert record.issues == ()


def test_bridge_local_protein_ligand_keeps_peptide_case_unresolved() -> None:
    record = bridge_local_protein_ligand(
        source_name="processed_rcsb",
        source_record_id="1BB0:peptide",
        pdb_id="1BB0",
        protein_accessions=("P00734",),
        ligand_role="peptide",
    )

    assert record.status == "unresolved"
    assert record.ligands[0].canonical_id is None
    assert any(issue.code == "unresolved_ligand_identity" for issue in record.issues)


def test_bridge_local_record_supports_processed_pair_payload_shape() -> None:
    record = bridge_local_record(
        {
            "pdb_id": "2PTC",
            "uniprot_ids_1": ["P00760"],
            "uniprot_ids_2": ["P00974"],
            "chain_ids_1": ["E"],
            "chain_ids_2": ["I"],
        },
        source_name="processed_rcsb",
        source_kind="protein_protein",
    )

    assert record.status == "resolved"
    assert record.pdb_id == "2PTC"
    assert record.protein_canonical_ids == ("protein:P00760", "protein:P00974")
