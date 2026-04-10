from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.affinity_interaction_preview_support import (
        build_bindingdb_subset_measurements,
    )
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from affinity_interaction_preview_support import build_bindingdb_subset_measurements
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_BINDINGDB_ZIP = (
    REPO_ROOT / "data" / "raw" / "local_copies" / "bindingdb" / "BDB-mySQL_All_202603_dmp.zip"
)
DEFAULT_TARGET_POLYMER_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_target_polymer_context_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_measurement_subset_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "bindingdb_measurement_subset_preview.md"
)


def build_bindingdb_measurement_subset_preview(
    bindingdb_zip_path: Path,
    target_polymer_context_preview: dict[str, Any],
) -> dict[str, Any]:
    accession_polymer_rows = [
        row
        for row in target_polymer_context_preview.get("rows") or []
        if row.get("bindingdb_polymer_presence") == "present"
    ]
    rows = build_bindingdb_subset_measurements(bindingdb_zip_path, accession_polymer_rows)
    measurement_type_counts: dict[str, int] = {}
    accession_counts: dict[str, int] = {}
    for row in rows:
        measurement_type = str(row.get("measurement_type") or "unknown")
        accession = str(row.get("accession") or "unknown")
        measurement_type_counts[measurement_type] = (
            measurement_type_counts.get(measurement_type, 0) + 1
        )
        accession_counts[accession] = accession_counts.get(accession, 0) + 1
    return {
        "artifact_id": "bindingdb_measurement_subset_preview",
        "schema_id": "proteosphere-bindingdb-measurement-subset-preview-2026-04-03",
        "status": "report_only_local_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_bindingdb_measurements": len(accession_counts),
            "measurement_type_counts": measurement_type_counts,
            "accession_counts": accession_counts,
        },
        "truth_boundary": {
            "summary": (
                "This is a locally joined BindingDB subset preview built from polymer-target "
                "bridges and ki_result-linked assay rows. It is descriptive only."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Measurement Subset Preview",
        "",
        f"- Rows: `{payload['row_count']}`",
        "",
    ]
    accession_counts = (payload.get("summary") or {}).get("accession_counts", {})
    for accession, count in sorted(accession_counts.items()):
        lines.append(f"- `{accession}`: `{count}` rows")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build BindingDB measurement subset preview.")
    parser.add_argument("--bindingdb-zip", type=Path, default=DEFAULT_BINDINGDB_ZIP)
    parser.add_argument(
        "--target-polymer-context",
        type=Path,
        default=DEFAULT_TARGET_POLYMER_CONTEXT,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_measurement_subset_preview(
        args.bindingdb_zip,
        read_json(args.target_polymer_context),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
