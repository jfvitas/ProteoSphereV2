from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAYLOAD_SCHEMA = (
    REPO_ROOT / "artifacts" / "status" / "p69_structure_followup_payload_schema.json"
)
DEFAULT_NEXT_SAFE_IMPL_ORDER = (
    REPO_ROOT / "artifacts" / "status" / "p72_structure_followup_next_safe_impl_order.json"
)
DEFAULT_ANCHOR_CANDIDATES = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_anchor_candidates.json"
)
DEFAULT_ANCHOR_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_anchor_validation.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_payload_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "structure_followup_payload_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json(path)


def _pick_row(
    anchor_candidates: dict[str, Any],
    accession: str,
) -> dict[str, Any]:
    for row in anchor_candidates.get("rows", []):
        if row["accession"] == accession:
            return row
    raise KeyError(f"missing anchor candidate row for {accession}")


def _build_payload_row(
    accession: str,
    anchor_row: dict[str, Any],
    source_artifact_ids: list[str],
) -> dict[str, Any]:
    recommended = anchor_row["recommended_experimental_anchor"]
    variant_anchor = anchor_row["candidate_variant_anchors"][0]
    return {
        "accession": accession,
        "protein_ref": anchor_row["protein_ref"],
        "variant_ref": variant_anchor["summary_id"],
        "protein_variant.summary_id": variant_anchor["summary_id"],
        "structure_id": recommended["pdb_id"],
        "chain_id": recommended["chain_id"],
        "residue_span_start": recommended["unp_start"],
        "residue_span_end": recommended["unp_end"],
        "uniprot_span": f"{recommended['unp_start']}-{recommended['unp_end']}",
        "coverage": recommended["coverage"],
        "experimental_method": recommended["experimental_method"],
        "resolution_angstrom": recommended["resolution"],
        "source_artifact_ids": source_artifact_ids,
        "candidate_only_status": "candidate_only_no_variant_anchor",
        "join_status": "candidate_only",
        "join_reason": "explicit structure-side variant_ref required before promotion",
        "truth_note": (
            "This is a narrow executable payload preview row, not a certified direct "
            "structure-backed join."
        ),
    }


def build_structure_followup_payload_preview(
    payload_schema: dict[str, Any],
    next_safe_impl_order: dict[str, Any] | None,
    anchor_candidates: dict[str, Any],
    anchor_validation: dict[str, Any],
) -> dict[str, Any]:
    payload_scope = payload_schema["payload_scope"]
    primary_accession = payload_scope["accession"]
    validated_rows = {
        row["accession"]: row for row in anchor_validation.get("validated_rows", [])
    }
    payload_accessions = [primary_accession]
    if next_safe_impl_order is not None:
        next_target = next_safe_impl_order.get("next_safe_target", {}).get("accession")
        if next_target and next_target not in payload_accessions:
            payload_accessions.append(next_target)

    source_artifact_ids = [
        "structure_followup_anchor_candidates",
        "structure_followup_anchor_validation",
        "p68_structure_followup_first_payload_plan",
        "p69_structure_followup_payload_schema",
    ]
    if next_safe_impl_order is not None:
        source_artifact_ids.append("p72_structure_followup_next_safe_impl_order")

    payload_rows = []
    row_validation = []
    for accession in payload_accessions:
        anchor_row = _pick_row(anchor_candidates, accession)
        validated = validated_rows[accession]
        payload_rows.append(_build_payload_row(accession, anchor_row, source_artifact_ids))
        row_validation.append(
            {
                "accession": accession,
                "recommended_anchor_present_in_best_targets": validated[
                    "recommended_anchor_present_in_best_targets"
                ],
                "variant_positions_within_recommended_span": validated[
                    "variant_positions_within_recommended_span"
                ],
                "candidate_variant_anchor_count": validated[
                    "candidate_variant_anchor_count"
                ],
            }
        )

    return {
        "artifact_id": "structure_followup_payload_preview",
        "schema_id": "proteosphere-structure-followup-payload-preview-2026-04-01",
        "status": "complete",
        "target_accession": primary_accession,
        "payload_accessions": payload_accessions,
        "payload_row_count": len(payload_rows),
        "payload_rows": payload_rows,
        "validation_context": {
            "anchor_validation_status": anchor_validation["status"],
            "validated_accessions": payload_accessions,
            "candidate_variant_anchor_count_total": sum(
                row["candidate_variant_anchor_count"] for row in row_validation
            ),
            "row_validation": row_validation,
        },
        "truth_boundary": {
            "summary": (
                "This preview materializes a narrow two-row structure-followup payload "
                "for P31749 and P04637. Both rows remain explicitly candidate-only and "
                "do not certify or promote direct structure-backed variant joins."
            ),
            "candidate_only_no_variant_anchor": True,
            "direct_structure_backed_join_certified": False,
            "promoted_structure_unit": False,
            "ready_for_preview_validation": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    validation = payload["validation_context"]
    lines = [
        "# Structure Follow-Up Payload Preview",
        "",
        f"- Target accession: `{payload['target_accession']}`",
        f"- Payload accessions: `{', '.join(payload['payload_accessions'])}`",
        f"- Payload rows: `{payload['payload_row_count']}`",
        "",
        "## Payload Rows",
        "",
    ]
    for row in payload["payload_rows"]:
        lines.extend(
            [
                f"- `{row['accession']}` -> `{row['variant_ref']}` at "
                f"`{row['structure_id']}:{row['chain_id']}` "
                f"covering `{row['uniprot_span']}` with coverage `{row['coverage']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Validation Context",
            "",
        ]
    )
    for row in validation["row_validation"]:
        lines.append(
            f"- `{row['accession']}` recommended-anchor-present="
            f"`{row['recommended_anchor_present_in_best_targets']}`, "
            f"span-compatible=`{row['variant_positions_within_recommended_span']}`, "
            f"candidate-anchors=`{row['candidate_variant_anchor_count']}`"
        )
    lines.extend(
        [
        f"- Anchor validation status: `{validation['anchor_validation_status']}`",
        (
            "- Total candidate variant anchors: "
            f"`{validation['candidate_variant_anchor_count_total']}`"
        ),
        "",
        "## Truth Boundary",
        "",
        f"- {payload['truth_boundary']['summary']}",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the first narrow structure follow-up payload preview."
    )
    parser.add_argument("--payload-schema", type=Path, default=DEFAULT_PAYLOAD_SCHEMA)
    parser.add_argument(
        "--next-safe-impl-order",
        type=Path,
        default=DEFAULT_NEXT_SAFE_IMPL_ORDER,
    )
    parser.add_argument("--anchor-candidates", type=Path, default=DEFAULT_ANCHOR_CANDIDATES)
    parser.add_argument("--anchor-validation", type=Path, default=DEFAULT_ANCHOR_VALIDATION)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_structure_followup_payload_preview(
        _read_json(args.payload_schema),
        _read_json_if_exists(args.next_safe_impl_order),
        _read_json(args.anchor_candidates),
        _read_json(args.anchor_validation),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
