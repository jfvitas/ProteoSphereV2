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
DEFAULT_ACCEPTANCE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json"
)
DEFAULT_ISSUE_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_issue_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "external_dataset_blocked_acquisition_batch_preview.json"
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


def build_external_dataset_blocked_acquisition_batch_preview(
    remediation_readiness_preview: dict[str, Any],
    acceptance_gate_preview: dict[str, Any],
    issue_matrix_preview: dict[str, Any],
) -> dict[str, Any]:
    readiness_rows = remediation_readiness_preview.get("rows") or []
    gate_reports = acceptance_gate_preview.get("gate_reports") or []
    issue_rows = issue_matrix_preview.get("rows") or []

    blocked_issue_rows_by_accession: dict[str, list[dict[str, Any]]] = {}
    if isinstance(issue_rows, list):
        for row in issue_rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("verdict") or "").strip() != "blocked_pending_acquisition":
                continue
            accession = str(row.get("accession") or "").strip()
            if accession:
                blocked_issue_rows_by_accession.setdefault(accession, []).append(row)

    blocking_gate_reports = [
        report
        for report in gate_reports
        if isinstance(report, dict)
        and str(report.get("verdict") or "").strip() == "blocked_pending_acquisition"
    ]

    rows: list[dict[str, Any]] = []
    issue_category_counts: Counter[str] = Counter()
    remediation_action_counts: Counter[str] = Counter()
    priority_bucket_counts: Counter[str] = Counter()
    blocking_gate_counts: Counter[str] = Counter()

    for readiness_row in readiness_rows:
        if not isinstance(readiness_row, dict):
            continue
        if str(readiness_row.get("remediation_readiness_state") or "").strip() != (
            "blocked_pending_acquisition"
        ):
            continue

        accession = str(readiness_row.get("accession") or "").strip()
        if not accession:
            continue

        accession_issue_rows = blocked_issue_rows_by_accession.get(accession, [])
        issue_categories = _listify(readiness_row.get("issue_categories"))
        remediation_actions = _listify(readiness_row.get("remediation_actions"))
        source_artifacts = _listify(readiness_row.get("supporting_artifacts"))

        for issue_row in accession_issue_rows:
            issue_categories.extend(_listify(issue_row.get("issue_category")))
            remediation_actions.extend(_listify(issue_row.get("remediation_action")))
            source_artifacts.extend(_listify(issue_row.get("source_artifacts")))

        issue_categories = _listify(issue_categories)
        remediation_actions = _listify(remediation_actions)
        source_artifacts = _listify(source_artifacts) or [
            "external_dataset_remediation_readiness_preview",
            "external_dataset_acceptance_gate_preview",
            "external_dataset_issue_matrix_preview",
        ]

        lead_blocking_gate = (
            "issue_matrix"
            if accession_issue_rows
            else str(readiness_row.get("acceptance_path_state") or "resolution").strip()
        )
        blocking_gate_counts[lead_blocking_gate] += 1

        priority_bucket = str(readiness_row.get("priority_bucket") or "p0_blocker").strip()
        priority_bucket_counts[priority_bucket] += 1
        for issue_category in issue_categories:
            issue_category_counts[issue_category] += 1
        for action in remediation_actions:
            remediation_action_counts[action] += 1

        rows.append(
            {
                "accession": accession,
                "blocked_acquisition_batch_state": "blocked_pending_acquisition",
                "priority_bucket": priority_bucket,
                "acceptance_path_state": readiness_row.get("acceptance_path_state"),
                "resolution_state": readiness_row.get("resolution_state"),
                "worst_verdict": readiness_row.get("worst_verdict"),
                "issue_categories": issue_categories,
                "blocking_dependencies": _listify(
                    readiness_row.get("blocking_dependencies")
                ),
                "remediation_actions": remediation_actions,
                "blocked_issue_row_count": len(accession_issue_rows),
                "lead_blocking_gate": lead_blocking_gate,
                "next_blocked_action": readiness_row.get("next_action")
                or "wait_for_acquisition_or_mapping_fix",
                "supporting_artifacts": source_artifacts,
            }
        )

    rows.sort(
        key=lambda row: (
            0 if str(row.get("priority_bucket") or "") == "p0_blocker" else 1,
            str(row.get("accession") or "").casefold(),
        )
    )

    next_blocked_batch = rows[0]["lead_blocking_gate"] if rows else None

    return {
        "artifact_id": "external_dataset_blocked_acquisition_batch_preview",
        "schema_id": "proteosphere-external-dataset-blocked-acquisition-batch-preview-2026-04-03",
        "status": "report_only",
        "generated_at": remediation_readiness_preview.get("generated_at")
        or acceptance_gate_preview.get("generated_at")
        or issue_matrix_preview.get("generated_at"),
        "summary": {
            "dataset_accession_count": int(
                (remediation_readiness_preview.get("summary") or {}).get(
                    "dataset_accession_count"
                )
                or 0
            ),
            "blocked_acquisition_row_count": len(rows),
            "current_batch_state": (
                "blocked_pending_acquisition_batch"
                if rows
                else "no_blocked_acquisition_batch_required"
            ),
            "next_blocked_batch": next_blocked_batch,
            "p0_blocker_count": priority_bucket_counts.get("p0_blocker", 0),
            "blocked_gate_count": len(blocking_gate_reports),
            "top_blocking_gates": [
                {"gate_name": item, "accession_count": count}
                for item, count in blocking_gate_counts.most_common(8)
            ],
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
            "external_dataset_acceptance_gate_preview": str(
                DEFAULT_ACCEPTANCE_GATE_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_issue_matrix_preview": str(
                DEFAULT_ISSUE_MATRIX_PREVIEW
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This blocked-acquisition batch preview is advisory and fail-closed. "
                "It groups acquisition-blocked external accessions for follow-up, "
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
        description="Export the external-dataset blocked acquisition batch preview."
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
    payload = build_external_dataset_blocked_acquisition_batch_preview(
        _load_payload(DEFAULT_REMEDIATION_READINESS_PREVIEW),
        _load_payload(DEFAULT_ACCEPTANCE_GATE_PREVIEW),
        _load_payload(DEFAULT_ISSUE_MATRIX_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
