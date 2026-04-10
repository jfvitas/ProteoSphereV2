from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from training_set_builder_preview_support import read_json, write_json  # noqa: E402

DEFAULT_PREVIEW_HOLD_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_preview_hold_register_preview.json"
)
DEFAULT_GATE_LADDER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_gate_ladder_preview.json"
)
DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_package_blocker_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "training_set_preview_hold_exit_criteria_preview.json"
)

EXIT_CRITERIA_BY_REASON = {
    "packet_partial_or_missing": "packet completeness must reach non-partial state",
    "modality_gap": "required missing modalities must be materialized",
    "package_gate_closed": "package gate must open before promotion",
    "preview_only_non_governing": (
        "preview-only rows must remain non-governing unless explicitly rescoped"
    ),
    "thin_coverage": "coverage depth must improve beyond thin-coverage state",
    "mixed_evidence": "mixed evidence must be reconciled or retained as support-only",
    "fold_export_ready=false": "fold export readiness must become true",
    "cv_fold_export_unlocked=false": "cross-validation fold export must unlock",
    "split_post_staging_gate_closed": "post-staging split gate must open",
    "split_dry_run_not_aligned": "split dry run must align with readiness state",
    "source_fix_available": "source-fix opportunities must be resolved or accepted as support-only",
}


def _load_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _listify(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    seen: dict[str, str] = {}
    for value in values:
        text = str(value or "").strip()
        if text:
            seen.setdefault(text.casefold(), text)
    return list(seen.values())


def _rows_by_accession(rows: Any) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return indexed
    for row in rows:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if accession:
            indexed[accession] = row
    return indexed


def _derive_exit_criteria(blocking_reasons: list[str]) -> list[str]:
    criteria: list[str] = []
    for reason in blocking_reasons:
        mapped = EXIT_CRITERIA_BY_REASON.get(reason)
        if mapped:
            criteria.append(mapped)
        elif reason.startswith("gap:"):
            criteria.append(
                f"{reason.removeprefix('gap:')} modality must be materialized"
            )
    return _listify(criteria)


def build_training_set_preview_hold_exit_criteria_preview(
    preview_hold_register_preview: dict[str, Any],
    gate_ladder_preview: dict[str, Any],
    package_blocker_matrix_preview: dict[str, Any],
) -> dict[str, Any]:
    hold_rows = preview_hold_register_preview.get("rows") or []
    gate_rows = gate_ladder_preview.get("rows") or []
    blocker_rows = package_blocker_matrix_preview.get("rows") or []

    gate_by_accession = _rows_by_accession(gate_rows)
    blocker_by_accession = _rows_by_accession(blocker_rows)

    rows: list[dict[str, Any]] = []
    state_counts: Counter[str] = Counter()
    criteria_counts: Counter[str] = Counter()
    review_counts: Counter[str] = Counter()

    for hold_row in hold_rows:
        if not isinstance(hold_row, dict):
            continue
        accession = str(hold_row.get("accession") or "").strip()
        if not accession:
            continue

        gate_row = gate_by_accession.get(accession, {})
        blocker_row = blocker_by_accession.get(accession, {})
        blocking_reasons = _listify(hold_row.get("hold_reasons"))
        blocking_reasons.extend(_listify(gate_row.get("blocked_reasons")))
        blocking_reasons.extend(_listify(blocker_row.get("package_blockers")))
        blocking_reasons = _listify(blocking_reasons)

        exit_criteria = _derive_exit_criteria(blocking_reasons)
        must_remain_true = _listify(
            [
                "training row remains non-governing until package gates explicitly unlock",
                "preview visibility must not be mistaken for release readiness",
            ]
        )
        prohibited_promotions = _listify(
            [
                "package promotion",
                "release-ready claim",
                "governing upgrade without explicit gate unlock",
            ]
        )

        if any(
            reason in blocking_reasons
            for reason in (
                "package_gate_closed",
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
                "split_post_staging_gate_closed",
            )
        ):
            exit_state = "blocked_pending_package_gate_unlock"
            next_review_step = "recheck fold export and package gates after split unlock"
        elif any(
            reason in blocking_reasons
            for reason in ("packet_partial_or_missing", "modality_gap", "thin_coverage")
        ):
            exit_state = "blocked_pending_packet_and_modality_completion"
            next_review_step = "recheck packet completeness and modality gaps after source refresh"
        else:
            exit_state = "support_only_hold_pending_manual_review"
            next_review_step = (
                "reconfirm support-only visibility boundary before next package review"
            )

        state_counts[exit_state] += 1
        review_counts[next_review_step] += 1
        for criterion in exit_criteria:
            criteria_counts[criterion] += 1

        rows.append(
            {
                "accession": accession,
                "preview_hold_state": hold_row.get("preview_hold_state"),
                "hold_lane": hold_row.get("hold_lane"),
                "training_set_state": hold_row.get("training_set_state"),
                "exit_criteria_state": exit_state,
                "blocking_reasons": blocking_reasons,
                "exit_criteria": exit_criteria,
                "clear_when_true": exit_criteria,
                "must_remain_true": must_remain_true,
                "prohibited_promotions": prohibited_promotions,
                "next_review_step": next_review_step,
                "priority_bucket": hold_row.get("priority_bucket")
                or gate_row.get("priority_bucket")
                or blocker_row.get("priority_bucket"),
                "modality_gap_categories": _listify(
                    hold_row.get("modality_gap_categories")
                    or gate_row.get("modality_gap_categories")
                    or blocker_row.get("modality_gap_categories")
                ),
                "source_fix_refs": _listify(hold_row.get("source_fix_refs")),
                "supporting_artifacts": _listify(hold_row.get("supporting_artifacts"))
                or [
                    "training_set_preview_hold_register_preview",
                    "training_set_gate_ladder_preview",
                    "training_set_package_blocker_matrix_preview",
                ],
            }
        )

    rows.sort(
        key=lambda row: (
            str(row.get("priority_bucket") or ""),
            str(row.get("accession") or "").casefold(),
        )
    )

    return {
        "artifact_id": "training_set_preview_hold_exit_criteria_preview",
        "schema_id": "proteosphere-training-set-preview-hold-exit-criteria-preview-2026-04-03",
        "status": "report_only",
        "generated_at": preview_hold_register_preview.get("generated_at")
        or gate_ladder_preview.get("generated_at")
        or package_blocker_matrix_preview.get("generated_at"),
        "summary": {
            "selected_count": int(
                (preview_hold_register_preview.get("summary") or {}).get("selected_count")
                or 0
            ),
            "exit_criteria_row_count": len(rows),
            "current_exit_state": (
                "preview_hold_exit_criteria_active"
                if rows
                else "no_preview_hold_exit_criteria_rows"
            ),
            "package_gate_blocked_count": state_counts.get(
                "blocked_pending_package_gate_unlock", 0
            ),
            "packet_and_modality_blocked_count": state_counts.get(
                "blocked_pending_packet_and_modality_completion", 0
            ),
            "support_only_review_count": state_counts.get(
                "support_only_hold_pending_manual_review", 0
            ),
            "top_exit_criteria": [
                {"exit_criterion": item, "accession_count": count}
                for item, count in criteria_counts.most_common(8)
            ],
            "top_next_review_steps": [
                {"next_review_step": item, "accession_count": count}
                for item, count in review_counts.most_common(8)
            ],
            "fail_closed": True,
            "non_mutating": True,
        },
        "rows": rows,
        "source_artifacts": {
            "training_set_preview_hold_register_preview": str(
                DEFAULT_PREVIEW_HOLD_REGISTER_PREVIEW
            ).replace("\\", "/"),
            "training_set_gate_ladder_preview": str(
                DEFAULT_GATE_LADDER_PREVIEW
            ).replace("\\", "/"),
            "training_set_package_blocker_matrix_preview": str(
                DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This exit-criteria preview is report-only and fail-closed. "
                "It makes preview-hold exit conditions explicit for operator review, "
                "but it does not unlock packaging, release claims, or governing use."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "package_not_authorized": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the training-set preview hold exit criteria preview."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_training_set_preview_hold_exit_criteria_preview(
        _load_payload(DEFAULT_PREVIEW_HOLD_REGISTER_PREVIEW),
        _load_payload(DEFAULT_GATE_LADDER_PREVIEW),
        _load_payload(DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
