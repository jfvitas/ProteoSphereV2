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

DEFAULT_BLOCKED_ACQUISITION_BATCH_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "external_dataset_blocked_acquisition_batch_preview.json"
)
DEFAULT_ACCEPTANCE_PATH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_path_preview.json"
)
DEFAULT_REMEDIATION_QUEUE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_remediation_queue_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "external_dataset_acquisition_unblock_preview.json"
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


def build_external_dataset_acquisition_unblock_preview(
    blocked_acquisition_batch_preview: dict[str, Any],
    acceptance_path_preview: dict[str, Any],
    remediation_queue_preview: dict[str, Any],
) -> dict[str, Any]:
    batch_rows = blocked_acquisition_batch_preview.get("rows") or []
    acceptance_rows = acceptance_path_preview.get("rows") or []
    queue_rows = remediation_queue_preview.get("rows") or []

    acceptance_by_accession = _rows_by_accession(acceptance_rows)
    queue_rows_by_accession: dict[str, list[dict[str, Any]]] = {}
    if isinstance(queue_rows, list):
        for row in queue_rows:
            if not isinstance(row, dict):
                continue
            accession = str(row.get("accession") or "").strip()
            if accession:
                queue_rows_by_accession.setdefault(accession, []).append(row)

    rows: list[dict[str, Any]] = []
    unblock_lane_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    gate_counts: Counter[str] = Counter()

    for batch_row in batch_rows:
        if not isinstance(batch_row, dict):
            continue
        accession = str(batch_row.get("accession") or "").strip()
        if not accession:
            continue

        acceptance_row = acceptance_by_accession.get(accession, {})
        accession_queue_rows = queue_rows_by_accession.get(accession, [])
        remediation_actions = _listify(batch_row.get("remediation_actions"))
        for queue_row in accession_queue_rows:
            remediation_actions.extend(_listify(queue_row.get("remediation_action")))
        remediation_actions = _listify(remediation_actions)

        lead_gate = str(batch_row.get("lead_blocking_gate") or "issue_matrix").strip()
        gate_counts[lead_gate] += 1
        next_blocked_action = str(
            batch_row.get("next_blocked_action") or "wait_for_acquisition_or_mapping_fix"
        ).strip()
        if "wait_for_acquisition" in next_blocked_action:
            unblock_lane = "acquisition_blocker_follow_up"
        else:
            unblock_lane = "mapping_or_resolution_follow_up"
        unblock_lane_counts[unblock_lane] += 1

        for action in remediation_actions:
            action_counts[action] += 1

        rows.append(
            {
                "accession": accession,
                "acquisition_unblock_state": "blocked_pending_acquisition",
                "unblock_lane": unblock_lane,
                "priority_bucket": batch_row.get("priority_bucket"),
                "acceptance_path_state": acceptance_row.get("acceptance_path_state"),
                "resolution_state": batch_row.get("resolution_state"),
                "lead_blocking_gate": lead_gate,
                "next_blocked_action": next_blocked_action,
                "issue_categories": _listify(batch_row.get("issue_categories")),
                "remediation_actions": remediation_actions,
                "queue_row_count": len(accession_queue_rows),
                "supporting_artifacts": _listify(batch_row.get("supporting_artifacts"))
                or _listify(acceptance_row.get("supporting_artifacts"))
                or [
                    "external_dataset_blocked_acquisition_batch_preview",
                    "external_dataset_acceptance_path_preview",
                    "external_dataset_remediation_queue_preview",
                ],
            }
        )

    rows.sort(
        key=lambda row: (
            0
            if str(row.get("unblock_lane") or "") == "acquisition_blocker_follow_up"
            else 1,
            str(row.get("accession") or "").casefold(),
        )
    )

    next_unblock_batch = rows[0]["unblock_lane"] if rows else None

    return {
        "artifact_id": "external_dataset_acquisition_unblock_preview",
        "schema_id": "proteosphere-external-dataset-acquisition-unblock-preview-2026-04-03",
        "status": "report_only",
        "generated_at": blocked_acquisition_batch_preview.get("generated_at")
        or acceptance_path_preview.get("generated_at")
        or remediation_queue_preview.get("generated_at"),
        "summary": {
            "dataset_accession_count": int(
                (blocked_acquisition_batch_preview.get("summary") or {}).get(
                    "dataset_accession_count"
                )
                or 0
            ),
            "acquisition_unblock_row_count": len(rows),
            "current_unblock_state": (
                "blocked_acquisition_follow_up_required"
                if rows
                else "no_blocked_acquisition_follow_up_required"
            ),
            "next_unblock_batch": next_unblock_batch,
            "acquisition_follow_up_count": unblock_lane_counts.get(
                "acquisition_blocker_follow_up", 0
            ),
            "mapping_follow_up_count": unblock_lane_counts.get(
                "mapping_or_resolution_follow_up", 0
            ),
            "top_blocking_gates": [
                {"gate_name": item, "accession_count": count}
                for item, count in gate_counts.most_common(8)
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
            "external_dataset_blocked_acquisition_batch_preview": str(
                DEFAULT_BLOCKED_ACQUISITION_BATCH_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_acceptance_path_preview": str(
                DEFAULT_ACCEPTANCE_PATH_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_remediation_queue_preview": str(
                DEFAULT_REMEDIATION_QUEUE_PREVIEW
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This acquisition unblock preview is advisory and fail-closed. "
                "It organizes blocked-acquisition follow-up work, but it does not "
                "admit the dataset for training."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "training_safe_acceptance_not_implied": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the external-dataset acquisition unblock preview."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_external_dataset_acquisition_unblock_preview(
        _load_payload(DEFAULT_BLOCKED_ACQUISITION_BATCH_PREVIEW),
        _load_payload(DEFAULT_ACCEPTANCE_PATH_PREVIEW),
        _load_payload(DEFAULT_REMEDIATION_QUEUE_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
