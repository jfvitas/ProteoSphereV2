from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_MANIFEST_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "sample_external_dataset_manifest_preview.json"
)
DEFAULT_FOLDER_PACKAGE_MANIFEST_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "sample_folder_package_manifest_preview.json"
)
DEFAULT_EXTERNAL_DATASET_ASSESSMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_assessment_preview.json"
)
DEFAULT_EXTERNAL_DATASET_LEAKAGE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_leakage_audit_preview.json"
)
DEFAULT_EXTERNAL_DATASET_MODALITY_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_modality_audit_preview.json"
)
DEFAULT_EXTERNAL_DATASET_BINDING_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_binding_audit_preview.json"
)
DEFAULT_EXTERNAL_DATASET_STRUCTURE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_structure_audit_preview.json"
)
DEFAULT_EXTERNAL_DATASET_PROVENANCE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_provenance_audit_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "sample_external_dataset_assessment_bundle_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "sample_external_dataset_assessment_bundle_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _count_rows(payload: dict[str, Any]) -> int:
    rows = payload.get("rows") or []
    return sum(1 for row in rows if isinstance(row, dict))


def build_sample_external_dataset_assessment_bundle_preview(
    json_manifest_preview: dict[str, Any],
    folder_package_manifest_preview: dict[str, Any],
    external_dataset_assessment_preview: dict[str, Any],
    external_dataset_leakage_audit_preview: dict[str, Any],
    external_dataset_modality_audit_preview: dict[str, Any],
    external_dataset_binding_audit_preview: dict[str, Any],
    external_dataset_structure_audit_preview: dict[str, Any],
    external_dataset_provenance_audit_preview: dict[str, Any],
) -> dict[str, Any]:
    sample_manifests = [json_manifest_preview, folder_package_manifest_preview]
    sub_audits = {
        "leakage": external_dataset_leakage_audit_preview,
        "modality": external_dataset_modality_audit_preview,
        "binding": external_dataset_binding_audit_preview,
        "structure": external_dataset_structure_audit_preview,
        "provenance": external_dataset_provenance_audit_preview,
    }
    sample_manifest_row_count = sum(_count_rows(payload) for payload in sample_manifests)
    sub_audit_verdicts = {
        name: str(payload.get("verdict") or "unknown")
        for name, payload in sub_audits.items()
    }
    payload = {
        "artifact_id": "sample_external_dataset_assessment_bundle_preview",
        "schema_id": "proteosphere-sample-external-dataset-assessment-bundle-preview-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "bundle_kind": "sample_external_dataset_assessment_bundle",
        "bundle_status": "report_only_composite_preview",
        "source_artifacts": {
            "sample_external_dataset_manifest_preview": str(
                DEFAULT_JSON_MANIFEST_PREVIEW
            ).replace("\\", "/"),
            "sample_folder_package_manifest_preview": str(
                DEFAULT_FOLDER_PACKAGE_MANIFEST_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_assessment_preview": str(
                DEFAULT_EXTERNAL_DATASET_ASSESSMENT_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_leakage_audit_preview": str(
                DEFAULT_EXTERNAL_DATASET_LEAKAGE_AUDIT_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_modality_audit_preview": str(
                DEFAULT_EXTERNAL_DATASET_MODALITY_AUDIT_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_binding_audit_preview": str(
                DEFAULT_EXTERNAL_DATASET_BINDING_AUDIT_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_structure_audit_preview": str(
                DEFAULT_EXTERNAL_DATASET_STRUCTURE_AUDIT_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_provenance_audit_preview": str(
                DEFAULT_EXTERNAL_DATASET_PROVENANCE_AUDIT_PREVIEW
            ).replace("\\", "/"),
        },
        "summary": {
            "sample_manifest_count": len(sample_manifests),
            "sample_manifest_row_count": sample_manifest_row_count,
            "assessment_overall_verdict": str(
                (external_dataset_assessment_preview.get("summary") or {}).get(
                    "overall_verdict"
                )
                or external_dataset_assessment_preview.get("verdict")
                or "unknown"
            ),
            "assessment_dataset_accession_count": int(
                (external_dataset_assessment_preview.get("summary") or {}).get(
                    "dataset_accession_count"
                )
                or 0
            ),
            "sub_audit_count": len(sub_audits),
            "sub_audit_verdicts": sub_audit_verdicts,
            "sub_audits_all_usable_with_caveats": all(
                verdict == "usable_with_caveats" for verdict in sub_audit_verdicts.values()
            ),
        },
        "sections": {
            "sample_manifests": sample_manifests,
            "external_dataset_assessment": external_dataset_assessment_preview,
            "sub_audits": sub_audits,
        },
        "truth_boundary": {
            "summary": (
                "This bundle is report-only and non-mutating. It composes the existing "
                "sample external dataset previews with the existing external dataset "
                "assessment and standalone subaudit surfaces for operator review only."
            ),
            "report_only": True,
            "non_mutating": True,
            "conservative_defaults": True,
            "package_not_authorized": True,
        },
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    sections = payload.get("sections") or {}
    lines = [
        "# Sample External Dataset Assessment Bundle Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Bundle status: `{payload.get('bundle_status')}`",
        f"- Sample manifest count: `{summary.get('sample_manifest_count')}`",
        f"- Sample manifest row count: `{summary.get('sample_manifest_row_count')}`",
        f"- Assessment verdict: `{summary.get('assessment_overall_verdict')}`",
        f"- Sub-audit count: `{summary.get('sub_audit_count')}`",
        "",
        "## Sample Manifests",
        "",
        "| Artifact | Rows | Status |",
        "| --- | --- | --- |",
    ]
    for manifest in sections.get("sample_manifests") or []:
        lines.append(
            "| "
            + f"`{manifest.get('artifact_id')}` | "
            + f"{_count_rows(manifest)} | "
            + f"{manifest.get('status')} |"
        )
    lines.extend(["", "## Sub-Audits", "", "| Audit | Verdict |", "| --- | --- |"])
    for name, payload_item in (sections.get("sub_audits") or {}).items():
        lines.append(f"| `{name}` | `{payload_item.get('verdict')}` |")
    truth_boundary = payload.get("truth_boundary") or {}
    if truth_boundary.get("summary"):
        lines.extend(["", "## Truth Boundary", "", f"- {truth_boundary['summary']}"])
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only sample external dataset assessment bundle preview."
    )
    parser.add_argument(
        "--json-manifest-preview",
        type=Path,
        default=DEFAULT_JSON_MANIFEST_PREVIEW,
    )
    parser.add_argument(
        "--folder-package-manifest-preview",
        type=Path,
        default=DEFAULT_FOLDER_PACKAGE_MANIFEST_PREVIEW,
    )
    parser.add_argument(
        "--external-dataset-assessment-preview",
        type=Path,
        default=DEFAULT_EXTERNAL_DATASET_ASSESSMENT_PREVIEW,
    )
    parser.add_argument(
        "--external-dataset-leakage-audit-preview",
        type=Path,
        default=DEFAULT_EXTERNAL_DATASET_LEAKAGE_AUDIT_PREVIEW,
    )
    parser.add_argument(
        "--external-dataset-modality-audit-preview",
        type=Path,
        default=DEFAULT_EXTERNAL_DATASET_MODALITY_AUDIT_PREVIEW,
    )
    parser.add_argument(
        "--external-dataset-binding-audit-preview",
        type=Path,
        default=DEFAULT_EXTERNAL_DATASET_BINDING_AUDIT_PREVIEW,
    )
    parser.add_argument(
        "--external-dataset-structure-audit-preview",
        type=Path,
        default=DEFAULT_EXTERNAL_DATASET_STRUCTURE_AUDIT_PREVIEW,
    )
    parser.add_argument(
        "--external-dataset-provenance-audit-preview",
        type=Path,
        default=DEFAULT_EXTERNAL_DATASET_PROVENANCE_AUDIT_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_sample_external_dataset_assessment_bundle_preview(
        _read_json(args.json_manifest_preview),
        _read_json(args.folder_package_manifest_preview),
        _read_json(args.external_dataset_assessment_preview),
        _read_json(args.external_dataset_leakage_audit_preview),
        _read_json(args.external_dataset_modality_audit_preview),
        _read_json(args.external_dataset_binding_audit_preview),
        _read_json(args.external_dataset_structure_audit_preview),
        _read_json(args.external_dataset_provenance_audit_preview),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
