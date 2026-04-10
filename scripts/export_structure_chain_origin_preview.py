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
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "structure_chain_origin_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "structure_chain_origin_preview.md"


def _first_name(rows: list[dict[str, Any]] | None, key: str) -> str | None:
    for row in rows or []:
        value = row.get(key)
        if value:
            return str(value).strip()
    return None


def _rows_for_structure(structure_id: str) -> list[dict[str, Any]]:
    entry = fetch_json(f"https://data.rcsb.org/rest/v1/core/entry/{structure_id}")
    entity_ids = (entry.get("rcsb_entry_container_identifiers") or {}).get(
        "polymer_entity_ids"
    ) or []
    rows: list[dict[str, Any]] = []
    for entity_id in entity_ids:
        entity = fetch_json(
            f"https://data.rcsb.org/rest/v1/core/polymer_entity/{structure_id}/{entity_id}"
        )
        identifiers = entity.get("rcsb_polymer_entity_container_identifiers") or {}
        chain_ids = identifiers.get("auth_asym_ids") or identifiers.get("asym_ids") or []
        source_orgs = entity.get("rcsb_entity_source_organism") or []
        host_orgs = entity.get("rcsb_entity_host_organism") or []
        for chain_id in chain_ids:
            rows.append(
                {
                    "structure_id": structure_id,
                    "entity_id": str(entity_id),
                    "chain_id": str(chain_id),
                    "entity_description": (entity.get("rcsb_polymer_entity") or {}).get(
                        "pdbx_description"
                    ),
                    "polymer_type": (entity.get("entity_poly") or {}).get("type"),
                    "source_organism": _first_name(source_orgs, "scientific_name"),
                    "expression_host": _first_name(host_orgs, "scientific_name"),
                    "engineered_flag": bool(source_orgs or host_orgs),
                    "uniprot_mapping_count": len(identifiers.get("uniprot_ids") or []),
                }
            )
    return rows


def build_structure_chain_origin_preview(
    structure_entry_context_preview: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for row in structure_entry_context_preview.get("rows") or []:
        structure_id = str(row.get("structure_id") or "").strip().upper()
        if not structure_id:
            continue
        rows.extend(_rows_for_structure(structure_id))
    return {
        "artifact_id": "structure_chain_origin_preview",
        "schema_id": "proteosphere-structure-chain-origin-preview-2026-04-03",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "structure_count": len({row["structure_id"] for row in rows}),
            "chain_count": len(rows),
        },
        "truth_boundary": {
            "summary": (
                "This is a structured chain-origin harvest derived from "
                "RCSB polymer-entity metadata only."
            ),
            "report_only": True,
            "governing": False,
            "structured_sources_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Structure Chain Origin Preview",
        "",
        f"- Chains: `{payload['row_count']}`",
        "",
    ]
    for row in payload["rows"][:10]:
        lines.append(
            f"- `{row['structure_id']}:{row['chain_id']}` / `{row.get('source_organism')}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harvest structure chain origin context.")
    parser.add_argument(
        "--structure-entry-context", type=Path, default=DEFAULT_STRUCTURE_ENTRY_CONTEXT
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_structure_chain_origin_preview(read_json(args.structure_entry_context))
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
