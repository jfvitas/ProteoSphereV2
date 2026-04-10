from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_ligand_similarity_signature_preview(tmp_path: Path) -> None:
    ligand_row_preview = tmp_path / "ligand_row_materialization_preview.json"
    output_json = tmp_path / "ligand_similarity_signature_preview.json"
    output_md = tmp_path / "ligand_similarity_signature_preview.md"

    ligand_row_preview.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "row_id": "ligand_row:protein:P00387:chembl:CHEMBL1",
                        "accession": "P00387",
                        "protein_ref": "protein:P00387",
                        "ligand_ref": "chembl:CHEMBL1",
                        "ligand_namespace": "ChEMBL",
                        "canonical_smiles": "CC",
                        "candidate_only": False,
                        "evidence_kind": "local_chembl_bulk_assay_row",
                    },
                    {
                        "row_id": "ligand_row:protein:P00387:chembl:CHEMBL2",
                        "accession": "P00387",
                        "protein_ref": "protein:P00387",
                        "ligand_ref": "chembl:CHEMBL2",
                        "ligand_namespace": "ChEMBL",
                        "canonical_smiles": "CC",
                        "candidate_only": False,
                        "evidence_kind": "local_chembl_bulk_assay_row",
                    },
                    {
                        "row_id": "ligand_row:protein:Q9NZD4:pdb_ccd:CHK",
                        "accession": "Q9NZD4",
                        "protein_ref": "protein:Q9NZD4",
                        "ligand_ref": "pdb_ccd:CHK",
                        "ligand_namespace": "PDB_CCD",
                        "candidate_only": True,
                        "evidence_kind": "local_structure_bridge_component",
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_ligand_similarity_signature_preview.py"),
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

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "complete"
    assert payload["row_count"] == 3
    assert payload["summary"]["accession_count"] == 2
    assert payload["summary"]["exact_identity_group_count"] == 3
    assert payload["summary"]["chemical_series_group_count"] == 2
    assert payload["summary"]["candidate_only_count"] == 1
    assert payload["summary"]["ligand_namespace_counts"] == {"ChEMBL": 2, "PDB_CCD": 1}
    assert payload["truth_boundary"]["ready_for_bundle_preview"] is True
    assert payload["truth_boundary"]["ligand_rows_materialized"] is True
    assert payload["truth_boundary"]["canonical_ligand_reconciliation_claimed"] is False
    first_row = payload["rows"][0]
    assert first_row["exact_ligand_identity_group"] == "chembl:CHEMBL1"
    assert first_row["chemical_series_group"].startswith("smiles:")
    assert payload["rows"][2]["candidate_only"] is True
    assert "Ligand Similarity Signature Preview" in output_md.read_text(encoding="utf-8")
