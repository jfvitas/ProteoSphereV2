from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_materialize_local_bridge_ligand_payloads_cli_reproduces_bridge_only_backfill(
    tmp_path: Path,
) -> None:
    cohort_slice_path = tmp_path / "p15_upgraded_cohort_slice.json"
    bound_object_root = tmp_path / "bound_objects"
    master_repository_path = tmp_path / "master_pdb_repository.csv"
    output_path = tmp_path / "bridge_ligand_payloads.json"

    _write_json(
        cohort_slice_path,
        {
            "rows": [
                {
                    "accession": "P02042",
                    "canonical_id": "protein:P02042",
                    "split": "train",
                    "bridge": {
                        "state": "positive_hit",
                        "bridge_kind": "bridge_only",
                        "pdb_id": "1SHR",
                        "chain_ids": ["A", "B"],
                    },
                },
                {
                    "accession": "P02100",
                    "canonical_id": "protein:P02100",
                    "split": "val",
                    "bridge": {
                        "state": "positive_hit",
                        "bridge_kind": "bridge_only",
                        "pdb_id": "1A9W",
                        "chain_ids": ["A", "C"],
                    },
                },
            ]
        },
    )
    _write_json(
        bound_object_root / "1SHR.json",
        [
            {
                "pdb_id": "1SHR",
                "component_id": "HEM",
                "component_type": "cofactor",
                "component_role": "catalytic_cofactor",
                "chain_ids": ["A", "B"],
            },
            {
                "pdb_id": "1SHR",
                "component_id": "CYN",
                "component_type": "small_molecule",
                "component_role": "primary_binder",
                "chain_ids": ["A", "B"],
            },
        ],
    )
    _write_json(
        bound_object_root / "1A9W.json",
        [
            {
                "pdb_id": "1A9W",
                "component_id": "HEM",
                "component_type": "cofactor",
                "component_role": "catalytic_cofactor",
                "chain_ids": ["A", "C"],
            },
            {
                "pdb_id": "1A9W",
                "component_id": "CMO",
                "component_type": "small_molecule",
                "component_role": "primary_binder",
                "component_inchikey": "UGFAIRIUMAVXCW-UHFFFAOYSA-N",
                "component_smiles": "[C-]#[O+]",
                "chain_ids": ["A", "C"],
            },
        ],
    )
    master_repository_path.write_text(
        "\n".join(
            [
                "pdb_id,protein_chain_uniprot_ids,ligand_types,ligand_component_ids,has_ligand_signal,quality_score",
                "1SHR,P02042,small_molecule,CYN,true,0.90",
                "1A9W,P02100; P69905,cofactor; small_molecule,HEM; CMO,true,0.92",
            ]
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "materialize_local_bridge_ligand_payloads.py"),
            "--cohort-slice",
            str(cohort_slice_path),
            "--bound-object-root",
            str(bound_object_root),
            "--master-repository",
            str(master_repository_path),
            "--accessions",
            "P02042,P02100",
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = _read_json(output_path)
    assert report["entry_count"] == 2
    assert report["resolved_count"] == 2
    assert report["master_repository_path"] == str(master_repository_path)
    by_accession = {entry["accession"]: entry for entry in report["entries"]}
    assert by_accession["P02042"]["selected_ligand"]["component_id"] == "CYN"
    assert by_accession["P02100"]["selected_ligand"]["component_id"] == "CMO"
    assert (
        by_accession["P02100"]["bridge_record"]["ligands"][0]["canonical_id"] == "ligand:CMO"
    )


def test_materialize_local_bridge_ligand_payloads_cli_appends_ready_now_probe_accession(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    cohort_slice_path = tmp_path / "p15_upgraded_cohort_slice.json"
    bound_object_root = storage_root / "data" / "extracted" / "bound_objects"
    master_repository_path = storage_root / "master_pdb_repository.csv"
    gap_probe_path = tmp_path / "local_ligand_gap_probe.json"
    output_path = tmp_path / "bridge_ligand_payloads.real.json"

    _write_json(
        cohort_slice_path,
        {
            "rows": [
                {
                    "accession": "P02042",
                    "canonical_id": "protein:P02042",
                    "split": "train",
                    "bridge": {
                        "state": "positive_hit",
                        "bridge_kind": "bridge_only",
                        "pdb_id": "1SHR",
                        "chain_ids": ["A", "B"],
                    },
                },
                {
                    "accession": "P02100",
                    "canonical_id": "protein:P02100",
                    "split": "val",
                    "bridge": {
                        "state": "positive_hit",
                        "bridge_kind": "bridge_only",
                        "pdb_id": "1A9W",
                        "chain_ids": ["A", "C"],
                    },
                },
            ]
        },
    )
    _write_json(
        bound_object_root / "1SHR.json",
        [
            {
                "pdb_id": "1SHR",
                "component_id": "HEM",
                "component_type": "cofactor",
                "component_role": "catalytic_cofactor",
                "chain_ids": ["A", "B"],
            },
            {
                "pdb_id": "1SHR",
                "component_id": "CYN",
                "component_type": "small_molecule",
                "component_role": "primary_binder",
                "chain_ids": ["A", "B"],
            },
        ],
    )
    _write_json(
        bound_object_root / "1A9W.json",
        [
            {
                "pdb_id": "1A9W",
                "component_id": "HEM",
                "component_type": "cofactor",
                "component_role": "catalytic_cofactor",
                "chain_ids": ["A", "C"],
            },
            {
                "pdb_id": "1A9W",
                "component_id": "CMO",
                "component_type": "small_molecule",
                "component_role": "primary_binder",
                "component_inchikey": "UGFAIRIUMAVXCW-UHFFFAOYSA-N",
                "component_smiles": "[C-]#[O+]",
                "chain_ids": ["A", "C"],
            },
        ],
    )
    _write_json(
        bound_object_root / "1Y01.json",
        [
            {
                "pdb_id": "1Y01",
                "component_id": "HEM",
                "component_type": "cofactor",
                "component_role": "catalytic_cofactor",
                "chain_ids": ["B"],
            },
            {
                "pdb_id": "1Y01",
                "component_id": "CHK",
                "component_type": "small_molecule",
                "component_role": "primary_binder",
                "component_smiles": "CCO",
                "component_inchikey": "TEST-INCHI",
                "chain_ids": ["B"],
            },
        ],
    )
    master_repository_path.write_text(
        "\n".join(
            [
                (
                    "pdb_id,protein_chain_uniprot_ids,ligand_types,ligand_component_ids,"
                    "has_ligand_signal,quality_score,raw_file_path"
                ),
                "1SHR,P02042,small_molecule,CYN,true,0.90,data/raw/rcsb/1SHR.json",
                (
                    "1A9W,P02100; P69905,cofactor; small_molecule,"
                    "HEM; CMO,true,0.92,data/raw/rcsb/1A9W.json"
                ),
                (
                    "1Y01,P69905; Q9NZD4,cofactor; small_molecule,"
                    "HEM; CHK,true,0.95,data/raw/rcsb/1Y01.json"
                ),
            ]
        ),
        encoding="utf-8",
    )
    _write_json(
        gap_probe_path,
        {
            "entries": [
                {
                    "accession": "Q9NZD4",
                    "classification": "rescuable_now",
                    "best_next_source": str(
                        storage_root / "data" / "structures" / "rcsb" / "1Y01.cif"
                    ),
                    "best_next_action": "Ingest the local structure bridge for Q9NZD4 using 1Y01",
                    "evidence": {
                        "structure_bridge": {
                            "best_pdb_id": "1Y01",
                            "best_source_path": str(
                                storage_root / "data" / "structures" / "rcsb" / "1Y01.cif"
                            ),
                            "concrete_paths": [
                                str(storage_root / "data" / "structures" / "rcsb" / "1Y01.cif")
                            ],
                            "matched_pdb_ids": ["1Y01"],
                            "rows": [
                                {
                                    "pdb_id": "1Y01",
                                    "protein_chain_uniprot_ids": "P69905; Q9NZD4",
                                }
                            ],
                            "state": "ready_now",
                        }
                    },
                }
            ]
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "materialize_local_bridge_ligand_payloads.py"),
            "--cohort-slice",
            str(cohort_slice_path),
            "--gap-probe",
            str(gap_probe_path),
            "--bound-object-root",
            str(bound_object_root),
            "--master-repository",
            str(master_repository_path),
            "--accessions",
            "Q9NZD4",
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = _read_json(output_path)
    assert report["entry_count"] == 3
    assert report["resolved_count"] == 3
    assert report["synthetic_accessions"] == ["Q9NZD4"]
    by_accession = {entry["accession"]: entry for entry in report["entries"]}
    assert by_accession["Q9NZD4"]["bridge_state"] == "ready_now"
    assert by_accession["Q9NZD4"]["selected_ligand"]["component_id"] == "CHK"
    assert by_accession["Q9NZD4"]["bridge_record"]["source_record_id"] == "Q9NZD4:1Y01:CHK"


def test_materialize_local_bridge_ligand_payloads_cli_upgrades_existing_cohort_bridge_from_probe(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    cohort_slice_path = tmp_path / "p15_upgraded_cohort_slice.json"
    bound_object_root = storage_root / "data" / "extracted" / "bound_objects"
    master_repository_path = storage_root / "master_pdb_repository.csv"
    gap_probe_path = tmp_path / "local_ligand_gap_probe.json"
    output_path = tmp_path / "bridge_ligand_payloads.real.json"

    _write_json(
        cohort_slice_path,
        {
            "rows": [
                {
                    "accession": "Q9NZD4",
                    "canonical_id": "protein:Q9NZD4",
                    "split": "train",
                    "bridge": {
                        "state": "positive_hit",
                        "bridge_kind": "bridge_only",
                        "pdb_id": "1Z8U",
                        "chain_ids": ["A", "C", "B", "D"],
                    },
                }
            ]
        },
    )
    _write_json(
        bound_object_root / "1Z8U.json",
        [
            {
                "pdb_id": "1Z8U",
                "component_id": "HEM",
                "component_type": "cofactor",
                "component_role": "catalytic_cofactor",
                "chain_ids": ["B", "D"],
            }
        ],
    )
    _write_json(
        bound_object_root / "1Y01.json",
        [
            {
                "pdb_id": "1Y01",
                "component_id": "HEM",
                "component_type": "cofactor",
                "component_role": "catalytic_cofactor",
                "chain_ids": ["B"],
            },
            {
                "pdb_id": "1Y01",
                "component_id": "CHK",
                "component_type": "small_molecule",
                "component_role": "primary_binder",
                "component_smiles": "CCO",
                "component_inchikey": "TEST-INCHI",
                "chain_ids": ["B"],
            },
        ],
    )
    master_repository_path.write_text(
        "\n".join(
            [
                (
                    "pdb_id,protein_chain_uniprot_ids,ligand_types,ligand_component_ids,"
                    "has_ligand_signal,quality_score,raw_file_path"
                ),
                (
                    "1Y01,P69905; Q9NZD4,cofactor; small_molecule,"
                    "HEM; CHK,true,0.95,data/raw/rcsb/1Y01.json"
                ),
            ]
        ),
        encoding="utf-8",
    )
    _write_json(
        gap_probe_path,
        {
            "entries": [
                {
                    "accession": "Q9NZD4",
                    "classification": "rescuable_now",
                    "evidence": {
                        "structure_bridge": {
                            "best_pdb_id": "1Y01",
                            "matched_pdb_ids": ["1Y01"],
                            "state": "ready_now",
                        }
                    },
                }
            ]
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "materialize_local_bridge_ligand_payloads.py"),
            "--cohort-slice",
            str(cohort_slice_path),
            "--gap-probe",
            str(gap_probe_path),
            "--bound-object-root",
            str(bound_object_root),
            "--master-repository",
            str(master_repository_path),
            "--accessions",
            "Q9NZD4",
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = _read_json(output_path)
    assert report["entry_count"] == 1
    assert report["resolved_count"] == 1
    assert report["synthetic_accessions"] == []
    assert report["upgraded_accessions"] == ["Q9NZD4"]
    entry = report["entries"][0]
    assert entry["accession"] == "Q9NZD4"
    assert entry["pdb_id"] == "1Y01"
    assert entry["bridge_state"] == "ready_now"
    assert entry["selected_ligand"]["component_id"] == "CHK"
