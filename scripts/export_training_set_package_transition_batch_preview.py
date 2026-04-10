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

DEFAULT_TRANSITION_CONTRACT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_transition_contract_preview.json"
)
DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "training_set_package_blocker_matrix_preview.json"
)
DEFAULT_PACKAGE_READINESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "training_set_package_transition_batch_preview.json"
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


def build_training_set_package_transition_batch_preview(
    transition_contract_preview: dict[str, Any],
    package_blocker_matrix_preview: dict[str, Any],
    package_readiness_preview: dict[str, Any],
) -> dict[str, Any]:
    transition_rows = transition_contract_preview.get("rows") or []
    package_blocker_rows = package_blocker_matrix_preview.get("rows") or []
    package_summary = package_readiness_preview.get("summary") or {}

    package_blocker_by_accession = _rows_by_accession(package_blocker_rows)

    rows: list[dict[str, Any]] = []
    route_state_counts: Counter[str] = Counter()
    priority_bucket_counts: Counter[str] = Counter()
    package_blocker_counts: Counter[str] = Counter()
    next_step_counts: Counter[str] = Counter()

    for transition_row in transition_rows:
        if not isinstance(transition_row, dict):
            continue
        if str(transition_row.get("current_transition_state") or "").strip() != (
            "package_transition_blocked"
        ):
            continue

        accession = str(transition_row.get("accession") or "").strip()
        if not accession:
            continue

        package_row = package_blocker_by_accession.get(accession, {})
        package_blockers = _listify(
            package_row.get("package_blockers") or transition_row.get("package_blockers")
        )
        blocked_reasons = _listify(package_row.get("blocked_reasons"))
        modality_gap_categories = _listify(package_row.get("modality_gap_categories"))
        supporting_artifacts = _listify(transition_row.get("supporting_artifacts"))
        supporting_artifacts.extend(_listify(package_row.get("supporting_artifacts")))
        supporting_artifacts = _listify(supporting_artifacts) or [
            "training_set_transition_contract_preview",
            "training_set_package_blocker_matrix_preview",
            "package_readiness_preview",
        ]

        route_state = str(transition_row.get("route_state") or "").strip()
        priority_bucket = str(package_row.get("priority_bucket") or "critical").strip()
        next_package_action = str(
            package_row.get("recommended_next_step")
            or transition_row.get("next_transition")
            or "unlock_package_transition"
        ).strip()

        route_state_counts[route_state] += 1
        priority_bucket_counts[priority_bucket] += 1
        next_step_counts[next_package_action] += 1
        for blocker in package_blockers:
            package_blocker_counts[blocker] += 1

        rows.append(
            {
                "accession": accession,
                "package_transition_batch_state": "package_transition_blocked",
                "route_state": route_state,
                "training_set_state": transition_row.get("training_set_state"),
                "split": transition_row.get("split"),
                "bucket": transition_row.get("bucket"),
                "priority_bucket": priority_bucket,
                "blocked_reason_count": int(
                    package_row.get("blocked_reason_count") or len(blocked_reasons)
                ),
                "blocked_reasons": blocked_reasons,
                "package_blockers": package_blockers,
                "modality_gap_categories": modality_gap_categories,
                "fold_export_blocked": bool(package_row.get("fold_export_blocked")),
                "package_ready": bool(package_row.get("package_ready")),
                "next_package_action": next_package_action,
                "global_package_gate_blockers": _listify(
                    package_summary.get("blocked_reasons")
                ),
                "supporting_artifacts": supporting_artifacts,
            }
        )

    rows.sort(
        key=lambda row: (
            0 if str(row.get("priority_bucket") or "") == "critical" else 1,
            str(row.get("accession") or "").casefold(),
        )
    )

    next_package_batch = rows[0]["next_package_action"] if rows else None

    return {
        "artifact_id": "training_set_package_transition_batch_preview",
        "schema_id": "proteosphere-training-set-package-transition-batch-preview-2026-04-03",
        "status": "report_only",
        "generated_at": transition_contract_preview.get("generated_at")
        or package_blocker_matrix_preview.get("generated_at")
        or package_readiness_preview.get("generated_at"),
        "summary": {
            "selected_count": int(
                (transition_contract_preview.get("summary") or {}).get("selected_count")
                or 0
            ),
            "package_transition_batch_row_count": len(rows),
            "current_batch_state": (
                "blocked_pending_package_transition_batch"
                if rows
                else "no_package_transition_batch_required"
            ),
            "next_package_batch": next_package_batch,
            "preview_visible_package_count": route_state_counts.get(
                "preview_visible_non_governing", 0
            ),
            "governing_ready_package_count": route_state_counts.get(
                "governing_ready_but_package_blocked", 0
            ),
            "critical_priority_count": priority_bucket_counts.get("critical", 0),
            "fold_export_blocked_count": sum(
                1 for row in rows if bool(row.get("fold_export_blocked"))
            ),
            "top_package_blockers": [
                {"package_blocker": item, "accession_count": count}
                for item, count in package_blocker_counts.most_common(8)
            ],
            "top_next_package_actions": [
                {"next_package_action": item, "accession_count": count}
                for item, count in next_step_counts.most_common(8)
            ],
            "fail_closed": True,
            "non_mutating": True,
        },
        "rows": rows,
        "source_artifacts": {
            "training_set_transition_contract_preview": str(
                DEFAULT_TRANSITION_CONTRACT_PREVIEW
            ).replace("\\", "/"),
            "training_set_package_blocker_matrix_preview": str(
                DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW
            ).replace("\\", "/"),
            "package_readiness_preview": str(DEFAULT_PACKAGE_READINESS_PREVIEW).replace(
                "\\", "/"
            ),
        },
        "truth_boundary": {
            "summary": (
                "This package-transition batch preview is report-only and fail-closed. "
                "It groups package-transition-blocked accessions for operator follow-up, "
                "but it does not unlock fold export, packaging, or release."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "package_not_authorized": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the training-set package transition batch preview."
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
    payload = build_training_set_package_transition_batch_preview(
        _load_payload(DEFAULT_TRANSITION_CONTRACT_PREVIEW),
        _load_payload(DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW),
        _load_payload(DEFAULT_PACKAGE_READINESS_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
