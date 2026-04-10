from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_ligand_similarity_signature_gate_preview(tmp_path: Path) -> None:
    bundle_manifest = tmp_path / "lightweight_bundle_manifest.json"
    ligand_identity_core = tmp_path / "ligand_identity_core_materialization_preview.json"
    ligand_row_preview = tmp_path / "ligand_row_materialization_preview.json"
    output_json = tmp_path / "ligand_similarity_signature_gate_preview.json"
    output_md = tmp_path / "ligand_similarity_signature_gate_preview.md"

    bundle_manifest.write_text(
        json.dumps({"record_counts": {"ligands": 0}}, indent=2),
        encoding="utf-8",
    )
    ligand_identity_core.write_text(
        json.dumps(
            {
                "row_count": 4,
                "summary": {"grounded_accession_count": 2},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_row_preview.write_text(
        json.dumps({"row_count": 0}, indent=2),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_ligand_similarity_signature_gate_preview.py"),
            "--bundle-manifest",
            str(bundle_manifest),
            "--ligand-identity-core-preview",
            str(ligand_identity_core),
            "--ligand-row-preview",
            str(ligand_row_preview),
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
    assert artifact["status"] == "complete"
    assert artifact["gate_status"] == "blocked_pending_real_ligands"
    assert artifact["identity_core_preview_row_count"] == 4
    assert artifact["identity_core_grounded_accession_count"] == 2
    assert artifact["ligands_materialized"] is False
    assert artifact["next_unlocked_stage"] == "materialize_real_ligand_rows_first"
    assert artifact["truth_boundary"]["ligand_similarity_signatures_materialized"] is False
    assert "Ligand Similarity Signature Gate Preview" in output_md.read_text(
        encoding="utf-8"
    )
