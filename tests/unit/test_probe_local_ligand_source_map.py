from __future__ import annotations

import gzip
import json
from pathlib import Path

from scripts.probe_local_ligand_source_map import build_local_ligand_source_map_report


def test_build_local_ligand_source_map_report_uses_selected_accessions(tmp_path: Path) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    master_path = storage_root / "master_pdb_repository.csv"
    master_path.parent.mkdir(parents=True, exist_ok=True)
    master_path.write_text(
        "pdb_id,protein_chain_uniprot_ids\n1Y01,P69905;Q9NZD4\n",
        encoding="utf-8",
    )

    biolip_path = storage_root / "data_sources" / "biolip" / "BioLiP.txt"
    biolip_path.parent.mkdir(parents=True, exist_ok=True)
    biolip_path.write_text("", encoding="utf-8")

    chembl_path = storage_root / "data_sources" / "chembl" / "chembl.db"
    chembl_path.parent.mkdir(parents=True, exist_ok=True)
    chembl_path.write_bytes(b"")

    bindingdb_index_path = storage_root / "metadata" / "source_indexes" / "bindingdb.sqlite"
    bindingdb_index_path.parent.mkdir(parents=True, exist_ok=True)
    bindingdb_index_path.write_bytes(b"")

    alphafold_index_path = storage_root / "metadata" / "source_indexes" / "alphafold.jsonl.gz"
    alphafold_index_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(alphafold_index_path, "wt", encoding="utf-8") as handle:
        handle.write("")

    payload = build_local_ligand_source_map_report(
        accessions=("Q9UCM0",),
        storage_root=storage_root,
        master_pdb_repository_path=master_path,
        biolip_path=biolip_path,
        chembl_path=chembl_path,
        bindingdb_index_path=bindingdb_index_path,
        alphafold_index_path=alphafold_index_path,
    )

    assert payload["schema_id"] == "proteosphere-local-ligand-source-map-2026-03-23"
    assert payload["selected_accessions"] == ["Q9UCM0"]
    assert payload["entry_count"] == 1
    assert payload["entries"][0]["accession"] == "Q9UCM0"
    json.dumps(payload)
