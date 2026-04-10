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

DEFAULT_STRUCTURE_LIGAND_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "structure_ligand_context_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bound_ligand_character_context_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "bound_ligand_character_context_preview.md"


def build_bound_ligand_character_context_preview(
    structure_ligand_context_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        {
            "structure_id": row.get("structure_id"),
            "ccd_id": row.get("ccd_id"),
            "name": row.get("name"),
            "formula": row.get("formula"),
            "formula_weight": row.get("formula_weight"),
            "inchi_present": bool(row.get("inchi")),
            "inchi_key_present": bool(row.get("inchi_key")),
            "smiles_present": bool(row.get("smiles")),
        }
        for row in (structure_ligand_context_preview.get("rows") or [])
        if isinstance(row, dict)
    ]
    return {
        "artifact_id": "bound_ligand_character_context_preview",
        "schema_id": "proteosphere-bound-ligand-character-context-preview-2026-04-03",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {"ligand_count": len(rows)},
        "truth_boundary": {
            "summary": (
                "Bound ligand character context is derived from structured "
                "nonpolymer entity metadata only."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Bound Ligand Character Context Preview\n\n"
        + "\n".join(f"- `{row['structure_id']}` / `{row['ccd_id']}`" for row in payload["rows"])
        + "\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build bound ligand character context preview.")
    parser.add_argument(
        "--structure-ligand-context", type=Path, default=DEFAULT_STRUCTURE_LIGAND_CONTEXT
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bound_ligand_character_context_preview(
        read_json(args.structure_ligand_context)
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
