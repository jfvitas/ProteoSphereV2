from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_q9nzd4_bridge_validation_preview(tmp_path: Path) -> None:
    bridge_payload = tmp_path / "bridge_payload.json"
    execution_slice = tmp_path / "execution_slice.json"
    output_json = tmp_path / "preview.json"
    output_md = tmp_path / "preview.md"

    bridge_payload.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "accession": "Q9NZD4",
                        "pdb_id": "1Y01",
                        "status": "resolved",
                        "bridge_state": "ready_now",
                        "selected_ligand": {
                            "component_id": "CHK",
                            "component_name": "Cyclitol derivative",
                            "component_role": "primary_binder",
                            "chain_ids": ["B"],
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    execution_slice.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "accession": "Q9NZD4",
                        "classification": "rescuable_now",
                        "best_next_action": (
                            "Ingest the local structure bridge for Q9NZD4 using 1Y01"
                        ),
                        "evidence": {
                            "structure_bridge": {
                                "best_pdb_id": "1Y01",
                                "best_source_path": (
                                    "C:/bio-agent-lab/data/structures/rcsb/1Y01.cif"
                                ),
                                "matched_pdb_ids": ["1Y01", "1Z8U", "3OVU"],
                            }
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_q9nzd4_bridge_validation_preview.py"),
            "--bridge-payload",
            str(bridge_payload),
            "--execution-slice",
            str(execution_slice),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    artifact = json.loads(output_json.read_text(encoding="utf-8"))
    assert artifact["status"] == "aligned"
    assert artifact["accession"] == "Q9NZD4"
    assert artifact["best_pdb_id"] == "1Y01"
    assert artifact["component_id"] == "CHK"
    assert artifact["matched_pdb_id_count"] == 3
    assert artifact["validation_summary"]["ready_for_operator_preview"] is True
    assert artifact["truth_boundary"]["candidate_only"] is True
    assert "Q9NZD4 Bridge Validation Preview" in output_md.read_text(encoding="utf-8")
