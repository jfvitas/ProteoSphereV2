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
DEFAULT_STRUCTURE_LIGAND_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "structure_ligand_context_preview.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "ligand_environment_context_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "ligand_environment_context_preview.md"


def build_ligand_environment_context_preview(
    structure_entry_context_preview: dict[str, Any],
    structure_ligand_context_preview: dict[str, Any],
) -> dict[str, Any]:
    ligands_by_structure: dict[str, list[dict[str, Any]]] = {}
    for row in structure_ligand_context_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        ligands_by_structure.setdefault(str(row.get("structure_id") or ""), []).append(row)
    rows = []
    for row in structure_entry_context_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        structure_id = str(row.get("structure_id") or "")
        ligand_rows = ligands_by_structure.get(structure_id, [])
        rows.append(
            {
                "structure_id": structure_id,
                "mapped_chain_ids": row.get("mapped_chain_ids") or [],
                "ligand_count": len(ligand_rows),
                "ligand_ccd_ids": [
                    ligand.get("ccd_id") for ligand in ligand_rows if ligand.get("ccd_id")
                ],
                "bound_component_count": len(row.get("nonpolymer_bound_components") or []),
            }
        )
    return {
        "artifact_id": "ligand_environment_context_preview",
        "schema_id": "proteosphere-ligand-environment-context-preview-2026-04-03",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {"structure_count": len(rows)},
        "truth_boundary": {
            "summary": "Ligand environment context is a structure-level descriptive rollup only.",
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    return (
        "# Ligand Environment Context Preview\n\n"
        + "\n".join(
            f"- `{row['structure_id']}` / ligands `{row['ligand_count']}`"
            for row in payload["rows"]
        )
        + "\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ligand environment context preview.")
    parser.add_argument(
        "--structure-entry-context", type=Path, default=DEFAULT_STRUCTURE_ENTRY_CONTEXT
    )
    parser.add_argument(
        "--structure-ligand-context", type=Path, default=DEFAULT_STRUCTURE_LIGAND_CONTEXT
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_ligand_environment_context_preview(
        read_json(args.structure_entry_context),
        read_json(args.structure_ligand_context),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
