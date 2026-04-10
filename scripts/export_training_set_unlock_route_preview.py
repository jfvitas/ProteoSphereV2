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

DEFAULT_TRAINING_SET_GATE_LADDER = (
    REPO_ROOT / "artifacts" / "status" / "training_set_gate_ladder_preview.json"
)
DEFAULT_TRAINING_SET_UNBLOCK_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unblock_plan_preview.json"
)
DEFAULT_TRAINING_SET_ACTION_QUEUE = (
    REPO_ROOT / "artifacts" / "status" / "training_set_action_queue_preview.json"
)
DEFAULT_TRAINING_SET_PACKAGE_BLOCKER_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "training_set_package_blocker_matrix_preview.json"
)
DEFAULT_PACKAGE_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unlock_route_preview.json"
)


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


def _rows_grouped_by_accession(rows: Any) -> dict[str, list[dict[str, Any]]]:
    indexed: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(rows, list):
        return indexed
    for row in rows:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if accession:
            indexed.setdefault(accession, []).append(row)
    return indexed


def _ordered_accessions(*rows_sources: Any) -> list[str]:
    ordered: dict[str, None] = {}
    for rows in rows_sources:
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            accession = str(row.get("accession") or "").strip()
            if accession:
                ordered.setdefault(accession, None)
    return list(ordered)


def _path_stage(
    stage: str,
    *,
    status: str,
    clear_condition: str,
    blocking_reasons: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "status": status,
        "clear_condition": clear_condition,
        "blocking_reasons": _listify(blocking_reasons),
    }


def _route_state(
    training_set_state: str,
    gate_ladder_state: str,
    *,
    package_ready: bool,
    blocking_context: list[str],
) -> str:
    if package_ready and not blocking_context:
        return "ready_for_package"
    if training_set_state == "blocked_pending_acquisition":
        return "blocked_pending_acquisition"
    if (
        training_set_state == "governing_ready"
        or gate_ladder_state == "governing_ready_but_package_blocked"
    ):
        return "governing_ready_but_package_blocked"
    return "preview_visible_non_governing"


def build_training_set_unlock_route_preview(
    training_set_gate_ladder_preview: dict[str, Any],
    training_set_unblock_plan_preview: dict[str, Any],
    training_set_action_queue_preview: dict[str, Any],
    training_set_package_blocker_matrix_preview: dict[str, Any],
    package_readiness_preview: dict[str, Any],
) -> dict[str, Any]:
    gate_summary = dict(training_set_gate_ladder_preview.get("summary") or {})
    unblock_summary = dict(training_set_unblock_plan_preview.get("summary") or {})
    package_summary = dict(package_readiness_preview.get("summary") or {})

    gate_rows = training_set_gate_ladder_preview.get("rows") or []
    unblock_rows = training_set_unblock_plan_preview.get("rows") or []
    action_rows = training_set_action_queue_preview.get("rows") or []
    blocker_rows = training_set_package_blocker_matrix_preview.get("rows") or []

    gate_by_accession = _rows_by_accession(gate_rows)
    unblock_by_accession = _rows_by_accession(unblock_rows)
    blocker_by_accession = _rows_by_accession(blocker_rows)
    action_by_accession = _rows_grouped_by_accession(action_rows)
    selected_accessions = _ordered_accessions(gate_rows, unblock_rows, blocker_rows, action_rows)

    route_stages = [
        _path_stage(
            "readiness",
            status="ready" if gate_summary.get("assignment_ready") else "blocked",
            clear_condition="assignment_ready=true",
            blocking_reasons=(
                gate_summary.get("blocked_reasons")
                if not gate_summary.get("assignment_ready")
                else []
            ),
        ),
        _path_stage(
            "accession_remediation",
            status=(
                "blocked"
                if int(unblock_summary.get("impacted_accession_count") or 0) > 0
                else "ready"
            ),
            clear_condition="clear accession blockers and source-fix routes",
            blocking_reasons=[
                item.get("blocker")
                for item in (unblock_summary.get("package_blockers") or [])
                if isinstance(item, dict)
            ],
        ),
        _path_stage(
            "split_export",
            status=(
                "ready"
                if gate_summary.get("split_dry_run_status") == "aligned"
                and gate_summary.get("fold_export_ready")
                and gate_summary.get("cv_fold_export_unlocked")
                else "blocked"
            ),
            clear_condition="split dry run aligned and fold export unlocked",
            blocking_reasons=gate_summary.get("blocked_reasons"),
        ),
        _path_stage(
            "package",
            status="ready" if package_summary.get("ready_for_package") else "blocked",
            clear_condition="package_readiness.ready_for_package=true",
            blocking_reasons=package_summary.get("blocked_reasons"),
        ),
        _path_stage(
            "release_hold",
            status="preview_only_hold",
            clear_condition=(
                "explicit package materialization plus downstream release gates must clear"
            ),
            blocking_reasons=[
                "release_semantics_remain_blocked_during_report_only_phase"
            ],
        ),
    ]

    next_unlock_stage = next(
        (stage["stage"] for stage in route_stages if stage["status"] == "blocked"),
        "release_hold",
    )
    current_unlock_state = (
        "ready_for_package"
        if package_summary.get("ready_for_package")
        else "blocked_pending_unlock_route"
    )

    rows: list[dict[str, Any]] = []
    route_step_counts: Counter[str] = Counter()
    blocker_counts: Counter[str] = Counter()
    source_fix_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    impacted_accession_count = 0

    for accession in selected_accessions:
        gate_row = gate_by_accession.get(accession, {})
        unblock_row = unblock_by_accession.get(accession, {})
        blocker_row = blocker_by_accession.get(accession, {})
        accession_action_rows = action_by_accession.get(accession, [])

        route_steps: list[str] = []
        route_steps.extend(_listify(unblock_row.get("direct_remediation_routes")))
        route_steps.extend(
            _listify(row.get("action_ref"))[0]
            for row in accession_action_rows
            if _listify(row.get("action_ref"))
        )
        route_steps.extend(_listify(gate_row.get("recommended_next_step")))
        route_steps.extend(_listify(gate_row.get("top_next_actions")))
        route_steps = _listify(route_steps)

        source_fix_refs: list[str] = []
        source_fix_refs.extend(_listify(unblock_row.get("source_fix_refs")))
        for row in accession_action_rows:
            source_fix_refs.extend(_listify(row.get("source_fix_refs")))
        source_fix_refs.extend(_listify(gate_row.get("source_fix_refs")))
        source_fix_refs = _listify(source_fix_refs)

        blocking_context: list[str] = []
        blocking_context.extend(_listify(gate_row.get("blocked_reasons")))
        blocking_context.extend(_listify(unblock_row.get("package_blockers")))
        blocking_context.extend(_listify(blocker_row.get("package_blockers")))
        blocking_context = _listify(blocking_context)

        priority_bucket = next(
            (
                str(row.get("priority_bucket") or "").strip()
                for row in accession_action_rows
                if str(row.get("priority_bucket") or "").strip()
            ),
            str(blocker_row.get("priority_bucket") or "").strip() or "medium",
        )

        if blocking_context:
            impacted_accession_count += 1
        for blocker in blocking_context:
            blocker_counts[blocker] += 1
        for ref in source_fix_refs:
            source_fix_counts[ref] += 1
        if route_steps:
            route_step_counts[route_steps[0]] += 1
        priority_counts[priority_bucket] += 1

        supporting_artifacts = _listify(
            ["training_set_gate_ladder_preview", "training_set_unblock_plan_preview"]
        )
        for row in accession_action_rows:
            supporting_artifacts.extend(_listify(row.get("supporting_artifacts")))
        supporting_artifacts = _listify(supporting_artifacts)

        training_set_state = str(
            gate_row.get("training_set_state")
            or blocker_row.get("training_set_state")
            or ""
        ).strip()
        gate_ladder_state = str(gate_row.get("gate_ladder_state") or "").strip()

        rows.append(
            {
                "accession": accession,
                "current_training_set_state": training_set_state,
                "unlock_route_state": _route_state(
                    training_set_state,
                    gate_ladder_state,
                    package_ready=bool(package_summary.get("ready_for_package")),
                    blocking_context=blocking_context,
                ),
                "next_step": route_steps[0] if route_steps else "preserve_current_preview_state",
                "route_steps": route_steps[:6],
                "blocking_context": blocking_context,
                "source_fix_refs": source_fix_refs,
                "priority_bucket": priority_bucket,
                "supporting_artifacts": supporting_artifacts,
            }
        )

    rows.sort(
        key=lambda row: (
            0
            if row["priority_bucket"] == "critical"
            else 1 if row["priority_bucket"] == "high" else 2,
            row["accession"],
        )
    )

    return {
        "artifact_id": "training_set_unlock_route_preview",
        "schema_id": "proteosphere-training-set-unlock-route-preview-2026-04-03",
        "status": "report_only",
        "generated_at": (
            training_set_gate_ladder_preview.get("generated_at")
            or training_set_unblock_plan_preview.get("generated_at")
            or training_set_action_queue_preview.get("generated_at")
            or training_set_package_blocker_matrix_preview.get("generated_at")
            or package_readiness_preview.get("generated_at")
            or ""
        ),
        "summary": {
            "selected_count": len(selected_accessions),
            "current_unlock_state": current_unlock_state,
            "next_unlock_stage": next_unlock_stage,
            "unlock_route_stage_count": len(route_stages),
            "blocking_gate_count": sum(
                1 for stage in route_stages if stage["status"] == "blocked"
            ),
            "impacted_accession_count": impacted_accession_count,
            "critical_action_count": int(priority_counts.get("critical") or 0),
            "package_ready": bool(package_summary.get("ready_for_package")),
            "top_route_steps": [
                {"next_step": step, "accession_count": count}
                for step, count in route_step_counts.most_common(8)
            ],
            "top_blocking_reasons": [
                {"reason": reason, "accession_count": count}
                for reason, count in blocker_counts.most_common(8)
            ],
            "top_source_fix_refs": [
                {"source_fix_ref": ref, "accession_count": count}
                for ref, count in source_fix_counts.most_common(8)
            ],
            "priority_bucket_counts": dict(priority_counts),
            "fail_closed": True,
            "non_mutating": True,
        },
        "unlock_route_stages": route_stages,
        "rows": rows,
        "source_artifacts": {
            "training_set_gate_ladder_preview": str(
                DEFAULT_TRAINING_SET_GATE_LADDER
            ).replace("\\", "/"),
            "training_set_unblock_plan_preview": str(
                DEFAULT_TRAINING_SET_UNBLOCK_PLAN
            ).replace("\\", "/"),
            "training_set_action_queue_preview": str(
                DEFAULT_TRAINING_SET_ACTION_QUEUE
            ).replace("\\", "/"),
            "training_set_package_blocker_matrix_preview": str(
                DEFAULT_TRAINING_SET_PACKAGE_BLOCKER_MATRIX
            ).replace("\\", "/"),
            "package_readiness_preview": str(DEFAULT_PACKAGE_READINESS).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This unlock-route preview is report-only and fail-closed. It orders the "
                "current builder blockers into an operator route, but it does not mutate "
                "source artifacts or authorize packaging."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "package_not_authorized": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export training set unlock route preview."
    )
    parser.add_argument(
        "--training-set-gate-ladder",
        type=Path,
        default=DEFAULT_TRAINING_SET_GATE_LADDER,
    )
    parser.add_argument(
        "--training-set-unblock-plan",
        type=Path,
        default=DEFAULT_TRAINING_SET_UNBLOCK_PLAN,
    )
    parser.add_argument(
        "--training-set-action-queue",
        type=Path,
        default=DEFAULT_TRAINING_SET_ACTION_QUEUE,
    )
    parser.add_argument(
        "--training-set-package-blocker-matrix",
        type=Path,
        default=DEFAULT_TRAINING_SET_PACKAGE_BLOCKER_MATRIX,
    )
    parser.add_argument("--package-readiness", type=Path, default=DEFAULT_PACKAGE_READINESS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_training_set_unlock_route_preview(
        _load_payload(args.training_set_gate_ladder),
        _load_payload(args.training_set_unblock_plan),
        _load_payload(args.training_set_action_queue),
        _load_payload(args.training_set_package_blocker_matrix),
        _load_payload(args.package_readiness),
    )
    write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
