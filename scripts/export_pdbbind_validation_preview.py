from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.export_pdbbind_registry_preview import (
        DEFAULT_INDEX_DIR,
        build_pdbbind_registry_preview,
    )
    from scripts.export_pdbbind_registry_preview import (
        DEFAULT_OUTPUT_JSON as DEFAULT_REGISTRY_JSON,
    )
except ModuleNotFoundError:  # pragma: no cover
    from export_pdbbind_registry_preview import (
        DEFAULT_INDEX_DIR,
        build_pdbbind_registry_preview,
    )
    from export_pdbbind_registry_preview import (
        DEFAULT_OUTPUT_JSON as DEFAULT_REGISTRY_JSON,
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "pdbbind_validation_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "pdbbind_validation_preview.md"

REQUIRED_CLASSES = {
    "protein_ligand",
    "protein_protein",
    "protein_nucleic_acid",
    "nucleic_acid_ligand",
}


def build_pdbbind_validation_preview(registry_preview: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    summary = registry_preview.get("summary") or {}
    per_class_counts = {
        str(key): int(value)
        for key, value in (summary.get("per_class_counts") or {}).items()
    }
    files_present = {
        str(key): bool(value)
        for key, value in (summary.get("files_present") or {}).items()
    }
    class_samples = [
        row for row in registry_preview.get("class_samples") or [] if isinstance(row, dict)
    ]

    if registry_preview.get("status") != "complete":
        issues.append("registry preview must be complete")
    if int(summary.get("row_count") or 0) <= 0:
        issues.append("row_count must be positive")
    if not all(files_present.values()):
        issues.append("all four PDBbind class index files must be present")
    if set(per_class_counts) != REQUIRED_CLASSES:
        issues.append("per_class_counts must cover all four supported PDBbind classes")
    if any(count <= 0 for count in per_class_counts.values()):
        issues.append("each supported PDBbind class must have at least one parsed row")
    if len(class_samples) < 4:
        issues.append("class_samples must contain one sample per supported class")
    if any(not str(row.get("raw_binding_string") or "").strip() for row in class_samples):
        issues.append("class_samples must preserve raw binding strings")
    if any(not str(row.get("source_record_id") or "").strip() for row in class_samples):
        issues.append("class_samples must preserve source_record_id provenance")
    if any(int(value) == 0 for value in (summary.get("measurement_type_counts") or {}).values()):
        warnings.append("measurement_type_counts includes a zero-count bucket")

    status = "aligned" if not issues else "attention_needed"
    return {
        "artifact_id": "pdbbind_validation_preview",
        "schema_id": "proteosphere-pdbbind-validation-preview-2026-04-05",
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "validation": {
            "issue_count": len(issues),
            "warning_count": len(warnings),
            "class_count": len(per_class_counts),
            "row_count": int(summary.get("row_count") or 0),
            "required_classes": sorted(REQUIRED_CLASSES),
            "present_classes": sorted(per_class_counts),
            "issues": issues,
            "warnings": warnings,
        },
        "truth_boundary": {
            "summary": (
                "This validation only confirms local PDBbind registry integrity and class-specific "
                "parsing. It does not change package or release authorization."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    validation = payload.get("validation") or {}
    lines = [
        "# PDBbind Validation Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Issue count: `{validation.get('issue_count')}`",
        f"- Warning count: `{validation.get('warning_count')}`",
        "",
    ]
    for issue in validation.get("issues") or []:
        lines.append(f"- issue: {issue}")
    for warning in validation.get("warnings") or []:
        lines.append(f"- warning: {warning}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the local PDBbind registry preview.")
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.registry_json.exists():
        registry_preview = json.loads(args.registry_json.read_text(encoding="utf-8"))
    else:
        registry_preview = build_pdbbind_registry_preview(args.index_dir)
    payload = build_pdbbind_validation_preview(registry_preview)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
