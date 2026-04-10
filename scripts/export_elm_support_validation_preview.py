from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.export_elm_support_preview import (
        DEFAULT_ELM_CLASSES,
        DEFAULT_ELM_INTERACTIONS,
        DEFAULT_TRAINING_SET,
        build_elm_support_preview,
    )
    from scripts.export_elm_support_preview import (
        DEFAULT_OUTPUT_JSON as DEFAULT_SUPPORT_JSON,
    )
    from scripts.pre_tail_readiness_support import read_json
except ModuleNotFoundError:  # pragma: no cover
    from export_elm_support_preview import (
        DEFAULT_ELM_CLASSES,
        DEFAULT_ELM_INTERACTIONS,
        DEFAULT_TRAINING_SET,
        build_elm_support_preview,
    )
    from export_elm_support_preview import (
        DEFAULT_OUTPUT_JSON as DEFAULT_SUPPORT_JSON,
    )
    from pre_tail_readiness_support import read_json

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "elm_support_validation_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "elm_support_validation_preview.md"


def build_elm_support_validation_preview(payload: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    summary = payload.get("summary") or {}
    rows = [row for row in payload.get("rows") or [] if isinstance(row, dict)]
    if payload.get("status") != "complete":
        issues.append("ELM support preview must be complete")
    if int(summary.get("elm_class_catalog_count") or 0) <= 0:
        issues.append("ELM class catalog must contain at least one row")
    if int(summary.get("elm_interaction_row_count") or 0) <= 0:
        issues.append("ELM interaction TSV must contain at least one row")
    if int(summary.get("cohort_accession_count") or 0) != len(rows):
        issues.append("cohort_accession_count must match emitted rows")
    if any("candidate_only_non_governing" not in row for row in rows):
        issues.append("all emitted rows must carry candidate_only_non_governing")
    if not summary.get("supported_accessions"):
        warnings.append("no cohort accessions overlapped the local ELM interaction domain table")

    status = "aligned" if not issues else "attention_needed"
    return {
        "artifact_id": "elm_support_validation_preview",
        "schema_id": "proteosphere-elm-support-validation-preview-2026-04-05",
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "validation": {
            "issue_count": len(issues),
            "warning_count": len(warnings),
            "cohort_accession_count": int(summary.get("cohort_accession_count") or 0),
            "supported_accession_count": int(summary.get("cohort_supported_accession_count") or 0),
            "issues": issues,
            "warnings": warnings,
        },
        "truth_boundary": {
            "summary": (
                "This validation confirms the local ELM TSV snapshots are parseable "
                "and cohort-scoped. "
                "It does not promote ELM-derived rows beyond candidate-only status."
            ),
            "report_only": True,
            "candidate_only_non_governing": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    validation = payload.get("validation") or {}
    lines = [
        "# ELM Support Validation Preview",
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
    parser = argparse.ArgumentParser(
        description="Validate the accession-scoped ELM support preview."
    )
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--elm-classes", type=Path, default=DEFAULT_ELM_CLASSES)
    parser.add_argument("--elm-interactions", type=Path, default=DEFAULT_ELM_INTERACTIONS)
    parser.add_argument("--support-json", type=Path, default=DEFAULT_SUPPORT_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.support_json.exists():
        support_payload = json.loads(args.support_json.read_text(encoding="utf-8"))
    else:
        support_payload = build_elm_support_preview(
            read_json(args.training_set),
            elm_classes_path=args.elm_classes,
            elm_interactions_path=args.elm_interactions,
        )
    payload = build_elm_support_validation_preview(support_payload)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
