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

DEFAULT_REMEDIATION_READINESS_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "external_dataset_remediation_readiness_preview.json"
)
DEFAULT_ACCEPTANCE_PATH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_path_preview.json"
)
DEFAULT_REMEDIATION_QUEUE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_remediation_queue_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_caveat_execution_preview.json"
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


def build_external_dataset_caveat_execution_preview(
    remediation_readiness_preview: dict[str, Any],
    acceptance_path_preview: dict[str, Any],
    remediation_queue_preview: dict[str, Any],
) -> dict[str, Any]:
    readiness_rows = remediation_readiness_preview.get("rows") or []
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
    issue_category_counts: Counter[str] = Counter()
    remediation_action_counts: Counter[str] = Counter()
    priority_bucket_counts: Counter[str] = Counter()

    for readiness_row in readiness_rows:
        if not isinstance(readiness_row, dict):
            continue
        if str(readiness_row.get("remediation_readiness_state") or "").strip() != (
            "advisory_follow_up"
        ):
            continue

        accession = str(readiness_row.get("accession") or "").strip()
        if not accession:
            continue

        acceptance_row = acceptance_by_accession.get(accession, {})
        accession_queue_rows = queue_rows_by_accession.get(accession, [])

        issue_categories = _listify(readiness_row.get("issue_categories"))
        remediation_actions = _listify(readiness_row.get("remediation_actions"))
        for queue_row in accession_queue_rows:
            issue_categories.extend(_listify(queue_row.get("issue_category")))
            remediation_actions.extend(_listify(queue_row.get("remediation_action")))
        issue_categories = _listify(issue_categories)
        remediation_actions = _listify(remediation_actions)

        execution_lane = (
            "structure_alignment_caveat_follow_up"
            if "structure" in issue_categories
            else "binding_provenance_caveat_follow_up"
        )
        next_execution_step = (
            "preserve_structure_alignment_caveat"
            if execution_lane == "structure_alignment_caveat_follow_up"
            else "preserve_binding_and_provenance_caveats"
        )

        for issue_category in issue_categories:
            issue_category_counts[issue_category] += 1
        for remediation_action in remediation_actions:
            remediation_action_counts[remediation_action] += 1
        priority_bucket = str(
            readiness_row.get("priority_bucket")
            or acceptance_row.get("priority_bucket")
            or "p2_support_context"
        )
        priority_bucket_counts[priority_bucket] += 1

        rows.append(
            {
                "accession": accession,
                "caveat_execution_state": "advisory_follow_up",
                "execution_lane": execution_lane,
                "priority_bucket": priority_bucket,
                "acceptance_path_state": acceptance_row.get("acceptance_path_state"),
                "resolution_state": readiness_row.get("resolution_state"),
                "issue_categories": issue_categories,
                "blocking_dependencies": _listify(
                    readiness_row.get("blocking_dependencies")
                ),
                "remediation_actions": remediation_actions,
                "next_execution_step": next_execution_step,
                "queue_row_count": len(accession_queue_rows),
                "supporting_artifacts": _listify(
                    readiness_row.get("supporting_artifacts")
                )
                or _listify(acceptance_row.get("supporting_artifacts"))
                or [
                    "external_dataset_remediation_readiness_preview",
                    "external_dataset_acceptance_path_preview",
                    "external_dataset_remediation_queue_preview",
                ],
            }
        )

    rows.sort(
        key=lambda row: (
            0
            if str(row.get("execution_lane") or "")
            == "structure_alignment_caveat_follow_up"
            else 1,
            str(row.get("accession") or "").casefold(),
        )
    )

    next_execution_batch = rows[0]["execution_lane"] if rows else None

    return {
        "artifact_id": "external_dataset_caveat_execution_preview",
        "schema_id": "proteosphere-external-dataset-caveat-execution-preview-2026-04-03",
        "status": "report_only",
        "generated_at": remediation_readiness_preview.get("generated_at")
        or acceptance_path_preview.get("generated_at")
        or remediation_queue_preview.get("generated_at"),
        "summary": {
            "dataset_accession_count": int(
                (remediation_readiness_preview.get("summary") or {}).get(
                    "dataset_accession_count"
                )
                or 0
            ),
            "caveat_execution_row_count": len(rows),
            "current_execution_state": (
                "caveat_follow_up_ready" if rows else "no_caveat_execution_required"
            ),
            "next_execution_batch": next_execution_batch,
            "structure_sensitive_follow_up_count": issue_category_counts.get(
                "structure", 0
            ),
            "binding_follow_up_count": issue_category_counts.get("binding", 0),
            "provenance_follow_up_count": issue_category_counts.get("provenance", 0),
            "priority_bucket_counts": dict(priority_bucket_counts),
            "top_issue_categories": [
                {"issue_category": item, "accession_count": count}
                for item, count in issue_category_counts.most_common(8)
            ],
            "top_remediation_actions": [
                {"remediation_action": item, "accession_count": count}
                for item, count in remediation_action_counts.most_common(8)
            ],
            "advisory_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
        "rows": rows,
        "source_artifacts": {
            "external_dataset_remediation_readiness_preview": str(
                DEFAULT_REMEDIATION_READINESS_PREVIEW
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
                "This caveat-execution preview is advisory and fail-closed. "
                "It groups caveated external accessions into follow-up batches, "
                "but it does not admit the dataset for training."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "training_safe_acceptance_not_implied": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the external-dataset caveat execution preview."
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
    payload = build_external_dataset_caveat_execution_preview(
        _load_payload(DEFAULT_REMEDIATION_READINESS_PREVIEW),
        _load_payload(DEFAULT_ACCEPTANCE_PATH_PREVIEW),
        _load_payload(DEFAULT_REMEDIATION_QUEUE_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
