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
DEFAULT_PROTEIN_LIBRARY = REPO_ROOT / "artifacts" / "status" / "protein_summary_library.json"
DEFAULT_VARIANT_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "protein_variant_summary_library.json"
)
DEFAULT_STRUCTURE_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "structure_unit_summary_library.json"
)
DEFAULT_CANDIDATE_MAP = (
    REPO_ROOT / "artifacts" / "status" / "structure_variant_candidate_map.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "summary_library_operator_accession_matrix.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "summary_library_operator_accession_matrix.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_library(path: Path) -> SummaryLibrarySchema:
    return SummaryLibrarySchema.from_dict(_read_json(path))


def _accession_from_ref(protein_ref: str) -> str:
    return protein_ref.split(":", 1)[1] if ":" in protein_ref else protein_ref


def build_accession_coverage_matrix(
    protein_library: SummaryLibrarySchema,
    variant_library: SummaryLibrarySchema,
    structure_library: SummaryLibrarySchema,
    candidate_map: dict[str, Any],
) -> dict[str, Any]:
    variant_counts: dict[str, int] = {}
    for record in variant_library.variant_records:
        variant_counts[record.protein_ref] = variant_counts.get(record.protein_ref, 0) + 1

    structure_counts: dict[str, int] = {}
    for record in structure_library.structure_unit_records:
        structure_counts[record.protein_ref] = structure_counts.get(record.protein_ref, 0) + 1

    candidate_status_by_protein = {
        row["protein_ref"]: row["candidate_status"]
        for row in candidate_map.get("candidate_rows", [])
    }

    rows: list[dict[str, Any]] = []
    for record in sorted(protein_library.protein_records, key=lambda item: item.protein_ref):
        protein_ref = record.protein_ref
        accession = _accession_from_ref(protein_ref)
        motif_count = len(record.context.motif_references)
        domain_count = len(record.context.domain_references)
        pathway_count = len(record.context.pathway_references)
        provenance_count = len(record.context.provenance_pointers)
        variant_count = variant_counts.get(protein_ref, 0)
        structure_count = structure_counts.get(protein_ref, 0)
        candidate_status = candidate_status_by_protein.get(protein_ref)

        if variant_count > 0 and structure_count == 0:
            next_action = "structure_followup_candidate"
            priority = "high"
            truth_note = "Variant-bearing accession with no visible structure-unit slice yet."
        elif variant_count > 0 and structure_count > 0:
            next_action = (
                "candidate_only_no_variant_anchor"
                if candidate_status == "candidate_only_no_variant_anchor"
                else "reference_example_keep_visible"
            )
            priority = "medium"
            truth_note = (
                "Protein, variant, and structure slices are visible, but no direct "
                "structure-backed variant join is materialized."
                if candidate_status == "candidate_only_no_variant_anchor"
                else "Protein, variant, and structure slices are all visible."
            )
        else:
            next_action = "protein_only_current_slice"
            priority = "observe"
            truth_note = (
                "Useful protein-only summary exists, but no visible variant or "
                "structure slice exists yet."
            )

        rows.append(
            {
                "accession": accession,
                "protein_ref": protein_ref,
                "protein_name": record.protein_name,
                "protein_summary_present": True,
                "variant_count": variant_count,
                "structure_unit_count": structure_count,
                "motif_reference_count": motif_count,
                "domain_reference_count": domain_count,
                "pathway_reference_count": pathway_count,
                "provenance_pointer_count": provenance_count,
                "family_presence": {
                    "protein": True,
                    "protein_variant": variant_count > 0,
                    "structure_unit": structure_count > 0,
                },
                "candidate_status": candidate_status,
                "bundle_projection": (
                    "included_current_preview"
                    if variant_count > 0 or structure_count > 0
                    else "protein_only_current_preview"
                ),
                "next_operator_action": next_action,
                "operator_priority": priority,
                "truth_note": truth_note,
            }
        )

    return {
        "artifact_id": "summary_library_operator_accession_matrix",
        "schema_id": "proteosphere-summary-library-operator-accession-matrix-2026-04-01",
        "status": "complete",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "protein_accession_count": len(rows),
            "variant_bearing_accession_count": sum(
                1 for row in rows if row["variant_count"] > 0
            ),
            "structure_bearing_accession_count": sum(
                1 for row in rows if row["structure_unit_count"] > 0
            ),
            "high_priority_accessions": [
                row["accession"] for row in rows if row["operator_priority"] == "high"
            ],
            "candidate_only_accessions": [
                row["accession"]
                for row in rows
                if row["candidate_status"] == "candidate_only_no_variant_anchor"
            ],
        },
        "truth_boundary": {
            "summary": (
                "This matrix reports accession-level coverage across the currently "
                "materialized lightweight-library slices. It does not infer missing "
                "ligand or interaction families."
            ),
            "report_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Summary Library Operator Accession Matrix",
        "",
        f"- Accessions: `{payload['summary']['protein_accession_count']}`",
        (
            "- Variant-bearing accessions: "
            f"`{payload['summary']['variant_bearing_accession_count']}`"
        ),
        (
            "- Structure-bearing accessions: "
            f"`{payload['summary']['structure_bearing_accession_count']}`"
        ),
        "",
        "## Rows",
        "",
    ]
    for row in payload["rows"]:
        lines.extend(
            [
                f"- `{row['accession']}` (`{row['protein_name']}`)",
                f"  variants `{row['variant_count']}`; structures `{row['structure_unit_count']}`; "
                f"action `{row['next_operator_action']}`; priority `{row['operator_priority']}`",
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
        description="Export an operator-facing accession coverage matrix."
    )
    parser.add_argument("--protein-library", type=Path, default=DEFAULT_PROTEIN_LIBRARY)
    parser.add_argument("--variant-library", type=Path, default=DEFAULT_VARIANT_LIBRARY)
    parser.add_argument("--structure-library", type=Path, default=DEFAULT_STRUCTURE_LIBRARY)
    parser.add_argument("--candidate-map", type=Path, default=DEFAULT_CANDIDATE_MAP)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_accession_coverage_matrix(
        _read_library(args.protein_library),
        _read_library(args.variant_library),
        _read_library(args.structure_library),
        _read_json(args.candidate_map),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
