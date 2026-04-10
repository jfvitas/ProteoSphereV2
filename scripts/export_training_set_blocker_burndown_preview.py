from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAINING_SET_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "training_set_readiness_preview.json"
)
DEFAULT_TRAINING_SET_ACTION_QUEUE = (
    REPO_ROOT / "artifacts" / "status" / "training_set_action_queue_preview.json"
)
DEFAULT_TRAINING_SET_UNBLOCK_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unblock_plan_preview.json"
)
DEFAULT_TRAINING_SET_GATING_EVIDENCE = (
    REPO_ROOT / "artifacts" / "status" / "training_set_gating_evidence_preview.json"
)
DEFAULT_TRAINING_SET_REMEDIATION_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_remediation_plan_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_blocker_burndown_preview.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _listify(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    seen: dict[str, str] = {}
    for value in values:
        text = _normalize_text(value)
        if text:
            seen.setdefault(text.casefold(), text)
    return list(seen.values())


def _index_rows(rows: Any, *, key: str = "accession") -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        identifier = _normalize_text(row.get(key))
        if identifier:
            indexed[identifier] = dict(row)
    return indexed


def _collect_accessions(*sources: Any) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for source in sources:
        for row in source or []:
            if not isinstance(row, dict):
                continue
            accession = _normalize_text(row.get("accession"))
            if accession and accession not in seen:
                seen.add(accession)
                ordered.append(accession)
    return ordered


def _summary_bool(summary: dict[str, Any], key: str, fallback: bool = False) -> bool:
    value = summary.get(key)
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    return bool(value)


def _priority_bucket(blockers: list[str], action_row: dict[str, Any]) -> str:
    priority = _normalize_text(action_row.get("priority_bucket"))
    if priority in {"critical", "high", "medium", "low"}:
        return priority
    blocker_set = set(blockers)
    if blocker_set & {
        "assignment_ready=false",
        "fold_export_ready=false",
        "cv_fold_export_unlocked=false",
        "split_post_staging_gate_closed",
    }:
        return "critical"
    if blocker_set & {
        "package_gate_closed",
        "modality_gap",
        "packet_partial_or_missing",
    }:
        return "high"
    if blocker_set:
        return "medium"
    return "low"


def _merge_blockers(*lists: Any) -> list[str]:
    blockers: list[str] = []
    for values in lists:
        blockers.extend(_listify(values))
    return list(dict.fromkeys(blockers))


def build_training_set_blocker_burndown_preview(
    training_set_readiness: dict[str, Any],
    training_set_action_queue: dict[str, Any],
    training_set_unblock_plan: dict[str, Any],
    training_set_gating_evidence: dict[str, Any],
    training_set_remediation_plan: dict[str, Any],
) -> dict[str, Any]:
    readiness_rows = _index_rows(training_set_readiness.get("readiness_rows") or [])
    action_rows = _index_rows(training_set_action_queue.get("rows") or [])
    unblock_rows = _index_rows(training_set_unblock_plan.get("rows") or [])
    gating_rows = _index_rows(training_set_gating_evidence.get("rows") or [])
    remediation_rows = _index_rows(training_set_remediation_plan.get("rows") or [])

    selected_accessions = _collect_accessions(
        training_set_readiness.get("readiness_rows") or [],
        training_set_action_queue.get("rows") or [],
        training_set_unblock_plan.get("rows") or [],
        training_set_gating_evidence.get("rows") or [],
        training_set_remediation_plan.get("rows") or [],
    )

    readiness_summary = training_set_readiness.get("summary") or {}
    action_summary = training_set_action_queue.get("summary") or {}
    unblock_summary = training_set_unblock_plan.get("summary") or {}
    gating_summary = training_set_gating_evidence.get("summary") or {}
    remediation_summary = training_set_remediation_plan.get("summary") or {}

    package_ready = _summary_bool(
        action_summary,
        "package_ready",
        _summary_bool(unblock_summary, "package_ready", False),
    )
    if not selected_accessions:
        selected_accessions = _listify(readiness_summary.get("selected_accessions"))
    assignment_ready = _summary_bool(
        readiness_summary,
        "assignment_ready",
        not any(
            _normalize_text(row.get("training_set_state")) == "blocked_pending_acquisition"
            for row in readiness_rows.values()
        ),
    )

    rows: list[dict[str, Any]] = []
    blocker_to_accessions: dict[str, set[str]] = defaultdict(set)
    progression_counts: Counter[str] = Counter()
    critical_action_count = 0
    affected_accessions: set[str] = set()

    for accession in selected_accessions:
        readiness_row = readiness_rows.get(accession, {})
        action_row = action_rows.get(accession, {})
        unblock_row = unblock_rows.get(accession, {})
        gating_row = gating_rows.get(accession, {})
        remediation_row = remediation_rows.get(accession, {})

        blocker_context = _merge_blockers(
            action_row.get("blocker_context"),
            unblock_row.get("package_blockers"),
            gating_row.get("package_blockers"),
            gating_row.get("issue_buckets"),
            remediation_row.get("issue_buckets"),
        )
        if not package_ready:
            blocker_context.append("package_gate_closed")
        if not assignment_ready:
            blocker_context.append("assignment_ready=false")
        blocker_context = list(dict.fromkeys(blocker_context))
        if blocker_context:
            affected_accessions.add(accession)

        for blocker in blocker_context:
            blocker_to_accessions[blocker].add(accession)
            progression_counts[blocker] += 1

        row_priority = _priority_bucket(blocker_context, action_row)
        if row_priority == "critical":
            critical_action_count += 1

        remediation_actions = _merge_blockers(
            action_row.get("action_ref"),
            unblock_row.get("direct_remediation_routes"),
            unblock_row.get("recommended_next_actions"),
            gating_row.get("next_actions"),
            remediation_row.get("recommended_actions"),
            readiness_row.get("recommended_next_step"),
        )
        top_next_actions = remediation_actions[:3]
        top_source_fix_refs = _merge_blockers(
            unblock_row.get("source_fix_refs"),
            remediation_row.get("source_fix_refs"),
            gating_row.get("source_fix_refs"),
        )

        rows.append(
            {
                "accession": accession,
                "priority_bucket": row_priority,
                "blocker_context": blocker_context,
                "critical_action": row_priority == "critical",
                "action_ref": _normalize_text(action_row.get("action_ref")),
                "top_next_actions": top_next_actions,
                "top_source_fix_refs": top_source_fix_refs,
                "package_ready": package_ready,
                "assignment_ready": assignment_ready,
            }
        )

    rows.sort(
        key=lambda row: (
            row["priority_bucket"] != "critical",
            row["priority_bucket"] != "high",
            row["accession"],
        )
    )

    blocker_category_counts = {
        blocker: len(accessions)
        for blocker, accessions in sorted(
            blocker_to_accessions.items(),
            key=lambda item: (-len(item[1]), item[0].casefold()),
        )
    }
    top_blocker_categories = [
        {"blocker": blocker, "accession_count": count}
        for blocker, count in list(blocker_category_counts.items())[:10]
    ]

    top_progression_steps = [
        {"blocker": blocker, "count": count}
        for blocker, count in progression_counts.most_common(5)
    ]
    remediation_progression_summary = (
        f"{len(selected_accessions)} selected, {len(affected_accessions)} blocked, "
        f"{critical_action_count} critical actions, package_ready={package_ready}, "
        f"assignment_ready={assignment_ready}"
    )

    generated_at = (
        training_set_readiness.get("generated_at")
        or training_set_action_queue.get("generated_at")
        or training_set_unblock_plan.get("generated_at")
        or training_set_gating_evidence.get("generated_at")
        or training_set_remediation_plan.get("generated_at")
        or datetime.now(UTC).isoformat()
    )

    return {
        "artifact_id": "training_set_blocker_burndown_preview",
        "schema_id": "proteosphere-training-set-blocker-burndown-preview-2026-04-03",
        "status": "report_only",
        "generated_at": generated_at,
        "summary": {
            "selected_accession_count": len(selected_accessions),
            "blocked_accession_count": len(affected_accessions),
            "blocker_category_counts": blocker_category_counts,
            "top_blocker_categories": top_blocker_categories,
            "critical_action_count": critical_action_count,
            "package_ready": package_ready,
            "assignment_ready": assignment_ready,
            "remediation_progression_summary": remediation_progression_summary,
            "top_progression_steps": top_progression_steps,
            "gated_accession_count": int(gating_summary.get("gated_count") or 0),
            "preview_only_accession_count": int(
                gating_summary.get("preview_only_count") or 0
            ),
            "remediation_issue_bucket_counts": remediation_summary.get("issue_bucket_counts")
            or {},
            "action_priority_bucket_counts": action_summary.get("priority_bucket_counts")
            or {},
            "unblock_package_blocked_reasons": _listify(
                unblock_summary.get("package_blocked_reasons")
            ),
        },
        "rows": rows,
        "source_artifacts": {
            "training_set_readiness": str(DEFAULT_TRAINING_SET_READINESS).replace("\\", "/"),
            "training_set_action_queue": str(DEFAULT_TRAINING_SET_ACTION_QUEUE).replace(
                "\\", "/"
            ),
            "training_set_unblock_plan": str(DEFAULT_TRAINING_SET_UNBLOCK_PLAN).replace(
                "\\", "/"
            ),
            "training_set_gating_evidence": str(
                DEFAULT_TRAINING_SET_GATING_EVIDENCE
            ).replace("\\", "/"),
            "training_set_remediation_plan": str(
                DEFAULT_TRAINING_SET_REMEDIATION_PLAN
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This burndown preview is report-only and fail-closed. It summarizes "
                "blocking progress from the current training-set artifacts without "
                "mutating any source state or authorizing packaging."
            ),
            "report_only": True,
            "non_governing": True,
            "non_mutating": True,
            "fail_closed": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the training set blocker burndown preview."
    )
    parser.add_argument(
        "--training-set-readiness",
        type=Path,
        default=DEFAULT_TRAINING_SET_READINESS,
    )
    parser.add_argument(
        "--training-set-action-queue",
        type=Path,
        default=DEFAULT_TRAINING_SET_ACTION_QUEUE,
    )
    parser.add_argument(
        "--training-set-unblock-plan",
        type=Path,
        default=DEFAULT_TRAINING_SET_UNBLOCK_PLAN,
    )
    parser.add_argument(
        "--training-set-gating-evidence",
        type=Path,
        default=DEFAULT_TRAINING_SET_GATING_EVIDENCE,
    )
    parser.add_argument(
        "--training-set-remediation-plan",
        type=Path,
        default=DEFAULT_TRAINING_SET_REMEDIATION_PLAN,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_training_set_blocker_burndown_preview(
        _read_json(args.training_set_readiness),
        _read_json(args.training_set_action_queue),
        _read_json(args.training_set_unblock_plan),
        _read_json(args.training_set_gating_evidence),
        _read_json(args.training_set_remediation_plan),
    )
    _write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
