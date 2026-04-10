from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import accession_rows, fetch_json, read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import accession_rows, fetch_json, read_json, write_json, write_text

DEFAULT_TRAINING_SET = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "protein_function_context_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "protein_function_context_preview.md"
)


def _comment_text(comment: dict[str, Any]) -> str:
    texts = []
    for text_value in comment.get("texts") or []:
        value = text_value.get("value")
        if value:
            texts.append(str(value))
    return " ".join(texts).strip()


def build_protein_function_context_preview(training_set_eligibility_matrix_preview: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for row in accession_rows(training_set_eligibility_matrix_preview):
        accession = row["accession"]
        entry = fetch_json(f"https://rest.uniprot.org/uniprotkb/{accession}.json")
        comments = [comment for comment in (entry.get("comments") or []) if isinstance(comment, dict)]
        function_comments = [comment for comment in comments if comment.get("commentType") == "FUNCTION"]
        catalytic_comments = [comment for comment in comments if comment.get("commentType") == "CATALYTIC ACTIVITY"]
        cofactor_comments = [comment for comment in comments if comment.get("commentType") == "COFACTOR"]
        subcellular_comments = [comment for comment in comments if comment.get("commentType") == "SUBCELLULAR LOCATION"]
        rows.append(
            {
                "accession": accession,
                "function_comment_count": len(function_comments),
                "function_summary": _comment_text(function_comments[0]) if function_comments else None,
                "catalytic_activity_comment_count": len(catalytic_comments),
                "cofactor_comment_count": len(cofactor_comments),
                "subcellular_location_comment_count": len(subcellular_comments),
                "source_url": f"https://rest.uniprot.org/uniprotkb/{accession}.json",
            }
        )
    return {
        "artifact_id": "protein_function_context_preview",
        "schema_id": "proteosphere-protein-function-context-preview-2026-04-03",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {"accessions_with_function_comment": sum(1 for row in rows if row["function_comment_count"] > 0)},
        "truth_boundary": {"summary": "Protein function context is a structured UniProt harvest only.", "report_only": True, "governing": False, "structured_sources_only": True},
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Protein Function Context Preview", ""]
    for row in payload["rows"][:10]:
        lines.append(f"- `{row['accession']}` / function comments `{row['function_comment_count']}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build protein function context preview.")
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_protein_function_context_preview(read_json(args.training_set))
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
