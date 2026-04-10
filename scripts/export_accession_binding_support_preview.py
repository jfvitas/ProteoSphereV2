from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import (
        accession_rows,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import accession_rows, read_json, write_json, write_text

DEFAULT_TRAINING_SET = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_REGISTRY = REPO_ROOT / "artifacts" / "status" / "binding_measurement_registry_preview.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "accession_binding_support_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "accession_binding_support_preview.md"


def build_accession_binding_support_preview(
    training_set_eligibility_matrix_preview: dict[str, Any],
    binding_measurement_registry_preview: dict[str, Any],
) -> dict[str, Any]:
    by_accession: dict[str, list[dict[str, Any]]] = {}
    for row in binding_measurement_registry_preview.get("rows") or []:
        accession = str(row.get("accession") or "").strip()
        if accession:
            by_accession.setdefault(accession, []).append(row)

    rows = []
    for training_row in accession_rows(training_set_eligibility_matrix_preview):
        accession = training_row["accession"]
        measurements = by_accession.get(accession, [])
        measurement_type_counts: dict[str, int] = {}
        for measurement in measurements:
            key = str(measurement.get("measurement_type") or "unknown")
            measurement_type_counts[key] = measurement_type_counts.get(key, 0) + 1
        rows.append(
            {
                "accession": accession,
                "protein_ref": training_row.get("protein_ref"),
                "measurement_count": len(measurements),
                "measurement_type_counts": measurement_type_counts,
                "direct_delta_g_count": sum(
                    1
                    for row in measurements
                    if row.get("delta_g_reported_kcal_per_mol") is not None
                ),
                "derived_delta_g_count": sum(
                    1
                    for row in measurements
                    if row.get("delta_g_derived_298k_kcal_per_mol") is not None
                ),
                "best_p_affinity": max(
                    (
                        float(row["p_affinity"])
                        for row in measurements
                        if row.get("p_affinity") is not None
                    ),
                    default=None,
                ),
                "binding_support_status": (
                    "grounded preview-safe"
                    if any(not row.get("candidate_only", False) for row in measurements)
                    else "support-only"
                    if measurements
                    else "absent"
                ),
            }
        )

    return {
        "artifact_id": "accession_binding_support_preview",
        "schema_id": "proteosphere-accession-binding-support-preview-2026-04-03",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_measurements": sum(1 for row in rows if row["measurement_count"] > 0),
            "support_status_counts": {
                key: sum(1 for row in rows if row["binding_support_status"] == key)
                for key in ("grounded preview-safe", "support-only", "absent")
            },
        },
        "truth_boundary": {
            "summary": (
                "This accession-level support view summarizes current parsed binding evidence "
                "without changing ligand or split governance."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Accession Binding Support Preview",
        "",
        f"- Accessions: `{payload['row_count']}`",
        "",
    ]
    for row in payload["rows"]:
        if row["measurement_count"]:
            lines.append(
                f"- `{row['accession']}` / `{row['binding_support_status']}` / "
                f"measurements `{row['measurement_count']}`"
            )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build accession-level binding support summaries.")
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_accession_binding_support_preview(
        read_json(args.training_set),
        read_json(args.registry),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
