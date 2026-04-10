from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_REGISTRY = REPO_ROOT / "artifacts" / "status" / "binding_measurement_registry_preview.json"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "binding_measurement_validation_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "binding_measurement_validation_preview.md"


def build_binding_measurement_validation_preview(
    binding_measurement_registry_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = binding_measurement_registry_preview.get("rows") or []
    issues: list[str] = []
    representative_samples: dict[str, dict[str, Any]] = {}
    for complex_type in (
        "protein_ligand",
        "protein_protein",
        "protein_nucleic_acid",
        "nucleic_acid_ligand",
    ):
        sample = next(
            (
                row
                for row in rows
                if row.get("measurement_origin") == "pdbbind"
                and row.get("complex_type") == complex_type
            ),
            None,
        )
        if sample is None:
            issues.append(f"missing sample for {complex_type}")
        else:
            representative_samples[complex_type] = {
                "measurement_id": sample.get("measurement_id"),
                "raw_binding_string": sample.get("raw_binding_string"),
                "measurement_type": sample.get("measurement_type"),
                "confidence_for_normalization": sample.get("confidence_for_normalization"),
            }

    invalid_delta_g = [
        row["measurement_id"]
        for row in rows
        if row.get("measurement_type") in {"IC50", "EC50"}
        and row.get("delta_g_derived_298k_kcal_per_mol") is not None
    ]
    if invalid_delta_g:
        issues.append("delta_g may not be derived from IC50/EC50 rows")

    return {
        "artifact_id": "binding_measurement_validation_preview",
        "schema_id": "proteosphere-binding-measurement-validation-preview-2026-04-03",
        "status": "aligned" if not issues else "review_required",
        "generated_at": datetime.now(UTC).isoformat(),
        "validated_row_count": len(rows),
        "representative_samples": representative_samples,
        "issues": issues,
        "truth_boundary": {
            "summary": (
                "This validation preview checks row-shape integrity for the local binding "
                "measurement registry. It is report-only and non-governing."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Binding Measurement Validation Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Validated rows: `{payload['validated_row_count']}`",
        "",
    ]
    for complex_type, sample in (payload.get("representative_samples") or {}).items():
        lines.append(
            f"- `{complex_type}` / `{sample['raw_binding_string']}` / "
            f"`{sample['confidence_for_normalization']}`"
        )
    if payload.get("issues"):
        lines.append("")
        for issue in payload["issues"]:
            lines.append(f"- issue: {issue}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the binding measurement registry preview."
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_binding_measurement_validation_preview(read_json(args.registry))
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
