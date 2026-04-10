from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import fetch_json, read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import fetch_json, read_json, write_json, write_text

DEFAULT_STRUCTURE_ENTRY_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "structure_entry_context_preview.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "structure_ligand_context_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "structure_ligand_context_preview.md"


def _descriptor_value(descriptors: list[dict[str, Any]] | None, kind: str) -> str | None:
    for descriptor in descriptors or []:
        if str(descriptor.get("type") or "").lower() == kind.lower():
            value = descriptor.get("descriptor")
            if value:
                return str(value)
    return None


def build_structure_ligand_context_preview(
    structure_entry_context_preview: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for row in structure_entry_context_preview.get("rows") or []:
        structure_id = str(row.get("structure_id") or "").strip().upper()
        entry = fetch_json(f"https://data.rcsb.org/rest/v1/core/entry/{structure_id}")
        entity_ids = (entry.get("rcsb_entry_container_identifiers") or {}).get(
            "non_polymer_entity_ids"
        ) or []
        for entity_id in entity_ids:
            entity = fetch_json(
                f"https://data.rcsb.org/rest/v1/core/nonpolymer_entity/{structure_id}/{entity_id}"
            )
            identifiers = entity.get("rcsb_nonpolymer_entity_container_identifiers") or {}
            ccd_id = identifiers.get("nonpolymer_comp_id")
            chemcomp = (
                fetch_json(f"https://data.rcsb.org/rest/v1/core/chemcomp/{ccd_id}")
                if ccd_id
                else {}
            )
            comp = chemcomp.get("chem_comp") or {}
            descriptors = (
                chemcomp.get("pdbx_chem_comp_descriptor")
                or chemcomp.get("rcsb_chem_comp_descriptor")
                or []
            )
            rows.append(
                {
                    "structure_id": structure_id,
                    "entity_id": str(entity_id),
                    "ccd_id": ccd_id or comp.get("id"),
                    "formula": comp.get("formula"),
                    "formula_weight": comp.get("formula_weight"),
                    "name": comp.get("name")
                    or (entity.get("pdbx_entity_nonpoly") or {}).get("name")
                    or (entity.get("rcsb_nonpolymer_entity") or {}).get("pdbx_description"),
                    "inchi": _descriptor_value(descriptors, "InChI"),
                    "inchi_key": _descriptor_value(descriptors, "InChIKey"),
                    "smiles": _descriptor_value(descriptors, "SMILES"),
                }
            )
    return {
        "artifact_id": "structure_ligand_context_preview",
        "schema_id": "proteosphere-structure-ligand-context-preview-2026-04-03",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "structure_count": len({row["structure_id"] for row in rows}),
            "ligand_count": len(rows),
            "ccd_ids": sorted({row["ccd_id"] for row in rows if row.get("ccd_id")}),
        },
        "truth_boundary": {
            "summary": (
                "This is a structured bound-ligand harvest derived from RCSB "
                "nonpolymer entity metadata only."
            ),
            "report_only": True,
            "governing": False,
            "structured_sources_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Structure Ligand Context Preview",
        "",
        f"- Ligands: `{payload['row_count']}`",
        "",
    ]
    for row in payload["rows"]:
        lines.append(f"- `{row['structure_id']}` / `{row.get('ccd_id')}` / `{row.get('name')}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harvest structure ligand context.")
    parser.add_argument(
        "--structure-entry-context", type=Path, default=DEFAULT_STRUCTURE_ENTRY_CONTEXT
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_structure_ligand_context_preview(read_json(args.structure_entry_context))
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
