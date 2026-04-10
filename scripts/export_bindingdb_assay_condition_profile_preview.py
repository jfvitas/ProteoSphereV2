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

DEFAULT_BINDINGDB_MEASUREMENT_SUBSET = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_measurement_subset_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_assay_condition_profile_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "bindingdb_assay_condition_profile_preview.md"
)


def _range_from_values(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    return {
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def build_bindingdb_assay_condition_profile_preview(
    bindingdb_measurement_subset_preview: dict[str, Any],
) -> dict[str, Any]:
    accession_states: dict[str, dict[str, Any]] = {}
    for row in bindingdb_measurement_subset_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        state = accession_states.setdefault(
            accession,
            {
                "measurement_count": 0,
                "rows_with_reported_pH": 0,
                "rows_with_reported_temperature": 0,
                "rows_with_i_conc_range": 0,
                "rows_with_e_conc_range": 0,
                "rows_with_s_conc_range": 0,
                "pH_values": [],
                "temperature_values": [],
                "technique_counts": Counter(),
                "assay_name_counts": Counter(),
            },
        )
        state["measurement_count"] += 1
        reported_pH = row.get("reported_pH")
        if reported_pH is not None:
            state["rows_with_reported_pH"] += 1
            state["pH_values"].append(float(reported_pH))
        reported_temperature = row.get("reported_temperature_celsius")
        if reported_temperature is not None:
            state["rows_with_reported_temperature"] += 1
            state["temperature_values"].append(float(reported_temperature))
        assay_context = row.get("assay_context") or {}
        if assay_context.get("i_conc_range"):
            state["rows_with_i_conc_range"] += 1
        if assay_context.get("e_conc_range"):
            state["rows_with_e_conc_range"] += 1
        if assay_context.get("s_conc_range"):
            state["rows_with_s_conc_range"] += 1
        technique = str(row.get("bindingdb_measurement_technique") or "").strip()
        if technique:
            state["technique_counts"][technique] += 1
        assay_name = str(row.get("bindingdb_assay_name") or "").strip()
        if assay_name:
            state["assay_name_counts"][assay_name] += 1

    rows = []
    for accession, state in sorted(accession_states.items()):
        rows.append(
            {
                "accession": accession,
                "measurement_count": state["measurement_count"],
                "rows_with_reported_pH": state["rows_with_reported_pH"],
                "rows_with_reported_temperature": state["rows_with_reported_temperature"],
                "rows_with_i_conc_range": state["rows_with_i_conc_range"],
                "rows_with_e_conc_range": state["rows_with_e_conc_range"],
                "rows_with_s_conc_range": state["rows_with_s_conc_range"],
                "reported_pH_range": _range_from_values(state["pH_values"]),
                "reported_temperature_celsius_range": _range_from_values(
                    state["temperature_values"]
                ),
                "measurement_technique_counts": dict(sorted(state["technique_counts"].items())),
                "top_assay_names": [
                    name for name, _ in state["assay_name_counts"].most_common(5)
                ],
            }
        )

    return {
        "artifact_id": "bindingdb_assay_condition_profile_preview",
        "schema_id": "proteosphere-bindingdb-assay-condition-profile-preview-2026-04-03",
        "status": "report_only_local_projection",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_condition_profile": len(rows),
            "accessions_with_reported_pH": sum(
                1 for row in rows if row.get("rows_with_reported_pH", 0) > 0
            ),
            "accessions_with_reported_temperature": sum(
                1 for row in rows if row.get("rows_with_reported_temperature", 0) > 0
            ),
            "accessions_with_concentration_ranges": sum(
                1
                for row in rows
                if (
                    row.get("rows_with_i_conc_range", 0) > 0
                    or row.get("rows_with_e_conc_range", 0) > 0
                    or row.get("rows_with_s_conc_range", 0) > 0
                )
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a compact, report-only BindingDB assay condition summary by accession "
                "built from locally joined measurement rows."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Assay Condition Profile Preview",
        "",
        f"- Accessions: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['accession']}` / pH rows `{row['rows_with_reported_pH']}` / "
            f"temperature rows `{row['rows_with_reported_temperature']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build BindingDB assay condition profile preview."
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
    payload = build_bindingdb_assay_condition_profile_preview(
        read_json(args.bindingdb_measurement_subset)
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
