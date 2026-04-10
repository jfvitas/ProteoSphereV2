from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validate_ligand_similarity_signature_preview(tmp_path: Path) -> None:
    similarity_preview = tmp_path / "ligand_similarity_signature_preview.json"
    gate_preview = tmp_path / "ligand_similarity_signature_gate_preview.json"
    output_json = tmp_path / "ligand_similarity_signature_validation.json"
    output_md = tmp_path / "ligand_similarity_signature_validation.md"

    similarity_preview.write_text(
        json.dumps(
            {
                "row_count": 2,
                "rows": [
                    {
                        "signature_id": (
                            "ligand_similarity:ligand_row:protein:P00387:chembl:CHEMBL1"
                        ),
                        "accession": "P00387",
                        "exact_ligand_identity_group": "chembl:CHEMBL1",
                        "chemical_series_group": "smiles:abc",
                        "candidate_only": False,
                        "ligand_namespace": "ChEMBL",
                        "canonical_smiles_present": True,
                        "evidence_kind": "local_chembl_bulk_assay_row",
                        "ligand_rows_materialized": True,
                    },
                    {
                        "signature_id": "ligand_similarity:ligand_row:protein:Q9NZD4:pdb_ccd:CHK",
                        "accession": "Q9NZD4",
                        "exact_ligand_identity_group": "pdb_ccd:CHK",
                        "chemical_series_group": "pdb_ccd:CHK",
                        "candidate_only": True,
                        "ligand_namespace": "PDB_CCD",
                        "canonical_smiles_present": False,
                        "evidence_kind": "local_structure_bridge_component",
                        "ligand_rows_materialized": True,
                    },
                ],
                "summary": {
                    "accession_count": 2,
                    "exact_identity_group_count": 2,
                    "chemical_series_group_count": 2,
                    "candidate_only_count": 1,
                },
                "truth_boundary": {
                    "canonical_ligand_reconciliation_claimed": False,
                    "split_claims_changed": False,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    gate_preview.write_text(
        json.dumps(
            {
                "gate_status": "ready_for_signature_preview",
                "ligands_materialized": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_ligand_similarity_signature_preview.py"),
            "--ligand-similarity-signature-preview",
            str(similarity_preview),
            "--ligand-similarity-signature-gate-preview",
            str(gate_preview),
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

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "aligned"
    assert payload["validation"]["row_count"] == 2
    assert payload["validation"]["grounded_accessions"] == ["P00387"]
    assert payload["validation"]["candidate_only_accessions"] == ["Q9NZD4"]
    assert payload["validation"]["policy_mode"] == "mixed_grounded_and_candidate_only_preview"
    assert payload["truth_boundary"]["candidate_only_rows_non_governing"] is True
    assert "Ligand Similarity Signature Validation" in output_md.read_text(encoding="utf-8")
