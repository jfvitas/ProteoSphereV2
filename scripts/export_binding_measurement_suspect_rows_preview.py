from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_REGISTRY = REPO_ROOT / "artifacts" / "status" / "binding_measurement_registry_preview.json"
DEFAULT_ACCESSION_SUPPORT = (
    REPO_ROOT / "artifacts" / "status" / "accession_binding_support_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "binding_measurement_suspect_rows_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "binding_measurement_suspect_rows_preview.md"
)

_ROW_LEVEL_SUSPECT_CONFIDENCES = {
    "bindingdb_exact_value_without_unit",
    "exact_relation_non_comparable",
    "non_exact_relation",
    "unparsed",
}


def _accession_support_map(accession_binding_support_preview: dict[str, Any]) -> dict[str, str]:
    support_map: dict[str, str] = {}
    for row in accession_binding_support_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if accession:
            support_map[accession] = str(row.get("binding_support_status") or "absent").strip()
    return support_map


def _row_suspect_reason_codes(
    row: dict[str, Any],
    accession_support_status: str,
) -> list[str]:
    reasons: list[str] = []
    if bool(row.get("candidate_only")):
        reasons.append("candidate_only")

    confidence = str(row.get("confidence_for_normalization") or "").strip()
    if confidence in _ROW_LEVEL_SUSPECT_CONFIDENCES:
        reasons.append(f"confidence:{confidence}")

    measurement_type = str(row.get("measurement_type") or "").strip()
    if not measurement_type:
        reasons.append("missing_measurement_type")

    if accession_support_status and accession_support_status != "grounded preview-safe":
        reasons.append(f"accession_support:{accession_support_status}")
    return reasons


def build_binding_measurement_suspect_rows_preview(
    binding_measurement_registry_preview: dict[str, Any],
    accession_binding_support_preview: dict[str, Any],
) -> dict[str, Any]:
    support_map = _accession_support_map(accession_binding_support_preview)
    suspect_rows: list[dict[str, Any]] = []

    for row in binding_measurement_registry_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        origin = str(row.get("measurement_origin") or "").strip()
        if origin not in {"chembl_lightweight", "bindingdb"}:
            continue

        accession = str(row.get("accession") or "").strip()
        support_status = support_map.get(accession, "absent") if accession else "absent"
        suspect_reason_codes = _row_suspect_reason_codes(row, support_status)
        if not suspect_reason_codes:
            continue

        suspect_rows.append(
            {
                "measurement_id": row.get("measurement_id"),
                "accession": accession,
                "measurement_origin": origin,
                "source_name": row.get("source_name"),
                "measurement_type": row.get("measurement_type"),
                "raw_binding_string": row.get("raw_binding_string"),
                "relation": row.get("relation"),
                "candidate_only": bool(row.get("candidate_only")),
                "confidence_for_normalization": row.get("confidence_for_normalization"),
                "accession_support_status": support_status,
                "suspect_reason_codes": suspect_reason_codes,
                "p_affinity": row.get("p_affinity"),
                "value_molar_normalized": row.get("value_molar_normalized"),
                "delta_g_derived_298k_kcal_per_mol": row.get(
                    "delta_g_derived_298k_kcal_per_mol"
                ),
            }
        )

    suspect_rows.sort(
        key=lambda row: (
            str(row.get("accession") or ""),
            str(row.get("measurement_origin") or ""),
            str(row.get("measurement_id") or ""),
        )
    )

    origin_counts = Counter(str(row.get("measurement_origin") or "unknown") for row in suspect_rows)
    support_status_counts = Counter(
        str(row.get("accession_support_status") or "unknown") for row in suspect_rows
    )
    reason_counts = Counter(
        reason for row in suspect_rows for reason in (row.get("suspect_reason_codes") or [])
    )
    accession_counts = Counter(str(row.get("accession") or "unknown") for row in suspect_rows)

    return {
        "artifact_id": "binding_measurement_suspect_rows_preview",
        "schema_id": "proteosphere-binding-measurement-suspect-rows-preview-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(suspect_rows),
        "rows": suspect_rows,
        "summary": {
            "registry_row_count": int(binding_measurement_registry_preview.get("row_count") or 0),
            "accession_support_row_count": int(
                accession_binding_support_preview.get("row_count") or 0
            ),
            "suspect_row_count": len(suspect_rows),
            "suspect_accession_count": len(accession_counts),
            "measurement_origin_counts": dict(origin_counts),
            "accession_support_status_counts": dict(support_status_counts),
            "suspect_reason_counts": dict(reason_counts),
            "top_suspect_accessions": [
                {"accession": accession, "row_count": count}
                for accession, count in accession_counts.most_common(10)
            ],
        },
        "truth_boundary": {
            "summary": (
                "This preview is report-only and non-governing. It highlights binding "
                "measurements that still need normalization or accession support review."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Binding Measurement Suspect Rows Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Suspect rows: `{payload.get('row_count')}`",
        f"- Suspect accessions: `{summary.get('suspect_accession_count')}`",
        "",
        "## Summary",
        "",
        f"- Registry rows: `{summary.get('registry_row_count')}`",
        f"- Accessions with support rows: `{summary.get('accession_support_row_count')}`",
    ]
    for key, value in sorted((summary.get("measurement_origin_counts") or {}).items()):
        lines.append(f"- `{key}` suspect rows: `{value}`")
    for key, value in sorted((summary.get("accession_support_status_counts") or {}).items()):
        lines.append(f"- `{key}` support status rows: `{value}`")
    lines.extend(["", "## Top Suspect Accessions", ""])
    for item in summary.get("top_suspect_accessions") or []:
        if not isinstance(item, dict):
            continue
        lines.append(f"- `{item.get('accession')}` -> `{item.get('row_count')}` rows")
    lines.extend(["", "## Sample Rows", ""])
    for row in payload.get("rows", [])[:20]:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- `{row.get('accession') or 'no accession'}` / "
            f"`{row.get('measurement_origin')}` / "
            f"`{', '.join(row.get('suspect_reason_codes') or [])}`"
        )
    truth_boundary = payload.get("truth_boundary") or {}
    if truth_boundary.get("summary"):
        lines.extend(["", "## Truth Boundary", "", f"- {truth_boundary['summary']}"])
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the binding measurement suspect rows preview."
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--accession-support", type=Path, default=DEFAULT_ACCESSION_SUPPORT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_binding_measurement_suspect_rows_preview(
        read_json(args.registry),
        read_json(args.accession_support),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
