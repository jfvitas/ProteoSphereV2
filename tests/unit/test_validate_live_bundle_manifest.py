from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validate_live_bundle_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    protein_inventory = tmp_path / "protein_inventory.json"
    variant_inventory = tmp_path / "variant_inventory.json"
    structure_inventory = tmp_path / "structure_inventory.json"
    protein_similarity_signature_preview = tmp_path / "protein_similarity_signature_preview.json"
    dictionary_preview = tmp_path / "dictionary_preview.json"
    structure_followup_payload_preview = tmp_path / "structure_followup_payload_preview.json"
    ligand_support_readiness_preview = tmp_path / "ligand_support_readiness_preview.json"
    ligand_identity_pilot_preview = tmp_path / "ligand_identity_pilot_preview.json"
    ligand_stage1_validation_panel_preview = (
        tmp_path / "ligand_stage1_validation_panel_preview.json"
    )
    ligand_identity_core_materialization_preview = (
        tmp_path / "ligand_identity_core_materialization_preview.json"
    )
    ligand_row_materialization_preview = (
        tmp_path / "ligand_row_materialization_preview.json"
    )
    ligand_similarity_signature_preview = (
        tmp_path / "ligand_similarity_signature_preview.json"
    )
    q9nzd4_bridge_validation_preview = (
        tmp_path / "q9nzd4_bridge_validation_preview.json"
    )
    motif_domain_compact_preview_family = (
        tmp_path / "motif_domain_compact_preview_family.json"
    )
    kinetics_support_preview = tmp_path / "kinetics_support_preview.json"
    structure_signature_preview = tmp_path / "structure_similarity_signature_preview.json"
    leakage_group_preview = tmp_path / "leakage_group_preview.json"
    contents_doc = tmp_path / "contents.md"
    schema_doc = tmp_path / "schema.md"
    bundle_asset_dir = tmp_path / "bundle"
    bundle_asset_dir.mkdir()
    bundle_file = bundle_asset_dir / "proteosphere-lite.sqlite.zst"
    bundle_file.write_bytes(b"bundle-bytes")
    checksum_file = bundle_asset_dir / "proteosphere-lite.sha256"
    manifest_file = bundle_asset_dir / "proteosphere-lite.release_manifest.json"

    manifest_path.write_text(
        json.dumps(
                {
                    "manifest_status": "preview_generated_verified_assets",
                "bundle_id": "proteosphere-lite",
                "bundle_kind": "debug_bundle",
                "bundle_version": "0.1.0-preview",
                "release_id": "rel-1",
                "packaging_layout": "compressed_sqlite",
                "artifact_files": [
                    {
                        "filename": bundle_file.name,
                        "role": "core_bundle",
                        "required": True,
                        "size_bytes": bundle_file.stat().st_size,
                        "sha256": "placeholder",
                    },
                    {
                        "filename": manifest_file.name,
                        "role": "manifest",
                        "required": True,
                        "size_bytes": 0,
                        "sha256": "placeholder",
                    },
                    {
                        "filename": checksum_file.name,
                        "role": "checksum_root",
                        "required": True,
                        "size_bytes": 0,
                        "sha256": "placeholder",
                    },
                ],
                "record_counts": {
                    "proteins": 11,
                    "protein_variants": 3,
                    "structures": 4,
                    "ligands": 24,
                    "ligand_similarity_signatures": 24,
                    "protein_similarity_signatures": 7,
                    "dictionaries": 9,
                    "structure_followup_payloads": 2,
                    "ligand_support_readiness": 4,
                    "ligand_identity_pilot": 4,
                    "ligand_stage1_validation_panel": 2,
                    "ligand_identity_core_materialization_preview": 2,
                    "ligand_row_materialization_preview": 24,
                    "q9nzd4_bridge_validation_preview": 1,
                    "motif_domain_compact_preview_family": 5,
                    "kinetics_support_preview": 3,
                    "structure_similarity_signatures": 2,
                    "leakage_groups": 5,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    protein_inventory.write_text(json.dumps({"record_count": 11}), encoding="utf-8")
    variant_inventory.write_text(json.dumps({"record_count": 3}), encoding="utf-8")
    structure_inventory.write_text(json.dumps({"record_count": 4}), encoding="utf-8")
    protein_similarity_signature_preview.write_text(
        json.dumps({"row_count": 7}), encoding="utf-8"
    )
    dictionary_preview.write_text(json.dumps({"row_count": 9}), encoding="utf-8")
    structure_followup_payload_preview.write_text(
        json.dumps({"payload_row_count": 2}),
        encoding="utf-8",
    )
    ligand_support_readiness_preview.write_text(
        json.dumps({"row_count": 4}),
        encoding="utf-8",
    )
    ligand_identity_pilot_preview.write_text(
        json.dumps({"row_count": 4}),
        encoding="utf-8",
    )
    ligand_stage1_validation_panel_preview.write_text(
        json.dumps({"row_count": 2}),
        encoding="utf-8",
    )
    ligand_identity_core_materialization_preview.write_text(
        json.dumps({"row_count": 2}),
        encoding="utf-8",
    )
    ligand_row_materialization_preview.write_text(
        json.dumps({"row_count": 24}),
        encoding="utf-8",
    )
    ligand_similarity_signature_preview.write_text(
        json.dumps({"row_count": 24}),
        encoding="utf-8",
    )
    q9nzd4_bridge_validation_preview.write_text(
        json.dumps(
            {
                "status": "aligned",
                "accession": "Q9NZD4",
                "best_pdb_id": "1Y01",
                "component_id": "CHK",
                "component_role": "primary_binder",
                "matched_pdb_id_count": 3,
                "truth_boundary": {"candidate_only": True},
            }
        ),
        encoding="utf-8",
    )
    motif_domain_compact_preview_family.write_text(
        json.dumps({"status": "complete", "row_count": 5}),
        encoding="utf-8",
    )
    kinetics_support_preview.write_text(
        json.dumps({"status": "complete", "row_count": 3}),
        encoding="utf-8",
    )
    structure_signature_preview.write_text(json.dumps({"row_count": 2}), encoding="utf-8")
    leakage_group_preview.write_text(json.dumps({"row_count": 5}), encoding="utf-8")
    contents_doc.write_text("# contents\n", encoding="utf-8")
    schema_doc.write_text("# schema\n", encoding="utf-8")
    checksum_file.write_text(
        __import__("hashlib").sha256(bundle_file.read_bytes()).hexdigest()
        + f"  {bundle_file.name}\n",
        encoding="utf-8",
    )
    manifest_file.write_text('{"status":"preview_generated_assets"}\n', encoding="utf-8")

    output_json = tmp_path / "validation.json"
    output_md = tmp_path / "validation.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_live_bundle_manifest.py"),
            "--manifest",
            str(manifest_path),
            "--protein-inventory",
            str(protein_inventory),
            "--variant-inventory",
            str(variant_inventory),
            "--structure-inventory",
            str(structure_inventory),
            "--protein-similarity-signature-preview",
            str(protein_similarity_signature_preview),
            "--dictionary-preview",
            str(dictionary_preview),
            "--structure-followup-payload-preview",
            str(structure_followup_payload_preview),
            "--ligand-support-readiness-preview",
            str(ligand_support_readiness_preview),
            "--ligand-identity-pilot-preview",
            str(ligand_identity_pilot_preview),
            "--ligand-stage1-validation-panel-preview",
            str(ligand_stage1_validation_panel_preview),
            "--ligand-identity-core-materialization-preview",
            str(ligand_identity_core_materialization_preview),
            "--ligand-row-materialization-preview",
            str(ligand_row_materialization_preview),
            "--ligand-similarity-signature-preview",
            str(ligand_similarity_signature_preview),
            "--q9nzd4-bridge-validation-preview",
            str(q9nzd4_bridge_validation_preview),
            "--motif-domain-compact-preview-family",
            str(motif_domain_compact_preview_family),
            "--kinetics-support-preview",
            str(kinetics_support_preview),
            "--structure-signature-preview",
            str(structure_signature_preview),
            "--leakage-group-preview",
            str(leakage_group_preview),
            "--contents-doc",
            str(contents_doc),
            "--schema-doc",
            str(schema_doc),
            "--bundle-asset-dir",
            str(bundle_asset_dir),
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
    assert payload["overall_assessment"]["status"] == "aligned_current_preview_with_verified_assets"
    assert payload["docs"]["contents_doc_exists"] is True
    assert payload["docs"]["schema_doc_exists"] is True
    assert payload["asset_validation"]["required_assets_present"] is True
    assert payload["asset_validation"]["checksum_verified"] is True
    assert all(item["status"] == "aligned" for item in payload["slice_truth_assessment"])
    assert [item["slice"] for item in payload["slice_truth_assessment"]] == [
        "protein",
        "protein_variant",
        "structure_unit",
        "protein_similarity_signature",
        "dictionary",
        "structure_followup_payload",
        "ligand_support_readiness",
        "ligand",
        "ligand_identity_pilot",
        "ligand_stage1_validation_panel",
        "ligand_identity_core_materialization_preview",
        "ligand_row_materialization_preview",
        "ligand_similarity_signature",
        "q9nzd4_bridge_validation_preview",
        "motif_domain_compact_preview_family",
        "kinetics_support_preview",
        "structure_similarity_signature",
        "leakage_group",
    ]
