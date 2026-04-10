from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_gzip_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)


def _write_local_ligand_gap_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
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
        raw_root / "local_registry_runs" / "LATEST.json",
        {
            "imported_sources": [
                {"source_name": "alphafold_db", "status": "present"},
                {"source_name": "bindingdb", "status": "present"},
                {"source_name": "extracted_entry", "status": "present"},
                {"source_name": "extracted_bound_objects", "status": "present"},
                {"source_name": "uniprot", "status": "partial"},
            ]
        },
    )

    return storage_root, raw_root, master_path


def test_cli_exports_ligand_gap_probe_outputs(tmp_path: Path) -> None:
    storage_root, raw_root, master_path = _write_local_ligand_gap_fixture(tmp_path)
    output_path = tmp_path / "artifacts" / "status" / "local_ligand_gap_probe.json"
    markdown_path = tmp_path / "docs" / "reports" / "local_ligand_gap_probe.md"

    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "scripts\\export_local_ligand_gap_probe.py",
            "--storage-root",
            str(storage_root),
            "--raw-root",
            str(raw_root),
            "--local-registry",
            str(raw_root / "local_registry_runs" / "LATEST.json"),
            "--master-pdb-repository",
            str(master_path),
            "--output",
            str(output_path),
            "--markdown",
            str(markdown_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Local ligand gap probe exported" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["report_type"] == "local_ligand_gap_probe"
    assert payload["classification_counts"] == {
        "rescuable_now": 1,
        "requires_extraction": 2,
        "not_found": 1,
    }
    assert payload["entries"][0]["accession"] == "P09105"
    assert markdown_path.exists()
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# Local Ligand Gap Probe" in markdown
    assert "`Q9NZD4`" in markdown
    assert "`rescuable_now`" in markdown
