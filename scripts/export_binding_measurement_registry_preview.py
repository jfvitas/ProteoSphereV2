from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.affinity_interaction_preview_support import (
        bindingdb_zip_inventory,
        build_bindingdb_subset_measurements,
        build_ligand_row_measurements,
        iter_pdbbind_rows,
    )
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from affinity_interaction_preview_support import (
        bindingdb_zip_inventory,
        build_bindingdb_subset_measurements,
        build_ligand_row_measurements,
        iter_pdbbind_rows,
    )
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_PDBBIND_INDEX_DIR = REPO_ROOT / "data" / "raw" / "local_copies" / "pdbbind" / "index"
DEFAULT_BINDINGDB_ZIP = (
    REPO_ROOT / "data" / "raw" / "local_copies" / "bindingdb" / "BDB-mySQL_All_202603_dmp.zip"
)
DEFAULT_LIGAND_ROWS = REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
DEFAULT_BINDINGDB_TARGET_POLYMER_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_target_polymer_context_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "binding_measurement_registry_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "binding_measurement_registry_preview.md"


def build_binding_measurement_registry_preview(
    pdbbind_index_dir: Path,
    ligand_row_materialization_preview: dict[str, Any],
    bindingdb_zip_path: Path,
    bindingdb_target_polymer_context_preview: dict[str, Any],
) -> dict[str, Any]:
    pdbbind_rows = iter_pdbbind_rows(pdbbind_index_dir)
    ligand_rows = build_ligand_row_measurements(ligand_row_materialization_preview)
    bindingdb_rows = build_bindingdb_subset_measurements(
        bindingdb_zip_path,
        [
            row
            for row in bindingdb_target_polymer_context_preview.get("rows") or []
            if row.get("bindingdb_polymer_presence") == "present"
        ],
    )
    rows = pdbbind_rows + ligand_rows + bindingdb_rows

    measurement_type_counts: dict[str, int] = {}
    complex_type_counts: dict[str, int] = {}
    for row in rows:
        measurement_type = str(row.get("measurement_type") or "unknown")
        complex_type = str(row.get("complex_type") or "unknown")
        measurement_type_counts[measurement_type] = (
            measurement_type_counts.get(measurement_type, 0) + 1
        )
        complex_type_counts[complex_type] = complex_type_counts.get(complex_type, 0) + 1

    payload = {
        "artifact_id": "binding_measurement_registry_preview",
        "schema_id": "proteosphere-binding-measurement-registry-preview-2026-04-03",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "source_counts": {
                "pdbbind": len(pdbbind_rows),
                "chembl_lightweight": len(ligand_rows),
                "bindingdb": len(bindingdb_rows),
            },
            "complex_type_counts": complex_type_counts,
            "measurement_type_counts": measurement_type_counts,
            "bindingdb_inventory": bindingdb_zip_inventory(bindingdb_zip_path),
        },
        "truth_boundary": {
            "summary": (
                "This registry is a local-data-first binding measurement preview. It includes "
                "parsed PDBbind rows, current lightweight ChEMBL ligand measurements, and a "
                "first locally joined BindingDB subset for in-scope polymer targets."
            ),
            "report_only": True,
            "governing": False,
        },
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Binding Measurement Registry Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Rows: `{payload['row_count']}`",
        f"- PDBbind rows: `{summary.get('source_counts', {}).get('pdbbind')}`",
        (
            "- ChEMBL lightweight rows: "
            f"`{summary.get('source_counts', {}).get('chembl_lightweight')}`"
        ),
        "",
    ]
    for complex_type, count in sorted((summary.get("complex_type_counts") or {}).items()):
        lines.append(f"- `{complex_type}`: `{count}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the binding measurement registry preview.")
    parser.add_argument("--pdbbind-index-dir", type=Path, default=DEFAULT_PDBBIND_INDEX_DIR)
    parser.add_argument("--ligand-rows", type=Path, default=DEFAULT_LIGAND_ROWS)
    parser.add_argument("--bindingdb-zip", type=Path, default=DEFAULT_BINDINGDB_ZIP)
    parser.add_argument(
        "--bindingdb-target-polymer-context",
        type=Path,
        default=DEFAULT_BINDINGDB_TARGET_POLYMER_CONTEXT,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_binding_measurement_registry_preview(
        args.pdbbind_index_dir,
        read_json(args.ligand_rows),
        args.bindingdb_zip,
        read_json(args.bindingdb_target_polymer_context),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
