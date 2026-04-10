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
DEFAULT_UNLOCK_ROUTE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unlock_route_preview.json"
)
DEFAULT_REMEDIATION_PLAN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_remediation_plan_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_source_fix_batch_preview.json"
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


def build_training_set_source_fix_batch_preview(
    transition_contract_preview: dict[str, Any],
    unlock_route_preview: dict[str, Any],
    remediation_plan_preview: dict[str, Any],
) -> dict[str, Any]:
    transition_rows = transition_contract_preview.get("rows") or []
    unlock_rows = unlock_route_preview.get("rows") or []
    remediation_rows = remediation_plan_preview.get("rows") or []

    unlock_by_accession = _rows_by_accession(unlock_rows)
    remediation_by_accession = _rows_by_accession(remediation_rows)

    rows: list[dict[str, Any]] = []
    source_fix_ref_counts: Counter[str] = Counter()
    route_state_counts: Counter[str] = Counter()
    issue_bucket_counts: Counter[str] = Counter()
    missing_modality_counts: Counter[str] = Counter()

    for transition_row in transition_rows:
        if not isinstance(transition_row, dict):
            continue
        if str(transition_row.get("current_transition_state") or "").strip() != (
            "source_fix_transition_pending"
        ):
            continue

        accession = str(transition_row.get("accession") or "").strip()
        if not accession:
            continue

        unlock_row = unlock_by_accession.get(accession, {})
        remediation_row = remediation_by_accession.get(accession, {})

        source_fix_refs = _listify(transition_row.get("source_fix_refs"))
        missing_modalities = _listify(remediation_row.get("missing_modalities"))
        issue_buckets = _listify(remediation_row.get("issue_buckets"))
        route_steps = _listify(unlock_row.get("route_steps"))
        recommended_actions = _listify(remediation_row.get("recommended_actions"))

        lead_source_fix_ref = source_fix_refs[0] if source_fix_refs else None
        route_state = str(transition_row.get("route_state") or "").strip()
        route_state_counts[route_state] += 1
        for source_fix_ref in source_fix_refs:
            source_fix_ref_counts[source_fix_ref] += 1
        for issue_bucket in issue_buckets:
            issue_bucket_counts[issue_bucket] += 1
        for modality in missing_modalities:
            missing_modality_counts[modality] += 1

        rows.append(
            {
                "accession": accession,
                "source_fix_batch_state": "source_fix_transition_pending",
                "route_state": route_state,
                "training_set_state": transition_row.get("training_set_state"),
                "split": transition_row.get("split"),
                "bucket": transition_row.get("bucket"),
                "lead_source_fix_ref": lead_source_fix_ref,
                "source_fix_ref_count": len(source_fix_refs),
                "source_fix_refs": source_fix_refs,
                "issue_buckets": issue_buckets,
                "missing_modalities": missing_modalities,
                "route_steps": route_steps,
                "recommended_actions": recommended_actions,
                "next_source_fix_action": transition_row.get("next_transition")
                or unlock_row.get("next_step")
                or "clear_source_fix_route",
                "supporting_artifacts": _listify(
                    transition_row.get("supporting_artifacts")
                )
                or _listify(unlock_row.get("supporting_artifacts"))
                or [
                    "training_set_transition_contract_preview",
                    "training_set_unlock_route_preview",
                    "training_set_remediation_plan_preview",
                ],
            }
        )

    rows.sort(
        key=lambda row: (
            0
            if str(row.get("training_set_state") or "") == "blocked_pending_acquisition"
            else 1,
            str(row.get("accession") or "").casefold(),
        )
    )

    next_source_fix_batch = (
        rows[0]["lead_source_fix_ref"] if rows and rows[0].get("lead_source_fix_ref") else None
    )

    return {
        "artifact_id": "training_set_source_fix_batch_preview",
        "schema_id": "proteosphere-training-set-source-fix-batch-preview-2026-04-03",
        "status": "report_only",
        "generated_at": transition_contract_preview.get("generated_at")
        or unlock_route_preview.get("generated_at")
        or remediation_plan_preview.get("generated_at"),
        "summary": {
            "selected_count": int(
                (transition_contract_preview.get("summary") or {}).get("selected_count") or 0
            ),
            "source_fix_batch_row_count": len(rows),
            "current_batch_state": (
                "blocked_pending_source_fix_batch" if rows else "no_source_fix_batch_required"
            ),
            "next_source_fix_batch": next_source_fix_batch,
            "shared_source_fix_ref_count": len(source_fix_ref_counts),
            "blocked_pending_acquisition_count": route_state_counts.get(
                "blocked_pending_acquisition", 0
            ),
            "preview_visible_source_fix_count": route_state_counts.get(
                "preview_visible_non_governing", 0
            ),
            "governing_ready_source_fix_count": route_state_counts.get(
                "governing_ready_but_package_blocked", 0
            ),
            "top_source_fix_refs": [
                {"source_fix_ref": item, "accession_count": count}
                for item, count in source_fix_ref_counts.most_common(8)
            ],
            "top_issue_buckets": [
                {"issue_bucket": item, "accession_count": count}
                for item, count in issue_bucket_counts.most_common(8)
            ],
            "top_missing_modalities": [
                {"modality": item, "accession_count": count}
                for item, count in missing_modality_counts.most_common(8)
            ],
            "fail_closed": True,
            "non_mutating": True,
        },
        "rows": rows,
        "source_artifacts": {
            "training_set_transition_contract_preview": str(
                DEFAULT_TRANSITION_CONTRACT_PREVIEW
            ).replace("\\", "/"),
            "training_set_unlock_route_preview": str(
                DEFAULT_UNLOCK_ROUTE_PREVIEW
            ).replace("\\", "/"),
            "training_set_remediation_plan_preview": str(
                DEFAULT_REMEDIATION_PLAN_PREVIEW
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This source-fix batch preview is report-only and fail-closed. "
                "It groups the current source-fix-pending accessions for operator follow-up, "
                "but it does not clear blockers or authorize packaging."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "package_not_authorized": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the training-set source-fix batch preview."
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
    payload = build_training_set_source_fix_batch_preview(
        _load_payload(DEFAULT_TRANSITION_CONTRACT_PREVIEW),
        _load_payload(DEFAULT_UNLOCK_ROUTE_PREVIEW),
        _load_payload(DEFAULT_REMEDIATION_PLAN_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
