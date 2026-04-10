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

DEFAULT_STRUCTURE_PROJECTION = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_structure_measurement_projection_preview.json"
)
DEFAULT_BINDINGDB_MEASUREMENT_SUBSET = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_measurement_subset_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_structure_assay_summary_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "bindingdb_structure_assay_summary_preview.md"
)


def build_bindingdb_structure_assay_summary_preview(
    bindingdb_structure_measurement_projection_preview: dict[str, Any],
    bindingdb_measurement_subset_preview: dict[str, Any],
) -> dict[str, Any]:
    measurements_by_accession: dict[str, list[dict[str, Any]]] = {}
    for row in bindingdb_measurement_subset_preview.get("rows") or []:
        accession = str(row.get("accession") or "").strip()
        if accession:
            measurements_by_accession.setdefault(accession, []).append(row)

    rows = []
    for projection_row in bindingdb_structure_measurement_projection_preview.get("rows") or []:
        if not isinstance(projection_row, dict):
            continue
        matched_measurements = []
        polymer_ids = {
            str(polymer_id).strip()
            for polymer_id in projection_row.get("bindingdb_bridge_polymer_ids") or []
            if str(polymer_id).strip()
        }
        for accession in projection_row.get("matched_accessions") or []:
            for measurement in measurements_by_accession.get(str(accession), []):
                measurement_polymer_id = str(measurement.get("bindingdb_polymer_id") or "").strip()
                if polymer_ids and measurement_polymer_id not in polymer_ids:
                    continue
                matched_measurements.append(measurement)

        assay_name_counts = Counter(
            str(row.get("bindingdb_assay_name") or "").strip()
            for row in matched_measurements
            if str(row.get("bindingdb_assay_name") or "").strip()
        )
        technique_counts = Counter(
            str(row.get("bindingdb_measurement_technique") or "").strip()
            for row in matched_measurements
            if str(row.get("bindingdb_measurement_technique") or "").strip()
        )
        partner_names = []
        for measurement in matched_measurements:
            for monomer_ref in measurement.get("bindingdb_partner_monomer_refs") or []:
                name = str(
                    monomer_ref.get("display_name")
                    or monomer_ref.get("monomer_id")
                    or ""
                ).strip()
                if name and name not in partner_names:
                    partner_names.append(name)

        rows.append(
            {
                "structure_id": projection_row.get("structure_id"),
                "bindingdb_projection_status": projection_row.get("bindingdb_projection_status"),
                "matched_accessions": projection_row.get("matched_accessions") or [],
                "measurement_count": len(matched_measurements),
                "measurement_type_counts": projection_row.get("measurement_type_counts") or {},
                "top_assay_names": [
                    name for name, _ in assay_name_counts.most_common(5)
                ],
                "measurement_technique_counts": dict(sorted(technique_counts.items())),
                "partner_monomer_name_sample": partner_names[:10],
            }
        )

    return {
        "artifact_id": "bindingdb_structure_assay_summary_preview",
        "schema_id": "proteosphere-bindingdb-structure-assay-summary-preview-2026-04-03",
        "status": "report_only_local_projection",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "structures_with_assay_summary": sum(
                1 for row in rows if row.get("measurement_count", 0) > 0
            ),
            "structures_with_measurement_technique": sum(
                1 for row in rows if row.get("measurement_technique_counts")
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a compact, report-only summary of BindingDB-linked assay evidence "
                "projected onto currently harvested structures."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Structure Assay Summary Preview",
        "",
        f"- Structures: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['structure_id']}` / `{row['bindingdb_projection_status']}` / "
            f"measurements `{row['measurement_count']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build BindingDB structure assay summary preview."
    )
    parser.add_argument(
        "--structure-projection",
        type=Path,
        default=DEFAULT_STRUCTURE_PROJECTION,
    )
    parser.add_argument(
        "--bindingdb-measurement-subset",
        type=Path,
        default=DEFAULT_BINDINGDB_MEASUREMENT_SUBSET,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_structure_assay_summary_preview(
        read_json(args.structure_projection),
        read_json(args.bindingdb_measurement_subset),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
