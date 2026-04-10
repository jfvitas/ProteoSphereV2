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

from training_set_builder_preview_support import (  # noqa: E402
    read_json,
    write_json,
    write_text,
)

DEFAULT_TRAINING_SET_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "training_set_readiness_preview.json"
)
DEFAULT_PACKAGE_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
)
DEFAULT_SPLIT_SIMULATION = REPO_ROOT / "artifacts" / "status" / "split_simulation_preview.json"
DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_blocker_burndown_preview.json"
)
DEFAULT_TRAINING_SET_MODALITY_GAP_REGISTER = (
    REPO_ROOT / "artifacts" / "status" / "training_set_modality_gap_register_preview.json"
)
DEFAULT_TRAINING_SET_PACKAGE_BLOCKER_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "training_set_package_blocker_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "training_set_gate_ladder_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "training_set_gate_ladder_preview.md"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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


def _ordered_accessions(*rows_sources: Any) -> list[str]:
    seen: dict[str, None] = {}
    for rows in rows_sources:
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            accession = str(row.get("accession") or "").strip()
            if accession and accession not in seen:
                seen[accession] = None
    return list(seen.keys())


def _normalize_list(values: Any) -> list[str]:
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


def _count_values(values: Any) -> dict[str, int]:
    counter = Counter()
    if isinstance(values, list):
        for value in values:
            text = str(value or "").strip()
            if text:
                counter[text] += 1
    return dict(sorted(counter.items()))


def _top_n(counter: Counter[str], limit: int = 5) -> list[dict[str, Any]]:
    return [
        {"reason": item, "accession_count": count}
        for item, count in counter.most_common(limit)
    ]


def _derive_inclusion_class(training_set_state: str) -> str:
    if training_set_state == "governing_ready":
        return "selected"
    if training_set_state == "blocked_pending_acquisition":
        return "gated"
    return "preview-only"


def _gate_ladder_state(
    readiness_row: dict[str, Any],
    package_summary: dict[str, Any],
    split_summary: dict[str, Any],
) -> str:
    package_ready = bool(package_summary.get("ready_for_package"))
    fold_export_ready = bool(split_summary.get("fold_export_ready"))
    cv_unlocked = bool(split_summary.get("cv_fold_export_unlocked"))
    assignment_ready = bool(readiness_row.get("assignment_ready"))
    training_set_state = str(readiness_row.get("training_set_state") or "").strip()

    if package_ready and fold_export_ready and cv_unlocked and assignment_ready:
        return "ready_for_package"
    if training_set_state == "blocked_pending_acquisition":
        return "blocked_pending_acquisition"
    if training_set_state == "governing_ready":
        return "governing_ready_but_package_blocked"
    return "preview_visible_non_governing"


def _collect_blocking_reasons(*rows_sources: Any) -> Counter[str]:
    reasons: Counter[str] = Counter()
    for rows in rows_sources:
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key in ("blocked_reasons", "blocker_context", "package_blockers"):
                for reason in _normalize_list(row.get(key)):
                    reasons[reason] += 1
            for reason in _normalize_list(row.get("gap_categories")):
                reasons[f"gap:{reason}"] += 1
            for reason in _normalize_list(row.get("modality_gap_categories")):
                reasons[f"gap:{reason}"] += 1
    return reasons


def _collect_next_steps(*rows_sources: Any) -> Counter[str]:
    next_steps: Counter[str] = Counter()
    for rows in rows_sources:
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            candidates = _normalize_list(
                row.get("recommended_next_step")
                or row.get("recommended_next_actions")
                or row.get("top_next_actions")
            )
            if candidates:
                next_steps[candidates[0]] += 1
    return next_steps


def build_training_set_gate_ladder_preview(
    training_set_readiness_preview: dict[str, Any],
    package_readiness_preview: dict[str, Any],
    split_simulation_preview: dict[str, Any],
    training_set_blocker_burndown_preview: dict[str, Any],
    training_set_modality_gap_register_preview: dict[str, Any],
    training_set_package_blocker_matrix_preview: dict[str, Any],
) -> dict[str, Any]:
    readiness_summary = _as_dict(training_set_readiness_preview.get("summary"))
    package_summary = _as_dict(package_readiness_preview.get("summary"))
    split_summary = _as_dict(split_simulation_preview.get("summary"))
    burndown_rows = training_set_blocker_burndown_preview.get("rows") or []
    modality_rows = training_set_modality_gap_register_preview.get("rows") or []
    package_rows = training_set_package_blocker_matrix_preview.get("rows") or []
    readiness_rows = training_set_readiness_preview.get("readiness_rows") or []
    split_rows = split_simulation_preview.get("rows") or []

    readiness_by_accession = _rows_by_accession(readiness_rows)
    burndown_by_accession = _rows_by_accession(burndown_rows)
    modality_by_accession = _rows_by_accession(modality_rows)
    package_by_accession = _rows_by_accession(package_rows)
    split_by_accession = _rows_by_accession(split_rows)

    selected_accessions = _ordered_accessions(readiness_rows, package_rows, split_rows)
    rows: list[dict[str, Any]] = []
    for accession in selected_accessions:
        readiness_row = readiness_by_accession.get(accession, {})
        package_row = package_by_accession.get(accession, {})
        modality_row = modality_by_accession.get(accession, {})
        burndown_row = burndown_by_accession.get(accession, {})
        split_row = split_by_accession.get(accession, {})

        training_set_state = str(
            readiness_row.get("training_set_state")
            or package_row.get("training_set_state")
            or split_row.get("status")
            or "unknown"
        ).strip()
        split_name = str(split_row.get("split") or readiness_row.get("split") or "").strip()
        bucket = str(split_row.get("bucket") or "").strip()

        package_blockers = _normalize_list(
            package_row.get("package_blockers") or burndown_row.get("blocker_context")
        )
        blocked_reasons = _normalize_list(package_row.get("blocked_reasons"))
        if not blocked_reasons:
            blocked_reasons = package_blockers[:]
        blocked_reason_count = int(
            package_row.get("blocked_reason_count")
            or len(blocked_reasons)
            or len(package_blockers)
            or 0
        )

        rows.append(
            {
                "accession": accession,
                "split": split_name,
                "bucket": bucket,
                "training_set_state": training_set_state,
                "inclusion_class": _derive_inclusion_class(training_set_state),
                "gate_ladder_state": _gate_ladder_state(
                    readiness_row,
                    package_summary,
                    split_summary,
                ),
                "assignment_ready": bool(readiness_summary.get("assignment_ready")),
                "fold_export_ready": bool(readiness_summary.get("fold_export_ready")),
                "cv_fold_export_unlocked": bool(
                    split_summary.get("cv_fold_export_unlocked")
                    if split_summary
                    else package_summary.get("cv_fold_export_unlocked")
                ),
                "split_dry_run_validation_status": split_summary.get(
                    "dry_run_validation_status"
                ),
                "package_ready": bool(package_summary.get("ready_for_package")),
                "critical_action": bool(burndown_row.get("critical_action")),
                "priority_bucket": str(
                    package_row.get("priority_bucket") or burndown_row.get("priority_bucket") or ""
                ).strip(),
                "packet_status": str(
                    readiness_row.get("packet_status")
                    or package_row.get("packet_status")
                    or "partial"
                ).strip(),
                "blocked_reason_count": blocked_reason_count,
                "blocked_reasons": blocked_reasons,
                "modality_gap_categories": _normalize_list(
                    package_row.get("modality_gap_categories") or modality_row.get("gap_categories")
                ),
                "modality_blocked": bool(
                    package_row.get("modality_blocked")
                    or bool(_normalize_list(modality_row.get("gap_categories")))
                ),
                "recommended_next_step": str(
                    readiness_row.get("recommended_next_step")
                    or package_row.get("recommended_next_step")
                    or burndown_row.get("action_ref")
                    or "keep_visible_as_support_only"
                ).strip(),
                "top_next_actions": _normalize_list(
                    package_row.get("recommended_next_actions")
                    or burndown_row.get("top_next_actions")
                ),
                "source_fix_refs": _normalize_list(
                    package_row.get("source_fix_refs")
                    or burndown_row.get("top_source_fix_refs")
                ),
            }
        )

    blocking_reason_counts = _collect_blocking_reasons(
        training_set_blocker_burndown_preview.get("rows"),
        training_set_modality_gap_register_preview.get("rows"),
        training_set_package_blocker_matrix_preview.get("rows"),
    )
    next_step_counts = _collect_next_steps(
        training_set_readiness_preview.get("readiness_rows"),
        training_set_blocker_burndown_preview.get("rows"),
        training_set_package_blocker_matrix_preview.get("rows"),
    )

    readiness_blocked_reasons = _normalize_list(readiness_summary.get("blocked_reasons"))
    package_blocked_reasons = _normalize_list(package_summary.get("blocked_reasons"))
    consistency_alerts: list[str] = []
    if "split_dry_run_not_aligned" in readiness_blocked_reasons and (
        split_summary.get("dry_run_validation_status") == "aligned"
    ):
        consistency_alerts.append(
            "training_set_readiness reports split_dry_run_not_aligned while "
            "split_simulation is aligned"
        )
    if readiness_summary.get("assignment_ready") and not split_summary.get("fold_export_ready"):
        consistency_alerts.append(
            "assignment is ready, but fold export remains blocked in split simulation"
        )

    ladder_steps = [
        {
            "stage": "readiness",
            "status": (
                "assignment_ready" if readiness_summary.get("assignment_ready") else "blocked"
            ),
            "assignment_ready": bool(readiness_summary.get("assignment_ready")),
            "blocked_reasons": readiness_blocked_reasons,
            "source_artifact": "training_set_readiness_preview",
        },
        {
            "stage": "split",
            "status": split_summary.get("dry_run_validation_status") or "unknown",
            "fold_export_ready": bool(split_summary.get("fold_export_ready")),
            "cv_fold_export_unlocked": bool(split_summary.get("cv_fold_export_unlocked")),
            "blocked_reasons": _normalize_list(split_summary.get("package_blocking_factors")),
            "source_artifact": "split_simulation_preview",
        },
        {
            "stage": "package",
            "status": "ready" if package_summary.get("ready_for_package") else "blocked",
            "ready_for_package": bool(package_summary.get("ready_for_package")),
            "blocked_reasons": package_blocked_reasons,
            "source_artifact": "package_readiness_preview",
        },
        {
            "stage": "release",
            "status": "blocked" if not package_summary.get("ready_for_package") else "ready",
            "ready_for_release": False,
            "blocked_reasons": package_blocked_reasons or readiness_blocked_reasons,
            "source_artifact": "training_set_readiness_preview",
        },
    ]

    selected_count = len(rows)
    blocked_count = sum(1 for row in rows if row["package_ready"] is False)
    critical_action_count = sum(1 for row in rows if row["critical_action"])
    modality_blocked_count = sum(1 for row in rows if row["modality_blocked"])
    packet_partial_count = sum(1 for row in rows if row["packet_status"] != "ready")
    missing_inputs = [
        name
        for name, payload in {
            "training_set_readiness_preview": training_set_readiness_preview,
            "package_readiness_preview": package_readiness_preview,
            "split_simulation_preview": split_simulation_preview,
            "training_set_blocker_burndown_preview": training_set_blocker_burndown_preview,
            "training_set_modality_gap_register_preview": (
                training_set_modality_gap_register_preview
            ),
            "training_set_package_blocker_matrix_preview": (
                training_set_package_blocker_matrix_preview
            ),
        }.items()
        if not payload
    ]
    gate_ladder_status = (
        "blocked_missing_inputs"
        if missing_inputs
        else (
            "ready_for_package"
            if package_summary.get("ready_for_package")
            else "blocked_pending_package_gate"
        )
    )

    return {
        "artifact_id": "training_set_gate_ladder_preview",
        "schema_id": "proteosphere-training-set-gate-ladder-preview-2026-04-03",
        "status": "report_only",
        "generated_at": max(
            [
                str(
                    readiness_summary.get("generated_at")
                    or training_set_readiness_preview.get("generated_at")
                    or ""
                ),
                str(
                    package_summary.get("generated_at")
                    or package_readiness_preview.get("generated_at")
                    or ""
                ),
                str(
                    split_summary.get("generated_at")
                    or split_simulation_preview.get("generated_at")
                    or ""
                ),
                str(
                    training_set_blocker_burndown_preview.get("generated_at")
                    or training_set_modality_gap_register_preview.get("generated_at")
                    or training_set_package_blocker_matrix_preview.get("generated_at")
                    or ""
                ),
            ]
        ).strip(),
        "summary": {
            "selected_count": selected_count,
            "selected_accessions": selected_accessions,
            "assignment_ready": bool(readiness_summary.get("assignment_ready")),
            "split_dry_run_status": split_summary.get("dry_run_validation_status"),
            "fold_export_ready": bool(readiness_summary.get("fold_export_ready")),
            "cv_fold_export_unlocked": bool(split_summary.get("cv_fold_export_unlocked")),
            "package_ready": bool(package_summary.get("ready_for_package")),
            "release_ready": False,
            "blocked_accession_count": blocked_count,
            "critical_action_count": critical_action_count,
            "modality_blocked_count": modality_blocked_count,
            "packet_partial_count": packet_partial_count,
            "non_mutating": True,
            "fail_closed": True,
            "gate_ladder_status": gate_ladder_status,
            "gate_ladder_steps": ladder_steps,
            "blocked_reasons": _normalize_list(
                readiness_blocked_reasons
                + package_blocked_reasons
                + list(blocking_reason_counts.keys())
            ),
            "top_blocking_reasons": _top_n(blocking_reason_counts),
            "top_next_steps": [
                {"next_step": step, "accession_count": count}
                for step, count in next_step_counts.most_common(5)
            ],
            "selected_split_counts": _count_values([row.get("split") for row in rows]),
            "consistency_alerts": consistency_alerts,
            "missing_inputs": missing_inputs,
        },
        "rows": rows,
        "source_artifacts": {
            "training_set_readiness": str(DEFAULT_TRAINING_SET_READINESS),
            "package_readiness": str(DEFAULT_PACKAGE_READINESS),
            "split_simulation": str(DEFAULT_SPLIT_SIMULATION),
            "training_set_blocker_burndown": str(DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN),
            "training_set_modality_gap_register": str(DEFAULT_TRAINING_SET_MODALITY_GAP_REGISTER),
            "training_set_package_blocker_matrix": str(
                DEFAULT_TRAINING_SET_PACKAGE_BLOCKER_MATRIX
            ),
        },
        "truth_boundary": {
            "summary": (
                "This gate-ladder preview is report-only. It compacts readiness, split, and "
                "package gate state for operator review, but it does not mutate artifacts or "
                "authorize packaging."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Training Set Gate Ladder Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Gate ladder status: `{summary.get('gate_ladder_status')}`",
        f"- Selected count: `{summary.get('selected_count')}`",
        f"- Package ready: `{summary.get('package_ready')}`",
        "",
        "## Gate Ladder",
        "",
    ]
    for step in summary.get("gate_ladder_steps") or []:
        if not isinstance(step, dict):
            continue
        lines.append(
            f"- `{step.get('stage')}`: `{step.get('status')}`"
        )
    lines.extend(["", "## Selected Accessions", ""])
    for row in payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        accession = row.get("accession")
        if accession:
            lines.append(
                f"- `{accession}` -> `{row.get('training_set_state')}` / "
                f"`{row.get('gate_ladder_state')}`"
            )
    if summary.get("consistency_alerts"):
        lines.extend(["", "## Consistency Alerts", ""])
        for alert in summary["consistency_alerts"]:
            lines.append(f"- {alert}")
    lines.extend(["", "## Truth Boundary", ""])
    lines.append(f"- {payload.get('truth_boundary', {}).get('summary')}")
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export training set gate ladder preview.")
    parser.add_argument(
        "--training-set-readiness",
        type=Path,
        default=DEFAULT_TRAINING_SET_READINESS,
    )
    parser.add_argument("--package-readiness", type=Path, default=DEFAULT_PACKAGE_READINESS)
    parser.add_argument("--split-simulation", type=Path, default=DEFAULT_SPLIT_SIMULATION)
    parser.add_argument(
        "--training-set-blocker-burndown",
        type=Path,
        default=DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN,
    )
    parser.add_argument(
        "--training-set-modality-gap-register",
        type=Path,
        default=DEFAULT_TRAINING_SET_MODALITY_GAP_REGISTER,
    )
    parser.add_argument(
        "--training-set-package-blocker-matrix",
        type=Path,
        default=DEFAULT_TRAINING_SET_PACKAGE_BLOCKER_MATRIX,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_training_set_gate_ladder_preview(
        read_json(args.training_set_readiness),
        read_json(args.package_readiness),
        read_json(args.split_simulation),
        read_json(args.training_set_blocker_burndown),
        read_json(args.training_set_modality_gap_register),
        read_json(args.training_set_package_blocker_matrix),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
