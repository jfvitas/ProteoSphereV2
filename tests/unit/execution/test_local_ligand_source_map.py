from __future__ import annotations

import csv
import gzip
import json
import sqlite3
from pathlib import Path

from execution.acquire.local_ligand_source_map import build_local_ligand_source_map


def _write_master(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("pdb_id", "protein_chain_uniprot_ids"),
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_chembl(
    path: Path,
    accession: str,
    chembl_id: str,
    pref_name: str,
    activity_count: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            create table component_sequences (component_id integer, accession text);
            create table target_components (component_id integer, tid integer);
            create table target_dictionary (tid integer, chembl_id text, pref_name text);
            create table assays (assay_id integer, tid integer);
            create table activities (activity_id integer, assay_id integer);
            """
        )
        cur.execute("insert into component_sequences values (1, ?)", (accession,))
        cur.execute("insert into target_components values (1, 11)")
        cur.execute("insert into target_dictionary values (11, ?, ?)", (chembl_id, pref_name))
        cur.execute("insert into assays values (101, 11)")
        for idx in range(activity_count):
            cur.execute("insert into activities values (?, 101)", (idx + 1,))
        conn.commit()
    finally:
        conn.close()


def _write_bindingdb_index(path: Path, accession: str, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.execute("create table bindingdb_bulk_rows (uniprot_accession text)")
        for _ in range(count):
            cur.execute("insert into bindingdb_bulk_rows values (?)", (accession,))
        conn.commit()
    finally:
        conn.close()


def _write_bindingdb_index_real_schema(path: Path, accession: str, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            create table bindingdb_bulk_rows (
                target_unpid1 text,
                target_unpid2 text
            );
            create table polymer_rows (
                unpid1 text,
                unpid2 text
            );
            """
        )
        for _ in range(count):
            cur.execute("insert into bindingdb_bulk_rows values (?, ?)", (accession, ""))
        cur.execute("insert into polymer_rows values (?, ?)", (accession, ""))
        conn.commit()
    finally:
        conn.close()


def _write_alphafold_index(path: Path, accession: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "accession": accession,
                    "entry_id": f"AF-{accession}-F1-model_v6",
                    "member_name": f"AF-{accession}-F1-model_v6.pdb.gz",
                    "model_version": "v6",
                    "size_bytes": 1234,
                }
            )
            + "\n"
        )


def test_build_local_ligand_source_map_prioritizes_actionable_structure_bridge(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    master_path = storage_root / "master_pdb_repository.csv"
    biolip_path = storage_root / "data_sources" / "biolip" / "BioLiP.txt"
    chembl_path = storage_root / "data_sources" / "chembl" / "chembl.db"
    bindingdb_index_path = storage_root / "metadata" / "source_indexes" / "bindingdb.sqlite"
    alphafold_index_path = storage_root / "metadata" / "source_indexes" / "alphafold.jsonl.gz"

    _write_master(
        master_path,
        [{"pdb_id": "1Y01", "protein_chain_uniprot_ids": "P69905;Q9NZD4"}],
    )
    (storage_root / "data" / "raw" / "rcsb").mkdir(parents=True, exist_ok=True)
    (storage_root / "data" / "structures" / "rcsb").mkdir(parents=True, exist_ok=True)
    (storage_root / "data" / "extracted" / "entry").mkdir(parents=True, exist_ok=True)
    (storage_root / "data" / "extracted" / "bound_objects").mkdir(parents=True, exist_ok=True)
    (storage_root / "data" / "raw" / "rcsb" / "1Y01.json").write_text("{}", encoding="utf-8")
    (storage_root / "data" / "structures" / "rcsb" / "1Y01.cif").write_text(
        "data",
        encoding="utf-8",
    )
    (storage_root / "data" / "extracted" / "entry" / "1Y01.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (storage_root / "data" / "raw" / "rcsb" / "1Y01.json").write_text(
        json.dumps(
            {
                "polymer_entities": [
                    {
                        "rcsb_polymer_entity_container_identifiers": {
                            "auth_asym_ids": ["A"],
                            "uniprot_ids": ["Q9NZD4"],
                        }
                    },
                    {
                        "rcsb_polymer_entity_container_identifiers": {
                            "auth_asym_ids": ["B"],
                            "uniprot_ids": ["P69905"],
                        }
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (storage_root / "data" / "extracted" / "bound_objects" / "1Y01.json").write_text(
        json.dumps(
            [
                {
                    "pdb_id": "1Y01",
                    "component_id": "CHK",
                    "component_type": "small_molecule",
                    "component_role": "primary_binder",
                    "chain_ids": ["A"],
                }
            ]
        ),
        encoding="utf-8",
    )
    biolip_path.parent.mkdir(parents=True, exist_ok=True)
    biolip_path.write_text("", encoding="utf-8")
    _write_chembl(chembl_path, "Q9NZD4", "CHEMBL999", "Test target", 3)
    _write_bindingdb_index(bindingdb_index_path, "Q9NZD4", 2)
    _write_alphafold_index(alphafold_index_path, "Q9NZD4")

    payload = build_local_ligand_source_map(
        accessions=("Q9NZD4",),
        storage_root=storage_root,
        master_pdb_repository_path=master_path,
        biolip_path=biolip_path,
        chembl_path=chembl_path,
        bindingdb_index_path=bindingdb_index_path,
        alphafold_index_path=alphafold_index_path,
    )

    entry = payload["entries"][0]
    assert entry["classification"] == "structure_bridge_actionable"
    assert entry["recommended_next_action"] == "ingest_local_structure_bridge"
    assert entry["master_repository_pdb_ids"] == ["1Y01"]
    assert entry["structure_rows"][0]["actionable_structure_bridge"] is True
    assert entry["structure_rows"][0]["target_chain_ids"] == ["A"]
    assert entry["structure_rows"][0]["chain_truthful_small_molecule"] is True


def test_build_local_ligand_source_map_demotes_companion_chain_only_structure_bridge(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    master_path = storage_root / "master_pdb_repository.csv"
    biolip_path = storage_root / "data_sources" / "biolip" / "BioLiP.txt"
    chembl_path = storage_root / "data_sources" / "chembl" / "chembl.db"
    bindingdb_index_path = storage_root / "metadata" / "source_indexes" / "bindingdb.sqlite"
    alphafold_index_path = storage_root / "metadata" / "source_indexes" / "alphafold.jsonl.gz"

    _write_master(
        master_path,
        [{"pdb_id": "1Y01", "protein_chain_uniprot_ids": "P69905;Q9NZD4"}],
    )
    (storage_root / "data" / "raw" / "rcsb").mkdir(parents=True, exist_ok=True)
    (storage_root / "data" / "structures" / "rcsb").mkdir(parents=True, exist_ok=True)
    (storage_root / "data" / "extracted" / "entry").mkdir(parents=True, exist_ok=True)
    (storage_root / "data" / "extracted" / "bound_objects").mkdir(parents=True, exist_ok=True)
    (storage_root / "data" / "raw" / "rcsb" / "1Y01.json").write_text(
        json.dumps(
            {
                "polymer_entities": [
                    {
                        "rcsb_polymer_entity_container_identifiers": {
                            "auth_asym_ids": ["A"],
                            "uniprot_ids": ["Q9NZD4"],
                        }
                    },
                    {
                        "rcsb_polymer_entity_container_identifiers": {
                            "auth_asym_ids": ["B"],
                            "uniprot_ids": ["P69905"],
                        }
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (storage_root / "data" / "structures" / "rcsb" / "1Y01.cif").write_text(
        "data",
        encoding="utf-8",
    )
    (storage_root / "data" / "extracted" / "entry" / "1Y01.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (storage_root / "data" / "extracted" / "bound_objects" / "1Y01.json").write_text(
        json.dumps(
            [
                {
                    "pdb_id": "1Y01",
                    "component_id": "CHK",
                    "component_type": "small_molecule",
                    "component_role": "primary_binder",
                    "chain_ids": ["B"],
                }
            ]
        ),
        encoding="utf-8",
    )
    biolip_path.parent.mkdir(parents=True, exist_ok=True)
    biolip_path.write_text("", encoding="utf-8")
    _write_bindingdb_index(bindingdb_index_path, "OTHER", 1)
    _write_alphafold_index(alphafold_index_path, "Q9NZD4")
    chembl_path.parent.mkdir(parents=True, exist_ok=True)
    sqlite3.connect(str(chembl_path)).close()

    payload = build_local_ligand_source_map(
        accessions=("Q9NZD4",),
        storage_root=storage_root,
        master_pdb_repository_path=master_path,
        biolip_path=biolip_path,
        chembl_path=chembl_path,
        bindingdb_index_path=bindingdb_index_path,
        alphafold_index_path=alphafold_index_path,
    )

    entry = payload["entries"][0]
    assert entry["classification"] == "structure_bridge_backfill_needed"
    assert entry["recommended_next_action"] == "backfill_local_structure_bridge"
    assert entry["structure_rows"][0]["actionable_structure_bridge"] is False
    assert entry["structure_rows"][0]["chain_truthful_small_molecule"] is False
    assert entry["structure_rows"][0]["target_chain_ids"] == ["A"]
    assert entry["structure_rows"][0]["chain_truthful_ligand_issue_codes"] == [
        "no_primary_small_molecule_on_target_chains"
    ]


def test_build_local_ligand_source_map_falls_back_to_bulk_assay_when_structure_missing(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    master_path = storage_root / "master_pdb_repository.csv"
    biolip_path = storage_root / "data_sources" / "biolip" / "BioLiP.txt"
    chembl_path = storage_root / "data_sources" / "chembl" / "chembl.db"
    bindingdb_index_path = storage_root / "metadata" / "source_indexes" / "bindingdb.sqlite"
    alphafold_index_path = storage_root / "metadata" / "source_indexes" / "alphafold.jsonl.gz"

    _write_master(master_path, [])
    biolip_path.parent.mkdir(parents=True, exist_ok=True)
    biolip_path.write_text(
        "1umk\tA\t1.75\tBS01\tFAD\tA\t1\tres\tres\t\t\t1.6.2.2\t\t\t\tP00387\t\n",
        encoding="utf-8",
    )
    _write_chembl(
        chembl_path,
        "P00387",
        "CHEMBL2146",
        "NADH-cytochrome b5 reductase",
        93,
    )
    _write_bindingdb_index(bindingdb_index_path, "OTHER", 1)
    _write_alphafold_index(alphafold_index_path, "P00387")

    payload = build_local_ligand_source_map(
        accessions=("P00387",),
        storage_root=storage_root,
        master_pdb_repository_path=master_path,
        biolip_path=biolip_path,
        chembl_path=chembl_path,
        bindingdb_index_path=bindingdb_index_path,
        alphafold_index_path=alphafold_index_path,
    )

    entry = payload["entries"][0]
    assert entry["classification"] == "bulk_assay_actionable"
    assert entry["recommended_next_action"] == "extract_local_bulk_assay_first"
    assert entry["biolip_pdb_ids"] == ["1UMK"]
    assert entry["chembl_hits"][0]["chembl_id"] == "CHEMBL2146"
    assert entry["structure_rows"][0]["actionable_structure_bridge"] is False


def test_build_local_ligand_source_map_marks_true_local_gap(tmp_path: Path) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    master_path = storage_root / "master_pdb_repository.csv"
    biolip_path = storage_root / "data_sources" / "biolip" / "BioLiP.txt"
    chembl_path = storage_root / "data_sources" / "chembl" / "chembl.db"
    bindingdb_index_path = storage_root / "metadata" / "source_indexes" / "bindingdb.sqlite"
    alphafold_index_path = storage_root / "metadata" / "source_indexes" / "alphafold.jsonl.gz"

    _write_master(master_path, [])
    biolip_path.parent.mkdir(parents=True, exist_ok=True)
    biolip_path.write_text("", encoding="utf-8")
    _write_bindingdb_index(bindingdb_index_path, "OTHER", 1)
    _write_alphafold_index(alphafold_index_path, "OTHER")
    chembl_path.parent.mkdir(parents=True, exist_ok=True)
    sqlite3.connect(str(chembl_path)).close()

    payload = build_local_ligand_source_map(
        accessions=("Q9UCM0",),
        storage_root=storage_root,
        master_pdb_repository_path=master_path,
        biolip_path=biolip_path,
        chembl_path=chembl_path,
        bindingdb_index_path=bindingdb_index_path,
        alphafold_index_path=alphafold_index_path,
    )

    entry = payload["entries"][0]
    assert entry["classification"] == "no_local_candidate"
    assert entry["recommended_next_action"] == "fresh_acquisition_required"
    assert entry["master_repository_pdb_ids"] == []
    assert entry["chembl_hits"] == []
    assert entry["bindingdb_hits"] == []
    assert entry["alphafold_hits"] == []


def test_build_local_ligand_source_map_detects_real_bindingdb_unpid_columns(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    master_path = storage_root / "master_pdb_repository.csv"
    biolip_path = storage_root / "data_sources" / "biolip" / "BioLiP.txt"
    chembl_path = storage_root / "data_sources" / "chembl" / "chembl.db"
    bindingdb_index_path = storage_root / "metadata" / "source_indexes" / "bindingdb.sqlite"
    alphafold_index_path = storage_root / "metadata" / "source_indexes" / "alphafold.jsonl.gz"

    _write_master(master_path, [])
    biolip_path.parent.mkdir(parents=True, exist_ok=True)
    biolip_path.write_text("", encoding="utf-8")
    _write_bindingdb_index_real_schema(bindingdb_index_path, "P31749", 4)
    chembl_path.parent.mkdir(parents=True, exist_ok=True)
    sqlite3.connect(str(chembl_path)).close()
    _write_alphafold_index(alphafold_index_path, "P31749")

    payload = build_local_ligand_source_map(
        accessions=("P31749",),
        storage_root=storage_root,
        master_pdb_repository_path=master_path,
        biolip_path=biolip_path,
        chembl_path=chembl_path,
        bindingdb_index_path=bindingdb_index_path,
        alphafold_index_path=alphafold_index_path,
    )

    entry = payload["entries"][0]
    assert entry["classification"] == "bulk_assay_actionable"
    assert entry["recommended_next_action"] == "ingest_local_bulk_assay"
    assert entry["bindingdb_hits"] == [
        {"table": "bindingdb_bulk_rows", "column": "target_unpid1", "count": 4},
        {"table": "polymer_rows", "column": "unpid1", "count": 1},
    ]
