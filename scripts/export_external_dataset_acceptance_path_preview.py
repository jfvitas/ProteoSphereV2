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

DEFAULT_ASSESSMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_assessment_preview.json"
)
DEFAULT_ACCEPTANCE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json"
)
DEFAULT_ADMISSION_DECISION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_admission_decision_preview.json"
)
DEFAULT_CLEARANCE_DELTA_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_clearance_delta_preview.json"
)
DEFAULT_RESOLUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)
DEFAULT_REMEDIATION_QUEUE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_remediation_queue_preview.json"
)
DEFAULT_ISSUE_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_issue_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_path_preview.json"
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


def build_external_dataset_acceptance_path_preview(
    assessment_preview: dict[str, Any],
    acceptance_gate_preview: dict[str, Any],
    admission_decision_preview: dict[str, Any],
    clearance_delta_preview: dict[str, Any],
    resolution_preview: dict[str, Any],
    remediation_queue_preview: dict[str, Any],
    issue_matrix_preview: dict[str, Any],
) -> dict[str, Any]:
    assessment_summary = dict(assessment_preview.get("summary") or {})
    admission_summary = dict(admission_decision_preview.get("summary") or {})
    clearance_summary = dict(clearance_delta_preview.get("summary") or {})
    resolution_summary = dict(resolution_preview.get("summary") or {})
    remediation_summary = dict(remediation_queue_preview.get("summary") or {})

    resolution_rows = resolution_preview.get("accession_resolution_rows") or []
    remediation_rows = remediation_queue_preview.get("rows") or []
    issue_rows = issue_matrix_preview.get("rows") or []

    resolution_by_accession = _rows_by_accession(resolution_rows)
    remediation_by_accession = _rows_grouped_by_accession(remediation_rows)
    issue_by_accession = _rows_grouped_by_accession(issue_rows)
    accessions = _ordered_accessions(resolution_rows, remediation_rows, issue_rows)

    path_stages = [
        _path_stage(
            "assessment",
            status="advisory_only",
            clear_condition="retain advisory posture until downstream blockers clear",
            blocking_reasons=[str(assessment_summary.get("overall_verdict") or "").strip()],
        ),
        _path_stage(
            "issue_resolution",
            status=(
                "blocked"
                if int(resolution_summary.get("blocked_accession_count") or 0) > 0
                or int(resolution_summary.get("mapping_incomplete_accession_count") or 0) > 0
                else "ready"
            ),
            clear_condition="clear blocked and mapping-incomplete accession rows",
            blocking_reasons=[
                str(item.get("gate_name") or "").strip()
                for item in (resolution_summary.get("top_blocking_gates") or [])
                if isinstance(item, dict)
            ],
        ),
        _path_stage(
            "remediation_execution",
            status=(
                "blocked"
                if int(remediation_summary.get("remediation_queue_row_count") or 0) > 0
                else "ready"
            ),
            clear_condition="drain remediation queue items for blocked or caveated rows",
            blocking_reasons=[
                str(item.get("gate_name") or "").strip()
                for item in (remediation_summary.get("top_blocking_gates") or [])
                if isinstance(item, dict)
            ],
        ),
        _path_stage(
            "clearance",
            status=str(clearance_summary.get("current_clearance_state") or "advisory_only"),
            clear_condition="satisfy required changes in clearance delta",
            blocking_reasons=clearance_summary.get("required_changes"),
        ),
        _path_stage(
            "admission",
            status=str(admission_summary.get("overall_decision") or "advisory_only"),
            clear_condition=(
                "clear admission blockers and keep dataset advisory until explicitly "
                "rescoped"
            ),
            blocking_reasons=admission_summary.get("decision_reasons"),
        ),
        _path_stage(
            "training_acceptance_hold",
            status="preview_only_hold",
            clear_condition=(
                "explicit human review is still required before any training-safe "
                "claim"
            ),
            blocking_reasons=["external_assessment_remains_advisory_and_non_mutating"],
        ),
    ]

    next_acceptance_stage = next(
        (
            stage["stage"]
            for stage in path_stages
            if stage["status"] in {"blocked", "advisory_only"}
        ),
        "training_acceptance_hold",
    )
    current_path_state = (
        "blocked"
        if any(stage["status"] == "blocked" for stage in path_stages)
        else "advisory_only"
    )

    rows: list[dict[str, Any]] = []
    remediation_action_counts: Counter[str] = Counter()
    blocking_gate_counts: Counter[str] = Counter()

    for accession in accessions:
        resolution_row = resolution_by_accession.get(accession, {})
        accession_remediation_rows = remediation_by_accession.get(accession, [])
        accession_issue_rows = issue_by_accession.get(accession, [])

        issue_categories: list[str] = _listify(resolution_row.get("issue_categories"))
        for row in accession_issue_rows:
            issue_categories.extend(_listify(row.get("issue_category")))
        issue_categories = _listify(issue_categories)

        blocking_gates: list[str] = _listify(resolution_row.get("blocking_gates"))
        for row in accession_remediation_rows:
            blocking_gates.extend(_listify(row.get("blocking_gate")))
        blocking_gates = _listify(blocking_gates)

        remediation_actions: list[str] = _listify(resolution_row.get("remediation_actions"))
        for row in accession_remediation_rows:
            remediation_actions.extend(_listify(row.get("remediation_action")))
        remediation_actions = _listify(remediation_actions)

        supporting_artifacts: list[str] = _listify(resolution_row.get("supporting_artifacts"))
        for row in accession_remediation_rows:
            supporting_artifacts.extend(_listify(row.get("supporting_artifacts")))
        for row in accession_issue_rows:
            supporting_artifacts.extend(_listify(row.get("source_artifacts")))
        supporting_artifacts = _listify(supporting_artifacts)

        for action in remediation_actions:
            remediation_action_counts[action] += 1
        for gate in blocking_gates:
            blocking_gate_counts[gate] += 1

        resolution_state = str(resolution_row.get("resolution_state") or "").strip()
        worst_verdict = str(resolution_row.get("worst_verdict") or "").strip()
        if not worst_verdict and accession_issue_rows:
            worst_verdict = max(
                (str(row.get("verdict") or "") for row in accession_issue_rows),
                key=lambda verdict: (
                    verdict.startswith("blocked"),
                    verdict == "usable_with_caveats",
                    verdict == "audit_only",
                    verdict,
                ),
            )

        acceptance_path_state = (
            "blocked"
            if resolution_state in {"blocked", "mapping-incomplete"}
            or worst_verdict.startswith("blocked")
            else "caveated"
            if issue_categories
            else "advisory_only"
        )

        rows.append(
            {
                "accession": accession,
                "acceptance_path_state": acceptance_path_state,
                "resolution_state": resolution_state or acceptance_path_state,
                "worst_verdict": worst_verdict,
                "issue_categories": issue_categories,
                "blocking_gates": blocking_gates,
                "next_step": (
                    remediation_actions[0]
                    if remediation_actions
                    else "retain_advisory_only_posture"
                ),
                "remediation_actions": remediation_actions[:6],
                "priority_bucket": next(
                    (
                        str(row.get("priority_bucket") or "").strip()
                        for row in accession_remediation_rows
                        if str(row.get("priority_bucket") or "").strip()
                    ),
                    "medium",
                ),
                "supporting_artifacts": supporting_artifacts,
            }
        )

    rows.sort(
        key=lambda row: (0 if row["acceptance_path_state"] == "blocked" else 1, row["accession"])
    )

    return {
        "artifact_id": "external_dataset_acceptance_path_preview",
        "schema_id": "proteosphere-external-dataset-acceptance-path-preview-2026-04-03",
        "status": "report_only",
        "generated_at": (
            assessment_preview.get("generated_at")
            or acceptance_gate_preview.get("generated_at")
            or admission_decision_preview.get("generated_at")
            or clearance_delta_preview.get("generated_at")
            or resolution_preview.get("generated_at")
            or remediation_queue_preview.get("generated_at")
            or issue_matrix_preview.get("generated_at")
            or ""
        ),
        "summary": {
            "dataset_accession_count": int(
                assessment_summary.get("dataset_accession_count")
                or clearance_summary.get("dataset_accession_count")
                or admission_summary.get("dataset_accession_count")
                or 0
            ),
            "acceptance_path_row_count": len(rows),
            "current_path_state": current_path_state,
            "overall_decision": admission_summary.get("overall_decision"),
            "overall_verdict": (
                clearance_summary.get("current_clearance_verdict")
                or admission_summary.get("overall_verdict")
                or assessment_summary.get("overall_verdict")
            ),
            "next_acceptance_stage": next_acceptance_stage,
            "path_stage_count": len(path_stages),
            "blocking_gate_count": int(
                clearance_summary.get("blocking_gate_count")
                or admission_summary.get("blocking_gate_count")
                or 0
            ),
            "required_change_count": int(clearance_summary.get("required_change_count") or 0),
            "blocked_accession_count": int(resolution_summary.get("blocked_accession_count") or 0),
            "mapping_incomplete_accession_count": int(
                resolution_summary.get("mapping_incomplete_accession_count") or 0
            ),
            "remediation_queue_row_count": int(
                remediation_summary.get("remediation_queue_row_count") or 0
            ),
            "top_required_changes": _listify(clearance_summary.get("required_changes"))[:8],
            "top_remediation_actions": [
                {"remediation_action": action, "accession_count": count}
                for action, count in remediation_action_counts.most_common(8)
            ],
            "top_blocking_gates": [
                {"gate_name": gate, "accession_count": count}
                for gate, count in blocking_gate_counts.most_common(8)
            ],
            "advisory_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
        "acceptance_path_stages": path_stages,
        "rows": rows,
        "source_artifacts": {
            "external_dataset_assessment_preview": str(
                DEFAULT_ASSESSMENT_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_acceptance_gate_preview": str(
                DEFAULT_ACCEPTANCE_GATE_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_admission_decision_preview": str(
                DEFAULT_ADMISSION_DECISION_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_clearance_delta_preview": str(
                DEFAULT_CLEARANCE_DELTA_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_resolution_preview": str(
                DEFAULT_RESOLUTION_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_remediation_queue_preview": str(
                DEFAULT_REMEDIATION_QUEUE_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_issue_matrix_preview": str(
                DEFAULT_ISSUE_MATRIX_PREVIEW
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This acceptance-path preview is advisory and fail-closed. It orders the "
                "current external-dataset blockers into an acceptance path, but it does not "
                "mutate source truth or imply training-safe admission."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "training_safe_acceptance_not_implied": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export external dataset acceptance path preview."
    )
    parser.add_argument("--assessment-preview", type=Path, default=DEFAULT_ASSESSMENT_PREVIEW)
    parser.add_argument(
        "--acceptance-gate-preview",
        type=Path,
        default=DEFAULT_ACCEPTANCE_GATE_PREVIEW,
    )
    parser.add_argument(
        "--admission-decision-preview",
        type=Path,
        default=DEFAULT_ADMISSION_DECISION_PREVIEW,
    )
    parser.add_argument(
        "--clearance-delta-preview",
        type=Path,
        default=DEFAULT_CLEARANCE_DELTA_PREVIEW,
    )
    parser.add_argument("--resolution-preview", type=Path, default=DEFAULT_RESOLUTION_PREVIEW)
    parser.add_argument(
        "--remediation-queue-preview",
        type=Path,
        default=DEFAULT_REMEDIATION_QUEUE_PREVIEW,
    )
    parser.add_argument("--issue-matrix-preview", type=Path, default=DEFAULT_ISSUE_MATRIX_PREVIEW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_external_dataset_acceptance_path_preview(
        _load_payload(args.assessment_preview),
        _load_payload(args.acceptance_gate_preview),
        _load_payload(args.admission_decision_preview),
        _load_payload(args.clearance_delta_preview),
        _load_payload(args.resolution_preview),
        _load_payload(args.remediation_queue_preview),
        _load_payload(args.issue_matrix_preview),
    )
    write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
