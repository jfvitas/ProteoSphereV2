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
    REPO_ROOT / "artifacts" / "status" / "structure_variant_candidate_map.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "structure_variant_candidate_map.md"
)


def _read_library(path: Path) -> SummaryLibrarySchema:
    return SummaryLibrarySchema.from_dict(json.loads(path.read_text(encoding="utf-8")))


def build_candidate_map(
    variant_library: SummaryLibrarySchema,
    structure_library: SummaryLibrarySchema,
) -> dict[str, Any]:
    variant_records_by_protein: dict[str, list[dict[str, Any]]] = {}
    for record in variant_library.variant_records:
        variant_records_by_protein.setdefault(record.protein_ref, []).append(record.to_dict())

    structure_records_by_protein: dict[str, list[dict[str, Any]]] = {}
    for record in structure_library.structure_unit_records:
        structure_records_by_protein.setdefault(record.protein_ref, []).append(record.to_dict())

    candidate_rows: list[dict[str, Any]] = []
    overlap_proteins = sorted(
        set(variant_records_by_protein).intersection(structure_records_by_protein)
    )
    for protein_ref in overlap_proteins:
        variant_rows = variant_records_by_protein[protein_ref]
        structure_rows = structure_records_by_protein[protein_ref]
        structure_variant_refs = sorted(
            {
                row["variant_ref"]
                for row in structure_rows
                if row.get("variant_ref")
            }
        )
        candidate_rows.append(
            {
                "protein_ref": protein_ref,
                "candidate_status": (
                    "join_ready"
                    if structure_variant_refs
                    else "candidate_only_no_variant_anchor"
                ),
                "variant_count": len(variant_rows),
                "structure_unit_count": len(structure_rows),
                "example_variant_signatures": [
                    row["variant_signature"] for row in variant_rows[:5]
                ],
                "structure_summary_ids": [
                    row["summary_id"] for row in structure_rows
                ],
                "structure_ids": sorted({row["structure_id"] for row in structure_rows}),
                "variant_refs_on_structure_side": structure_variant_refs,
                "truth_note": (
                    "Shared accession-level overlap exists, but structure rows still have "
                    "variant_ref=null, so this remains a candidate-only bridge."
                    if not structure_variant_refs
                    else "Structure-side variant anchors exist for this protein."
                ),
            }
        )

    return {
        "artifact_id": "structure_variant_candidate_map",
        "schema_id": "proteosphere-structure-variant-candidate-map-2026-04-01",
        "status": "complete",
        "variant_library_id": variant_library.library_id,
        "structure_library_id": structure_library.library_id,
        "candidate_count": len(candidate_rows),
        "candidate_rows": candidate_rows,
        "truth_boundary": {
            "summary": (
                "This surface records accession-level structure/variant candidate overlap. "
                "It does not claim direct structure-backed variant joins unless variant_ref "
                "is explicit on the structure side."
            ),
            "direct_structure_backed_variant_join_materialized": any(
                row["candidate_status"] == "join_ready" for row in candidate_rows
            ),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Structure Variant Candidate Map",
        "",
        f"- Candidate proteins: `{payload['candidate_count']}`",
        "",
        "## Candidate Rows",
        "",
    ]
    for row in payload["candidate_rows"]:
        lines.extend(
            [
                f"- `{row['protein_ref']}`",
                f"  status `{row['candidate_status']}`; `{row['variant_count']}` variants; "
                f"`{row['structure_unit_count']}` structure units; "
                f"structures `{', '.join(row['structure_ids'])}`",
                f"  example variants `{', '.join(row['example_variant_signatures'])}`",
                f"  {row['truth_note']}",
            ]
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
        description="Export accession-level structure/variant candidate overlap."
    )
    parser.add_argument("--variant-library", type=Path, default=DEFAULT_VARIANT_LIBRARY)
    parser.add_argument("--structure-library", type=Path, default=DEFAULT_STRUCTURE_LIBRARY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_candidate_map(
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
