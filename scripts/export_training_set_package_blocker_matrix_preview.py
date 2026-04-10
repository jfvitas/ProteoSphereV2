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
DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_blocker_burndown_preview.json"
)
DEFAULT_TRAINING_SET_MODALITY_GAP_REGISTER = (
    REPO_ROOT / "artifacts" / "status" / "training_set_modality_gap_register_preview.json"
)
DEFAULT_TRAINING_SET_UNBLOCK_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unblock_plan_preview.json"
)
DEFAULT_PACKAGE_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_package_blocker_matrix_preview.json"
)

_BLOCKER_CONTEXT_IGNORES = {
    "",
    "assignment_ready",
    "governing_ready",
    "preview_only_non_governing",
    "preview_visible_non_governing",
    "package_ready",
    "package_ready=false",
    "source_fix_available",
}

_FOLD_EXPORT_BLOCKER_REASONS = {
    "fold_export_ready=false",
    "cv_fold_export_unlocked=false",
    "split_post_staging_gate_closed",
}


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


def _coerce_int(value: Any, fallback: int = 0) -> int:
    try:
        if value is None:
            return fallback
        if isinstance(value, bool):
            return int(value)
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return bool(value)


def _summary_bool(summary: dict[str, Any], key: str, fallback: bool = False) -> bool:
    value = summary.get(key)
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    return bool(value)


def _collect_selected_accessions(
    readiness_rows: Any,
    blocker_rows: Any,
    modality_rows: Any,
    unblock_rows: Any,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for rows in (readiness_rows, blocker_rows, modality_rows, unblock_rows):
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            accession = _normalize_text(row.get("accession"))
            if accession and accession not in seen:
                seen.add(accession)
                ordered.append(accession)
    return ordered


def _extend_reasons(
    reason_counts: Counter[str],
    accession_to_reasons: dict[str, set[str]],
    accession: str,
    values: Any,
) -> None:
    for reason in _listify(values):
        if reason in _BLOCKER_CONTEXT_IGNORES:
            continue
        reason_counts[reason] += 1
        accession_to_reasons.setdefault(accession, set()).add(reason)


def _row_blockers(
    *,
    accession: str,
    readiness_row: dict[str, Any],
    blocker_row: dict[str, Any],
    modality_row: dict[str, Any],
    unblock_row: dict[str, Any],
    package_summary: dict[str, Any],
    package_ready: bool,
) -> dict[str, Any]:
    reasons: list[str] = []
    _extend_reasons(
        Counter(),
        defaultdict(set),
        accession,
        readiness_row.get("blocked_reasons"),
    )
    reasons.extend(_listify(readiness_row.get("blocked_reasons")))
    reasons.extend(_listify(blocker_row.get("blocker_context")))
    reasons.extend(_listify(unblock_row.get("package_blockers")))

    if not package_ready:
        reasons.extend(_listify(package_summary.get("blocked_reasons")))
        if not _listify(package_summary.get("blocked_reasons")):
            reasons.append("package_gate_closed")

    modality_gap_categories = _listify(modality_row.get("gap_categories"))
    modality_blocked = _coerce_int(modality_row.get("blocked_modality_count")) > 0
    if modality_blocked:
        reasons.append("modality_gap")

    reasons = [
        reason
        for reason in _listify(reasons)
        if reason not in _BLOCKER_CONTEXT_IGNORES
    ]
    if not reasons and not package_ready:
        reasons.append("package_gate_closed")

    fold_export_blocked = any(reason in _FOLD_EXPORT_BLOCKER_REASONS for reason in reasons)
    if fold_export_blocked and "package_gate_closed" not in reasons:
        reasons.append("package_gate_closed")

    blocked_reason_count = len(reasons)
    priority_bucket = "low"
    if fold_export_blocked or "blocked_pending_acquisition" in reasons:
        priority_bucket = "critical"
    elif "modality_gap" in reasons or "packet_partial_or_missing" in reasons:
        priority_bucket = "high"
    elif reasons:
        priority_bucket = "medium"

    return {
        "accession": accession,
        "training_set_state": _normalize_text(readiness_row.get("training_set_state")),
        "package_ready": package_ready,
        "blocked_reasons": reasons,
        "blocked_reason_count": blocked_reason_count,
        "priority_bucket": priority_bucket,
        "fold_export_blocked": fold_export_blocked,
        "modality_blocked": modality_blocked,
        "modality_gap_categories": modality_gap_categories,
        "blocker_context": _listify(blocker_row.get("blocker_context")),
        "package_blockers": _listify(unblock_row.get("package_blockers")),
        "recommended_next_step": _normalize_text(readiness_row.get("recommended_next_step")),
    }


def build_training_set_package_blocker_matrix_preview(
    training_set_readiness: dict[str, Any],
    training_set_blocker_burndown: dict[str, Any],
    training_set_modality_gap_register: dict[str, Any],
    training_set_unblock_plan: dict[str, Any],
    package_readiness: dict[str, Any],
) -> dict[str, Any]:
    readiness_rows = _index_rows(training_set_readiness.get("readiness_rows") or [])
    blocker_rows = _index_rows(training_set_blocker_burndown.get("rows") or [])
    modality_rows = _index_rows(training_set_modality_gap_register.get("rows") or [])
    unblock_rows = _index_rows(training_set_unblock_plan.get("rows") or [])

    selected_accessions = _collect_selected_accessions(
        training_set_readiness.get("readiness_rows") or [],
        training_set_blocker_burndown.get("rows") or [],
        training_set_modality_gap_register.get("rows") or [],
        training_set_unblock_plan.get("rows") or [],
    )

    readiness_summary = training_set_readiness.get("summary") or {}
    blocker_summary = training_set_blocker_burndown.get("summary") or {}
    modality_summary = training_set_modality_gap_register.get("summary") or {}
    unblock_summary = training_set_unblock_plan.get("summary") or {}
    package_summary = package_readiness.get("summary") or {}

    selected_count = len(selected_accessions)
    if selected_count == 0:
        selected_count = _coerce_int(
            readiness_summary.get("selected_count")
            or readiness_summary.get("accession_count")
            or blocker_summary.get("selected_accession_count")
            or modality_summary.get("selected_accession_count")
            or unblock_summary.get("selected_count")
            or package_summary.get("packet_count"),
            0,
        )

    package_ready = _summary_bool(
        package_summary,
        "ready_for_package",
        _summary_bool(package_summary, "package_ready", False),
    )
    if not package_ready and not package_summary:
        package_ready = False

    rows: list[dict[str, Any]] = []
    reason_to_accessions: dict[str, set[str]] = defaultdict(set)
    accession_reason_counts: dict[str, set[str]] = {}
    fold_export_blocked_accessions: set[str] = set()
    modality_blocked_accessions: set[str] = set()

    for accession in selected_accessions:
        readiness_row = readiness_rows.get(accession, {})
        blocker_row = blocker_rows.get(accession, {})
        modality_row = modality_rows.get(accession, {})
        unblock_row = unblock_rows.get(accession, {})

        row = _row_blockers(
            accession=accession,
            readiness_row=readiness_row,
            blocker_row=blocker_row,
            modality_row=modality_row,
            unblock_row=unblock_row,
            package_summary=package_summary,
            package_ready=package_ready,
        )
        rows.append(row)
        accession_reason_counts[accession] = set(row["blocked_reasons"])
        if row["fold_export_blocked"]:
            fold_export_blocked_accessions.add(accession)
        if row["modality_blocked"]:
            modality_blocked_accessions.add(accession)
        for reason in row["blocked_reasons"]:
            reason_to_accessions[reason].add(accession)

    rows.sort(
        key=lambda row: (
            -int(row.get("blocked_reason_count") or 0),
            row.get("priority_bucket") != "critical",
            row.get("priority_bucket") != "high",
            row.get("accession") or "",
        )
    )

    blocked_accession_count = sum(1 for row in rows if int(row["blocked_reason_count"]) > 0)
    blocked_reason_counts = {
        reason: len(accessions)
        for reason, accessions in sorted(
            reason_to_accessions.items(),
            key=lambda item: (-len(item[1]), item[0].casefold()),
        )
    }
    top_blocking_reasons = [
        {"reason": reason, "accession_count": count}
        for reason, count in list(blocked_reason_counts.items())[:10]
    ]
    top_blocked_accessions = [
        {
            "accession": row["accession"],
            "blocked_reason_count": row["blocked_reason_count"],
            "blocked_reasons": row["blocked_reasons"],
            "priority_bucket": row["priority_bucket"],
            "training_set_state": row["training_set_state"],
            "package_ready": row["package_ready"],
            "fold_export_blocked": row["fold_export_blocked"],
            "modality_blocked": row["modality_blocked"],
        }
        for row in rows[:10]
    ]

    fold_export_blocked_count = len(fold_export_blocked_accessions)
    modality_blocked_count = len(modality_blocked_accessions)
    generated_at = (
        training_set_readiness.get("generated_at")
        or training_set_blocker_burndown.get("generated_at")
        or training_set_modality_gap_register.get("generated_at")
        or training_set_unblock_plan.get("generated_at")
        or package_readiness.get("generated_at")
        or datetime.now(UTC).isoformat()
    )

    return {
        "artifact_id": "training_set_package_blocker_matrix_preview",
        "schema_id": "proteosphere-training-set-package-blocker-matrix-preview-2026-04-03",
        "status": "report_only",
        "generated_at": generated_at,
        "summary": {
            "selected_accession_count": selected_count,
            "blocked_accession_count": blocked_accession_count,
            "package_ready": package_ready,
            "blocked_reason_counts": blocked_reason_counts,
            "top_blocking_reasons": top_blocking_reasons,
            "top_blocked_accessions": top_blocked_accessions,
            "fold_export_blocked_count": fold_export_blocked_count,
            "modality_blocked_count": modality_blocked_count,
            "non_mutating": True,
            "package_blocked_reasons": _listify(package_summary.get("blocked_reasons")),
            "selected_count": _coerce_int(readiness_summary.get("selected_count"), selected_count),
        },
        "rows": rows,
        "source_artifacts": {
            "training_set_readiness": str(DEFAULT_TRAINING_SET_READINESS).replace("\\", "/"),
            "training_set_blocker_burndown": str(
                DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN
            ).replace("\\", "/"),
            "training_set_modality_gap_register": str(
                DEFAULT_TRAINING_SET_MODALITY_GAP_REGISTER
            ).replace("\\", "/"),
            "training_set_unblock_plan": str(
                DEFAULT_TRAINING_SET_UNBLOCK_PLAN
            ).replace("\\", "/"),
            "package_readiness": str(DEFAULT_PACKAGE_READINESS).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This package blocker matrix is report-only and fail-closed. It "
                "summarizes the current package blocking state without mutating "
                "source artifacts or authorizing packaging."
            ),
            "report_only": True,
            "non_governing": True,
            "non_mutating": True,
            "fail_closed": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only training set package blocker matrix preview."
    )
    parser.add_argument(
        "--training-set-readiness",
        type=Path,
        default=DEFAULT_TRAINING_SET_READINESS,
    )
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
        "--training-set-unblock-plan",
        type=Path,
        default=DEFAULT_TRAINING_SET_UNBLOCK_PLAN,
    )
    parser.add_argument("--package-readiness", type=Path, default=DEFAULT_PACKAGE_READINESS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_training_set_package_blocker_matrix_preview(
        _read_json(args.training_set_readiness),
        _read_json(args.training_set_blocker_burndown),
        _read_json(args.training_set_modality_gap_register),
        _read_json(args.training_set_unblock_plan),
        _read_json(args.package_readiness),
    )
    _write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
