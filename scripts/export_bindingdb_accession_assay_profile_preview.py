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
DEFAULT_STRUCTURE_PROJECTION = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_structure_measurement_projection_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_accession_assay_profile_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "bindingdb_accession_assay_profile_preview.md"
)


def _sorted_counter(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))


def build_bindingdb_accession_assay_profile_preview(
    bindingdb_measurement_subset_preview: dict[str, Any],
    bindingdb_structure_measurement_projection_preview: dict[str, Any],
) -> dict[str, Any]:
    projected_structure_ids_by_accession: dict[str, set[str]] = {}
    for row in bindingdb_structure_measurement_projection_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        structure_id = str(row.get("structure_id") or "").strip()
        if not structure_id:
            continue
        for accession in row.get("matched_accessions") or []:
            accession_text = str(accession or "").strip()
            if accession_text:
                projected_structure_ids_by_accession.setdefault(accession_text, set()).add(
                    structure_id
                )

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
                "measurement_type_counts": Counter(),
                "measurement_technique_counts": Counter(),
                "target_role_counts": Counter(),
                "assay_name_counts": Counter(),
                "entry_title_counts": Counter(),
                "partner_name_counts": Counter(),
                "measurement_count": 0,
                "exact_measurement_count": 0,
                "normalized_measurement_count": 0,
                "reported_delta_g_count": 0,
                "derived_delta_g_count": 0,
                "structure_linked_measurement_count": 0,
            },
        )
        state["measurement_count"] += 1
        measurement_type = str(row.get("measurement_type") or "unknown").strip() or "unknown"
        state["measurement_type_counts"][measurement_type] += 1
        if str(row.get("relation") or "").strip() == "=":
            state["exact_measurement_count"] += 1
        if row.get("value_molar_normalized") is not None:
            state["normalized_measurement_count"] += 1
        if row.get("delta_g_reported_kcal_per_mol") is not None:
            state["reported_delta_g_count"] += 1
        if row.get("delta_g_derived_298k_kcal_per_mol") is not None:
            state["derived_delta_g_count"] += 1
        technique = str(row.get("bindingdb_measurement_technique") or "").strip()
        if technique:
            state["measurement_technique_counts"][technique] += 1
        target_role = str(row.get("bindingdb_target_role") or "").strip()
        if target_role:
            state["target_role_counts"][target_role] += 1
        assay_name = str(row.get("bindingdb_assay_name") or "").strip()
        if assay_name:
            state["assay_name_counts"][assay_name] += 1
        entry_title = str(row.get("bindingdb_entry_title") or "").strip()
        if entry_title:
            state["entry_title_counts"][entry_title] += 1
        partner_refs = row.get("bindingdb_partner_monomer_refs") or []
        if projected_structure_ids_by_accession.get(accession):
            state["structure_linked_measurement_count"] += 1
        for partner_ref in partner_refs:
            partner_name = str(
                partner_ref.get("display_name") or partner_ref.get("monomer_id") or ""
            ).strip()
            if partner_name:
                state["partner_name_counts"][partner_name] += 1

    rows = []
    for accession, state in sorted(accession_states.items()):
        projected_structure_ids = sorted(projected_structure_ids_by_accession.get(accession, set()))
        rows.append(
            {
                "accession": accession,
                "measurement_count": state["measurement_count"],
                "exact_measurement_count": state["exact_measurement_count"],
                "normalized_measurement_count": state["normalized_measurement_count"],
                "reported_delta_g_count": state["reported_delta_g_count"],
                "derived_delta_g_count": state["derived_delta_g_count"],
                "structure_linked_measurement_count": state["structure_linked_measurement_count"],
                "projected_structure_ids": projected_structure_ids,
                "projected_structure_count": len(projected_structure_ids),
                "measurement_type_counts": _sorted_counter(state["measurement_type_counts"]),
                "measurement_technique_counts": _sorted_counter(
                    state["measurement_technique_counts"]
                ),
                "target_role_counts": _sorted_counter(state["target_role_counts"]),
                "top_assay_names": [
                    name for name, _ in state["assay_name_counts"].most_common(5)
                ],
                "top_entry_titles": [
                    title for title, _ in state["entry_title_counts"].most_common(3)
                ],
                "top_partner_monomer_names": [
                    name for name, _ in state["partner_name_counts"].most_common(8)
                ],
            }
        )

    return {
        "artifact_id": "bindingdb_accession_assay_profile_preview",
        "schema_id": "proteosphere-bindingdb-accession-assay-profile-preview-2026-04-03",
        "status": "report_only_local_projection",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_assay_profile": len(rows),
            "accessions_with_projected_structure_support": sum(
                1 for row in rows if row.get("projected_structure_count", 0) > 0
            ),
            "accessions_with_direct_thermodynamics": sum(
                1 for row in rows if row.get("reported_delta_g_count", 0) > 0
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a compact, report-only BindingDB assay profile by accession built "
                "from locally joined measurement rows and current structure projections."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Accession Assay Profile Preview",
        "",
        f"- Accessions: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['accession']}` / measurements `{row['measurement_count']}` / "
            f"projected structures `{row['projected_structure_count']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact BindingDB accession assay profile preview."
    )
    parser.add_argument(
        "--bindingdb-measurement-subset",
        type=Path,
        default=DEFAULT_BINDINGDB_MEASUREMENT_SUBSET,
    )
    parser.add_argument(
        "--structure-projection",
        type=Path,
        default=DEFAULT_STRUCTURE_PROJECTION,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_accession_assay_profile_preview(
        read_json(args.bindingdb_measurement_subset),
        read_json(args.structure_projection),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
