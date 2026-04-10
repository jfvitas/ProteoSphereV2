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

DEFAULT_KINETICS_SUPPORT = (
    REPO_ROOT / "artifacts" / "status" / "kinetics_enzyme_support_preview.json"
)
DEFAULT_PROTEIN_FUNCTION = (
    REPO_ROOT / "artifacts" / "status" / "protein_function_context_preview.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "enzyme_behavior_context_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "enzyme_behavior_context_preview.md"


def build_enzyme_behavior_context_preview(
    kinetics_support_preview: dict[str, Any],
    protein_function_context_preview: dict[str, Any],
) -> dict[str, Any]:
    function_by_accession = {
        str(row.get("accession") or "").strip(): row
        for row in (protein_function_context_preview.get("rows") or [])
        if isinstance(row, dict)
    }
    rows = []
    for row in kinetics_support_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        function_row = function_by_accession.get(accession) or {}
        rows.append(
            {
                "accession": accession,
                "kinetics_support_status": row.get("kinetics_support_status"),
                "support_sources": row.get("support_sources") or [],
                "function_comment_count": function_row.get("function_comment_count", 0),
                "catalytic_activity_comment_count": function_row.get(
                    "catalytic_activity_comment_count", 0
                ),
                "cofactor_comment_count": function_row.get("cofactor_comment_count", 0),
                "next_truthful_stage": row.get("next_truthful_stage"),
            }
        )
    return {
        "artifact_id": "enzyme_behavior_context_preview",
        "schema_id": "proteosphere-enzyme-behavior-context-preview-2026-04-03",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "supported_now_count": sum(
                1 for row in rows if row["kinetics_support_status"] == "supported_now"
            )
        },
        "truth_boundary": {
            "summary": "Enzyme behavior context remains support-only in this phase.",
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Enzyme Behavior Context Preview", ""]
    for row in payload["rows"]:
        lines.append(f"- `{row['accession']}` / `{row['kinetics_support_status']}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build enzyme behavior context preview.")
    parser.add_argument("--kinetics-support", type=Path, default=DEFAULT_KINETICS_SUPPORT)
    parser.add_argument("--protein-function", type=Path, default=DEFAULT_PROTEIN_FUNCTION)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_enzyme_behavior_context_preview(
        read_json(args.kinetics_support),
        read_json(args.protein_function),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
