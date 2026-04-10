from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import (
        accession_rows,
        fetch_json,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import (
        accession_rows,
        fetch_json,
        read_json,
        write_json,
        write_text,
    )

DEFAULT_TRAINING_SET = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "protein_reference_context_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "protein_reference_context_preview.md"


def build_protein_reference_context_preview(
    training_set_eligibility_matrix_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = []
    for row in accession_rows(training_set_eligibility_matrix_preview):
        accession = row["accession"]
        entry = fetch_json(f"https://rest.uniprot.org/uniprotkb/{accession}.json")
        comments = [
            comment for comment in (entry.get("comments") or []) if isinstance(comment, dict)
        ]
        references = entry.get("references") or []
        rows.append(
            {
                "accession": accession,
                "reference_count": len(references),
                "disease_comment_present": any(
                    comment.get("commentType") == "DISEASE" for comment in comments
                ),
                "pathway_comment_present": any(
                    comment.get("commentType") == "PATHWAY" for comment in comments
                ),
                "source_url": f"https://rest.uniprot.org/uniprotkb/{accession}.json",
            }
        )
    return {
        "artifact_id": "protein_reference_context_preview",
        "schema_id": "proteosphere-protein-reference-context-preview-2026-04-03",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_references": sum(1 for row in rows if row["reference_count"] > 0),
            "accessions_with_disease_comment": sum(
                1 for row in rows if row["disease_comment_present"]
            ),
        },
        "truth_boundary": {
            "summary": "Protein reference context is a structured UniProt harvest only.",
            "report_only": True,
            "governing": False,
            "structured_sources_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Protein Reference Context Preview", ""]
    for row in payload["rows"][:10]:
        lines.append(f"- `{row['accession']}` / references `{row['reference_count']}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build protein reference context preview.")
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_protein_reference_context_preview(read_json(args.training_set))
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
