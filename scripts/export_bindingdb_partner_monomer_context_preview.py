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

DEFAULT_BINDINGDB_MEASUREMENT_SUBSET = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_measurement_subset_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_partner_monomer_context_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "bindingdb_partner_monomer_context_preview.md"
)


def build_bindingdb_partner_monomer_context_preview(
    bindingdb_measurement_subset_preview: dict[str, Any],
) -> dict[str, Any]:
    monomer_rows: dict[str, dict[str, Any]] = {}
    for row in bindingdb_measurement_subset_preview.get("rows") or []:
        accession = str(row.get("accession") or "").strip()
        structure_ref = str(row.get("primary_structure_or_target_ref") or "").strip()
        for monomer_ref in row.get("bindingdb_partner_monomer_refs") or []:
            monomer_id = str(monomer_ref.get("monomer_id") or "").strip()
            if not monomer_id:
                continue
            state = monomer_rows.setdefault(
                monomer_id,
                {
                    "bindingdb_monomer_id": monomer_id,
                    "display_name": monomer_ref.get("display_name"),
                    "chembl_id": monomer_ref.get("chembl_id"),
                    "het_pdb": monomer_ref.get("het_pdb"),
                    "type": monomer_ref.get("type"),
                    "inchi_key_present": bool(monomer_ref.get("inchi_key_present")),
                    "smiles_present": bool(monomer_ref.get("smiles_present")),
                    "pdb_ids_exact_sample": monomer_ref.get("pdb_ids_exact_sample") or [],
                    "linked_accessions": set(),
                    "linked_measurement_ids": set(),
                    "linked_structure_refs": set(),
                },
            )
            if accession:
                state["linked_accessions"].add(accession)
            if row.get("measurement_id"):
                state["linked_measurement_ids"].add(str(row["measurement_id"]))
            if structure_ref:
                state["linked_structure_refs"].add(structure_ref)

    rows = []
    for monomer_id, row in sorted(monomer_rows.items()):
        rows.append(
            {
                "bindingdb_monomer_id": monomer_id,
                "display_name": row["display_name"],
                "chembl_id": row["chembl_id"],
                "het_pdb": row["het_pdb"],
                "type": row["type"],
                "inchi_key_present": row["inchi_key_present"],
                "smiles_present": row["smiles_present"],
                "pdb_ids_exact_sample": row["pdb_ids_exact_sample"],
                "linked_accessions": sorted(row["linked_accessions"]),
                "linked_structure_refs": sorted(row["linked_structure_refs"]),
                "linked_measurement_count": len(row["linked_measurement_ids"]),
            }
        )

    return {
        "artifact_id": "bindingdb_partner_monomer_context_preview",
        "schema_id": "proteosphere-bindingdb-partner-monomer-context-preview-2026-04-03",
        "status": "report_only_local_projection",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "monomer_count": len(rows),
            "monomers_with_chembl_id": sum(1 for row in rows if row.get("chembl_id")),
            "monomers_with_smiles": sum(1 for row in rows if row.get("smiles_present")),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only partner-monomer context view derived from locally "
                "joined BindingDB measurement rows."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Partner Monomer Context Preview",
        "",
        f"- Monomers: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['bindingdb_monomer_id']}` / `{row.get('display_name')}` / "
            f"measurements `{row['linked_measurement_count']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build BindingDB partner monomer context preview."
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
    payload = build_bindingdb_partner_monomer_context_preview(
        read_json(args.bindingdb_measurement_subset)
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
