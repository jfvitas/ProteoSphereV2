from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_ANCHOR_CANDIDATES = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_anchor_candidates.json"
)
DEFAULT_OPERATOR_ACCESSION_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "summary_library_operator_accession_matrix.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_anchor_validation.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "structure_followup_anchor_validation.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_validation_payload(
    anchor_candidates: dict[str, Any],
    operator_matrix: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    rows = anchor_candidates.get("rows", [])
    candidate_accessions = [row["accession"] for row in rows]
    summary = anchor_candidates.get("summary", {})
    matrix_summary = operator_matrix.get("summary", {})
    high_priority_accessions = matrix_summary.get("high_priority_accessions", [])

    if anchor_candidates.get("row_count") != len(rows):
        issues.append("row_count does not match the number of emitted rows")
    if summary.get("candidate_accessions") != candidate_accessions:
        issues.append("summary candidate_accessions diverge from row ordering")
    if candidate_accessions != high_priority_accessions:
        issues.append("anchor candidate accessions diverge from high-priority accessions")
    if anchor_candidates.get("truth_boundary", {}).get(
        "direct_structure_backed_join_materialized"
    ) is not False:
        issues.append("direct structure-backed join must remain false on this surface")

    validated_rows: list[dict[str, Any]] = []
    total_candidate_variants = 0
    for row in rows:
        accession = row["accession"]
        best_targets = row.get("best_experimental_targets", [])
        recommended = row.get("recommended_experimental_anchor") or {}
        candidates = row.get("candidate_variant_anchors", [])
        total_candidate_variants += len(candidates)

        recommended_in_targets = any(
            target.get("pdb_id") == recommended.get("pdb_id")
            and target.get("chain_id") == recommended.get("chain_id")
            for target in best_targets
        )
        if not recommended_in_targets:
            issues.append(
                f"{accession} recommended_experimental_anchor is not present in "
                "best_experimental_targets"
            )

        coverage_start = recommended.get("unp_start")
        coverage_end = recommended.get("unp_end")
        out_of_span = [
            candidate["variant_signature"]
            for candidate in candidates
            if (
                coverage_start is not None
                and candidate.get("variant_position") is not None
                and candidate["variant_position"] < coverage_start
            )
            or (
                coverage_end is not None
                and candidate.get("variant_position") is not None
                and candidate["variant_position"] > coverage_end
            )
        ]
        if out_of_span:
            issues.append(
                f"{accession} candidate variants fall outside the recommended structure span: "
                + ", ".join(out_of_span)
            )

        if row.get("candidate_variant_anchor_count") != len(candidates):
            issues.append(
                f"{accession} candidate_variant_anchor_count diverges from emitted candidates"
            )
        if not row.get("alphafold_primary_model"):
            warnings.append(f"{accession} is missing an AlphaFold primary model surface")

        validated_rows.append(
            {
                "accession": accession,
                "recommended_anchor": f"{recommended.get('pdb_id')}:{recommended.get('chain_id')}",
                "recommended_anchor_present_in_best_targets": recommended_in_targets,
                "candidate_variant_anchor_count": len(candidates),
                "variant_positions_within_recommended_span": not out_of_span,
                "variant_position_parse_failures": row.get("variant_position_parse_failures", 0),
            }
        )

    status = "aligned" if not issues else "attention_needed"
    return {
        "artifact_id": "structure_followup_anchor_validation",
        "schema_id": "proteosphere-structure-followup-anchor-validation-2026-04-01",
        "status": status,
        "validation": {
            "issues": issues,
            "warnings": warnings,
            "high_priority_accessions": high_priority_accessions,
            "candidate_accessions": candidate_accessions,
            "validated_row_count": len(validated_rows),
            "candidate_variant_anchor_count": total_candidate_variants,
        },
        "validated_rows": validated_rows,
        "truth_boundary": {
            "summary": (
                "This validation only checks internal consistency of the current anchor-candidate "
                "surface against operator priority and span-compatible variant positions. It does "
                "not certify a direct structure-backed variant join."
            ),
            "direct_structure_backed_join_certified": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    validation = payload["validation"]
    lines = [
        "# Structure Follow-Up Anchor Validation",
        "",
        f"- Status: `{payload['status']}`",
        f"- Validated rows: `{validation['validated_row_count']}`",
        f"- Candidate variant anchors: `{validation['candidate_variant_anchor_count']}`",
        "",
        "## Rows",
        "",
    ]
    for row in payload["validated_rows"]:
        lines.append(
            f"- `{row['accession']}`: anchor `{row['recommended_anchor']}`, "
            f"targets ok `{row['recommended_anchor_present_in_best_targets']}`, "
            f"span ok `{row['variant_positions_within_recommended_span']}`, "
            f"candidates `{row['candidate_variant_anchor_count']}`"
        )
    if validation["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in validation["warnings"])
    if validation["issues"]:
        lines.extend(["", "## Issues", ""])
        lines.extend(f"- {issue}" for issue in validation["issues"])
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
        description="Validate the structure follow-up anchor-candidate surface."
    )
    parser.add_argument("--anchor-candidates", type=Path, default=DEFAULT_ANCHOR_CANDIDATES)
    parser.add_argument(
        "--operator-accession-matrix",
        type=Path,
        default=DEFAULT_OPERATOR_ACCESSION_MATRIX,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_validation_payload(
        _read_json(args.anchor_candidates),
        _read_json(args.operator_accession_matrix),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
