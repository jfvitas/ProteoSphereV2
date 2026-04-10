from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENTITY_SPLIT_RECIPE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_recipe_preview.json"
)
DEFAULT_ENTITY_SPLIT_ASSIGNMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_assignment_preview.json"
)
DEFAULT_LIGAND_ROW_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
)
DEFAULT_MOTIF_DOMAIN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "motif_domain_compact_preview_family.json"
)
DEFAULT_INTERACTION_SIMILARITY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "interaction_similarity_signature_preview.json"
)
DEFAULT_ELIGIBILITY_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_materialization_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_input_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "split_engine_input_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_supplemental_non_governing_signals(
    ligand_row_preview: dict[str, Any],
    motif_domain_preview: dict[str, Any],
    interaction_similarity_preview: dict[str, Any],
    eligibility_matrix_preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ligand_summary = ligand_row_preview.get("summary") or {}
    ligand_truth = ligand_row_preview.get("truth_boundary") or {}
    grounded_accessions = [
        str(value).strip()
        for value in (ligand_summary.get("grounded_accessions") or [])
        if str(value).strip()
    ]
    candidate_only_accessions = [
        str(value).strip()
        for value in (ligand_summary.get("candidate_only_accessions") or [])
        if str(value).strip()
    ]
    ligand_status = (
        "available_non_governing"
        if ligand_truth.get("ligand_rows_materialized")
        else "not_materialized"
    )
    ligand_notes = []
    if len(grounded_accessions) < 2:
        ligand_notes.append(
            "Only one grounded ligand accession exists, so ligand-aware split remains locked."
        )
    if candidate_only_accessions:
        ligand_notes.append(
            "Candidate-only ligand accessions remain visible but non-governing."
        )

    motif_truth = motif_domain_preview.get("truth_boundary") or {}
    motif_status = (
        "available_non_governing"
        if motif_truth.get("ready_for_bundle_preview")
        else "not_materialized"
    )

    interaction_truth = interaction_similarity_preview.get("truth_boundary") or {}
    interaction_status = (
        "blocked_candidate_only"
        if interaction_truth.get("candidate_only_rows")
        else "available_non_governing"
        if interaction_truth.get("ready_for_bundle_preview")
        else "not_materialized"
    )

    supplemental = {
        "ligand_rows": {
            "status": ligand_status,
            "row_count": int(ligand_row_preview.get("row_count") or 0),
            "grounded_accession_count": len(grounded_accessions),
            "candidate_only_accession_count": len(candidate_only_accessions),
            "split_governing_unlocked": len(grounded_accessions) >= 2,
            "notes": ligand_notes,
        },
        "motif_domain_compact": {
            "status": motif_status,
            "row_count": int(motif_domain_preview.get("row_count") or 0),
            "governing_for_split_or_leakage": bool(
                motif_truth.get("governing_for_split_or_leakage")
            ),
            "notes": [
                "Motif/domain compact rows may support audit or balancing context only."
            ],
        },
        "interaction_similarity_preview": {
            "status": interaction_status,
            "row_count": int(interaction_similarity_preview.get("row_count") or 0),
            "candidate_only_row_count": int(
                (interaction_similarity_preview.get("summary") or {}).get(
                    "candidate_only_row_count"
                )
                or 0
            ),
            "ready_for_bundle_preview": bool(
                interaction_truth.get("ready_for_bundle_preview")
            ),
            "notes": [
                "Interaction similarity remains blocked for split follow-through while the "
                "current preview is candidate-only and not bundle-ready."
            ],
        },
    }
    if eligibility_matrix_preview is not None:
        summary = eligibility_matrix_preview.get("summary") or {}
        supplemental["modality_readiness"] = {
            "status": "available_non_governing",
            "modality_counts": summary.get("modality_readiness_counts", {}),
            "ligand_readiness_counts": summary.get("ligand_readiness_ladder_counts", {}),
        }
    return supplemental


def build_split_engine_input_preview(
    recipe_preview: dict[str, Any],
    assignment_preview: dict[str, Any],
    ligand_row_preview: dict[str, Any],
    motif_domain_preview: dict[str, Any],
    interaction_similarity_preview: dict[str, Any],
    eligibility_matrix_preview: dict[str, Any] | None = None,
    split_fold_export_materialization_preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recipe = recipe_preview["recipe"]
    assignment_summary = assignment_preview["summary"]
    group_rows = assignment_preview["group_rows"]
    supplemental_non_governing_signals = _build_supplemental_non_governing_signals(
        ligand_row_preview,
        motif_domain_preview,
        interaction_similarity_preview,
        eligibility_matrix_preview,
    )
    ligand_split_governing_unlocked = supplemental_non_governing_signals["ligand_rows"][
        "split_governing_unlocked"
    ]
    fold_export_materialized = bool(
        (split_fold_export_materialization_preview or {}).get("truth_boundary", {}).get(
            "cv_folds_materialized"
        )
    )

    return {
        "artifact_id": "split_engine_input_preview",
        "schema_id": "proteosphere-split-engine-input-preview-2026-04-01",
        "status": "complete",
        "recipe_binding": {
            "recipe_id": recipe["recipe_id"],
            "input_artifact": recipe["input_artifact"],
            "atomic_unit": recipe["atomic_unit"],
            "primary_hard_group": recipe["hard_grouping"]["primary_group"],
            "secondary_hard_groups": recipe["hard_grouping"]["secondary_hard_groups"],
            "allowed_entity_families": recipe["allowed_entity_families"],
            "reserved_null_axes": recipe["reserved_null_axes"],
        },
        "assignment_binding": {
            "group_row_count": assignment_preview["group_row_count"],
            "candidate_row_count": assignment_summary["candidate_row_count"],
            "assignment_count": assignment_summary["assignment_count"],
            "split_group_counts": assignment_summary["split_group_counts"],
            "largest_groups": assignment_summary["largest_groups"],
        },
        "execution_readiness": {
            "recipe_ready": recipe_preview["truth_boundary"]["ready_for_recipe_export"],
            "assignment_ready": True,
            "fold_export_ready": (
                assignment_preview["truth_boundary"]["ready_for_fold_export"]
                or fold_export_materialized
            ),
            "next_unlocked_stage": (
                "split_fold_export_materialized"
                if fold_export_materialized
                else "split_engine_dry_run"
            ),
            "supplemental_non_governing_preview_ready": True,
            "ligand_governing_split_ready": ligand_split_governing_unlocked,
        },
        "supplemental_non_governing_signals": supplemental_non_governing_signals,
        "group_rows": group_rows,
        "truth_boundary": {
            "summary": (
                "This preview is the current split-engine handoff surface. It binds the live "
                "recipe preview to the live linked-group assignment preview, but it does not "
                "commit folds, CV partitions, or release-grade train/test exports. "
            "Supplemental ligand and motif/domain signals are visible here only as "
            "non-governing annotations."
        ),
        "final_split_committed": False,
        "cv_folds_materialized": fold_export_materialized,
        "ready_for_split_engine_dry_run": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    recipe_binding = payload["recipe_binding"]
    assignment_binding = payload["assignment_binding"]
    execution_readiness = payload["execution_readiness"]
    supplemental = payload["supplemental_non_governing_signals"]
    lines = [
        "# Split Engine Input Preview",
        "",
        f"- Recipe ID: `{recipe_binding['recipe_id']}`",
        f"- Input artifact: `{recipe_binding['input_artifact']}`",
        f"- Atomic unit: `{recipe_binding['atomic_unit']}`",
        f"- Primary hard group: `{recipe_binding['primary_hard_group']}`",
        f"- Group rows: `{assignment_binding['group_row_count']}`",
        f"- Candidate rows: `{assignment_binding['candidate_row_count']}`",
        "",
        "## Execution Readiness",
        "",
        f"- Recipe ready: `{execution_readiness['recipe_ready']}`",
        f"- Assignment ready: `{execution_readiness['assignment_ready']}`",
        f"- Fold export ready: `{execution_readiness['fold_export_ready']}`",
        f"- Next unlocked stage: `{execution_readiness['next_unlocked_stage']}`",
        f"- Ligand governing split ready: `{execution_readiness['ligand_governing_split_ready']}`",
        "",
        "## Supplemental Non-Governing Signals",
        "",
        "- Ligand rows: "
        f"`{supplemental['ligand_rows']['status']}` / "
        f"rows=`{supplemental['ligand_rows']['row_count']}` / "
        f"grounded_accessions=`{supplemental['ligand_rows']['grounded_accession_count']}`",
        "- Motif/domain compact: "
        f"`{supplemental['motif_domain_compact']['status']}` / "
        f"rows=`{supplemental['motif_domain_compact']['row_count']}`",
        "- Interaction similarity: "
        f"`{supplemental['interaction_similarity_preview']['status']}` / "
        f"rows=`{supplemental['interaction_similarity_preview']['row_count']}`",
        "",
        "## Truth Boundary",
        "",
        f"- {payload['truth_boundary']['summary']}",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a split-engine input preview from current split surfaces."
    )
    parser.add_argument(
        "--entity-split-recipe-preview",
        type=Path,
        default=DEFAULT_ENTITY_SPLIT_RECIPE_PREVIEW,
    )
    parser.add_argument(
        "--entity-split-assignment-preview",
        type=Path,
        default=DEFAULT_ENTITY_SPLIT_ASSIGNMENT_PREVIEW,
    )
    parser.add_argument("--ligand-row-preview", type=Path, default=DEFAULT_LIGAND_ROW_PREVIEW)
    parser.add_argument("--motif-domain-preview", type=Path, default=DEFAULT_MOTIF_DOMAIN_PREVIEW)
    parser.add_argument(
        "--interaction-similarity-preview",
        type=Path,
        default=DEFAULT_INTERACTION_SIMILARITY_PREVIEW,
    )
    parser.add_argument(
        "--eligibility-matrix-preview",
        type=Path,
        default=DEFAULT_ELIGIBILITY_MATRIX,
    )
    parser.add_argument(
        "--split-fold-export-materialization-preview",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_MATERIALIZATION_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_split_engine_input_preview(
        _read_json(args.entity_split_recipe_preview),
        _read_json(args.entity_split_assignment_preview),
        _read_json(args.ligand_row_preview),
        _read_json(args.motif_domain_preview),
        _read_json(args.interaction_similarity_preview),
        _read_json(args.eligibility_matrix_preview),
        _read_json(args.split_fold_export_materialization_preview)
        if args.split_fold_export_materialization_preview.exists()
        else None,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
