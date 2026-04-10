from __future__ import annotations

import argparse
import json
from collections import Counter
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
DEFAULT_TRAINING_SET_ACTION_QUEUE = (
    REPO_ROOT / "artifacts" / "status" / "training_set_action_queue_preview.json"
)
DEFAULT_TRAINING_SET_UNBLOCK_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unblock_plan_preview.json"
)
DEFAULT_OPERATOR_ACCESSION_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "summary_library_operator_accession_matrix.json"
)
DEFAULT_PACKAGE_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_modality_gap_register_preview.json"
)

KNOWN_MODALITIES = {"ligand", "ppi", "structure", "sequence", "variant"}


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


def _rows_by_accession(rows: Any) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        accession = _normalize_text(row.get("accession"))
        if accession:
            grouped.setdefault(accession, []).append(dict(row))
    return grouped


def _modalities_from_text(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        found: list[str] = []
        for item in value:
            found.extend(_modalities_from_text(item))
        return found
    text = _normalize_text(value)
    if not text:
        return []
    if text.startswith("fill_missing_modalities:"):
        text = text.split(":", 1)[1]
    pieces = text.replace("|", ",").replace(";", ",").split(",")
    found: list[str] = []
    for piece in pieces:
        token = _normalize_text(piece).split(":", 1)[0]
        if token in KNOWN_MODALITIES:
            found.append(token)
    if not found and text in KNOWN_MODALITIES:
        found.append(text)
    return found


def _collect_modalities(*values: Any) -> list[str]:
    seen: dict[str, str] = {}
    for value in values:
        for modality in _modalities_from_text(value):
            seen.setdefault(modality.casefold(), modality)
    return list(seen.values())


def _accession_modalities(
    readiness_row: dict[str, Any],
    action_rows: list[dict[str, Any]],
    unblock_row: dict[str, Any],
    matrix_row: dict[str, Any],
) -> list[str]:
    modalities = _collect_modalities(
        readiness_row.get("required_modalities"),
        readiness_row.get("missing_modalities"),
        readiness_row.get("modality_gaps"),
    )
    for row in action_rows:
        modalities.extend(_collect_modalities(row.get("affected_modalities")))
        modalities.extend(_collect_modalities(row.get("action_ref")))
        modalities.extend(_collect_modalities(row.get("blocker_context")))
        modalities.extend(_collect_modalities(row.get("source_fix_refs")))
        modalities.extend(_collect_modalities(row.get("supporting_artifacts")))
    modalities.extend(_collect_modalities(unblock_row.get("package_blockers")))
    modalities.extend(_collect_modalities(unblock_row.get("recommended_next_actions")))
    modalities.extend(_collect_modalities(unblock_row.get("direct_remediation_routes")))
    family_presence = matrix_row.get("family_presence") or {}
    if isinstance(family_presence, dict):
        if not family_presence.get("structure_unit", True):
            modalities.append("structure")
        if not family_presence.get("protein_variant", True):
            modalities.append("variant")
    if not modalities and any(
        _normalize_text(row.get("training_set_state"))
        in {"blocked_pending_acquisition", "preview_visible_non_governing"}
        for row in action_rows
    ):
        modalities.append("unknown")
    return list(dict.fromkeys(modalities))


def _summary_bool(summary: dict[str, Any], key: str, fallback: bool = False) -> bool:
    value = summary.get(key)
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    return bool(value)


def build_training_set_modality_gap_register_preview(
    training_set_readiness: dict[str, Any],
    training_set_blocker_burndown: dict[str, Any],
    training_set_action_queue: dict[str, Any],
    training_set_unblock_plan: dict[str, Any],
    operator_accession_matrix: dict[str, Any],
    package_readiness: dict[str, Any],
) -> dict[str, Any]:
    readiness_rows = _rows_by_accession(training_set_readiness.get("readiness_rows") or [])
    action_rows_by_accession = _rows_by_accession(training_set_action_queue.get("rows") or [])
    unblock_rows = _rows_by_accession(training_set_unblock_plan.get("rows") or [])
    matrix_rows = _rows_by_accession(operator_accession_matrix.get("rows") or [])
    burndown_rows = _rows_by_accession(training_set_blocker_burndown.get("rows") or [])

    selected_accessions = list(readiness_rows.keys())
    if not selected_accessions:
        selected_accessions = list(action_rows_by_accession.keys())
    if not selected_accessions:
        selected_accessions = list(unblock_rows.keys())
    if not selected_accessions:
        selected_accessions = list(matrix_rows.keys())

    readiness_summary = training_set_readiness.get("summary") or {}
    burndown_summary = training_set_blocker_burndown.get("summary") or {}
    action_summary = training_set_action_queue.get("summary") or {}
    unblock_summary = training_set_unblock_plan.get("summary") or {}
    package_summary = package_readiness.get("summary") or {}

    package_ready = _summary_bool(
        package_summary,
        "ready_for_package",
        _summary_bool(package_summary, "package_ready", False),
    )
    if package_ready is False:
        package_ready = _summary_bool(readiness_summary, "package_ready", False)

    rows: list[dict[str, Any]] = []
    gap_category_counts: Counter[str] = Counter()
    modality_to_accessions: dict[str, set[str]] = {}

    for accession in selected_accessions:
        readiness_row = (readiness_rows.get(accession) or [{}])[0]
        action_rows = action_rows_by_accession.get(accession, [])
        unblock_row = (unblock_rows.get(accession) or [{}])[0]
        matrix_row = (matrix_rows.get(accession) or [{}])[0]
        burndown_row = (burndown_rows.get(accession) or [{}])[0]

        modalities = _accession_modalities(
            readiness_row,
            action_rows,
            unblock_row,
            matrix_row,
        )
        if not modalities and _normalize_text(burndown_row.get("action_ref")):
            modalities = _collect_modalities(burndown_row.get("action_ref"))
        if not modalities and _normalize_text(readiness_row.get("training_set_state")):
            if _normalize_text(readiness_row.get("training_set_state")) != "governing_ready":
                modalities = ["unknown"]

        modality_count = len(modalities)
        if modality_count > 0:
            for modality in modalities:
                gap_category_counts[modality] += 1
                modality_to_accessions.setdefault(modality, set()).add(accession)

        rows.append(
            {
                "accession": accession,
                "blocked_modality_count": modality_count,
                "gap_categories": modalities,
                "package_ready": package_ready,
                "training_set_state": _normalize_text(readiness_row.get("training_set_state")),
                "next_step": _normalize_text(readiness_row.get("recommended_next_step")),
            }
        )

    rows.sort(
        key=lambda row: (
            -int(row.get("blocked_modality_count") or 0),
            row.get("accession") or "",
        )
    )

    top_gap_accessions = [
        {
            "accession": row["accession"],
            "blocked_modality_count": row["blocked_modality_count"],
            "gap_categories": row["gap_categories"],
            "package_ready": row["package_ready"],
            "training_set_state": row["training_set_state"],
        }
        for row in rows[:10]
    ]
    top_gap_modalities = [
        {"modality": modality, "accession_count": len(accessions)}
        for modality, accessions in sorted(
            modality_to_accessions.items(),
            key=lambda item: (-len(item[1]), item[0].casefold()),
        )
    ][:10]

    generated_at = (
        training_set_readiness.get("generated_at")
        or training_set_blocker_burndown.get("generated_at")
        or training_set_action_queue.get("generated_at")
        or training_set_unblock_plan.get("generated_at")
        or package_readiness.get("generated_at")
        or datetime.now(UTC).isoformat()
    )

    blocked_modality_count = len([row for row in rows if row["blocked_modality_count"] > 0])

    return {
        "artifact_id": "training_set_modality_gap_register_preview",
        "schema_id": "proteosphere-training-set-modality-gap-register-preview-2026-04-03",
        "status": "report_only",
        "generated_at": generated_at,
        "summary": {
            "selected_accession_count": len(selected_accessions),
            "blocked_modality_count": blocked_modality_count,
            "gap_category_counts": dict(gap_category_counts),
            "top_gap_accessions": top_gap_accessions,
            "top_gap_modalities": top_gap_modalities,
            "package_ready": package_ready,
            "non_mutating": True,
            "ready_accession_count": int(readiness_summary.get("selected_count") or 0),
            "assignment_ready": _summary_bool(readiness_summary, "assignment_ready", True),
            "blocker_count": len(burndown_summary.get("top_blocker_categories") or []),
            "blocked_reason_count": len(
                _listify(package_summary.get("blocked_reasons"))
                or _listify(burndown_summary.get("unblock_package_blocked_reasons"))
            ),
            "action_priority_bucket_counts": action_summary.get("priority_bucket_counts") or {},
            "unblock_package_blocked_reasons": _listify(
                unblock_summary.get("package_blocked_reasons")
            ),
        },
        "rows": rows,
        "source_artifacts": {
            "training_set_readiness": str(DEFAULT_TRAINING_SET_READINESS).replace("\\", "/"),
            "training_set_blocker_burndown": str(
                DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN
            ).replace("\\", "/"),
            "training_set_action_queue": str(DEFAULT_TRAINING_SET_ACTION_QUEUE).replace(
                "\\", "/"
            ),
            "training_set_unblock_plan": str(DEFAULT_TRAINING_SET_UNBLOCK_PLAN).replace(
                "\\", "/"
            ),
            "operator_accession_matrix": str(DEFAULT_OPERATOR_ACCESSION_MATRIX).replace(
                "\\", "/"
            ),
            "package_readiness": str(DEFAULT_PACKAGE_READINESS).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This modality-gap register is report-only and fail-closed. It "
                "summarizes modality-specific training-set gaps without mutating "
                "source artifacts or authorizing packaging."
            ),
            "report_only": True,
            "non_mutating": True,
            "non_governing": True,
            "package_not_authorized": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only training set modality-gap register preview."
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
        "--operator-accession-matrix",
        type=Path,
        default=DEFAULT_OPERATOR_ACCESSION_MATRIX,
    )
    parser.add_argument("--package-readiness", type=Path, default=DEFAULT_PACKAGE_READINESS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_training_set_modality_gap_register_preview(
        _read_json(args.training_set_readiness),
        _read_json(args.training_set_blocker_burndown),
        _read_json(args.training_set_action_queue),
        _read_json(args.training_set_unblock_plan),
        _read_json(args.operator_accession_matrix),
        _read_json(args.package_readiness),
    )
    _write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
