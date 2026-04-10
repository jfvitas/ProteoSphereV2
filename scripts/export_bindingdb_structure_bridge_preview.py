from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.affinity_interaction_preview_support import find_table_tuples_containing
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from affinity_interaction_preview_support import find_table_tuples_containing
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_BINDINGDB_ZIP = (
    REPO_ROOT / "data" / "raw" / "local_copies" / "bindingdb" / "BDB-mySQL_All_202603_dmp.zip"
)
DEFAULT_STRUCTURE_ENTRY_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "structure_entry_context_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_structure_bridge_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "bindingdb_structure_bridge_preview.md"
)

PDB_BDB_FIELDS = [
    "pdbid",
    "reactant_set_id_str",
    "reactant_set_id_90",
    "itc_result_a_b_ab_id_90",
    "monomerid_str_90",
    "monomerid_str",
    "polymerid_str",
    "complexid_str",
    "itc_result_a_b_ab_id_str",
]


def _split_id_list(raw_value: str | None) -> list[str]:
    text = str(raw_value or "").strip()
    if not text or text.lower() == "null":
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def build_bindingdb_structure_bridge_preview(
    bindingdb_zip_path: Path,
    structure_entry_context_preview: dict[str, Any],
) -> dict[str, Any]:
    structure_ids = sorted(
        {
            str(row.get("structure_id") or "").strip().upper()
            for row in (structure_entry_context_preview.get("rows") or [])
            if isinstance(row, dict)
        }
        - {""}
    )
    matched = find_table_tuples_containing(
        bindingdb_zip_path,
        "pdb_bdb",
        [f"'{structure_id}'" for structure_id in structure_ids],
    )
    rows = []
    for structure_id in structure_ids:
        values = matched.get(f"'{structure_id}'")
        if values is None:
            rows.append(
                {
                    "structure_id": structure_id,
                    "bindingdb_bridge_status": "absent",
                    "bindingdb_reactant_set_ids": [],
                    "bindingdb_monomer_ids": [],
                    "bindingdb_polymer_ids": [],
                    "bindingdb_complex_ids": [],
                }
            )
            continue
        record = {
            field: values[index] if index < len(values) else None
            for index, field in enumerate(PDB_BDB_FIELDS)
        }
        rows.append(
            {
                "structure_id": structure_id,
                "bindingdb_bridge_status": "present",
                "bindingdb_reactant_set_ids": _split_id_list(record.get("reactant_set_id_str")),
                "bindingdb_monomer_ids": _split_id_list(record.get("monomerid_str")),
                "bindingdb_polymer_ids": _split_id_list(record.get("polymerid_str")),
                "bindingdb_complex_ids": _split_id_list(record.get("complexid_str")),
                "bindingdb_itc_result_ids": _split_id_list(
                    record.get("itc_result_a_b_ab_id_str")
                ),
            }
        )
    return {
        "artifact_id": "bindingdb_structure_bridge_preview",
        "schema_id": "proteosphere-bindingdb-structure-bridge-preview-2026-04-03",
        "status": "report_only_local_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "structures_with_bindingdb_bridge": sum(
                1 for row in rows if row["bindingdb_bridge_status"] == "present"
            ),
            "structures_without_bindingdb_bridge": sum(
                1 for row in rows if row["bindingdb_bridge_status"] != "present"
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a BindingDB structure bridge harvested from the local MySQL dump. "
                "It provides bridge identifiers only and remains non-governing."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# BindingDB Structure Bridge Preview", ""]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['structure_id']}` / `{row['bindingdb_bridge_status']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build BindingDB structure bridge preview.")
    parser.add_argument("--bindingdb-zip", type=Path, default=DEFAULT_BINDINGDB_ZIP)
    parser.add_argument(
        "--structure-entry-context", type=Path, default=DEFAULT_STRUCTURE_ENTRY_CONTEXT
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_structure_bridge_preview(
        args.bindingdb_zip,
        read_json(args.structure_entry_context),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
