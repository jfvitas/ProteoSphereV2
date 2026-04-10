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
    REPO_ROOT / "artifacts" / "status" / "bindingdb_structure_partner_profile_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "bindingdb_structure_partner_profile_preview.md"
)


def build_bindingdb_structure_partner_profile_preview(
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
        structure_id = str(projection_row.get("structure_id") or "").strip()
        if not structure_id:
            continue
        polymer_ids = {
            str(polymer_id).strip()
            for polymer_id in projection_row.get("bindingdb_bridge_polymer_ids") or []
            if str(polymer_id).strip()
        }
        partner_counts: Counter[str] = Counter()
        partner_metadata: dict[str, dict[str, Any]] = {}
        for accession in projection_row.get("matched_accessions") or []:
            for measurement in measurements_by_accession.get(str(accession), []):
                measurement_polymer_id = str(measurement.get("bindingdb_polymer_id") or "").strip()
                if polymer_ids and measurement_polymer_id not in polymer_ids:
                    continue
                for partner_ref in measurement.get("bindingdb_partner_monomer_refs") or []:
                    partner_key = str(
                        partner_ref.get("display_name") or partner_ref.get("monomer_id") or ""
                    ).strip()
                    if not partner_key:
                        continue
                    partner_counts[partner_key] += 1
                    partner_metadata.setdefault(
                        partner_key,
                        {
                            "bindingdb_monomer_id": partner_ref.get("monomer_id"),
                            "chembl_id": partner_ref.get("chembl_id"),
                            "smiles_present": bool(partner_ref.get("smiles_present")),
                            "inchi_key_present": bool(partner_ref.get("inchi_key_present")),
                            "pdb_ids_exact_sample": partner_ref.get("pdb_ids_exact_sample") or [],
                        },
                    )

        rows.append(
            {
                "structure_id": structure_id,
                "bindingdb_projection_status": projection_row.get("bindingdb_projection_status"),
                "measurement_count": projection_row.get("measurement_count", 0),
                "unique_partner_monomer_count": len(partner_counts),
                "top_partner_monomers": [
                    {
                        "display_name": partner_name,
                        "linked_measurement_count": count,
                        **partner_metadata.get(partner_name, {}),
                    }
                    for partner_name, count in partner_counts.most_common(10)
                ],
            }
        )

    return {
        "artifact_id": "bindingdb_structure_partner_profile_preview",
        "schema_id": "proteosphere-bindingdb-structure-partner-profile-preview-2026-04-03",
        "status": "report_only_local_projection",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "structures_with_partner_profile": sum(
                1 for row in rows if row.get("unique_partner_monomer_count", 0) > 0
            ),
            "structures_with_smiles_backed_partners": sum(
                1
                for row in rows
                if any(
                    partner.get("smiles_present")
                    for partner in row.get("top_partner_monomers") or []
                )
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only structure partner profile built from locally joined "
                "BindingDB measurements projected onto harvested structures."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Structure Partner Profile Preview",
        "",
        f"- Structures: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['structure_id']}` / partners `{row['unique_partner_monomer_count']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build BindingDB structure partner profile preview."
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
    payload = build_bindingdb_structure_partner_profile_preview(
        read_json(args.structure_projection),
        read_json(args.bindingdb_measurement_subset),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
