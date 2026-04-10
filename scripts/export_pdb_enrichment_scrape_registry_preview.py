from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import (
        collect_seed_structures,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from web_enrichment_preview_support import (
        collect_seed_structures,
        read_json,
        write_json,
        write_text,
    )
DEFAULT_STRUCTURE_UNIT_SUMMARY_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "structure_unit_summary_library.json"
)
DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "q9nzd4_bridge_validation_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_enrichment_scrape_registry_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "pdb_enrichment_scrape_registry_preview.md"
)


def build_pdb_enrichment_scrape_registry_preview(
    structure_unit_summary_library: dict[str, Any],
    q9nzd4_bridge_validation_preview: dict[str, Any] | None,
) -> dict[str, Any]:
    rows = []
    for seed in collect_seed_structures(
        structure_unit_summary_library,
        q9nzd4_bridge_validation_preview,
    ):
        structure_id = seed["structure_id"]
        structure_id_lower = structure_id.lower()
        rows.append(
            {
                **seed,
                "structured_sources": [
                    {
                        "source_id": "rcsb_core_entry",
                        "url": f"https://data.rcsb.org/rest/v1/core/entry/{structure_id}",
                    },
                    {
                        "source_id": "pdbe_entry_summary",
                        "url": f"https://www.ebi.ac.uk/pdbe/api/pdb/entry/summary/{structure_id_lower}",
                    },
                    {
                        "source_id": "sifts_uniprot_mapping",
                        "url": f"https://www.ebi.ac.uk/pdbe/api/mappings/uniprot/{structure_id_lower}",
                    },
                ],
                "default_ingest_status": "support-only",
            }
        )
    return {
        "artifact_id": "pdb_enrichment_scrape_registry_preview",
        "schema_id": "proteosphere-pdb-enrichment-scrape-registry-preview-2026-04-02",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "seed_structure_ids": [row["structure_id"] for row in rows],
            "default_ingest_statuses": {
                row["structure_id"]: row["default_ingest_status"] for row in rows
            },
            "structured_source_ids": [
                "rcsb_core_entry",
                "pdbe_entry_summary",
                "sifts_uniprot_mapping",
            ],
        },
        "truth_boundary": {
            "summary": (
                "This registry defines the first structured PDB enrichment harvest targets. "
                "It is report-only and does not alter curated structure rows or governance."
            ),
            "report_only": True,
            "scraping_started": False,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# PDB Enrichment Scrape Registry Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Row count: `{payload['row_count']}`",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['structure_id']}` / sources `{len(row['structured_sources'])}` / "
            f"accessions `{', '.join(row['seed_accessions'])}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only structured PDB enrichment scrape registry preview."
    )
    parser.add_argument(
        "--structure-unit-summary-library",
        type=Path,
        default=DEFAULT_STRUCTURE_UNIT_SUMMARY_LIBRARY,
    )
    parser.add_argument(
        "--q9nzd4-bridge-validation-preview",
        type=Path,
        default=DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_pdb_enrichment_scrape_registry_preview(
        read_json(args.structure_unit_summary_library),
        read_json(args.q9nzd4_bridge_validation_preview)
        if args.q9nzd4_bridge_validation_preview.exists()
        else None,
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
