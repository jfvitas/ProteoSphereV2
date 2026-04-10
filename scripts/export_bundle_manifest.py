from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.library.summary_record import SummaryLibrarySchema  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY_LIBRARY = REPO_ROOT / "artifacts" / "status" / "protein_summary_library.json"
DEFAULT_VARIANT_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "protein_variant_summary_library.json"
)
DEFAULT_STRUCTURE_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "structure_unit_summary_library.json"
)
DEFAULT_STRUCTURE_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_similarity_signature_preview.json"
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
DEFAULT_COMPACT_ENRICHMENT_POLICY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "compact_enrichment_policy_preview.json"
)
DEFAULT_LEAKAGE_GROUP_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "leakage_group_preview.json"
)
DEFAULT_CANONICAL_STATUS = REPO_ROOT / "data" / "canonical" / "LATEST.json"
DEFAULT_COVERAGE_STATUS = REPO_ROOT / "artifacts" / "status" / "source_coverage_matrix.json"
DEFAULT_CONTRACT = REPO_ROOT / "artifacts" / "status" / "p51_bundle_manifest_budget_contract.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "lightweight_bundle_manifest.json"
DEFAULT_BUNDLE_ASSET_DIR = REPO_ROOT / "artifacts" / "bundles" / "preview"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_library(path: Path | None) -> SummaryLibrarySchema | None:
    if path is None or not path.exists():
        return None
    return SummaryLibrarySchema.from_dict(_read_json(path))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_source_snapshots(*manifest_ids: str | None) -> list[dict[str, str]]:
    snapshots: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for manifest_id in manifest_ids:
        if not manifest_id:
            continue
        for segment in str(manifest_id).split("|"):
            segment = segment.strip()
            if not segment or ":" not in segment:
                continue
            source_name, snapshot_id = segment.split(":", 1)
            key = (source_name, snapshot_id)
            if key in seen:
                continue
            seen.add(key)
            snapshots.append(
                {
                    "source_name": source_name,
                    "snapshot_id": snapshot_id,
                }
            )
    return snapshots


def _count_annotation_family(library: SummaryLibrarySchema | None, family: str) -> int:
    if library is None:
        return 0
    if family == "motif_annotations":
        return sum(
            len(record.context.motif_references) + len(record.context.domain_references)
            for record in library.records
        )
    if family == "pathway_annotations":
        return sum(len(record.context.pathway_references) for record in library.records)
    if family == "provenance_records":
        seen: set[str] = set()
        for record in library.records:
            for pointer in record.context.provenance_pointers:
                seen.add(pointer.provenance_id)
        return len(seen)
    return 0


def _family_counts(
    *,
    summary_library: SummaryLibrarySchema,
    variant_library: SummaryLibrarySchema | None,
    structure_library: SummaryLibrarySchema | None,
    protein_similarity_signature_preview: dict[str, Any] | None,
    dictionary_preview: dict[str, Any] | None,
    structure_followup_payload_preview: dict[str, Any] | None,
    ligand_support_readiness_preview: dict[str, Any] | None,
    ligand_identity_pilot_preview: dict[str, Any] | None,
    ligand_stage1_validation_panel_preview: dict[str, Any] | None,
    ligand_identity_core_materialization_preview: dict[str, Any] | None,
    ligand_row_materialization_preview: dict[str, Any] | None,
    ligand_similarity_signature_preview: dict[str, Any] | None,
    q9nzd4_bridge_validation_preview: dict[str, Any] | None,
    motif_domain_compact_preview_family: dict[str, Any] | None,
    kinetics_support_preview: dict[str, Any] | None,
    structure_signature_preview: dict[str, Any] | None,
    leakage_group_preview: dict[str, Any] | None,
) -> dict[str, int]:
    return {
        "proteins": len(summary_library.protein_records),
        "protein_variants": len(variant_library.variant_records) if variant_library else 0,
        "structures": len(structure_library.structure_unit_records) if structure_library else 0,
        "ligands": (
            int(ligand_row_materialization_preview.get("row_count", 0))
            if ligand_row_materialization_preview is not None
            else 0
        ),
        "interactions": 0,
        "motif_annotations": _count_annotation_family(summary_library, "motif_annotations"),
        "pathway_annotations": _count_annotation_family(summary_library, "pathway_annotations"),
        "provenance_records": (
            _count_annotation_family(summary_library, "provenance_records")
            + _count_annotation_family(variant_library, "provenance_records")
            + _count_annotation_family(structure_library, "provenance_records")
        ),
        "protein_similarity_signatures": (
            int(protein_similarity_signature_preview.get("row_count", 0))
            if protein_similarity_signature_preview is not None
            else 0
        ),
        "structure_followup_payloads": (
            int(structure_followup_payload_preview.get("payload_row_count", 0))
            if structure_followup_payload_preview is not None
            else 0
        ),
        "ligand_support_readiness": (
            int(ligand_support_readiness_preview.get("row_count", 0))
            if ligand_support_readiness_preview is not None
            else 0
        ),
        "ligand_identity_pilot": (
            int(ligand_identity_pilot_preview.get("row_count", 0))
            if ligand_identity_pilot_preview is not None
            else 0
        ),
        "ligand_stage1_validation_panel": (
            int(ligand_stage1_validation_panel_preview.get("row_count", 0))
            if ligand_stage1_validation_panel_preview is not None
            else 0
        ),
        "ligand_identity_core_materialization_preview": (
            int(ligand_identity_core_materialization_preview.get("row_count", 0))
            if ligand_identity_core_materialization_preview is not None
            else 0
        ),
        "ligand_row_materialization_preview": (
            int(ligand_row_materialization_preview.get("row_count", 0))
            if ligand_row_materialization_preview is not None
            else 0
        ),
        "q9nzd4_bridge_validation_preview": (
            1 if q9nzd4_bridge_validation_preview is not None else 0
        ),
        "motif_domain_compact_preview_family": (
            int(motif_domain_compact_preview_family.get("row_count", 0))
            if motif_domain_compact_preview_family is not None
            else 0
        ),
        "kinetics_support_preview": (
            int(kinetics_support_preview.get("row_count", 0))
            if kinetics_support_preview is not None
            else 0
        ),
        "structure_similarity_signatures": (
            int(structure_signature_preview.get("row_count", 0))
            if structure_signature_preview is not None
            else 0
        ),
        "ligand_similarity_signatures": (
            int(ligand_similarity_signature_preview.get("row_count", 0))
            if ligand_similarity_signature_preview is not None
            else 0
        ),
        "interaction_similarity_signatures": 0,
        "leakage_groups": (
            int(leakage_group_preview.get("row_count", 0))
            if leakage_group_preview is not None
            else 0
        ),
        "dictionaries": (
            int(dictionary_preview.get("row_count", 0))
            if dictionary_preview is not None
            else 0
        ),
    }


def _table_families(
    family_names: list[str],
    counts: dict[str, int],
    required_default: set[str],
) -> list[dict[str, Any]]:
    families: list[dict[str, Any]] = []
    for family_name in family_names:
        count = counts.get(family_name, 0)
        included = count > 0
        notes: list[str] = []
        if included:
            notes.append("materialized in current live library surfaces")
        else:
            notes.append("declared but not yet materialized in current live library surfaces")
        families.append(
            {
                "family_name": family_name,
                "included": included,
                "required": family_name in required_default,
                "record_count": count,
                "dictionary_coded": family_name == "dictionaries",
                "notes": notes,
            }
        )
    return families


def _budget_class(
    compressed_size_bytes: int,
    budget_classes: list[dict[str, Any]],
) -> str:
    for budget in budget_classes:
        minimum = budget.get("compressed_size_min_exclusive_bytes")
        maximum = budget.get("compressed_size_max_bytes")
        if minimum is not None and compressed_size_bytes <= minimum:
            continue
        if maximum is not None and compressed_size_bytes > maximum:
            continue
        return str(budget["class_id"])
    return "D"


def _budget_threshold(budget_classes: list[dict[str, Any]], index: int, fallback: int) -> int:
    if 0 <= index < len(budget_classes):
        value = budget_classes[index].get("compressed_size_max_bytes")
        if value is not None:
            return int(value)
    return fallback


def _artifact_file(
    *,
    filename: str,
    role: str,
    required: bool,
    path: Path | None,
    placeholder_checksum: str,
) -> dict[str, Any]:
    if path is None or not path.exists():
        return {
            "filename": filename,
            "size_bytes": 0,
            "required": required,
            "role": role,
            "sha256": placeholder_checksum,
        }
    return {
        "filename": filename,
        "size_bytes": path.stat().st_size,
        "required": required,
        "role": role,
        "sha256": _sha256(path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a compact bundle manifest from current lightweight-library surfaces."
        )
    )
    parser.add_argument("--bundle-id", type=str, default="proteosphere-lite")
    parser.add_argument("--bundle-kind", type=str, default="debug_bundle")
    parser.add_argument("--bundle-version", type=str, default="0.1.0-preview")
    parser.add_argument("--release-id", type=str, default="2026.04.01-lightweight-preview.1")
    parser.add_argument("--packaging-layout", type=str, default="compressed_sqlite")
    parser.add_argument(
        "--summary-library",
        type=Path,
        default=DEFAULT_SUMMARY_LIBRARY,
    )
    parser.add_argument(
        "--protein-variant-library",
        type=Path,
        default=DEFAULT_VARIANT_LIBRARY,
    )
    parser.add_argument(
        "--structure-library",
        type=Path,
        default=DEFAULT_STRUCTURE_LIBRARY,
    )
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
        "--compact-enrichment-policy-preview",
        type=Path,
        default=DEFAULT_COMPACT_ENRICHMENT_POLICY_PREVIEW,
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
    parser.add_argument("--canonical-status", type=Path, default=DEFAULT_CANONICAL_STATUS)
    parser.add_argument("--coverage-status", type=Path, default=DEFAULT_COVERAGE_STATUS)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--bundle-file",
        type=Path,
        default=DEFAULT_BUNDLE_ASSET_DIR / "proteosphere-lite.sqlite.zst",
    )
    parser.add_argument(
        "--manifest-file",
        type=Path,
        default=DEFAULT_BUNDLE_ASSET_DIR / "proteosphere-lite.release_manifest.json",
    )
    parser.add_argument(
        "--checksum-file",
        type=Path,
        default=DEFAULT_BUNDLE_ASSET_DIR / "proteosphere-lite.sha256",
    )
    parser.add_argument(
        "--contents-doc",
        type=Path,
        default=REPO_ROOT / "docs" / "reports" / "proteosphere-lite.contents.md",
    )
    parser.add_argument(
        "--schema-doc",
        type=Path,
        default=REPO_ROOT / "docs" / "reports" / "proteosphere-lite.schema.md",
    )
    parser.add_argument("--compatibility-min-version", type=str, default="tbd-by-runtime")
    parser.add_argument("--mode", choices=("example", "preview", "release"), default="example")
    parser.add_argument("--notes", action="append", default=[])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = _read_json(args.contract)
    canonical_status = _read_json(args.canonical_status)
    coverage_status = _read_json(args.coverage_status)
    summary_library = _read_library(args.summary_library)
    if summary_library is None:
        raise FileNotFoundError(f"missing summary library: {args.summary_library}")
    variant_library = _read_library(args.protein_variant_library)
    structure_library = _read_library(args.structure_library)

    validation_errors: list[str] = []
    validation_warnings: list[str] = []
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
    compact_enrichment_policy_preview = _read_json(args.compact_enrichment_policy_preview)
    structure_signature_preview = _read_json(args.structure_signature_preview)
    leakage_group_preview = _read_json(args.leakage_group_preview)
    if protein_similarity_signature_preview.get("status") != "complete":
        validation_warnings.append("protein_similarity_signature_preview_not_complete")
    if dictionary_preview.get("status") != "complete":
        validation_warnings.append("dictionary_preview_not_complete")
    if structure_followup_payload_preview.get("status") != "complete":
        validation_warnings.append("structure_followup_payload_preview_not_complete")
    if ligand_support_readiness_preview.get("status") != "complete":
        validation_warnings.append("ligand_support_readiness_preview_not_complete")
    if ligand_identity_pilot_preview.get("status") != "complete":
        validation_warnings.append("ligand_identity_pilot_preview_not_complete")
    if ligand_stage1_validation_panel_preview.get("status") != "complete":
        validation_warnings.append("ligand_stage1_validation_panel_preview_not_complete")
    if ligand_identity_core_materialization_preview.get("status") != "complete":
        validation_warnings.append(
            "ligand_identity_core_materialization_preview_not_complete"
        )
    if ligand_row_materialization_preview.get("status") != "complete":
        validation_warnings.append("ligand_row_materialization_preview_not_complete")
    if ligand_similarity_signature_preview.get("status") != "complete":
        validation_warnings.append("ligand_similarity_signature_preview_not_complete")
    if q9nzd4_bridge_validation_preview.get("status") != "aligned":
        validation_warnings.append("q9nzd4_bridge_validation_preview_not_aligned")
    if motif_domain_compact_preview_family.get("status") != "complete":
        validation_warnings.append("motif_domain_compact_preview_family_not_complete")
    if kinetics_support_preview.get("status") != "complete":
        validation_warnings.append("kinetics_support_preview_not_complete")
    if structure_signature_preview.get("status") != "complete":
        validation_warnings.append("structure_signature_preview_not_complete")
    if leakage_group_preview.get("status") != "complete":
        validation_warnings.append("leakage_group_preview_not_complete")
    if args.packaging_layout != "compressed_sqlite":
        validation_errors.append("unsupported_packaging_layout")

    if args.mode == "release":
        for required_path, label in (
            (args.bundle_file, "bundle_file"),
            (args.manifest_file, "manifest_file"),
            (args.checksum_file, "checksum_file"),
        ):
            if required_path is None or not required_path.exists():
                validation_errors.append(f"missing_required_asset:{label}")

    placeholder_checksum = "example-not-built"
    artifact_basename = args.bundle_id
    bundle_filename = (
        args.bundle_file.name if args.bundle_file else f"{artifact_basename}.sqlite.zst"
    )
    manifest_filename = (
        args.manifest_file.name
        if args.manifest_file
        else f"{artifact_basename}.release_manifest.json"
    )
    checksum_filename = (
        args.checksum_file.name if args.checksum_file else f"{artifact_basename}.sha256"
    )
    contents_filename = (
        args.contents_doc.name if args.contents_doc else f"{artifact_basename}.contents.md"
    )
    schema_filename = (
        args.schema_doc.name if args.schema_doc else f"{artifact_basename}.schema.md"
    )

    artifact_files = [
        _artifact_file(
            filename=bundle_filename,
            role="core_bundle",
            required=True,
            path=args.bundle_file,
            placeholder_checksum=placeholder_checksum,
        ),
        _artifact_file(
            filename=manifest_filename,
            role="manifest",
            required=True,
            path=args.manifest_file,
            placeholder_checksum=placeholder_checksum,
        ),
        _artifact_file(
            filename=checksum_filename,
            role="checksum_root",
            required=True,
            path=args.checksum_file,
            placeholder_checksum=placeholder_checksum,
        ),
        _artifact_file(
            filename=contents_filename,
            role="human_contents",
            required=False,
            path=args.contents_doc,
            placeholder_checksum=placeholder_checksum,
        ),
        _artifact_file(
            filename=schema_filename,
            role="human_schema",
            required=False,
            path=args.schema_doc,
            placeholder_checksum=placeholder_checksum,
        ),
    ]

    counts = _family_counts(
        summary_library=summary_library,
        variant_library=variant_library,
        structure_library=structure_library,
        protein_similarity_signature_preview=protein_similarity_signature_preview,
        dictionary_preview=dictionary_preview,
        structure_followup_payload_preview=structure_followup_payload_preview,
        ligand_support_readiness_preview=ligand_support_readiness_preview,
        ligand_identity_pilot_preview=ligand_identity_pilot_preview,
        ligand_stage1_validation_panel_preview=ligand_stage1_validation_panel_preview,
        ligand_identity_core_materialization_preview=(
            ligand_identity_core_materialization_preview
        ),
        ligand_row_materialization_preview=ligand_row_materialization_preview,
        ligand_similarity_signature_preview=ligand_similarity_signature_preview,
        q9nzd4_bridge_validation_preview=q9nzd4_bridge_validation_preview,
        motif_domain_compact_preview_family=motif_domain_compact_preview_family,
        kinetics_support_preview=kinetics_support_preview,
        structure_signature_preview=structure_signature_preview,
        leakage_group_preview=leakage_group_preview,
    )
    family_names = list(contract["table_family_contract"])
    for preview_family in (
        "structure_followup_payloads",
        "ligand_support_readiness",
        "ligand_identity_pilot",
        "ligand_stage1_validation_panel",
        "ligand_identity_core_materialization_preview",
        "ligand_row_materialization_preview",
        "ligand_similarity_signatures",
        "q9nzd4_bridge_validation_preview",
        "motif_domain_compact_preview_family",
        "kinetics_support_preview",
    ):
        if preview_family not in family_names:
            family_names.append(preview_family)
    families = _table_families(
        family_names,
        counts,
        required_default={
            "proteins",
            "motif_annotations",
            "pathway_annotations",
            "provenance_records",
        },
    )

    if args.bundle_file and args.bundle_file.exists():
        bundle_size = args.bundle_file.stat().st_size
    else:
        bundle_size = args.summary_library.stat().st_size
        if args.protein_variant_library.exists():
            bundle_size += args.protein_variant_library.stat().st_size
        if args.structure_library.exists():
            bundle_size += args.structure_library.stat().st_size
    budget_class = _budget_class(bundle_size, contract["budget_classes"])
    hard_cap = max(
        int(item.get("compressed_size_max_bytes", 0))
        for item in contract["budget_classes"]
        if item.get("compressed_size_max_bytes") is not None
    )
    if args.mode == "example":
        validation_warnings.append("example_mode_placeholder_integrity")
        manifest_status = "example_only_not_built"
        validation_status = "warning"
    elif args.mode == "preview":
        all_assets_present = all(
            path is not None and path.exists()
            for path in (args.bundle_file, args.manifest_file, args.checksum_file)
        )
        manifest_status = (
            "preview_generated_verified_assets"
            if all_assets_present
            else "preview_generated_unverified"
        )
        validation_status = "passed" if all_assets_present else "warning"
        if not all_assets_present:
            validation_warnings.append("preview_mode_missing_assets")
    else:
        manifest_status = (
            "release_generated_verified" if not validation_errors else "export_failed"
        )
        validation_status = "failed" if validation_errors else "passed"

    if bundle_size > hard_cap and args.mode == "release":
        validation_errors.append("hard_cap_violation_in_release_mode")
        manifest_status = "export_failed"
        validation_status = "failed"

    source_snapshots = _parse_source_snapshots(
        summary_library.source_manifest_id,
        variant_library.source_manifest_id if variant_library else None,
        structure_library.source_manifest_id if structure_library else None,
        canonical_status.get("run_id"),
    )

    payload = {
        "bundle_id": args.bundle_id,
        "bundle_kind": args.bundle_kind,
        "bundle_version": args.bundle_version,
        "schema_version": 1,
        "release_id": args.release_id,
        "created_at": datetime.now(UTC).isoformat(),
        "packaging_layout": args.packaging_layout,
        "compression": {
            "algorithm": "zstd",
            "container": "sqlite",
            "filename": bundle_filename.removesuffix(".zst"),
        },
        "artifact_files": artifact_files,
        "required_assets": list(contract["primary_bundle_shape"]["required_assets"]),
        "optional_assets": list(contract["primary_bundle_shape"]["optional_assets"]),
        "table_families": families,
        "record_counts": counts,
        "compact_enrichment_family_policies": {
            row["family_name"]: row["policy_label"]
            for row in (compact_enrichment_policy_preview.get("rows") or [])
            if isinstance(row, dict)
        },
        "source_snapshot_ids": source_snapshots,
        "source_coverage_summary": {
            "source_count": coverage_status["summary"]["source_count"],
            "present_source_count": coverage_status["summary"]["present_source_count"],
            "partial_source_count": coverage_status["summary"]["partial_source_count"],
            "missing_source_count": coverage_status["summary"]["missing_source_count"],
            "procurement_priority_sources": coverage_status["summary"].get(
                "procurement_priority_sources",
                [],
            ),
        },
        "build_inputs": {
            "summary_library_artifact": str(args.summary_library).replace("\\", "/"),
            "protein_variant_library_artifact": str(args.protein_variant_library).replace(
                "\\",
                "/",
            )
            if args.protein_variant_library.exists()
            else None,
            "structure_library_artifact": str(args.structure_library).replace("\\", "/")
            if args.structure_library.exists()
            else None,
            "structure_signature_preview_artifact": (
                str(args.structure_signature_preview).replace("\\", "/")
                if args.structure_signature_preview.exists()
                else None
            ),
            "protein_similarity_signature_preview_artifact": (
                str(args.protein_similarity_signature_preview).replace("\\", "/")
                if args.protein_similarity_signature_preview.exists()
                else None
            ),
            "dictionary_preview_artifact": (
                str(args.dictionary_preview).replace("\\", "/")
                if args.dictionary_preview.exists()
                else None
            ),
            "structure_followup_payload_preview_artifact": (
                str(args.structure_followup_payload_preview).replace("\\", "/")
                if args.structure_followup_payload_preview.exists()
                else None
            ),
            "ligand_support_readiness_preview_artifact": (
                str(args.ligand_support_readiness_preview).replace("\\", "/")
                if args.ligand_support_readiness_preview.exists()
                else None
            ),
            "ligand_identity_pilot_preview_artifact": (
                str(args.ligand_identity_pilot_preview).replace("\\", "/")
                if args.ligand_identity_pilot_preview.exists()
                else None
            ),
            "ligand_stage1_validation_panel_preview_artifact": (
                str(args.ligand_stage1_validation_panel_preview).replace("\\", "/")
                if args.ligand_stage1_validation_panel_preview.exists()
                else None
            ),
            "ligand_identity_core_materialization_preview_artifact": (
                str(args.ligand_identity_core_materialization_preview).replace("\\", "/")
                if args.ligand_identity_core_materialization_preview.exists()
                else None
            ),
            "ligand_row_materialization_preview_artifact": (
                str(args.ligand_row_materialization_preview).replace("\\", "/")
                if args.ligand_row_materialization_preview.exists()
                else None
            ),
            "ligand_similarity_signature_preview_artifact": (
                str(args.ligand_similarity_signature_preview).replace("\\", "/")
                if args.ligand_similarity_signature_preview.exists()
                else None
            ),
            "q9nzd4_bridge_validation_preview_artifact": (
                str(args.q9nzd4_bridge_validation_preview).replace("\\", "/")
                if args.q9nzd4_bridge_validation_preview.exists()
                else None
            ),
            "motif_domain_compact_preview_family_artifact": (
                str(args.motif_domain_compact_preview_family).replace("\\", "/")
                if args.motif_domain_compact_preview_family.exists()
                else None
            ),
            "kinetics_support_preview_artifact": (
                str(args.kinetics_support_preview).replace("\\", "/")
                if args.kinetics_support_preview.exists()
                else None
            ),
            "compact_enrichment_policy_preview_artifact": (
                str(args.compact_enrichment_policy_preview).replace("\\", "/")
                if args.compact_enrichment_policy_preview.exists()
                else None
            ),
            "leakage_group_preview_artifact": (
                str(args.leakage_group_preview).replace("\\", "/")
                if args.leakage_group_preview.exists()
                else None
            ),
            "canonical_status_artifact": str(args.canonical_status).replace("\\", "/"),
            "coverage_status_artifact": str(args.coverage_status).replace("\\", "/"),
            "bundle_contract": str(args.contract).replace("\\", "/"),
        },
        "integrity": {
            "status": manifest_status,
            "bundle_sha256": artifact_files[0]["sha256"],
            "manifest_sha256": artifact_files[1]["sha256"],
            "per_table_fingerprints": [],
        },
        "compatibility": {
            "status": "example_only" if args.mode == "example" else "bundle_defined",
            "minimum_supported_tool_version": args.compatibility_min_version,
            "compatible_schema_versions": [1, 2],
            "optional_expansion_supported": False,
        },
        "budget_status": {
            "measurement_mode": (
                "measured_bundle"
                if args.bundle_file and args.bundle_file.exists()
                else "estimated_from_current_surfaces"
            ),
            "compressed_size_bytes": bundle_size,
            "uncompressed_size_bytes": bundle_size,
            "soft_target_bytes": _budget_threshold(contract["budget_classes"], 0, hard_cap),
            "warning_threshold_bytes": _budget_threshold(
                contract["budget_classes"],
                1,
                hard_cap,
            ),
            "hard_cap_bytes": hard_cap,
            "budget_class": budget_class,
            "cap_compliance": bundle_size <= hard_cap,
            "notes": [
                "derived from current live library surfaces"
                if not (args.bundle_file and args.bundle_file.exists())
                else "measured from provided bundle artifact",
                *args.notes,
            ],
        },
        "content_scope": contract["primary_bundle_shape"]["content_scope"],
        "exclusions": list(contract["default_exclusions"]),
        "manifest_status": manifest_status,
        "export_mode": args.mode,
        "export_timestamp": datetime.now(UTC).isoformat(),
        "validation_status": validation_status if not validation_errors else "failed",
        "validation_errors": validation_errors,
        "validation_warnings": validation_warnings,
    }
    _write_json(args.output, payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
