from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

from execution.acquire.local_ligand_gap_probe import probe_local_ligand_gap_candidates


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_gzip_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)


def _build_local_registry_summary() -> dict[str, object]:
    return {
        "imported_sources": [
            {"source_name": "alphafold_db", "status": "present"},
            {"source_name": "bindingdb", "status": "present"},
            {"source_name": "extracted_entry", "status": "present"},
            {"source_name": "extracted_bound_objects", "status": "present"},
            {"source_name": "uniprot", "status": "partial"},
        ]
    }


def test_probe_local_ligand_gap_candidates_classifies_live_paths_honestly(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    raw_root = tmp_path / "repo" / "data" / "raw"

    master_path = storage_root / "master_pdb_repository.csv"
    structure_root = storage_root / "data" / "structures" / "rcsb"
    entry_root = storage_root / "data" / "extracted" / "entry"
    bound_root = storage_root / "data" / "extracted" / "bound_objects"
    for root in (structure_root, entry_root, bound_root):
        root.mkdir(parents=True, exist_ok=True)

    master_path.parent.mkdir(parents=True, exist_ok=True)
    with master_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "pdb_id",
                "category",
                "protein_chain_uniprot_ids",
                "structure_file_cif_path",
                "raw_file_path",
                "resolution",
            ),
        )
        writer.writeheader()
        writer.writerow(
            {
                "pdb_id": "1Y01",
                "category": "protein_ligand",
                "protein_chain_uniprot_ids": "P69905;Q9NZD4",
                "structure_file_cif_path": str(structure_root / "1Y01.cif"),
                "raw_file_path": "data/raw/rcsb/1Y01.json",
                "resolution": "2.8",
            }
        )

    (structure_root / "1Y01.cif").write_text("data", encoding="utf-8")
    _write_json(entry_root / "1Y01.json", {})
    _write_json(bound_root / "1Y01.json", {})

    _write_gzip_text(
        (
            raw_root
            / "alphafold_local"
            / "20260323T160000Z"
            / "P09105"
            / "AF-P09105-F1-model_v6.pdb.gz"
        ),
        "MODEL",
    )
    _write_gzip_text(
        (
            raw_root
            / "alphafold_local"
            / "20260323T160000Z"
            / "Q2TAC2"
            / "AF-Q2TAC2-F1-model_v6.pdb.gz"
        ),
        "MODEL",
    )
    _write_json(
        raw_root / "alphafold" / "20260323T182231Z" / "P09105" / "P09105.prediction.json",
        [
            {
                "entryId": "AF-P09105-F1",
                "modelEntityId": "AF-P09105-F1",
                "uniprotAccession": "P09105",
            }
        ],
    )
    _write_json(
        raw_root / "alphafold" / "20260323T182231Z" / "Q2TAC2" / "Q2TAC2.prediction.json",
        [
            {
                "entryId": "AF-Q2TAC2-F1",
                "modelEntityId": "AF-Q2TAC2-F1",
                "uniprotAccession": "Q2TAC2",
            }
        ],
    )
    _write_json(
        raw_root / "bindingdb" / "20260323T182231Z" / "Q9UCM0" / "Q9UCM0.bindingdb.json",
        [],
    )
    _write_json(
        raw_root / "rcsb_pdbe" / "20260323T182231Z" / "Q9UCM0" / "Q9UCM0.best_structures.json",
        [],
    )
    _write_json(
        raw_root / "intact" / "20260323T182231Z" / "Q9UCM0" / "Q9UCM0.interactor.json",
        {"content": [{"interactorPreferredIdentifier": "Q9UCM0"}], "totalElements": 1},
    )
    _write_json(
        raw_root / "uniprot" / "20260323T182231Z" / "Q9UCM0" / "Q9UCM0.json",
        {"accession": "Q9UCM0"},
    )

    payload = probe_local_ligand_gap_candidates(
        accessions=("P09105", "Q2TAC2", "Q9NZD4", "Q9UCM0"),
        local_registry_summary=_build_local_registry_summary(),
        storage_root=storage_root,
        raw_root=raw_root,
        master_pdb_repository_path=master_path,
    )

    assert payload["entry_count"] == 4
    assert payload["classification_counts"] == {
        "rescuable_now": 1,
        "requires_extraction": 2,
        "not_found": 1,
    }
    assert payload["registry_source_count"] == 5

    entries = {entry["accession"]: entry for entry in payload["entries"]}
    assert entries["Q9NZD4"]["classification"] == "rescuable_now"
    assert entries["Q9NZD4"]["best_next_source"].endswith("1Y01.cif")
    assert "1Y01" in entries["Q9NZD4"]["best_next_action"]
    assert entries["P09105"]["classification"] == "requires_extraction"
    assert entries["P09105"]["best_next_source"].endswith("AF-P09105-F1-model_v6.pdb.gz")
    assert entries["Q2TAC2"]["classification"] == "requires_extraction"
    assert entries["Q2TAC2"]["best_next_source"].endswith("AF-Q2TAC2-F1-model_v6.pdb.gz")
    assert entries["Q9UCM0"]["classification"] == "not_found"
    assert entries["Q9UCM0"]["best_next_source"] == ""
    assert entries["Q9UCM0"]["best_next_action"].startswith("Fresh acquisition required")

    assert entries["Q9UCM0"]["evidence"]["bindingdb_raw"]["state"] == "empty"
    assert entries["Q9UCM0"]["evidence"]["rcsb_pdbe_raw"]["state"] == "empty"
    assert entries["Q9UCM0"]["evidence"]["secondary_context"]["intact_interactor_count"] == 1
