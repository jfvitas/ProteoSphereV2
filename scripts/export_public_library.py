from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.storage.reference_corpus_control import ValidationReceipt, WorkUnit
from api.model_studio.reference_library import build_public_warning_banner
from scripts.build_lightweight_preview_bundle_assets import (
    DEFAULT_DICTIONARY_PREVIEW,
    DEFAULT_KINETICS_SUPPORT_PREVIEW,
    DEFAULT_LEAKAGE_GROUP_PREVIEW,
    DEFAULT_LIGAND_IDENTITY_CORE_MATERIALIZATION_PREVIEW,
    DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW,
    DEFAULT_LIGAND_ROW_MATERIALIZATION_PREVIEW,
    DEFAULT_LIGAND_SIMILARITY_SIGNATURE_PREVIEW,
    DEFAULT_LIGAND_STAGE1_VALIDATION_PANEL_PREVIEW,
    DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW,
    DEFAULT_MOTIF_DOMAIN_COMPACT_PREVIEW_FAMILY,
    DEFAULT_PROTEIN_LIBRARY,
    DEFAULT_PROTEIN_SIMILARITY_SIGNATURE_PREVIEW,
    DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW,
    DEFAULT_STRUCTURE_FOLLOWUP_PAYLOAD_PREVIEW,
    DEFAULT_STRUCTURE_LIBRARY,
    DEFAULT_STRUCTURE_SIGNATURE_PREVIEW,
    DEFAULT_VARIANT_LIBRARY,
    build_preview_bundle_assets,
)
from scripts.reference_warehouse_common import (
    DEFAULT_WAREHOUSE_MANIFEST,
    load_reference_warehouse_manifest,
    read_json,
    write_json,
    write_text,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "bundles" / "public_metadata"
DEFAULT_PUBLIC_MANIFEST = DEFAULT_OUTPUT_DIR / "public_reference_library_manifest.json"
DEFAULT_WARNING_PATH = DEFAULT_OUTPUT_DIR / "WARNING.txt"
GITHUB_RELEASE_ASSET_LIMIT_BYTES = 2 * 1024 * 1024 * 1024
DEFAULT_SHARD_TARGET_BYTES = int(1.9 * 1024 * 1024 * 1024)


def shard_file_for_github_releases(
    file_path: Path,
    *,
    output_dir: Path,
    shard_target_bytes: int = DEFAULT_SHARD_TARGET_BYTES,
) -> list[dict[str, Any]]:
    shard_rows: list[dict[str, Any]] = []
    file_size = file_path.stat().st_size
    if file_size <= shard_target_bytes:
        return shard_rows
    total_shards = math.ceil(file_size / shard_target_bytes)
    with file_path.open("rb") as handle:
        for shard_index in range(total_shards):
            shard_path = output_dir / f"{file_path.name}.part{shard_index + 1:04d}"
            shard_path.parent.mkdir(parents=True, exist_ok=True)
            remaining = min(shard_target_bytes, file_size - shard_index * shard_target_bytes)
            shard_path.write_bytes(handle.read(remaining))
            shard_rows.append(
                {
                    "shard_index": shard_index + 1,
                    "path": str(shard_path).replace("\\", "/"),
                    "size_bytes": shard_path.stat().st_size,
                }
            )
    return shard_rows


def export_public_library(
    *,
    warehouse_manifest_path: Path,
    output_dir: Path,
    public_manifest_path: Path,
    warning_path: Path,
    validation_receipts_dir: Path | None = None,
    work_units_path: Path | None = None,
) -> dict[str, Any]:
    warehouse_manifest = load_reference_warehouse_manifest(warehouse_manifest_path)
    if validation_receipts_dir is not None and work_units_path is not None:
        work_units_payload = read_json(work_units_path) if work_units_path.exists() else {}
        missing_validation_units: list[str] = []
        for item in work_units_payload.get("work_units") or []:
            if not isinstance(item, dict):
                continue
            unit = WorkUnit.from_dict(item)
            if unit.status != "promoted":
                continue
            receipt_path = validation_receipts_dir / (
                unit.work_unit_id.replace(":", "__").replace("/", "_").replace("\\", "_") + ".json"
            )
            if not receipt_path.exists():
                missing_validation_units.append(unit.work_unit_id)
                continue
            receipt_payload = read_json(receipt_path)
            if not isinstance(receipt_payload, dict):
                missing_validation_units.append(unit.work_unit_id)
                continue
            receipt = ValidationReceipt.from_dict(receipt_payload)
            if receipt.decision not in {"passed", "warning"}:
                missing_validation_units.append(unit.work_unit_id)
        if missing_validation_units:
            raise ValueError(
                "public export blocked; promoted exportable work units lack passing validation receipts: "
                + ", ".join(sorted(missing_validation_units)[:10])
            )
    bundle_manifest = build_preview_bundle_assets(
        protein_library_path=DEFAULT_PROTEIN_LIBRARY,
        variant_library_path=DEFAULT_VARIANT_LIBRARY,
        structure_library_path=DEFAULT_STRUCTURE_LIBRARY,
        protein_similarity_signature_preview_path=DEFAULT_PROTEIN_SIMILARITY_SIGNATURE_PREVIEW,
        dictionary_preview_path=DEFAULT_DICTIONARY_PREVIEW,
        structure_followup_payload_preview_path=DEFAULT_STRUCTURE_FOLLOWUP_PAYLOAD_PREVIEW,
        ligand_support_readiness_preview_path=DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW,
        ligand_identity_pilot_preview_path=DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW,
        ligand_stage1_validation_panel_preview_path=DEFAULT_LIGAND_STAGE1_VALIDATION_PANEL_PREVIEW,
        ligand_identity_core_materialization_preview_path=(
            DEFAULT_LIGAND_IDENTITY_CORE_MATERIALIZATION_PREVIEW
        ),
        ligand_row_materialization_preview_path=DEFAULT_LIGAND_ROW_MATERIALIZATION_PREVIEW,
        ligand_similarity_signature_preview_path=DEFAULT_LIGAND_SIMILARITY_SIGNATURE_PREVIEW,
        q9nzd4_bridge_validation_preview_path=DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW,
        motif_domain_compact_preview_family_path=DEFAULT_MOTIF_DOMAIN_COMPACT_PREVIEW_FAMILY,
        kinetics_support_preview_path=DEFAULT_KINETICS_SUPPORT_PREVIEW,
        structure_signature_preview_path=DEFAULT_STRUCTURE_SIGNATURE_PREVIEW,
        leakage_group_preview_path=DEFAULT_LEAKAGE_GROUP_PREVIEW,
        output_dir=output_dir,
    )
    bundle_path = output_dir / "proteosphere-lite.sqlite.zst"
    if not bundle_path.exists():
        raise FileNotFoundError(f"missing public bundle payload: {bundle_path}")
    warning_banner = build_public_warning_banner(
        {
            "export_policy": dict(warehouse_manifest.export_policy),
            "warehouse_id": warehouse_manifest.warehouse_id,
            "bundle_version": bundle_manifest["bundle_version"],
        }
    )
    write_text(warning_path, warning_banner + "\n")

    shards = shard_file_for_github_releases(
        bundle_path,
        output_dir=output_dir / "release_shards",
    )
    payload = {
        "artifact_id": "public_reference_library_manifest",
        "schema_id": "proteosphere-public-reference-library-manifest-2026-04-10",
        "status": "metadata_only_exported",
        "metadata_only_bundle": True,
        "promoted_only_source": True,
        "warehouse_manifest_path": str(warehouse_manifest_path).replace("\\", "/"),
        "warehouse_id": warehouse_manifest.warehouse_id,
        "warning_path": str(warning_path).replace("\\", "/"),
        "warning_banner": warning_banner,
        "default_reader_view": "best_evidence",
        "storage_contract": "summary_backed_reference_warehouse",
        "truth_surface_policy": {
            "default_view": "best_evidence",
            "claim_surface_materialization": "logical_only",
            "summary_record_shape": [
                "family_summary_row",
                "registry_mediated_heavy_resolution",
                "conflict_disclosure",
            ],
            "field_origin_labels": ["raw", "derived", "promoted_scrape"],
        },
        "public_export_allowed_families": [
            family.family_name
            for family in warehouse_manifest.entity_families
            if family.public_export_allowed
        ],
        "internal_only_families": [
            family.family_name
            for family in warehouse_manifest.entity_families
            if not family.public_export_allowed
        ],
        "truth_surface_fields_by_family": {
            family.family_name: list(family.truth_surface_fields)
            for family in warehouse_manifest.entity_families
            if family.public_export_allowed
        },
        "public_bundle_manifest": bundle_manifest,
        "public_bundle_path": str(bundle_path).replace("\\", "/"),
        "public_bundle_size_bytes": bundle_path.stat().st_size,
        "github_release_asset_limit_bytes": GITHUB_RELEASE_ASSET_LIMIT_BYTES,
        "automatic_sharding_applied": bool(shards),
        "release_shards": shards,
    }
    write_json(public_manifest_path, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the metadata-only public ProteoSphere reference library bundle."
    )
    parser.add_argument("--warehouse-manifest", type=Path, default=DEFAULT_WAREHOUSE_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--public-manifest", type=Path, default=DEFAULT_PUBLIC_MANIFEST)
    parser.add_argument("--warning-path", type=Path, default=DEFAULT_WARNING_PATH)
    parser.add_argument("--validation-receipts-dir", type=Path)
    parser.add_argument("--work-units-path", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    export_public_library(
        warehouse_manifest_path=args.warehouse_manifest,
        output_dir=args.output_dir,
        public_manifest_path=args.public_manifest,
        warning_path=args.warning_path,
        validation_receipts_dir=args.validation_receipts_dir,
        work_units_path=args.work_units_path,
    )
    print(args.public_manifest)


if __name__ == "__main__":
    main()
