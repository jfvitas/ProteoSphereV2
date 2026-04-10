from __future__ import annotations

import csv
import json
from pathlib import Path

from execution.materialization.local_bridge_ppi_backfill import (
    build_local_bridge_ppi_backfill_entry,
    materialize_selected_cohort_bridge_ppi_entries,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_build_local_bridge_ppi_backfill_entry_resolves_pair_without_asserting_chains(
    tmp_path: Path,
) -> None:
    interface_root = tmp_path / "data" / "extracted" / "interfaces"
    structure_root = tmp_path / "data" / "structures" / "rcsb"
    row = {
        "pdb_id": "1GZH",
        "protein_chain_ids": "A; B; C; D",
        "protein_chain_uniprot_ids": "P04637; Q12888",
        "interface_count": 3,
        "interface_types": "protein_protein",
        "structure_file_cif_path": str(structure_root / "1GZH.cif"),
    }
    _write_json(
        interface_root / "1GZH.json",
        [
            {
                "pdb_id": "1GZH",
                "interface_type": "protein_protein",
                "partner_a_chain_ids": ["A"],
                "partner_b_chain_ids": ["B", "D"],
                "entity_id_a": "1GZH_1",
                "entity_id_b": "1GZH_2",
                "interface_is_symmetric": False,
                "is_hetero": True,
            }
        ],
    )
    (structure_root / "1GZH.cif").parent.mkdir(parents=True, exist_ok=True)
    (structure_root / "1GZH.cif").write_text("data_1GZH", encoding="utf-8")

    entry = build_local_bridge_ppi_backfill_entry(
        row,
        interface_root=interface_root,
        structure_root=structure_root,
    )

    assert entry.status == "resolved"
    assert entry.bridge_state == "positive_hit"
    assert entry.accession_a == "P04637"
    assert entry.accession_b == "Q12888"
    assert entry.bridge_record is not None
    assert entry.bridge_record.status == "resolved"
    assert entry.bridge_record.protein_canonical_ids == (
        "protein:P04637",
        "protein:Q12888",
    )
    assert entry.chain_assignment_state == "not_asserted"
    assert entry.pair_canonical_id == "pair:P04637--Q12888"
    assert "chain_assignment_not_asserted_from_local_files" in entry.notes


def test_build_local_bridge_ppi_backfill_entry_keeps_ambiguous_pair_unresolved(
    tmp_path: Path,
) -> None:
    interface_root = tmp_path / "data" / "extracted" / "interfaces"
    structure_root = tmp_path / "data" / "structures" / "rcsb"
    row = {
        "pdb_id": "4XR8",
        "protein_chain_ids": "A; B; C; D; F; H",
        "protein_chain_uniprot_ids": "P03126; P04637; P0AEX9",
        "interface_count": 3,
        "interface_types": "protein_protein",
        "structure_file_cif_path": str(structure_root / "4XR8.cif"),
    }
    _write_json(
        interface_root / "4XR8.json",
        [
            {
                "pdb_id": "4XR8",
                "interface_type": "protein_protein",
                "partner_a_chain_ids": ["A", "B"],
                "partner_b_chain_ids": ["C", "D"],
                "entity_id_a": "4XR8_1",
                "entity_id_b": "4XR8_2",
                "interface_is_symmetric": False,
                "is_hetero": True,
            }
        ],
    )
    (structure_root / "4XR8.cif").parent.mkdir(parents=True, exist_ok=True)
    (structure_root / "4XR8.cif").write_text("data_4XR8", encoding="utf-8")

    entry = build_local_bridge_ppi_backfill_entry(
        row,
        interface_root=interface_root,
        structure_root=structure_root,
    )

    assert entry.status == "unresolved"
    assert entry.bridge_state == "reachable_empty"
    assert entry.chain_assignment_state == "ambiguous"
    assert "ambiguous_pair_accessions" in entry.issues
    assert entry.bridge_record is None


def test_materialize_selected_cohort_bridge_ppi_entries_filters_by_accession(
    tmp_path: Path,
) -> None:
    master_repository = tmp_path / "master_pdb_repository.csv"
    interface_root = tmp_path / "data" / "extracted" / "interfaces"
    structure_root = tmp_path / "data" / "structures" / "rcsb"
    _write_csv(
        master_repository,
        [
            {
                "pdb_id": "1GZH",
                "protein_chain_ids": "A; B; C; D",
                "protein_chain_uniprot_ids": "P04637; Q12888",
                "interface_count": 3,
                "interface_types": "protein_protein",
                "structure_file_cif_path": str(structure_root / "1GZH.cif"),
            },
            {
                "pdb_id": "4QO1",
                "protein_chain_ids": "A; B",
                "protein_chain_uniprot_ids": "P04637",
                "interface_count": 1,
                "interface_types": "protein_protein",
                "structure_file_cif_path": str(structure_root / "4QO1.cif"),
            },
        ],
    )
    _write_json(
        interface_root / "1GZH.json",
        [
            {
                "pdb_id": "1GZH",
                "interface_type": "protein_protein",
                "partner_a_chain_ids": ["A"],
                "partner_b_chain_ids": ["B", "D"],
                "entity_id_a": "1GZH_1",
                "entity_id_b": "1GZH_2",
            }
        ],
    )
    _write_json(interface_root / "4QO1.json", [])
    (structure_root / "1GZH.cif").parent.mkdir(parents=True, exist_ok=True)
    (structure_root / "1GZH.cif").write_text("data_1GZH", encoding="utf-8")
    (structure_root / "4QO1.cif").write_text("data_4QO1", encoding="utf-8")

    entries = materialize_selected_cohort_bridge_ppi_entries(
        (),
        master_repository_path=master_repository,
        interface_root=interface_root,
        structure_root=structure_root,
        selected_accessions=("P04637",),
    )

    assert len(entries) == 2
    resolved = next(entry for entry in entries if entry.pdb_id == "1GZH")
    unresolved = next(entry for entry in entries if entry.pdb_id == "4QO1")
    assert resolved.status == "resolved"
    assert unresolved.status == "unresolved"
