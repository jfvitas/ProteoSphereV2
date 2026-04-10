from __future__ import annotations

import csv
from pathlib import Path

from execution.acquire.local_gap_probe import probe_local_gap_candidates


def test_probe_local_gap_candidates_distinguishes_exact_and_weak_hints(tmp_path: Path) -> None:
    exact_root = tmp_path / "bindingdb"
    exact_root.mkdir(parents=True, exist_ok=True)
    (exact_root / "P69905_binding.json").write_text("{}", encoding="utf-8")
    weak_root = tmp_path / "ppi"
    weak_root.mkdir(parents=True, exist_ok=True)
    (weak_root / "random.txt").write_text("x", encoding="utf-8")

    dashboard = {
        "source_fix_candidates": [
            {"source_ref": "ligand:P69905"},
            {"source_ref": "ppi:P04637"},
        ]
    }
    local_registry = {
        "imported_sources": [
            {
                "source_name": "bindingdb",
                "category": "protein_ligand",
                "status": "present",
                "inventory_path": "inventory-bindingdb.json",
                "manifest_path": "manifest-bindingdb.json",
                "join_keys": [],
                "present_root_summaries": [{"path": str(exact_root)}],
            },
            {
                "source_name": "pdbbind_pp",
                "category": "protein_protein",
                "status": "present",
                "inventory_path": "inventory-pdbbind.json",
                "manifest_path": "manifest-pdbbind.json",
                "join_keys": ["P04637"],
                "present_root_summaries": [{"path": str(weak_root)}],
            },
        ]
    }

    payload = probe_local_gap_candidates(
        packet_deficit_dashboard=dashboard,
        local_registry_summary=local_registry,
    )

    assert payload["candidate_count"] == 2
    assert payload["recovery_candidate_count"] == 1
    candidates = {item["source_ref"]: item for item in payload["candidates"]}
    assert candidates["ligand:P69905"]["evidence_strength"] == "exact_path_hint"
    assert candidates["ligand:P69905"]["recovery_candidate"] is True
    assert candidates["ligand:P69905"]["path_hints"] == [str(exact_root / "P69905_binding.json")]
    assert candidates["ppi:P04637"]["evidence_strength"] == "join_key_hint"
    assert candidates["ppi:P04637"]["recovery_candidate"] is False
    assert candidates["ppi:P04637"]["join_key_hits"] == ["P04637"]


def test_probe_local_gap_candidates_uses_master_repository_for_exact_interface_hints(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    interface_root = storage_root / "data" / "extracted" / "interfaces"
    structure_root = storage_root / "data" / "structures" / "rcsb"
    interface_root.mkdir(parents=True, exist_ok=True)
    structure_root.mkdir(parents=True, exist_ok=True)
    (interface_root / "1SHR.json").write_text("{}", encoding="utf-8")
    (structure_root / "1SHR.cif").write_text("data", encoding="utf-8")

    master_path = storage_root / "master_pdb_repository.csv"
    with master_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "pdb_id",
                "protein_chain_uniprot_ids",
                "structure_file_cif_path",
                "raw_file_path",
                "interface_count",
            ),
        )
        writer.writeheader()
        writer.writerow(
            {
                "pdb_id": "1SHR",
                "protein_chain_uniprot_ids": "P02042;P69905",
                "structure_file_cif_path": str(structure_root / "1SHR.cif"),
                "raw_file_path": "data/raw/rcsb/1SHR.json",
                "interface_count": "1",
            }
        )

    dashboard = {"source_fix_candidates": [{"source_ref": "ppi:P02042"}]}
    local_registry = {
        "storage_root": str(storage_root),
        "imported_sources": [
            {
                "source_name": "extracted_interfaces",
                "category": "protein_protein",
                "status": "present",
                "inventory_path": "inventory-interfaces.json",
                "manifest_path": "manifest-interfaces.json",
                "join_keys": [],
                "present_root_summaries": [{"path": str(interface_root)}],
            }
        ],
    }

    payload = probe_local_gap_candidates(
        packet_deficit_dashboard=dashboard,
        local_registry_summary=local_registry,
        master_pdb_repository_path=master_path,
    )

    assert payload["master_pdb_repository_available"] is True
    candidate = payload["candidates"][0]
    assert candidate["source_ref"] == "ppi:P02042"
    assert candidate["evidence_strength"] == "exact_path_hint"
    assert candidate["recovery_candidate"] is True
    assert candidate["path_hints"] == [str(interface_root / "1SHR.json")]
    assert candidate["master_pdb_ids"] == ["1SHR"]


def test_probe_local_gap_candidates_withholds_ambiguous_master_repository_bridge_hints(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    interface_root = storage_root / "data" / "extracted" / "interfaces"
    interface_root.mkdir(parents=True, exist_ok=True)
    (interface_root / "1SHR.json").write_text("{}", encoding="utf-8")
    (interface_root / "2HHB.json").write_text("{}", encoding="utf-8")

    master_path = storage_root / "master_pdb_repository.csv"
    with master_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "pdb_id",
                "protein_chain_uniprot_ids",
                "structure_file_cif_path",
                "raw_file_path",
                "interface_count",
            ),
        )
        writer.writeheader()
        writer.writerow(
            {
                "pdb_id": "1SHR",
                "protein_chain_uniprot_ids": "P02042;P69905",
                "structure_file_cif_path": "",
                "raw_file_path": "data/raw/rcsb/1SHR.json",
                "interface_count": "1",
            }
        )
        writer.writerow(
            {
                "pdb_id": "2HHB",
                "protein_chain_uniprot_ids": "P02042;P68871",
                "structure_file_cif_path": "",
                "raw_file_path": "data/raw/rcsb/2HHB.json",
                "interface_count": "1",
            }
        )

    dashboard = {"source_fix_candidates": [{"source_ref": "ppi:P02042"}]}
    local_registry = {
        "storage_root": str(storage_root),
        "imported_sources": [
            {
                "source_name": "extracted_interfaces",
                "category": "protein_protein",
                "status": "present",
                "inventory_path": "inventory-interfaces.json",
                "manifest_path": "manifest-interfaces.json",
                "join_keys": [],
                "present_root_summaries": [{"path": str(interface_root)}],
            }
        ],
    }

    payload = probe_local_gap_candidates(
        packet_deficit_dashboard=dashboard,
        local_registry_summary=local_registry,
        master_pdb_repository_path=master_path,
    )

    candidate = payload["candidates"][0]
    assert candidate["source_ref"] == "ppi:P02042"
    assert candidate["evidence_strength"] == "category_only"
    assert candidate["recovery_candidate"] is False
    assert candidate["path_hints"] == []
    assert candidate["master_pdb_ids"] == ["1SHR", "2HHB"]
    assert "fallback was withheld" in candidate["rationale"]
