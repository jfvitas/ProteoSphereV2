from __future__ import annotations

import json

from execution.acquire.bio_agent_lab_imports import build_bio_agent_lab_import_manifest
from execution.acquire.local_pair_ligand_bridge import (
    bridge_local_protein_ligand,
    bridge_local_protein_pair,
    bridge_local_record,
    canonical_pair_id,
)
from execution.acquire.local_source_registry import (
    DEFAULT_LOCAL_SOURCE_ROOT,
    build_default_local_source_registry,
)


def test_selected_local_corpora_manifest_uses_real_files_and_explicit_missing_roots() -> None:
    root = DEFAULT_LOCAL_SOURCE_ROOT
    assert root.exists()

    expected_present = (
        root / "data_sources/uniprot/uniprot_sprot.dat.gz",
        root / "data_sources/reactome/UniProt2Reactome_All_Levels.txt",
        root / "data_sources/biolip/BioLiP_extracted/BioLiP.txt",
        root / "data_sources/pdbbind/index/INDEX_general_PP.2020R1.lst",
        root / "data_sources/pdbbind/index/INDEX_general_PL.2020R1.lst",
    )
    for path in expected_present:
        assert path.exists(), path

    registry = build_default_local_source_registry(root)
    manifest = build_bio_agent_lab_import_manifest(
        root,
        registry=registry,
        source_names=("uniprot", "reactome", "biolip", "pdbbind_pp", "pdbbind_pl", "biogrid"),
    )

    assert manifest.present_source_count == 3
    assert manifest.partial_source_count == 2
    assert manifest.missing_source_count == 1
    assert manifest.get_source("biogrid") is not None
    assert manifest.get_source("biogrid").status == "missing"
    assert manifest.get_source("uniprot").status == "partial"
    assert manifest.get_source("reactome").status == "present"
    assert manifest.get_source("biolip").status == "present"
    assert manifest.get_source("pdbbind_pp").status == "present"
    assert manifest.get_source("pdbbind_pl").status == "partial"
    assert "P69905" in manifest.join_key_index
    assert "biogrid" in manifest.join_key_index["P69905"]


def test_real_biolip_row_bridges_small_molecule_identity() -> None:
    registry = build_default_local_source_registry(DEFAULT_LOCAL_SOURCE_ROOT)
    source_entry = registry.get("biolip")
    assert source_entry is not None

    biolip_path = DEFAULT_LOCAL_SOURCE_ROOT / "data_sources/biolip/BioLiP_extracted/BioLiP.txt"
    parts = biolip_path.read_text(encoding="utf-8").splitlines()[0].split("\t")

    record = bridge_local_protein_ligand(
        source_name="biolip",
        source_record_id=f"{parts[0]}:{parts[3]}",
        pdb_id=parts[0],
        protein_accessions=(parts[17],),
        protein_chain_ids=(parts[1],),
        ligand_id=parts[4],
        ligand_role="small_molecule",
        source_entry=source_entry,
    )

    assert record.status == "resolved"
    assert record.protein_canonical_ids == ("protein:P02185",)
    assert record.ligands[0].canonical_id == "ligand:HEM"
    assert record.issues == ()


def test_real_rcsb_pair_payload_bridges_resolved_pair_identity() -> None:
    registry = build_default_local_source_registry(DEFAULT_LOCAL_SOURCE_ROOT)
    source_entry = registry.get("pdbbind_pp")
    assert source_entry is not None

    raw_path = DEFAULT_LOCAL_SOURCE_ROOT / "data/raw/rcsb/1FC2.json"
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    chain_accessions: dict[str, str] = {}
    for entity in payload["polymer_entities"]:
        identifiers = entity["rcsb_polymer_entity_container_identifiers"]
        accession = identifiers["uniprot_ids"][0]
        for chain_id in identifiers["auth_asym_ids"]:
            chain_accessions[chain_id] = accession

    record = bridge_local_protein_pair(
        source_name="pdbbind_pp",
        source_record_id="1fc2",
        pdb_id="1FC2",
        receptor_accessions=(chain_accessions["C"],),
        partner_accessions=(chain_accessions["D"],),
        receptor_chain_ids=("C",),
        partner_chain_ids=("D",),
        source_entry=source_entry,
    )

    assert record.status == "resolved"
    assert record.pair_canonical_id == canonical_pair_id(("P38507", "P01857"))
    assert record.protein_canonical_ids == ("protein:P38507", "protein:P01857")
    assert record.provenance["source_name"] == "pdbbind_pp"
    assert record.provenance["status"] == "present"


def test_real_processed_ppi_candidate_stays_unresolved_without_role_specific_accessions() -> None:
    processed_path = DEFAULT_LOCAL_SOURCE_ROOT / "data/processed/rcsb/1FC2.json"
    payload = json.loads(processed_path.read_text(encoding="utf-8"))

    record = bridge_local_record(
        payload,
        source_name="processed_rcsb",
        source_kind="protein_protein",
    )

    assert record.status == "unresolved"
    issue_codes = {issue.code for issue in record.issues}
    assert "missing_receptor_accession" in issue_codes
    assert "missing_partner_accession" in issue_codes
