from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "artifacts" / "status" / "lightweight_bundle_manifest.json"
DEFAULT_PROTEIN_INVENTORY = REPO_ROOT / "artifacts" / "status" / "summary_library_inventory.json"
DEFAULT_VARIANT_INVENTORY = (
    REPO_ROOT / "artifacts" / "status" / "protein_variant_summary_library_inventory.json"
)
DEFAULT_STRUCTURE_INVENTORY = (
    REPO_ROOT / "artifacts" / "status" / "structure_unit_summary_library_inventory.json"
)
DEFAULT_PROTEIN_SIMILARITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "protein_similarity_signature_preview.json"
)
DEFAULT_DICTIONARY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "dictionary_preview.json"
)
DEFAULT_STRUCTURE_FOLLOWUP_PAYLOAD_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_payload_preview.json"
)
DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_support_readiness_preview.json"
)
DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_identity_pilot_preview.json"
)
DEFAULT_LIGAND_STAGE1_VALIDATION_PANEL_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_stage1_validation_panel_preview.json"
)
DEFAULT_LIGAND_IDENTITY_CORE_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_identity_core_materialization_preview.json"
)
DEFAULT_LIGAND_ROW_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
)
DEFAULT_LIGAND_SIMILARITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_similarity_signature_preview.json"
)
DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "q9nzd4_bridge_validation_preview.json"
)
DEFAULT_MOTIF_DOMAIN_COMPACT_PREVIEW_FAMILY = (
    REPO_ROOT / "artifacts" / "status" / "motif_domain_compact_preview_family.json"
)
DEFAULT_KINETICS_SUPPORT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "kinetics_enzyme_support_preview.json"
)
DEFAULT_STRUCTURE_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_similarity_signature_preview.json"
)
DEFAULT_LEAKAGE_GROUP_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "leakage_group_preview.json"
)
DEFAULT_CONTENTS_DOC = REPO_ROOT / "docs" / "reports" / "proteosphere-lite.contents.md"
DEFAULT_SCHEMA_DOC = REPO_ROOT / "docs" / "reports" / "proteosphere-lite.schema.md"
DEFAULT_BUNDLE_ASSET_DIR = REPO_ROOT / "artifacts" / "bundles" / "preview"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "live_bundle_manifest_validation.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "live_bundle_manifest_validation.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_slice(
    *,
    slice_name: str,
    manifest_count: int,
    inventory_count: int,
    inventory_path: Path,
) -> dict[str, Any]:
    if manifest_count == inventory_count:
        status = "aligned"
        note = "manifest count matches the current inventory count"
    elif manifest_count == 0 and inventory_count > 0:
        status = "missing_current_slice"
        note = "manifest still reports zero while the current inventory is populated"
    else:
        status = "mismatch"
        note = "manifest count differs from the current inventory count"
    return {
        "slice": slice_name,
        "manifest_count": manifest_count,
        "current_count": inventory_count,
        "status": status,
        "truth_note": note,
        "inventory_path": str(inventory_path).replace("\\", "/"),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Live Bundle Manifest Validation",
        "",
        f"- Status: `{payload['overall_assessment']['status']}`",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Manifest path: `{payload['manifest_under_validation']['path']}`",
        "",
        "## Slice Assessment",
        "",
    ]
    for item in payload["slice_truth_assessment"]:
        lines.append(
            f"- `{item['slice']}`: manifest `{item['manifest_count']}`, current "
            f"`{item['current_count']}`, status `{item['status']}`"
        )
    lines.extend(
        [
            "",
            "## Documentation Surfaces",
            "",
            f"- Contents doc present: `{payload['docs']['contents_doc_exists']}`",
            f"- Schema doc present: `{payload['docs']['schema_doc_exists']}`",
        ]
    )
    lines.extend(
        [
            "",
            "## Asset Validation",
            "",
            (
                "- Required assets present: "
                f"`{payload['asset_validation']['required_assets_present']}`"
            ),
            f"- Checksum verified: `{payload['asset_validation']['checksum_verified']}`",
        ]
    )
    if payload["validation_gates"]["needs_attention"]:
        lines.extend(["", "## Needs Attention", ""])
        lines.extend(f"- {item}" for item in payload["validation_gates"]["needs_attention"])
    return "\n".join(lines) + "\n"


def _resolve_asset_paths(manifest: dict[str, Any], bundle_asset_dir: Path) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for item in manifest.get("artifact_files", []):
        resolved[item["role"]] = bundle_asset_dir / item["filename"]
    return resolved


def _validate_assets(manifest: dict[str, Any], bundle_asset_dir: Path) -> dict[str, Any]:
    asset_paths = _resolve_asset_paths(manifest, bundle_asset_dir)
    required_assets = [
        item for item in manifest.get("artifact_files", []) if item.get("required")
    ]
    missing_required = [
        item["role"]
        for item in required_assets
        if not asset_paths.get(item["role"], Path()).exists()
    ]

    bundle_path = asset_paths.get("core_bundle")
    checksum_path = asset_paths.get("checksum_root")
    checksum_verified = False
    if bundle_path and checksum_path and bundle_path.exists() and checksum_path.exists():
        expected = checksum_path.read_text(encoding="utf-8").strip().split()[0]
        checksum_verified = expected == _sha256(bundle_path)

    return {
        "bundle_asset_dir": str(bundle_asset_dir).replace("\\", "/"),
        "required_assets_present": not missing_required,
        "missing_required_assets": missing_required,
        "checksum_verified": checksum_verified,
        "resolved_asset_paths": {
            key: str(value).replace("\\", "/") for key, value in asset_paths.items()
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the live lightweight bundle manifest against current inventories."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--protein-inventory", type=Path, default=DEFAULT_PROTEIN_INVENTORY)
    parser.add_argument("--variant-inventory", type=Path, default=DEFAULT_VARIANT_INVENTORY)
    parser.add_argument("--structure-inventory", type=Path, default=DEFAULT_STRUCTURE_INVENTORY)
    parser.add_argument(
        "--protein-similarity-signature-preview",
        type=Path,
        default=DEFAULT_PROTEIN_SIMILARITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--dictionary-preview",
        type=Path,
        default=DEFAULT_DICTIONARY_PREVIEW,
    )
    parser.add_argument(
        "--structure-followup-payload-preview",
        type=Path,
        default=DEFAULT_STRUCTURE_FOLLOWUP_PAYLOAD_PREVIEW,
    )
    parser.add_argument(
        "--ligand-support-readiness-preview",
        type=Path,
        default=DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW,
    )
    parser.add_argument(
        "--ligand-identity-pilot-preview",
        type=Path,
        default=DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW,
    )
    parser.add_argument(
        "--ligand-stage1-validation-panel-preview",
        type=Path,
        default=DEFAULT_LIGAND_STAGE1_VALIDATION_PANEL_PREVIEW,
    )
    parser.add_argument(
        "--ligand-identity-core-materialization-preview",
        type=Path,
        default=DEFAULT_LIGAND_IDENTITY_CORE_MATERIALIZATION_PREVIEW,
    )
    parser.add_argument(
        "--ligand-row-materialization-preview",
        type=Path,
        default=DEFAULT_LIGAND_ROW_MATERIALIZATION_PREVIEW,
    )
    parser.add_argument(
        "--ligand-similarity-signature-preview",
        type=Path,
        default=DEFAULT_LIGAND_SIMILARITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--q9nzd4-bridge-validation-preview",
        type=Path,
        default=DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW,
    )
    parser.add_argument(
        "--motif-domain-compact-preview-family",
        type=Path,
        default=DEFAULT_MOTIF_DOMAIN_COMPACT_PREVIEW_FAMILY,
    )
    parser.add_argument(
        "--kinetics-support-preview",
        type=Path,
        default=DEFAULT_KINETICS_SUPPORT_PREVIEW,
    )
    parser.add_argument(
        "--structure-signature-preview",
        type=Path,
        default=DEFAULT_STRUCTURE_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--leakage-group-preview",
        type=Path,
        default=DEFAULT_LEAKAGE_GROUP_PREVIEW,
    )
    parser.add_argument("--contents-doc", type=Path, default=DEFAULT_CONTENTS_DOC)
    parser.add_argument("--schema-doc", type=Path, default=DEFAULT_SCHEMA_DOC)
    parser.add_argument("--bundle-asset-dir", type=Path, default=DEFAULT_BUNDLE_ASSET_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = _read_json(args.manifest)
    protein_inventory = _read_json(args.protein_inventory)
    variant_inventory = _read_json(args.variant_inventory)
    structure_inventory = _read_json(args.structure_inventory)
    protein_similarity_signature_preview = _read_json(
        args.protein_similarity_signature_preview
    )
    dictionary_preview = _read_json(args.dictionary_preview)
    structure_followup_payload_preview = _read_json(
        args.structure_followup_payload_preview
    )
    ligand_support_readiness_preview = _read_json(
        args.ligand_support_readiness_preview
    )
    ligand_identity_pilot_preview = _read_json(args.ligand_identity_pilot_preview)
    ligand_stage1_validation_panel_preview = _read_json(
        args.ligand_stage1_validation_panel_preview
    )
    ligand_identity_core_materialization_preview = _read_json(
        args.ligand_identity_core_materialization_preview
    )
    ligand_row_materialization_preview = _read_json(
        args.ligand_row_materialization_preview
    )
    ligand_similarity_signature_preview = _read_json(
        args.ligand_similarity_signature_preview
    )
    q9nzd4_bridge_validation_preview = _read_json(
        args.q9nzd4_bridge_validation_preview
    )
    motif_domain_compact_preview_family = _read_json(
        args.motif_domain_compact_preview_family
    )
    kinetics_support_preview = _read_json(args.kinetics_support_preview)
    structure_signature_preview = _read_json(args.structure_signature_preview)
    leakage_group_preview = _read_json(args.leakage_group_preview)
    counts = manifest["record_counts"]

    slice_truth_assessment = [
        _validate_slice(
            slice_name="protein",
            manifest_count=int(counts["proteins"]),
            inventory_count=int(protein_inventory["record_count"]),
            inventory_path=args.protein_inventory,
        ),
        _validate_slice(
            slice_name="protein_variant",
            manifest_count=int(counts["protein_variants"]),
            inventory_count=int(variant_inventory["record_count"]),
            inventory_path=args.variant_inventory,
        ),
        _validate_slice(
            slice_name="structure_unit",
            manifest_count=int(counts["structures"]),
            inventory_count=int(structure_inventory["record_count"]),
            inventory_path=args.structure_inventory,
        ),
        _validate_slice(
            slice_name="protein_similarity_signature",
            manifest_count=int(counts["protein_similarity_signatures"]),
            inventory_count=int(protein_similarity_signature_preview["row_count"]),
            inventory_path=args.protein_similarity_signature_preview,
        ),
        _validate_slice(
            slice_name="dictionary",
            manifest_count=int(counts["dictionaries"]),
            inventory_count=int(dictionary_preview["row_count"]),
            inventory_path=args.dictionary_preview,
        ),
        _validate_slice(
            slice_name="structure_followup_payload",
            manifest_count=int(counts.get("structure_followup_payloads", 0)),
            inventory_count=int(structure_followup_payload_preview["payload_row_count"]),
            inventory_path=args.structure_followup_payload_preview,
        ),
        _validate_slice(
            slice_name="ligand_support_readiness",
            manifest_count=int(counts.get("ligand_support_readiness", 0)),
            inventory_count=int(ligand_support_readiness_preview["row_count"]),
            inventory_path=args.ligand_support_readiness_preview,
        ),
        _validate_slice(
            slice_name="ligand",
            manifest_count=int(counts.get("ligands", 0)),
            inventory_count=int(ligand_row_materialization_preview["row_count"]),
            inventory_path=args.ligand_row_materialization_preview,
        ),
        _validate_slice(
            slice_name="ligand_identity_pilot",
            manifest_count=int(counts.get("ligand_identity_pilot", 0)),
            inventory_count=int(ligand_identity_pilot_preview["row_count"]),
            inventory_path=args.ligand_identity_pilot_preview,
        ),
        _validate_slice(
            slice_name="ligand_stage1_validation_panel",
            manifest_count=int(counts.get("ligand_stage1_validation_panel", 0)),
            inventory_count=int(ligand_stage1_validation_panel_preview["row_count"]),
            inventory_path=args.ligand_stage1_validation_panel_preview,
        ),
        _validate_slice(
            slice_name="ligand_identity_core_materialization_preview",
            manifest_count=int(
                counts.get("ligand_identity_core_materialization_preview", 0)
            ),
            inventory_count=int(ligand_identity_core_materialization_preview["row_count"]),
            inventory_path=args.ligand_identity_core_materialization_preview,
        ),
        _validate_slice(
            slice_name="ligand_row_materialization_preview",
            manifest_count=int(counts.get("ligand_row_materialization_preview", 0)),
            inventory_count=int(ligand_row_materialization_preview["row_count"]),
            inventory_path=args.ligand_row_materialization_preview,
        ),
        _validate_slice(
            slice_name="ligand_similarity_signature",
            manifest_count=int(counts.get("ligand_similarity_signatures", 0)),
            inventory_count=int(ligand_similarity_signature_preview["row_count"]),
            inventory_path=args.ligand_similarity_signature_preview,
        ),
        _validate_slice(
            slice_name="q9nzd4_bridge_validation_preview",
            manifest_count=int(counts.get("q9nzd4_bridge_validation_preview", 0)),
            inventory_count=(
                1 if q9nzd4_bridge_validation_preview.get("accession") else 0
            ),
            inventory_path=args.q9nzd4_bridge_validation_preview,
        ),
        _validate_slice(
            slice_name="motif_domain_compact_preview_family",
            manifest_count=int(counts.get("motif_domain_compact_preview_family", 0)),
            inventory_count=int(motif_domain_compact_preview_family["row_count"]),
            inventory_path=args.motif_domain_compact_preview_family,
        ),
        _validate_slice(
            slice_name="kinetics_support_preview",
            manifest_count=int(counts.get("kinetics_support_preview", 0)),
            inventory_count=int(kinetics_support_preview["row_count"]),
            inventory_path=args.kinetics_support_preview,
        ),
        _validate_slice(
            slice_name="structure_similarity_signature",
            manifest_count=int(counts["structure_similarity_signatures"]),
            inventory_count=int(structure_signature_preview["row_count"]),
            inventory_path=args.structure_signature_preview,
        ),
        _validate_slice(
            slice_name="leakage_group",
            manifest_count=int(counts["leakage_groups"]),
            inventory_count=int(leakage_group_preview["row_count"]),
            inventory_path=args.leakage_group_preview,
        ),
    ]
    needs_attention = [
        item["slice"] for item in slice_truth_assessment if item["status"] != "aligned"
    ]
    contents_exists = args.contents_doc.exists()
    schema_exists = args.schema_doc.exists()
    asset_validation = _validate_assets(manifest, args.bundle_asset_dir)
    if not contents_exists:
        needs_attention.append("contents_doc_missing")
    if not schema_exists:
        needs_attention.append("schema_doc_missing")
    if not asset_validation["required_assets_present"]:
        needs_attention.append("required_assets_missing")
    if not asset_validation["checksum_verified"]:
        needs_attention.append("bundle_checksum_unverified")

    if not needs_attention and manifest["manifest_status"] == "preview_generated_verified_assets":
        overall_status = "aligned_current_preview_with_verified_assets"
        operator_implication = (
            "bundle manifest, docs, and preview assets are aligned with current emitted slices"
        )
    elif not needs_attention:
        overall_status = "aligned_current_preview"
        operator_implication = (
            "bundle manifest and live docs are aligned with current emitted slices"
        )
    else:
        overall_status = "attention_needed"
        operator_implication = (
            "bundle manifest or documentation needs refresh before operator trust"
        )

    payload = {
        "artifact_id": "live_bundle_manifest_validation",
        "schema_id": "proteosphere-live-bundle-manifest-validation-2026-04-01",
        "report_type": "live_bundle_manifest_validation",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest_under_validation": {
            "path": str(args.manifest).replace("\\", "/"),
            "manifest_status": manifest["manifest_status"],
            "bundle_id": manifest["bundle_id"],
            "bundle_kind": manifest["bundle_kind"],
            "bundle_version": manifest["bundle_version"],
            "release_id": manifest["release_id"],
            "packaging_layout": manifest["packaging_layout"],
        },
        "slice_truth_assessment": slice_truth_assessment,
        "docs": {
            "contents_doc_path": str(args.contents_doc).replace("\\", "/"),
            "contents_doc_exists": contents_exists,
            "schema_doc_path": str(args.schema_doc).replace("\\", "/"),
            "schema_doc_exists": schema_exists,
        },
        "asset_validation": asset_validation,
        "overall_assessment": {
            "status": overall_status,
            "operator_implication": operator_implication,
        },
        "validation_gates": {
            "pass": [
                (
                    "protein, variant, structure-unit, protein-similarity, "
                    "dictionary, structure-followup payload, ligand-support readiness, "
                    "ligand-identity pilot, ligand stage1 validation panel, "
                    "ligand identity-core materialization preview, Q9NZD4 bridge "
                    "validation preview, motif/domain compact preview family, "
                    "structure-signature, and leakage-group counts are checked "
                    "against live inventories or previews"
                ),
                "contents and schema docs are required to exist for the current preview surface",
            ],
            "needs_attention": needs_attention,
        },
        "truth_boundary": {
            "summary": (
                "This validation is generated from the current live bundle manifest and inventory "
                "artifacts. It does not authorize release promotion or mutate bundle assets."
            ),
            "report_only": True,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
