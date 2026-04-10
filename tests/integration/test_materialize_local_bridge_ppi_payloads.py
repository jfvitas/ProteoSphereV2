from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_materialize_local_bridge_ppi_payloads_cli_materializes_truthfully(
    tmp_path: Path,
) -> None:
    cohort_slice = tmp_path / "cohort.json"
    master_repository = tmp_path / "master_pdb_repository.csv"
    interface_root = tmp_path / "data" / "extracted" / "interfaces"
    structure_root = tmp_path / "data" / "structures" / "rcsb"
    output_path = tmp_path / "artifacts" / "status" / "local_bridge_ppi_payloads.json"

    _write_json(
        cohort_slice,
        {
            "rows": [
                {"accession": "P04637", "canonical_id": "protein:P04637", "split": "train"},
                {"accession": "Q12888", "canonical_id": "protein:Q12888", "split": "train"},
            ]
        },
    )
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
                "interface_is_symmetric": False,
                "is_hetero": True,
            }
        ],
    )
    _write_json(interface_root / "4QO1.json", [])
    (structure_root / "1GZH.cif").parent.mkdir(parents=True, exist_ok=True)
    (structure_root / "1GZH.cif").write_text("data_1GZH", encoding="utf-8")
    (structure_root / "4QO1.cif").write_text("data_4QO1", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "materialize_local_bridge_ppi_payloads.py"),
            "--cohort-slice",
            str(cohort_slice),
            "--master-repository",
            str(master_repository),
            "--interface-root",
            str(interface_root),
            "--structure-root",
            str(structure_root),
            "--output",
            str(output_path),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = json.loads(completed.stdout)
    saved_report = json.loads(output_path.read_text(encoding="utf-8"))

    assert report == saved_report
    assert report["task_id"] == "local_bridge_ppi_payloads"
    assert report["entry_count"] == 2
    assert report["resolved_count"] == 1
    assert report["unresolved_count"] == 1
    assert report["selected_accessions"] == ["P04637", "Q12888"]
    resolved = next(entry for entry in report["entries"] if entry["pdb_id"] == "1GZH")
    unresolved = next(entry for entry in report["entries"] if entry["pdb_id"] == "4QO1")
    assert resolved["status"] == "resolved"
    assert resolved["bridge_record"]["status"] == "resolved"
    assert unresolved["status"] == "unresolved"
    assert unresolved["issues"] == [
        "missing_partner_accession",
    ]
