from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from web_enrichment_preview_support import read_json, write_json, write_text
DEFAULT_PDB_ENRICHMENT_SCRAPE_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "pdb_enrichment_scrape_registry_preview.json"
)
DEFAULT_STRUCTURE_ENTRY_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "structure_entry_context_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_enrichment_harvest_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "pdb_enrichment_harvest_preview.md"
)


def build_pdb_enrichment_harvest_preview(
    pdb_enrichment_scrape_registry_preview: dict[str, Any],
    structure_entry_context_preview: dict[str, Any],
) -> dict[str, Any]:
    registry_rows = {
        str(row.get("structure_id") or "").strip().upper(): row
        for row in (pdb_enrichment_scrape_registry_preview.get("rows") or [])
        if isinstance(row, dict)
    }
    rows = []
    for row in structure_entry_context_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        structure_id = str(row.get("structure_id") or "").strip().upper()
        registry_row = registry_rows.get(structure_id) or {}
        source_statuses = row.get("source_api_statuses") or {}
        successful_source_count = sum(
            1 for status in source_statuses.values() if status == "ok"
        )
        expected_source_count = len(registry_row.get("structured_sources") or [])
        rows.append(
            {
                "structure_id": structure_id,
                "seed_accessions": row.get("seed_accessions") or [],
                "successful_source_count": successful_source_count,
                "expected_source_count": expected_source_count,
                "mapped_uniprot_accession_count": len(
                    row.get("mapped_uniprot_accessions") or []
                ),
                "bound_component_count": len(
                    row.get("nonpolymer_bound_components") or []
                ),
                "harvest_status": (
                    "complete"
                    if expected_source_count
                    and successful_source_count == expected_source_count
                    else "partial"
                ),
            }
        )
    return {
        "artifact_id": "pdb_enrichment_harvest_preview",
        "schema_id": "proteosphere-pdb-enrichment-harvest-preview-2026-04-02",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "harvested_structure_count": len(rows),
            "successful_source_call_count": sum(
                row["successful_source_count"] for row in rows
            ),
            "expected_source_call_count": sum(row["expected_source_count"] for row in rows),
        },
        "truth_boundary": {
            "summary": (
                "This is a harvest-status summary for structured PDB enrichment only. It is "
                "report-only and non-governing."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# PDB Enrichment Harvest Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Structures harvested: `{payload['summary']['harvested_structure_count']}`",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['structure_id']}` / `{row['harvest_status']}` / "
            f"sources `{row['successful_source_count']}/{row['expected_source_count']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize the structured PDB enrichment harvest."
    )
    parser.add_argument(
        "--pdb-enrichment-scrape-registry",
        type=Path,
        default=DEFAULT_PDB_ENRICHMENT_SCRAPE_REGISTRY,
    )
    parser.add_argument(
        "--structure-entry-context",
        type=Path,
        default=DEFAULT_STRUCTURE_ENTRY_CONTEXT,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_pdb_enrichment_harvest_preview(
        read_json(args.pdb_enrichment_scrape_registry),
        read_json(args.structure_entry_context),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
