from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.library.summary_record import SummaryLibrarySchema  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VARIANT_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "protein_variant_summary_library.json"
)
DEFAULT_STRUCTURE_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "structure_unit_summary_library.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "structure_variant_bridge_summary.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "structure_variant_bridge_summary.md"
)


def _read_library(path: Path) -> SummaryLibrarySchema:
    return SummaryLibrarySchema.from_dict(json.loads(path.read_text(encoding="utf-8")))


def build_bridge_summary(
    variant_library: SummaryLibrarySchema,
    structure_library: SummaryLibrarySchema,
) -> dict[str, Any]:
    variant_counts: dict[str, int] = {}
    for record in variant_library.variant_records:
        variant_counts[record.protein_ref] = variant_counts.get(record.protein_ref, 0) + 1

    structure_counts: dict[str, int] = {}
    structure_ids: dict[str, set[str]] = {}
    for record in structure_library.structure_unit_records:
        structure_counts[record.protein_ref] = structure_counts.get(record.protein_ref, 0) + 1
        structure_ids.setdefault(record.protein_ref, set()).add(record.structure_id)

    overlap_rows = []
    for protein_ref in sorted(set(variant_counts).intersection(structure_counts)):
        overlap_rows.append(
            {
                "protein_ref": protein_ref,
                "variant_count": variant_counts[protein_ref],
                "structure_unit_count": structure_counts[protein_ref],
                "structure_ids": sorted(structure_ids.get(protein_ref, set())),
            }
        )

    return {
        "artifact_id": "structure_variant_bridge_summary",
        "schema_id": "proteosphere-structure-variant-bridge-summary-2026-04-01",
        "status": "complete",
        "variant_library_id": variant_library.library_id,
        "structure_library_id": structure_library.library_id,
        "variant_record_count": len(variant_library.variant_records),
        "structure_unit_record_count": len(structure_library.structure_unit_records),
        "overlap_protein_count": len(overlap_rows),
        "overlap_rows": overlap_rows,
        "truth_boundary": {
            "summary": (
                "This surface reports protein-level overlap between the current variant and "
                "structure-unit slices. It does not claim per-variant structure mapping yet."
            ),
            "per_variant_structure_join_materialized": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Structure Variant Bridge Summary",
        "",
        f"- Variant records: `{payload['variant_record_count']}`",
        f"- Structure-unit records: `{payload['structure_unit_record_count']}`",
        f"- Overlap proteins: `{payload['overlap_protein_count']}`",
        "",
        "## Overlap Rows",
        "",
    ]
    for row in payload["overlap_rows"]:
        lines.append(
            f"- `{row['protein_ref']}`: `{row['variant_count']}` variants, "
            f"`{row['structure_unit_count']}` structure units, "
            f"structures `{', '.join(row['structure_ids'])}`"
        )
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- {payload['truth_boundary']['summary']}",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a protein-level overlap summary between variant and "
            "structure-unit slices."
        )
    )
    parser.add_argument("--variant-library", type=Path, default=DEFAULT_VARIANT_LIBRARY)
    parser.add_argument("--structure-library", type=Path, default=DEFAULT_STRUCTURE_LIBRARY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bridge_summary(
        _read_library(args.variant_library),
        _read_library(args.structure_library),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
