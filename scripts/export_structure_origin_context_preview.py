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

DEFAULT_STRUCTURE_CHAIN_ORIGIN = (
    REPO_ROOT / "artifacts" / "status" / "structure_chain_origin_preview.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "structure_origin_context_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "structure_origin_context_preview.md"


def build_structure_origin_context_preview(
    structure_chain_origin_preview: dict[str, Any],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in structure_chain_origin_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        grouped.setdefault(str(row.get("structure_id") or ""), []).append(row)
    rows = []
    for structure_id, chain_rows in sorted(grouped.items()):
        rows.append(
            {
                "structure_id": structure_id,
                "source_organisms": sorted(
                    {row.get("source_organism") for row in chain_rows if row.get("source_organism")}
                ),
                "expression_hosts": sorted(
                    {row.get("expression_host") for row in chain_rows if row.get("expression_host")}
                ),
                "engineered_chain_count": sum(
                    1 for row in chain_rows if row.get("engineered_flag")
                ),
                "chain_count": len(chain_rows),
            }
        )
    return {
        "artifact_id": "structure_origin_context_preview",
        "schema_id": "proteosphere-structure-origin-context-preview-2026-04-03",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {"structure_count": len(rows)},
        "truth_boundary": {
            "summary": "Structure origin context is aggregated from chain-origin metadata only.",
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Structure Origin Context Preview\n\n"
        + "\n".join(
            f"- `{row['structure_id']}` / chains `{row['chain_count']}`" for row in payload["rows"]
        )
        + "\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build structure origin context preview.")
    parser.add_argument(
        "--structure-chain-origin", type=Path, default=DEFAULT_STRUCTURE_CHAIN_ORIGIN
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_structure_origin_context_preview(read_json(args.structure_chain_origin))
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
