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

from external_dataset_assessment_support import read_json, write_json  # noqa: E402

DEFAULT_ACCEPTANCE_PATH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_path_preview.json"
)
DEFAULT_REMEDIATION_QUEUE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_remediation_queue_preview.json"
)
DEFAULT_RESOLUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)
DEFAULT_CLEARANCE_DELTA_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_clearance_delta_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "external_dataset_remediation_readiness_preview.json"
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


def _readiness_stage(
    stage: str,
    *,
    status: str,
    clear_condition: str,
    dependencies: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "status": status,
        "clear_condition": clear_condition,
        "dependencies": _listify(dependencies),
    }


def _readiness_state(
    acceptance_path_state: str,
    resolution_state: str,
    blocking_gates: list[str],
) -> str:
    if resolution_state == "blocked" or "modality" in blocking_gates:
        return "blocked_pending_acquisition"
    if acceptance_path_state == "caveated":
        return "advisory_follow_up"
    return "executable_now"


def build_external_dataset_remediation_readiness_preview(
    acceptance_path_preview: dict[str, Any],
    remediation_queue_preview: dict[str, Any],
    resolution_preview: dict[str, Any],
    clearance_delta_preview: dict[str, Any],
) -> dict[str, Any]:
    remediation_summary = dict(remediation_queue_preview.get("summary") or {})
    resolution_summary = dict(resolution_preview.get("summary") or {})
    clearance_summary = dict(clearance_delta_preview.get("summary") or {})

    acceptance_rows = acceptance_path_preview.get("rows") or []
    remediation_rows = remediation_queue_preview.get("rows") or []
    resolution_rows = resolution_preview.get("accession_resolution_rows") or []

    acceptance_by_accession = _rows_by_accession(acceptance_rows)
    resolution_by_accession = _rows_by_accession(resolution_rows)
    remediation_by_accession = _rows_grouped_by_accession(remediation_rows)
    accessions = _ordered_accessions(acceptance_rows, remediation_rows, resolution_rows)

    readiness_steps = [
        _readiness_stage(
            "resolution",
            status=(
                "blocked"
                if int(resolution_summary.get("blocked_accession_count") or 0) > 0
                else "ready"
            ),
            clear_condition="clear blocked accession resolution rows",
            dependencies=["external_dataset_resolution_preview"],
        ),
        _readiness_stage(
            "remediation_queue",
            status=(
                "blocked"
                if int(remediation_summary.get("remediation_queue_row_count") or 0) > 0
                else "ready"
            ),
            clear_condition="drain remediation queue for blocked or caveated rows",
            dependencies=["external_dataset_remediation_queue_preview"],
        ),
        _readiness_stage(
            "clearance",
            status=str(clearance_summary.get("current_clearance_state") or "blocked"),
            clear_condition="satisfy required clearance changes",
            dependencies=["external_dataset_clearance_delta_preview"],
        ),
        _readiness_stage(
            "training_hold",
            status="preview_only_hold",
            clear_condition="explicit human review remains required",
            dependencies=["external_dataset_acceptance_path_preview"],
        ),
    ]

    next_ready_batch = next(
        (step["stage"] for step in readiness_steps if step["status"] == "blocked"),
        "training_hold",
    )

    rows: list[dict[str, Any]] = []
    readiness_counts: Counter[str] = Counter()
    dependency_counts: Counter[str] = Counter()

    for accession in accessions:
        acceptance_row = acceptance_by_accession.get(accession, {})
        resolution_row = resolution_by_accession.get(accession, {})
        accession_remediation_rows = remediation_by_accession.get(accession, [])

        blocking_gates = _listify(acceptance_row.get("blocking_gates"))
        remediation_actions = _listify(acceptance_row.get("remediation_actions"))
        for row in accession_remediation_rows:
            remediation_actions.extend(_listify(row.get("remediation_action")))
            blocking_gates.extend(_listify(row.get("blocking_gate")))
        remediation_actions = _listify(remediation_actions)
        blocking_gates = _listify(blocking_gates)

        readiness_state = _readiness_state(
            str(acceptance_row.get("acceptance_path_state") or "advisory_only"),
            str(resolution_row.get("resolution_state") or "caveated"),
            blocking_gates,
        )
        next_action = (
            "wait_for_acquisition_or_mapping_fix"
            if readiness_state == "blocked_pending_acquisition"
            else "apply_caveat_preserving_remediation"
            if readiness_state == "advisory_follow_up"
            else "execute_remediation_queue"
        )

        dependency_refs = list(blocking_gates)
        dependency_refs.extend(remediation_actions)
        dependency_refs = _listify(dependency_refs)

        readiness_counts[readiness_state] += 1
        for dependency in dependency_refs:
            dependency_counts[dependency] += 1

        rows.append(
            {
                "accession": accession,
                "remediation_readiness_state": readiness_state,
                "acceptance_path_state": acceptance_row.get("acceptance_path_state"),
                "resolution_state": resolution_row.get("resolution_state"),
                "worst_verdict": acceptance_row.get("worst_verdict")
                or resolution_row.get("worst_verdict"),
                "priority_bucket": acceptance_row.get("priority_bucket")
                or (
                    accession_remediation_rows[0].get("priority_bucket")
                    if accession_remediation_rows
                    else None
                ),
                "next_action": next_action,
                "blocking_dependencies": dependency_refs,
                "remediation_actions": remediation_actions,
                "issue_categories": _listify(acceptance_row.get("issue_categories"))
                or _listify(resolution_row.get("issue_categories")),
                "supporting_artifacts": _listify(acceptance_row.get("supporting_artifacts"))
                or _listify(resolution_row.get("supporting_artifacts"))
                or [
                    "external_dataset_acceptance_path_preview",
                    "external_dataset_remediation_queue_preview",
                    "external_dataset_resolution_preview",
                ],
            }
        )

    current_readiness_state = (
        "blocked_pending_remediation"
        if any(step["status"] == "blocked" for step in readiness_steps)
        else "ready_for_human_review"
    )

    return {
        "artifact_id": "external_dataset_remediation_readiness_preview",
        "schema_id": "proteosphere-external-dataset-remediation-readiness-preview-2026-04-03",
        "status": "report_only",
        "generated_at": acceptance_path_preview.get("generated_at")
        or remediation_queue_preview.get("generated_at")
        or resolution_preview.get("generated_at")
        or clearance_delta_preview.get("generated_at"),
        "summary": {
            "dataset_accession_count": len(accessions),
            "current_readiness_state": current_readiness_state,
            "next_ready_batch": next_ready_batch,
            "readiness_step_count": len(readiness_steps),
            "blocked_pending_acquisition_count": readiness_counts.get(
                "blocked_pending_acquisition", 0
            ),
            "advisory_follow_up_count": readiness_counts.get(
                "advisory_follow_up", 0
            ),
            "executable_now_count": readiness_counts.get("executable_now", 0),
            "remediation_queue_row_count": remediation_summary.get(
                "remediation_queue_row_count"
            ),
            "blocked_accession_count": resolution_summary.get("blocked_accession_count"),
            "required_change_count": clearance_summary.get("required_change_count"),
            "top_blocking_dependencies": [
                {"dependency": item, "accession_count": count}
                for item, count in dependency_counts.most_common(8)
            ],
            "top_readiness_states": [
                {"readiness_state": item, "accession_count": count}
                for item, count in readiness_counts.most_common()
            ],
            "advisory_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
        "remediation_readiness_steps": readiness_steps,
        "rows": rows,
        "source_artifacts": {
            "external_dataset_acceptance_path_preview": str(
                DEFAULT_ACCEPTANCE_PATH_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_remediation_queue_preview": str(
                DEFAULT_REMEDIATION_QUEUE_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_resolution_preview": str(DEFAULT_RESOLUTION_PREVIEW).replace(
                "\\", "/"
            ),
            "external_dataset_clearance_delta_preview": str(
                DEFAULT_CLEARANCE_DELTA_PREVIEW
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This remediation-readiness preview is advisory and fail-closed. "
                "It separates executable remediation from acquisition-blocked work, "
                "but it does not admit external data for training."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "training_safe_acceptance_not_implied": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the external-dataset remediation-readiness preview."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help="Destination JSON path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_external_dataset_remediation_readiness_preview(
        _load_payload(DEFAULT_ACCEPTANCE_PATH_PREVIEW),
        _load_payload(DEFAULT_REMEDIATION_QUEUE_PREVIEW),
        _load_payload(DEFAULT_RESOLUTION_PREVIEW),
        _load_payload(DEFAULT_CLEARANCE_DELTA_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
