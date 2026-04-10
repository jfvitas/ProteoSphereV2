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

DEFAULT_UNLOCK_ROUTE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unlock_route_preview.json"
)
DEFAULT_GATE_LADDER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_gate_ladder_preview.json"
)
DEFAULT_SPLIT_SIMULATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_simulation_preview.json"
)
DEFAULT_PACKAGE_READINESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
)
DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_package_blocker_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_transition_contract_preview.json"
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


def _contract_step(
    stage: str,
    *,
    status: str,
    clear_condition: str,
    prerequisites: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "status": status,
        "clear_condition": clear_condition,
        "prerequisites": _listify(prerequisites),
    }


def _transition_state(
    route_state: str,
    package_ready: bool,
    package_blockers: list[str],
    source_fix_refs: list[str],
) -> str:
    if package_ready and not package_blockers and not source_fix_refs:
        return "package_transition_ready"
    if route_state == "blocked_pending_acquisition" or source_fix_refs:
        return "source_fix_transition_pending"
    if route_state == "governing_ready_but_package_blocked" or package_blockers:
        return "package_transition_blocked"
    return "preview_transition_hold"


def build_training_set_transition_contract_preview(
    unlock_route_preview: dict[str, Any],
    gate_ladder_preview: dict[str, Any],
    split_simulation_preview: dict[str, Any],
    package_readiness_preview: dict[str, Any],
    package_blocker_matrix_preview: dict[str, Any],
) -> dict[str, Any]:
    unlock_summary = dict(unlock_route_preview.get("summary") or {})
    split_summary = dict(split_simulation_preview.get("summary") or {})
    package_summary = dict(package_readiness_preview.get("summary") or {})

    unlock_rows = unlock_route_preview.get("rows") or []
    gate_rows = gate_ladder_preview.get("rows") or []
    split_rows = split_simulation_preview.get("rows") or []
    blocker_rows = package_blocker_matrix_preview.get("rows") or []

    unlock_by_accession = _rows_by_accession(unlock_rows)
    gate_by_accession = _rows_by_accession(gate_rows)
    split_by_accession = _rows_by_accession(split_rows)
    blocker_by_accession = _rows_by_accession(blocker_rows)
    accessions = _ordered_accessions(unlock_rows, gate_rows, split_rows, blocker_rows)

    contract_steps = [
        _contract_step(
            "accession_remediation",
            status=(
                "blocked"
                if unlock_summary.get("current_unlock_state") != "ready_for_package"
                else "ready"
            ),
            clear_condition="clear source-fix routes and accession blockers",
            prerequisites=[
                "training_set_unlock_route_preview",
                "training_set_gate_ladder_preview",
            ],
        ),
        _contract_step(
            "split_export",
            status=(
                "ready"
                if split_summary.get("dry_run_validation_status") == "aligned"
                and split_summary.get("fold_export_ready")
                and split_summary.get("cv_fold_export_unlocked")
                else "blocked"
            ),
            clear_condition="split dry run aligned and fold export unlocked",
            prerequisites=[
                "split_simulation_preview",
                "training_set_gate_ladder_preview",
            ],
        ),
        _contract_step(
            "package",
            status="ready" if package_summary.get("ready_for_package") else "blocked",
            clear_condition="package readiness explicitly unlocked",
            prerequisites=[
                "package_readiness_preview",
                "training_set_package_blocker_matrix_preview",
            ],
        ),
        _contract_step(
            "release_hold",
            status="preview_only_hold",
            clear_condition="explicit human-triggered package materialization remains required",
            prerequisites=["report_only_phase"],
        ),
    ]

    next_transition_contract = next(
        (step["stage"] for step in contract_steps if step["status"] == "blocked"),
        "release_hold",
    )

    rows: list[dict[str, Any]] = []
    transition_counts: Counter[str] = Counter()
    prerequisite_counts: Counter[str] = Counter()

    package_ready = bool(package_summary.get("ready_for_package"))
    split_ready = (
        split_summary.get("dry_run_validation_status") == "aligned"
        and split_summary.get("fold_export_ready")
        and split_summary.get("cv_fold_export_unlocked")
    )

    for accession in accessions:
        unlock_row = unlock_by_accession.get(accession, {})
        gate_row = gate_by_accession.get(accession, {})
        split_row = split_by_accession.get(accession, {})
        blocker_row = blocker_by_accession.get(accession, {})

        route_state = str(
            unlock_row.get("unlock_route_state") or "preview_visible_non_governing"
        )
        source_fix_refs = _listify(unlock_row.get("source_fix_refs"))
        package_blockers = _listify(blocker_row.get("package_blockers"))

        prerequisites = list(package_blockers)
        prerequisites.extend(source_fix_refs)
        if not split_ready:
            prerequisites.extend(_listify(split_summary.get("package_blocking_factors")))
        prerequisites = _listify(prerequisites)

        current_transition_state = _transition_state(
            route_state,
            package_ready,
            package_blockers,
            source_fix_refs,
        )
        next_transition = (
            "clear_source_fix_route"
            if current_transition_state == "source_fix_transition_pending"
            else "unlock_package_transition"
            if current_transition_state == "package_transition_blocked"
            else "preserve_preview_hold"
        )

        transition_counts[current_transition_state] += 1
        for item in prerequisites:
            prerequisite_counts[item] += 1

        rows.append(
            {
                "accession": accession,
                "current_transition_state": current_transition_state,
                "route_state": route_state,
                "training_set_state": str(
                    gate_row.get("training_set_state")
                    or unlock_row.get("current_training_set_state")
                    or ""
                ),
                "split": split_row.get("split"),
                "bucket": split_row.get("bucket"),
                "next_transition": next_transition,
                "prerequisites": prerequisites,
                "source_fix_refs": source_fix_refs,
                "package_blockers": package_blockers,
                "supporting_artifacts": _listify(unlock_row.get("supporting_artifacts"))
                or [
                    "training_set_unlock_route_preview",
                    "training_set_gate_ladder_preview",
                    "split_simulation_preview",
                    "package_readiness_preview",
                ],
            }
        )

    current_transition_state = (
        "package_transition_ready"
        if package_ready
        else "blocked_pending_transition_contract"
    )

    return {
        "artifact_id": "training_set_transition_contract_preview",
        "schema_id": "proteosphere-training-set-transition-contract-preview-2026-04-03",
        "status": "report_only",
        "generated_at": unlock_route_preview.get("generated_at")
        or gate_ladder_preview.get("generated_at")
        or split_simulation_preview.get("generated_at")
        or package_readiness_preview.get("generated_at"),
        "summary": {
            "selected_count": len(accessions),
            "current_transition_state": current_transition_state,
            "next_transition_contract": next_transition_contract,
            "transition_step_count": len(contract_steps),
            "source_fix_transition_pending_count": transition_counts.get(
                "source_fix_transition_pending", 0
            ),
            "package_transition_blocked_count": transition_counts.get(
                "package_transition_blocked", 0
            ),
            "preview_transition_hold_count": transition_counts.get(
                "preview_transition_hold", 0
            ),
            "package_transition_ready_count": transition_counts.get(
                "package_transition_ready", 0
            ),
            "split_aligned": split_summary.get("dry_run_validation_status") == "aligned",
            "fold_export_ready": split_summary.get("fold_export_ready"),
            "cv_fold_export_unlocked": split_summary.get("cv_fold_export_unlocked"),
            "package_ready": package_ready,
            "top_prerequisites": [
                {"prerequisite": item, "accession_count": count}
                for item, count in prerequisite_counts.most_common(8)
            ],
            "top_transition_states": [
                {"transition_state": item, "accession_count": count}
                for item, count in transition_counts.most_common()
            ],
            "fail_closed": True,
            "non_mutating": True,
        },
        "transition_contract_steps": contract_steps,
        "rows": rows,
        "source_artifacts": {
            "training_set_unlock_route_preview": str(DEFAULT_UNLOCK_ROUTE_PREVIEW).replace(
                "\\", "/"
            ),
            "training_set_gate_ladder_preview": str(DEFAULT_GATE_LADDER_PREVIEW).replace(
                "\\", "/"
            ),
            "split_simulation_preview": str(DEFAULT_SPLIT_SIMULATION_PREVIEW).replace(
                "\\", "/"
            ),
            "package_readiness_preview": str(DEFAULT_PACKAGE_READINESS_PREVIEW).replace(
                "\\", "/"
            ),
            "training_set_package_blocker_matrix_preview": str(
                DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This transition-contract preview is report-only and fail-closed. "
                "It explains the route from accession remediation to package transition, "
                "but it does not unlock packaging or mutate split state."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "package_not_authorized": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the training-set transition-contract preview."
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
    payload = build_training_set_transition_contract_preview(
        _load_payload(DEFAULT_UNLOCK_ROUTE_PREVIEW),
        _load_payload(DEFAULT_GATE_LADDER_PREVIEW),
        _load_payload(DEFAULT_SPLIT_SIMULATION_PREVIEW),
        _load_payload(DEFAULT_PACKAGE_READINESS_PREVIEW),
        _load_payload(DEFAULT_PACKAGE_BLOCKER_MATRIX_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
