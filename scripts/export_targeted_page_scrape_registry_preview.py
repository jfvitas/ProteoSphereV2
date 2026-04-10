from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import write_json, write_text
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from web_enrichment_preview_support import write_json, write_text
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_registry_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "targeted_page_scrape_registry_preview.md"
)


def build_targeted_page_scrape_registry_preview() -> dict[str, object]:
    rows = [
        {
            "accession": "P04637",
            "target_family": "elm_motif_context",
            "candidate_pages": [
                "https://elm.eu.org/",
                "https://rest.uniprot.org/uniprotkb/P04637.json",
            ],
            "default_ingest_status": "candidate_only_non_governing",
            "page_scraping_started": False,
        },
        {
            "accession": "P31749",
            "target_family": "elm_motif_context",
            "candidate_pages": [
                "https://elm.eu.org/",
                "https://rest.uniprot.org/uniprotkb/P31749.json",
            ],
            "default_ingest_status": "candidate_only_non_governing",
            "page_scraping_started": False,
        },
    ]
    return {
        "artifact_id": "targeted_page_scrape_registry_preview",
        "schema_id": "proteosphere-targeted-page-scrape-registry-preview-2026-04-02",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "truth_boundary": {
            "summary": (
                "This registry tracks high-value targeted page scraping candidates. Page-level "
                "scraping defaults to candidate-only non-governing until separately normalized."
            ),
            "report_only": True,
            "governing": False,
            "page_scraping_started": False,
        },
    }


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Targeted Page Scrape Registry Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Row count: `{payload['row_count']}`",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['accession']}` / `{row['target_family']}` / "
            f"started `{row['page_scraping_started']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export targeted page-scrape registry candidates for high-value motif "
            "enrichment."
        )
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_targeted_page_scrape_registry_preview()
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
