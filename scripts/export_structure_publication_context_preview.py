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

DEFAULT_STRUCTURE_ENTRY_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "structure_entry_context_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "structure_publication_context_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "structure_publication_context_preview.md"


def build_structure_publication_context_preview(
    structure_entry_context_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        {
            "structure_id": row.get("structure_id"),
            "citation_pubmed_id": row.get("citation_pubmed_id"),
            "deposit_date": row.get("deposit_date"),
            "release_date": row.get("release_date"),
            "revision_date": row.get("revision_date"),
            "title": row.get("title"),
        }
        for row in (structure_entry_context_preview.get("rows") or [])
        if isinstance(row, dict)
    ]
    return {
        "artifact_id": "structure_publication_context_preview",
        "schema_id": "proteosphere-structure-publication-context-preview-2026-04-03",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "structure_count": len(rows),
            "pubmed_backed_count": sum(1 for row in rows if row.get("citation_pubmed_id")),
        },
        "truth_boundary": {
            "summary": "Publication context is derived from structured entry harvests only.",
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Structure Publication Context Preview\n\n"
        + "\n".join(
            f"- `{row['structure_id']}` / PMID `{row['citation_pubmed_id']}`"
            for row in payload["rows"]
        )
        + "\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build structure publication context preview.")
    parser.add_argument(
        "--structure-entry-context", type=Path, default=DEFAULT_STRUCTURE_ENTRY_CONTEXT
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_structure_publication_context_preview(read_json(args.structure_entry_context))
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
