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

DEFAULT_STRUCTURE_ENTRY_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "structure_entry_context_preview.json"
)
DEFAULT_BINDINGDB_STRUCTURE_BRIDGE = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_structure_bridge_preview.json"
)
DEFAULT_BINDINGDB_MEASUREMENT_SUBSET = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_measurement_subset_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_structure_measurement_projection_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "bindingdb_structure_measurement_projection_preview.md"
)


def build_bindingdb_structure_measurement_projection_preview(
    structure_entry_context_preview: dict[str, Any],
    bindingdb_structure_bridge_preview: dict[str, Any],
    bindingdb_measurement_subset_preview: dict[str, Any],
) -> dict[str, Any]:
    bridge_by_structure = {
        str(row.get("structure_id") or "").strip().upper(): row
        for row in bindingdb_structure_bridge_preview.get("rows") or []
        if isinstance(row, dict)
    }
    measurements_by_accession: dict[str, list[dict[str, Any]]] = {}
    for row in bindingdb_measurement_subset_preview.get("rows") or []:
        accession = str(row.get("accession") or "").strip()
        if accession:
            measurements_by_accession.setdefault(accession, []).append(row)

    rows = []
    for structure_row in structure_entry_context_preview.get("rows") or []:
        if not isinstance(structure_row, dict):
            continue
        structure_id = str(structure_row.get("structure_id") or "").strip().upper()
        bridge_row = bridge_by_structure.get(structure_id, {})
        bridge_polymer_ids = {
            str(polymer_id).strip()
            for polymer_id in bridge_row.get("bindingdb_polymer_ids") or []
            if str(polymer_id).strip()
        }
        mapped_accessions = [
            str(accession).strip()
            for accession in structure_row.get("mapped_uniprot_accessions") or []
            if str(accession).strip()
        ]
        matched_measurements = []
        matched_accessions = set()
        if bridge_polymer_ids:
            for accession in mapped_accessions:
                for measurement in measurements_by_accession.get(accession, []):
                    measurement_polymer_id = str(
                        measurement.get("bindingdb_polymer_id") or ""
                    ).strip()
                    if measurement_polymer_id not in bridge_polymer_ids:
                        continue
                    matched_measurements.append(measurement)
                    matched_accessions.add(accession)

        measurement_type_counts = Counter(
            str(row.get("measurement_type") or "unknown") for row in matched_measurements
        )
        entry_titles = []
        assay_names = []
        partner_monomers = []
        for measurement in matched_measurements:
            entry_title = str(measurement.get("bindingdb_entry_title") or "").strip()
            assay_name = str(measurement.get("bindingdb_assay_name") or "").strip()
            if entry_title and entry_title not in entry_titles:
                entry_titles.append(entry_title)
            if assay_name and assay_name not in assay_names:
                assay_names.append(assay_name)
            for partner_name in measurement.get("bindingdb_partner_monomer_names") or []:
                if partner_name and partner_name not in partner_monomers:
                    partner_monomers.append(partner_name)

        rows.append(
            {
                "structure_id": structure_id,
                "bindingdb_projection_status": (
                    "present" if matched_measurements else "bridge_only_or_absent"
                ),
                "mapped_uniprot_accessions": mapped_accessions,
                "matched_accessions": sorted(matched_accessions),
                "bindingdb_bridge_polymer_ids": sorted(bridge_polymer_ids),
                "measurement_count": len(matched_measurements),
                "measurement_type_counts": dict(sorted(measurement_type_counts.items())),
                "bindingdb_entry_titles_sample": entry_titles[:10],
                "bindingdb_assay_names_sample": assay_names[:10],
                "bindingdb_partner_monomer_names_sample": partner_monomers[:10],
            }
        )

    return {
        "artifact_id": "bindingdb_structure_measurement_projection_preview",
        "schema_id": (
            "proteosphere-bindingdb-structure-measurement-projection-preview-2026-04-03"
        ),
        "status": "report_only_local_projection",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "structures_with_bindingdb_measurements": sum(
                1 for row in rows if row["bindingdb_projection_status"] == "present"
            ),
            "structures_without_bindingdb_measurements": sum(
                1 for row in rows if row["bindingdb_projection_status"] != "present"
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only projection of locally joined BindingDB measurements "
                "onto currently harvested structures using the local BindingDB PDB bridge "
                "and mapped UniProt accessions."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Structure Measurement Projection Preview",
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
        description="Build BindingDB structure measurement projection preview."
    )
    parser.add_argument(
        "--structure-entry-context",
        type=Path,
        default=DEFAULT_STRUCTURE_ENTRY_CONTEXT,
    )
    parser.add_argument(
        "--bindingdb-structure-bridge",
        type=Path,
        default=DEFAULT_BINDINGDB_STRUCTURE_BRIDGE,
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
    payload = build_bindingdb_structure_measurement_projection_preview(
        read_json(args.structure_entry_context),
        read_json(args.bindingdb_structure_bridge),
        read_json(args.bindingdb_measurement_subset),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
