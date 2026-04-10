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

DEFAULT_CAVEAT_EXIT_CRITERIA_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "external_dataset_caveat_exit_criteria_preview.json"
)
DEFAULT_ADVISORY_FOLLOWUP_REGISTER_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "external_dataset_advisory_followup_register_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "external_dataset_caveat_review_batch_preview.json"
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


def build_external_dataset_caveat_review_batch_preview(
    caveat_exit_criteria_preview: dict[str, Any],
    advisory_followup_register_preview: dict[str, Any],
) -> dict[str, Any]:
    exit_rows = caveat_exit_criteria_preview.get("rows") or []
    advisory_rows = advisory_followup_register_preview.get("rows") or []
    advisory_by_accession = _rows_by_accession(advisory_rows)

    rows: list[dict[str, Any]] = []
    batch_counts: Counter[str] = Counter()
    allowed_counts: Counter[str] = Counter()

    for exit_row in exit_rows:
        if not isinstance(exit_row, dict):
            continue
        accession = str(exit_row.get("accession") or "").strip()
        if not accession:
            continue

        advisory_row = advisory_by_accession.get(accession, {})
        caveat_state = str(exit_row.get("caveat_exit_state") or "").strip()
        if caveat_state == "caveated_pending_structure_alignment_review":
            review_batch = "structure_alignment_review_batch"
        else:
            review_batch = "binding_provenance_review_batch"

        allowed_current_use = str(exit_row.get("allowed_current_use") or "").strip()
        batch_counts[review_batch] += 1
        if allowed_current_use:
            allowed_counts[allowed_current_use] += 1

        rows.append(
            {
                "accession": accession,
                "followup_lane": exit_row.get("followup_lane")
                or advisory_row.get("followup_lane"),
                "review_batch": review_batch,
                "caveat_exit_state": caveat_state,
                "allowed_current_use": allowed_current_use,
                "next_review_action": exit_row.get("next_review_action"),
                "issue_categories": _listify(
                    exit_row.get("issue_categories")
                    or advisory_row.get("issue_categories")
                ),
                "exit_criteria": _listify(exit_row.get("exit_criteria")),
                "priority_bucket": exit_row.get("priority_bucket")
                or advisory_row.get("priority_bucket"),
                "supporting_artifacts": _listify(exit_row.get("supporting_artifacts"))
                or [
                    "external_dataset_caveat_exit_criteria_preview",
                    "external_dataset_advisory_followup_register_preview",
                ],
            }
        )

    rows.sort(
        key=lambda row: (
            str(row.get("review_batch") or ""),
            str(row.get("accession") or "").casefold(),
        )
    )

    return {
        "artifact_id": "external_dataset_caveat_review_batch_preview",
        "schema_id": "proteosphere-external-dataset-caveat-review-batch-preview-2026-04-03",
        "status": "report_only",
        "generated_at": caveat_exit_criteria_preview.get("generated_at")
        or advisory_followup_register_preview.get("generated_at"),
        "summary": {
            "dataset_accession_count": int(
                (caveat_exit_criteria_preview.get("summary") or {}).get(
                    "dataset_accession_count"
                )
                or 0
            ),
            "review_batch_row_count": len(rows),
            "current_batch_state": (
                "caveat_review_batch_active"
                if rows
                else "no_caveat_review_batch_rows"
            ),
            "structure_alignment_review_count": batch_counts.get(
                "structure_alignment_review_batch", 0
            ),
            "binding_provenance_review_count": batch_counts.get(
                "binding_provenance_review_batch", 0
            ),
            "allowed_current_use_counts": [
                {"allowed_current_use": item, "accession_count": count}
                for item, count in allowed_counts.most_common(8)
            ],
            "advisory_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
        "rows": rows,
        "source_artifacts": {
            "external_dataset_caveat_exit_criteria_preview": str(
                DEFAULT_CAVEAT_EXIT_CRITERIA_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_advisory_followup_register_preview": str(
                DEFAULT_ADVISORY_FOLLOWUP_REGISTER_PREVIEW
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This caveat review batch is advisory and fail-closed. "
                "It organizes caveated rows for recheck sequencing, but it does not "
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
        description="Export the external-dataset caveat review batch preview."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_external_dataset_caveat_review_batch_preview(
        _load_payload(DEFAULT_CAVEAT_EXIT_CRITERIA_PREVIEW),
        _load_payload(DEFAULT_ADVISORY_FOLLOWUP_REGISTER_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
