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
DEFAULT_PDB_ENRICHMENT_HARVEST = (
    REPO_ROOT / "artifacts" / "status" / "pdb_enrichment_harvest_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_enrichment_validation_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "pdb_enrichment_validation_preview.md"
)


def build_pdb_enrichment_validation_preview(
    pdb_enrichment_scrape_registry_preview: dict[str, Any],
    pdb_enrichment_harvest_preview: dict[str, Any],
) -> dict[str, Any]:
    registry_ids = sorted(
        str(row.get("structure_id") or "").strip().upper()
        for row in (pdb_enrichment_scrape_registry_preview.get("rows") or [])
        if isinstance(row, dict)
    )
    harvest_rows = [
        row
        for row in (pdb_enrichment_harvest_preview.get("rows") or [])
        if isinstance(row, dict)
    ]
    harvest_ids = sorted(
        str(row.get("structure_id") or "").strip().upper() for row in harvest_rows
    )
    issues = []
    if registry_ids != harvest_ids:
        issues.append("registry_structure_ids_do_not_match_harvest_structure_ids")
    for row in harvest_rows:
        if row.get("successful_source_count") != row.get("expected_source_count"):
            issues.append(f"incomplete_source_coverage:{row.get('structure_id')}")
    return {
        "artifact_id": "pdb_enrichment_validation_preview",
        "schema_id": "proteosphere-pdb-enrichment-validation-preview-2026-04-02",
        "status": "aligned" if not issues else "attention_needed",
        "generated_at": datetime.now(UTC).isoformat(),
        "validated_row_count": len(harvest_rows),
        "validated_structure_ids": harvest_ids,
        "issues": issues,
        "truth_boundary": {
            "summary": (
                "This validation surface checks only structured PDB enrichment scrape "
                "coverage and registry alignment. It is report-only and non-governing."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# PDB Enrichment Validation Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Validated rows: `{payload['validated_row_count']}`",
        "",
    ]
    if payload["issues"]:
        lines.extend(f"- Issue: `{issue}`" for issue in payload["issues"])
    else:
        lines.append("- No issues detected.")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the structured PDB enrichment harvest against its registry."
    )
    parser.add_argument(
        "--pdb-enrichment-scrape-registry",
        type=Path,
        default=DEFAULT_PDB_ENRICHMENT_SCRAPE_REGISTRY,
    )
    parser.add_argument(
        "--pdb-enrichment-harvest",
        type=Path,
        default=DEFAULT_PDB_ENRICHMENT_HARVEST,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_pdb_enrichment_validation_preview(
        read_json(args.pdb_enrichment_scrape_registry),
        read_json(args.pdb_enrichment_harvest),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
