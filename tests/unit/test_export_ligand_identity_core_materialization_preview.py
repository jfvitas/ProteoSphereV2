from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_ligand_identity_core_materialization_preview(tmp_path: Path) -> None:
    ligand_identity_pilot = tmp_path / "ligand_identity_pilot_preview.json"
    ligand_support = tmp_path / "ligand_support_readiness_preview.json"
    p00387_validation = tmp_path / "p00387_ligand_extraction_validation_preview.json"
    q9nzd4_validation = tmp_path / "q9nzd4_bridge_validation_preview.json"
    output_json = tmp_path / "ligand_identity_core_materialization_preview.json"
    output_md = tmp_path / "ligand_identity_core_materialization_preview.md"

    ligand_identity_pilot.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "rank": 1,
                        "accession": "P00387",
                        "source_ref": "ligand:P00387",
                        "pilot_role": "lead_anchor",
                        "grounded_evidence_kind": "local_chembl_bulk_assay_summary",
                        "grounded_evidence": {"target_chembl_id": "CHEMBL2146"},
                        "next_truthful_stage": "ingest_local_bulk_assay",
                    },
                    {
                        "rank": 2,
                        "accession": "Q9NZD4",
                        "source_ref": "ligand:Q9NZD4",
                        "pilot_role": "bridge_rescue_candidate",
                        "grounded_evidence_kind": "local_structure_bridge_summary",
                        "grounded_evidence": {"pdb_id": "1Y01"},
                        "next_truthful_stage": "ingest_local_structure_bridge_q9nzd4",
                    },
                    {
                        "rank": 3,
                        "accession": "P09105",
                        "source_ref": "ligand:P09105",
                        "pilot_role": "support_candidate",
                        "grounded_evidence_kind": "support_only_no_grounded_payload",
                        "grounded_evidence": None,
                        "next_truthful_stage": "hold_for_ligand_acquisition",
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_support.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "accession": "P00387",
                        "current_blocker": "support_only_only_no_ligand_rows_materialized",
                    },
                    {
                        "accession": "Q9NZD4",
                        "current_blocker": "bridge_rescue_not_materialized",
                    },
                    {
                        "accession": "P09105",
                        "current_blocker": "no_local_ligand_evidence_yet",
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    p00387_validation.write_text(
        json.dumps({"status": "aligned"}, indent=2),
        encoding="utf-8",
    )
    q9nzd4_validation.write_text(
        json.dumps({"status": "aligned"}, indent=2),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_ligand_identity_core_materialization_preview.py"),
            "--ligand-identity-pilot",
            str(ligand_identity_pilot),
            "--ligand-support",
            str(ligand_support),
            "--p00387-validation",
            str(p00387_validation),
            "--q9nzd4-validation",
            str(q9nzd4_validation),
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
    assert artifact["row_count"] == 3
    assert artifact["summary"]["ordered_accessions"] == ["P00387", "Q9NZD4", "P09105"]
    assert artifact["summary"]["grounded_accessions"] == ["P00387", "Q9NZD4"]
    assert artifact["summary"]["candidate_only_accessions"] == ["Q9NZD4"]
    assert artifact["summary"]["held_support_only_accessions"] == ["P09105"]
    assert artifact["truth_boundary"]["ligand_rows_materialized"] is False
    assert "Ligand Identity Core Materialization Preview" in output_md.read_text(
        encoding="utf-8"
    )
