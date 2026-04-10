from __future__ import annotations

import argparse
import json
import re
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
DEFAULT_OPERATOR_ACCESSION_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "summary_library_operator_accession_matrix.json"
)
DEFAULT_RCSB_ROOT = REPO_ROOT / "data" / "raw" / "rcsb_pdbe"
DEFAULT_ALPHAFOLD_ROOT = REPO_ROOT / "data" / "raw" / "alphafold"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_anchor_candidates.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "structure_followup_anchor_candidates.md"
)
VARIANT_POSITION_PATTERN = re.compile(r"[A-Za-z*](\d+)[A-Za-z*]")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_library(path: Path) -> SummaryLibrarySchema:
    return SummaryLibrarySchema.from_dict(_read_json(path))


def _protein_ref(accession: str) -> str:
    return accession if accession.startswith("protein:") else f"protein:{accession}"


def _latest_matching_file(root: Path, accession: str, filename: str) -> Path | None:
    matches = sorted(root.glob(f"*/{accession}/{filename}"))
    return matches[-1] if matches else None


def _parse_variant_position(signature: str) -> int | None:
    match = VARIANT_POSITION_PATTERN.search(signature)
    if match is None:
        return None
    return int(match.group(1))


def _high_priority_accessions(matrix_payload: dict[str, Any]) -> list[str]:
    summary = matrix_payload.get("summary", {})
    rows = matrix_payload.get("rows", [])
    accessions = summary.get("high_priority_accessions") or [
        row["accession"]
        for row in rows
        if row.get("operator_priority") == "high"
    ]
    return sorted(dict.fromkeys(accessions))


def _best_experimental_targets(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for entry in payload[:3]:
        rows.append(
            {
                "pdb_id": str(entry["pdb_id"]).upper(),
                "chain_id": entry["chain_id"],
                "experimental_method": entry["experimental_method"],
                "resolution": entry.get("resolution"),
                "coverage": entry.get("coverage"),
                "unp_start": entry.get("unp_start"),
                "unp_end": entry.get("unp_end"),
                "structure_path": str(path).replace("\\", "/"),
            }
        )
    return rows


def _alphafold_primary_model(path: Path, accession: str) -> dict[str, Any] | None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    exact = next(
        (row for row in payload if row.get("uniprotAccession") == accession),
        None,
    )
    if exact is None and payload:
        exact = payload[0]
    if exact is None:
        return None
    return {
        "model_entity_id": exact.get("modelEntityId"),
        "entry_id": exact.get("entryId"),
        "global_metric_value": exact.get("globalMetricValue"),
        "latest_version": exact.get("latestVersion"),
        "sequence_start": exact.get("sequenceStart"),
        "sequence_end": exact.get("sequenceEnd"),
        "cif_url": exact.get("cifUrl"),
        "prediction_path": str(path).replace("\\", "/"),
    }


def _candidate_variant_rows(
    variant_library: SummaryLibrarySchema,
    protein_ref: str,
    covered_start: int | None,
    covered_end: int | None,
) -> tuple[list[dict[str, Any]], int]:
    candidate_rows: list[dict[str, Any]] = []
    parse_failures = 0
    records = [
        record
        for record in variant_library.variant_records
        if record.protein_ref == protein_ref
    ]
    sortable: list[tuple[int, str, Any]] = []
    for record in records:
        position = _parse_variant_position(record.variant_signature)
        if position is None:
            parse_failures += 1
            continue
        if covered_start is not None and position < covered_start:
            continue
        if covered_end is not None and position > covered_end:
            continue
        sortable.append((position, record.variant_signature, record))

    for position, _, record in sorted(sortable)[:5]:
        candidate_rows.append(
            {
                "summary_id": record.summary_id,
                "variant_signature": record.variant_signature,
                "variant_kind": record.variant_kind,
                "variant_position": position,
                "join_status": record.join_status,
                "join_reason": record.join_reason,
            }
        )
    return candidate_rows, parse_failures


def build_structure_followup_anchor_candidates(
    variant_library: SummaryLibrarySchema,
    operator_accession_matrix: dict[str, Any],
    rcsb_root: Path,
    alphafold_root: Path,
) -> dict[str, Any]:
    candidate_rows: list[dict[str, Any]] = []
    missing_evidence: list[str] = []
    for accession in _high_priority_accessions(operator_accession_matrix):
        protein_ref = _protein_ref(accession)
        rcsb_path = _latest_matching_file(
            rcsb_root,
            accession,
            f"{accession}.best_structures.json",
        )
        alphafold_path = _latest_matching_file(
            alphafold_root,
            accession,
            f"{accession}.prediction.json",
        )
        if rcsb_path is None or alphafold_path is None:
            missing_evidence.append(accession)
            continue

        best_targets = _best_experimental_targets(rcsb_path)
        primary_target = best_targets[0]
        variant_candidates, parse_failures = _candidate_variant_rows(
            variant_library,
            protein_ref,
            primary_target.get("unp_start"),
            primary_target.get("unp_end"),
        )
        alphafold_model = _alphafold_primary_model(alphafold_path, accession)
        candidate_rows.append(
            {
                "accession": accession,
                "protein_ref": protein_ref,
                "current_operator_action": "structure_followup_candidate",
                "current_structure_anchor_status": "candidate_only_no_variant_anchor",
                "variant_count": sum(
                    1
                    for record in variant_library.variant_records
                    if record.protein_ref == protein_ref
                ),
                "best_experimental_targets": best_targets,
                "recommended_experimental_anchor": primary_target,
                "alphafold_primary_model": alphafold_model,
                "candidate_variant_anchors": variant_candidates,
                "candidate_variant_anchor_count": len(variant_candidates),
                "variant_position_parse_failures": parse_failures,
                "next_materialization_requirements": [
                    "materialize a structure_unit row or equivalent bridge for this accession",
                    "set variant_ref to one explicit protein_variant.summary_id",
                    "preserve chain-level provenance and residue-span coverage",
                    "keep candidate_only until the structure-side variant_ref is explicit",
                ],
                "truth_note": (
                    "These are structure-backed follow-up candidates only. The current "
                    "surface shows residue-span-compatible variant signatures, but it "
                    "does not yet materialize a direct structure-backed variant join."
                ),
            }
        )

    return {
        "artifact_id": "structure_followup_anchor_candidates",
        "schema_id": "proteosphere-structure-followup-anchor-candidates-2026-04-01",
        "status": "complete" if not missing_evidence else "usable_with_notes",
        "row_count": len(candidate_rows),
        "rows": candidate_rows,
        "summary": {
            "candidate_accessions": [row["accession"] for row in candidate_rows],
            "missing_evidence_accessions": missing_evidence,
            "experimental_target_count": sum(
                len(row["best_experimental_targets"]) for row in candidate_rows
            ),
            "candidate_variant_anchor_count": sum(
                row["candidate_variant_anchor_count"] for row in candidate_rows
            ),
        },
        "truth_boundary": {
            "summary": (
                "This surface promotes exact next structure-backed follow-up candidates "
                "for high-priority variant-bearing accessions. It does not claim a direct "
                "structure-backed variant join until a structure-side variant_ref is "
                "materialized explicitly."
            ),
            "direct_structure_backed_join_materialized": False,
            "uses_real_raw_structure_evidence": True,
            "uses_real_variant_library_rows": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Structure Follow-Up Anchor Candidates",
        "",
        f"- Accessions: `{payload['row_count']}`",
        (
            "- Candidate variant anchors: "
            f"`{payload['summary']['candidate_variant_anchor_count']}`"
        ),
        "",
        "## Candidate Rows",
        "",
    ]
    for row in payload["rows"]:
        primary = row["recommended_experimental_anchor"]
        model = row["alphafold_primary_model"] or {}
        variant_signatures = ", ".join(
            item["variant_signature"] for item in row["candidate_variant_anchors"]
        )
        lines.extend(
            [
                f"- `{row['accession']}`",
                (
                    f"  top experimental anchor `{primary['pdb_id']}:{primary['chain_id']}`; "
                    f"method `{primary['experimental_method']}`; "
                    f"resolution `{primary['resolution']}`; "
                    f"coverage `{primary['coverage']}`"
                ),
                (
                    f"  AlphaFold `{model.get('entry_id', 'n/a')}`; "
                    f"global metric `{model.get('global_metric_value', 'n/a')}`"
                ),
                (
                    "  candidate variants "
                    f"`{variant_signatures}`"
                ),
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
        description=(
            "Export concrete structure-backed follow-up candidates for high-priority "
            "variant-bearing accessions."
        )
    )
    parser.add_argument("--variant-library", type=Path, default=DEFAULT_VARIANT_LIBRARY)
    parser.add_argument(
        "--operator-accession-matrix",
        type=Path,
        default=DEFAULT_OPERATOR_ACCESSION_MATRIX,
    )
    parser.add_argument("--rcsb-root", type=Path, default=DEFAULT_RCSB_ROOT)
    parser.add_argument("--alphafold-root", type=Path, default=DEFAULT_ALPHAFOLD_ROOT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_structure_followup_anchor_candidates(
        _read_library(args.variant_library),
        _read_json(args.operator_accession_matrix),
        args.rcsb_root,
        args.alphafold_root,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
