from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_probe_local_packet_gap_candidates_cli(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    dashboard_path = tmp_path / "packet_deficit_dashboard.json"
    local_registry_path = tmp_path / "LATEST.json"
    output_path = tmp_path / "local_packet_gap_candidates.json"
    storage_root = tmp_path / "bio-agent-lab"
    interface_root = storage_root / "data" / "extracted" / "interfaces"
    interface_root.mkdir(parents=True, exist_ok=True)
    (interface_root / "1SHR.json").write_text("{}", encoding="utf-8")
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

    _write_json(
        dashboard_path,
        {"source_fix_candidates": [{"source_ref": "ppi:P02042"}]},
    )
    _write_json(
        local_registry_path,
        {
            "storage_root": str(storage_root),
            "imported_sources": [
                {
                    "source_name": "extracted_interfaces",
                    "category": "protein_protein",
                    "status": "present",
                    "inventory_path": "inventory.json",
                    "manifest_path": "manifest.json",
                    "join_keys": [],
                    "present_root_summaries": [{"path": str(interface_root)}],
                }
            ]
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "probe_local_packet_gap_candidates.py"),
            "--dashboard",
            str(dashboard_path),
            "--local-registry",
            str(local_registry_path),
            "--output",
            str(output_path),
            "--json",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    payload = json.loads(result.stdout)
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == saved
    assert payload["candidate_count"] == 1
    assert payload["recovery_candidate_count"] == 1
    assert payload["master_pdb_repository_path"] == str(master_path)
    assert payload["candidates"][0]["source_ref"] == "ppi:P02042"
    assert payload["candidates"][0]["evidence_strength"] == "exact_path_hint"
    assert payload["candidates"][0]["path_hints"] == [str(interface_root / "1SHR.json")]
    assert payload["candidates"][0]["master_pdb_ids"] == ["1SHR"]
