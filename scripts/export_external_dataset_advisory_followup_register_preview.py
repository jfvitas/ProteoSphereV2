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

DEFAULT_CAVEAT_EXECUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_caveat_execution_preview.json"
)
DEFAULT_RESOLUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)
DEFAULT_RISK_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_risk_register_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "external_dataset_advisory_followup_register_preview.json"
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


def build_external_dataset_advisory_followup_register_preview(
    caveat_execution_preview: dict[str, Any],
    resolution_preview: dict[str, Any],
    risk_register_preview: dict[str, Any],
) -> dict[str, Any]:
    caveat_rows = caveat_execution_preview.get("rows") or []
    resolution_rows = resolution_preview.get("accession_resolution_rows") or []
    risk_rows = risk_register_preview.get("top_risk_rows") or []

    resolution_by_accession = _rows_by_accession(resolution_rows)
    risk_by_accession: dict[str, list[dict[str, Any]]] = {}
    if isinstance(risk_rows, list):
        for row in risk_rows:
            if not isinstance(row, dict):
                continue
            accession = str(row.get("accession") or "").strip()
            if accession:
                risk_by_accession.setdefault(accession, []).append(row)

    rows: list[dict[str, Any]] = []
    followup_lane_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()

    for caveat_row in caveat_rows:
        if not isinstance(caveat_row, dict):
            continue
        accession = str(caveat_row.get("accession") or "").strip()
        if not accession:
            continue

        resolution_row = resolution_by_accession.get(accession, {})
        accession_risk_rows = risk_by_accession.get(accession, [])
        execution_lane = str(caveat_row.get("execution_lane") or "").strip()
        next_execution_step = str(caveat_row.get("next_execution_step") or "").strip()

        if execution_lane == "structure_alignment_caveat_follow_up":
            followup_lane = "structure_alignment_advisory_follow_up"
        else:
            followup_lane = "binding_provenance_advisory_follow_up"

        issue_categories = _listify(caveat_row.get("issue_categories"))
        remediation_actions = _listify(caveat_row.get("remediation_actions"))
        for risk_row in accession_risk_rows:
            remediation_actions.extend(_listify(risk_row.get("remediation_action")))
        remediation_actions = _listify(remediation_actions)

        top_risk_categories = _listify(
            [risk_row.get("issue_category") for risk_row in accession_risk_rows]
        )

        for category in issue_categories:
            category_counts[category] += 1
        for action in remediation_actions:
            action_counts[action] += 1
        followup_lane_counts[followup_lane] += 1

        rows.append(
            {
                "accession": accession,
                "advisory_followup_state": "advisory_follow_up_required",
                "followup_lane": followup_lane,
                "priority_bucket": caveat_row.get("priority_bucket"),
                "resolution_state": resolution_row.get("resolution_state")
                or caveat_row.get("resolution_state"),
                "acceptance_path_state": caveat_row.get("acceptance_path_state"),
                "issue_categories": issue_categories,
                "top_risk_categories": top_risk_categories,
                "next_execution_step": next_execution_step
                or "preserve_binding_and_provenance_caveats",
                "remediation_actions": remediation_actions,
                "queue_row_count": caveat_row.get("queue_row_count"),
                "supporting_artifacts": _listify(caveat_row.get("supporting_artifacts"))
                or _listify(resolution_row.get("supporting_artifacts"))
                or [
                    "external_dataset_caveat_execution_preview",
                    "external_dataset_resolution_preview",
                    "external_dataset_risk_register_preview",
                ],
            }
        )

    rows.sort(
        key=lambda row: (
            0
            if str(row.get("followup_lane") or "")
            == "structure_alignment_advisory_follow_up"
            else 1,
            str(row.get("accession") or "").casefold(),
        )
    )

    next_followup_lane = rows[0]["followup_lane"] if rows else None

    return {
        "artifact_id": "external_dataset_advisory_followup_register_preview",
        "schema_id": "proteosphere-external-dataset-advisory-followup-register-preview-2026-04-03",
        "status": "report_only",
        "generated_at": caveat_execution_preview.get("generated_at")
        or resolution_preview.get("generated_at")
        or risk_register_preview.get("generated_at"),
        "summary": {
            "dataset_accession_count": int(
                (caveat_execution_preview.get("summary") or {}).get(
                    "dataset_accession_count"
                )
                or 0
            ),
            "advisory_followup_row_count": len(rows),
            "current_followup_state": (
                "advisory_follow_up_register_active"
                if rows
                else "no_advisory_follow_up_register_entries"
            ),
            "next_followup_lane": next_followup_lane,
            "structure_alignment_followup_count": followup_lane_counts.get(
                "structure_alignment_advisory_follow_up", 0
            ),
            "binding_provenance_followup_count": followup_lane_counts.get(
                "binding_provenance_advisory_follow_up", 0
            ),
            "top_issue_categories": [
                {"issue_category": item, "accession_count": count}
                for item, count in category_counts.most_common(8)
            ],
            "top_remediation_actions": [
                {"remediation_action": item, "accession_count": count}
                for item, count in action_counts.most_common(8)
            ],
            "advisory_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
        "rows": rows,
        "source_artifacts": {
            "external_dataset_caveat_execution_preview": str(
                DEFAULT_CAVEAT_EXECUTION_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_resolution_preview": str(
                DEFAULT_RESOLUTION_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_risk_register_preview": str(
                DEFAULT_RISK_REGISTER_PREVIEW
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This advisory-follow-up register is advisory and fail-closed. "
                "It organizes caveated external rows for human follow-up, but it does "
                "not admit the dataset for training."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "training_safe_acceptance_not_implied": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the external-dataset advisory follow-up register preview."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_external_dataset_advisory_followup_register_preview(
        _load_payload(DEFAULT_CAVEAT_EXECUTION_PREVIEW),
        _load_payload(DEFAULT_RESOLUTION_PREVIEW),
        _load_payload(DEFAULT_RISK_REGISTER_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
