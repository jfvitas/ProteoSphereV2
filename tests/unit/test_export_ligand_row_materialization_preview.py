from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_ligand_row_materialization_preview(tmp_path: Path) -> None:
    p00387_payload = tmp_path / "p00387_local_chembl_ligand_payload.json"
    p00387_validation = tmp_path / "p00387_ligand_extraction_validation_preview.json"
    q9nzd4_validation = tmp_path / "q9nzd4_bridge_validation_preview.json"
    output_json = tmp_path / "ligand_row_materialization_preview.json"
    output_md = tmp_path / "ligand_row_materialization_preview.md"

    p00387_payload.write_text(
        json.dumps(
            {
                "status": "resolved",
                "rows": [
                    {
                        "activity_id": 2,
                        "assay_id": 11,
                        "ligand_chembl_id": "CHEMBL1",
                        "ligand_pref_name": "Ligand One",
                        "canonical_smiles": "CC",
                        "standard_relation": "=",
                        "standard_type": "IC50",
                        "standard_value": 10,
                        "standard_units": "nM",
                        "pchembl_value": 8.0,
                        "ligand_molecule_type": "Small molecule",
                        "full_mwt": 100.0,
                        "target_chembl_id": "CHEMBL2146",
                        "target_pref_name": "NADH-cytochrome b5 reductase",
                    },
                    {
                        "activity_id": 3,
                        "assay_id": 11,
                        "ligand_chembl_id": "CHEMBL1",
                        "ligand_pref_name": "Ligand One",
                        "canonical_smiles": "CC",
                        "standard_relation": "=",
                        "standard_type": "IC50",
                        "standard_value": 20,
                        "standard_units": "nM",
                        "pchembl_value": 7.0,
                        "ligand_molecule_type": "Small molecule",
                        "full_mwt": 100.0,
                        "target_chembl_id": "CHEMBL2146",
                        "target_pref_name": "NADH-cytochrome b5 reductase",
                    },
                    {
                        "activity_id": 4,
                        "assay_id": 12,
                        "ligand_chembl_id": "CHEMBL2",
                        "ligand_pref_name": "",
                        "canonical_smiles": "CCC",
                        "standard_relation": "=",
                        "standard_type": "Ki",
                        "standard_value": 30,
                        "standard_units": "nM",
                        "pchembl_value": 6.5,
                        "ligand_molecule_type": "Small molecule",
                        "full_mwt": 120.0,
                        "target_chembl_id": "CHEMBL2146",
                        "target_pref_name": "NADH-cytochrome b5 reductase",
                    },
                ],
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
        json.dumps(
            {
                "status": "aligned",
                "best_pdb_id": "1Y01",
                "component_id": "CHK",
                "component_name": "Bridge Ligand",
                "component_role": "primary_binder",
                "matched_pdb_id_count": 3,
                "chain_ids": ["B"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_ligand_row_materialization_preview.py"),
            "--p00387-payload",
            str(p00387_payload),
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
    assert artifact["summary"]["materialized_accessions"] == ["P00387", "Q9NZD4"]
    assert artifact["summary"]["grounded_accessions"] == ["P00387"]
    assert artifact["summary"]["candidate_only_accessions"] == ["Q9NZD4"]
    assert artifact["summary"]["grounded_row_count"] == 2
    assert artifact["summary"]["candidate_only_row_count"] == 1
    assert artifact["summary"]["ligand_namespace_counts"] == {"ChEMBL": 2, "PDB_CCD": 1}
    assert artifact["truth_boundary"]["ligand_rows_materialized"] is True
    assert artifact["truth_boundary"]["bundle_ligands_included"] is True
    assert artifact["truth_boundary"]["canonical_ligand_materialization_claimed"] is False
    assert artifact["rows"][0]["ligand_ref"] == "chembl:CHEMBL1"
    assert artifact["rows"][0]["activity_count_for_ligand"] == 2
    assert artifact["rows"][2]["ligand_ref"] == "pdb_ccd:CHK"
    assert artifact["rows"][2]["candidate_only"] is True
    assert "Ligand Row Materialization Preview" in output_md.read_text(encoding="utf-8")
