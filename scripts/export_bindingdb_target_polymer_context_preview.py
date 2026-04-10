from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.affinity_interaction_preview_support import find_table_tuples_containing
    from scripts.web_enrichment_preview_support import (
        accession_rows,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from affinity_interaction_preview_support import find_table_tuples_containing
    from web_enrichment_preview_support import accession_rows, read_json, write_json, write_text

DEFAULT_BINDINGDB_ZIP = (
    REPO_ROOT / "data" / "raw" / "local_copies" / "bindingdb" / "BDB-mySQL_All_202603_dmp.zip"
)
DEFAULT_TRAINING_SET = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_target_polymer_context_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "bindingdb_target_polymer_context_preview.md"
)

POLYMER_FIELDS = [
    "component_id",
    "comments",
    "topology",
    "weight",
    "source_organism",
    "unpid2",
    "scientific_name",
    "type",
    "display_name",
    "res_count",
    "sequence",
    "n_pdb_ids",
    "taxid",
    "unpid1",
    "polymerid",
    "pdb_ids",
    "short_name",
    "common_name",
    "chembl_id",
]


def _map_polymer_row(values: list[str | None]) -> dict[str, Any]:
    record = {
        field: values[index] if index < len(values) else None
        for index, field in enumerate(POLYMER_FIELDS)
    }
    pdb_ids = [item.strip() for item in str(record.get("pdb_ids") or "").split(",") if item.strip()]
    return {
        "component_id": record.get("component_id"),
        "display_name": record.get("display_name"),
        "source_organism": record.get("source_organism"),
        "scientific_name": record.get("scientific_name"),
        "polymer_type": record.get("type"),
        "taxid": record.get("taxid"),
        "unpid1": record.get("unpid1"),
        "unpid2": record.get("unpid2"),
        "polymerid": record.get("polymerid"),
        "res_count": int(record["res_count"]) if record.get("res_count") else None,
        "n_pdb_ids": int(record["n_pdb_ids"]) if record.get("n_pdb_ids") else 0,
        "pdb_ids_sample": pdb_ids[:20],
        "chembl_id": record.get("chembl_id"),
    }


def build_bindingdb_target_polymer_context_preview(
    bindingdb_zip_path: Path,
    training_set_eligibility_matrix_preview: dict[str, Any],
) -> dict[str, Any]:
    accessions = [
        row["accession"]
        for row in accession_rows(training_set_eligibility_matrix_preview)
    ]
    matched = find_table_tuples_containing(
        bindingdb_zip_path,
        "polymer",
        [f"'{accession}'" for accession in accessions],
    )
    rows = []
    for accession in accessions:
        values = matched.get(f"'{accession}'")
        if values is None:
            rows.append(
                {
                    "accession": accession,
                    "bindingdb_polymer_presence": "absent",
                }
            )
            continue
        polymer_row = _map_polymer_row(values)
        rows.append(
            {
                "accession": accession,
                "bindingdb_polymer_presence": "present",
                "bindingdb_polymer_id": polymer_row.get("polymerid"),
                "bindingdb_display_name": polymer_row.get("display_name"),
                "scientific_name": polymer_row.get("scientific_name"),
                "source_organism": polymer_row.get("source_organism"),
                "taxid": polymer_row.get("taxid"),
                "polymer_type": polymer_row.get("polymer_type"),
                "bindingdb_pdb_count": polymer_row.get("n_pdb_ids"),
                "bindingdb_pdb_ids_sample": polymer_row.get("pdb_ids_sample"),
                "bindingdb_chembl_id": polymer_row.get("chembl_id"),
            }
        )

    return {
        "artifact_id": "bindingdb_target_polymer_context_preview",
        "schema_id": "proteosphere-bindingdb-target-polymer-context-preview-2026-04-03",
        "status": "report_only_local_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_bindingdb_polymer_bridge": sum(
                1 for row in rows if row["bindingdb_polymer_presence"] == "present"
            ),
            "accessions_without_bindingdb_polymer_bridge": sum(
                1 for row in rows if row["bindingdb_polymer_presence"] != "present"
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a BindingDB polymer-target bridge harvested from the local MySQL dump. "
                "It is descriptive only and does not change ligand grounding."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# BindingDB Target Polymer Context Preview", ""]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['accession']}` / `{row['bindingdb_polymer_presence']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build BindingDB target polymer context preview.")
    parser.add_argument("--bindingdb-zip", type=Path, default=DEFAULT_BINDINGDB_ZIP)
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_target_polymer_context_preview(
        args.bindingdb_zip,
        read_json(args.training_set),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
