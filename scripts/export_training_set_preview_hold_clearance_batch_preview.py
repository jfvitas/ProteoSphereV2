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

DEFAULT_EXIT_CRITERIA_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "training_set_preview_hold_exit_criteria_preview.json"
)
DEFAULT_PREVIEW_HOLD_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_preview_hold_register_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "training_set_preview_hold_clearance_batch_preview.json"
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


def build_training_set_preview_hold_clearance_batch_preview(
    exit_criteria_preview: dict[str, Any],
    preview_hold_register_preview: dict[str, Any],
) -> dict[str, Any]:
    exit_rows = exit_criteria_preview.get("rows") or []
    hold_rows = preview_hold_register_preview.get("rows") or []
    hold_by_accession = _rows_by_accession(hold_rows)

    rows: list[dict[str, Any]] = []
    batch_counts: Counter[str] = Counter()
    review_counts: Counter[str] = Counter()

    for exit_row in exit_rows:
        if not isinstance(exit_row, dict):
            continue
        accession = str(exit_row.get("accession") or "").strip()
        if not accession:
            continue

        hold_row = hold_by_accession.get(accession, {})
        exit_state = str(exit_row.get("exit_criteria_state") or "").strip()
        if exit_state == "blocked_pending_package_gate_unlock":
            clearance_batch = "package_gate_recheck_batch"
        elif exit_state == "blocked_pending_packet_and_modality_completion":
            clearance_batch = "packet_modality_recheck_batch"
        else:
            clearance_batch = "support_only_manual_review_batch"

        next_review_step = str(exit_row.get("next_review_step") or "").strip()
        batch_counts[clearance_batch] += 1
        if next_review_step:
            review_counts[next_review_step] += 1

        rows.append(
            {
                "accession": accession,
                "preview_hold_state": exit_row.get("preview_hold_state"),
                "hold_lane": exit_row.get("hold_lane")
                or hold_row.get("hold_lane"),
                "clearance_batch": clearance_batch,
                "exit_criteria_state": exit_state,
                "next_review_step": next_review_step,
                "exit_criteria": _listify(exit_row.get("exit_criteria")),
                "priority_bucket": exit_row.get("priority_bucket")
                or hold_row.get("priority_bucket"),
                "modality_gap_categories": _listify(
                    exit_row.get("modality_gap_categories")
                    or hold_row.get("modality_gap_categories")
                ),
                "supporting_artifacts": _listify(exit_row.get("supporting_artifacts"))
                or [
                    "training_set_preview_hold_exit_criteria_preview",
                    "training_set_preview_hold_register_preview",
                ],
            }
        )

    rows.sort(
        key=lambda row: (
            str(row.get("clearance_batch") or ""),
            str(row.get("accession") or "").casefold(),
        )
    )

    return {
        "artifact_id": "training_set_preview_hold_clearance_batch_preview",
        "schema_id": "proteosphere-training-set-preview-hold-clearance-batch-preview-2026-04-03",
        "status": "report_only",
        "generated_at": exit_criteria_preview.get("generated_at")
        or preview_hold_register_preview.get("generated_at"),
        "summary": {
            "selected_count": int(
                (preview_hold_register_preview.get("summary") or {}).get("selected_count")
                or 0
            ),
            "clearance_batch_row_count": len(rows),
            "current_batch_state": (
                "preview_hold_clearance_batch_active"
                if rows
                else "no_preview_hold_clearance_batch_rows"
            ),
            "package_gate_recheck_count": batch_counts.get(
                "package_gate_recheck_batch", 0
            ),
            "packet_modality_recheck_count": batch_counts.get(
                "packet_modality_recheck_batch", 0
            ),
            "support_only_manual_review_count": batch_counts.get(
                "support_only_manual_review_batch", 0
            ),
            "top_next_review_steps": [
                {"next_review_step": item, "accession_count": count}
                for item, count in review_counts.most_common(8)
            ],
            "fail_closed": True,
            "non_mutating": True,
        },
        "rows": rows,
        "source_artifacts": {
            "training_set_preview_hold_exit_criteria_preview": str(
                DEFAULT_EXIT_CRITERIA_PREVIEW
            ).replace("\\", "/"),
            "training_set_preview_hold_register_preview": str(
                DEFAULT_PREVIEW_HOLD_REGISTER_PREVIEW
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This preview-hold clearance batch is report-only and fail-closed. "
                "It organizes held rows for recheck sequencing, but it does not unlock "
                "packaging or release claims."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "package_not_authorized": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the training-set preview hold clearance batch preview."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_training_set_preview_hold_clearance_batch_preview(
        _load_payload(DEFAULT_EXIT_CRITERIA_PREVIEW),
        _load_payload(DEFAULT_PREVIEW_HOLD_REGISTER_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
