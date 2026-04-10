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

DEFAULT_ADVISORY_FOLLOWUP_REGISTER_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "external_dataset_advisory_followup_register_preview.json"
)
DEFAULT_ACCEPTANCE_PATH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_path_preview.json"
)
DEFAULT_RESOLUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)
DEFAULT_ACCEPTANCE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "external_dataset_caveat_exit_criteria_preview.json"
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


def build_external_dataset_caveat_exit_criteria_preview(
    advisory_followup_register_preview: dict[str, Any],
    acceptance_path_preview: dict[str, Any],
    resolution_preview: dict[str, Any],
    acceptance_gate_preview: dict[str, Any],
) -> dict[str, Any]:
    advisory_rows = advisory_followup_register_preview.get("rows") or []
    acceptance_rows = acceptance_path_preview.get("rows") or []
    resolution_rows = resolution_preview.get("accession_resolution_rows") or []
    gate_reports = acceptance_gate_preview.get("gate_reports") or []

    acceptance_by_accession = _rows_by_accession(acceptance_rows)
    resolution_by_accession = _rows_by_accession(resolution_rows)

    global_gate_clear_conditions = _listify(
        [
            item.get("clear_condition")
            for item in (
                (acceptance_gate_preview.get("summary") or {}).get(
                    "training_safe_acceptance"
                )
                or {}
            ).get("must_clear", [])
            if isinstance(item, dict)
        ]
    )
    global_gate_clear_conditions.extend(
        _listify(
            [
                report.get("remediation_action")
                for report in gate_reports
                if isinstance(report, dict)
            ]
        )
    )
    global_gate_clear_conditions = _listify(global_gate_clear_conditions)

    rows: list[dict[str, Any]] = []
    state_counts: Counter[str] = Counter()
    criterion_counts: Counter[str] = Counter()
    allowed_counts: Counter[str] = Counter()

    for advisory_row in advisory_rows:
        if not isinstance(advisory_row, dict):
            continue
        accession = str(advisory_row.get("accession") or "").strip()
        if not accession:
            continue

        acceptance_row = acceptance_by_accession.get(accession, {})
        resolution_row = resolution_by_accession.get(accession, {})
        remediation_actions = _listify(
            advisory_row.get("remediation_actions")
            or acceptance_row.get("remediation_actions")
            or resolution_row.get("remediation_actions")
        )
        blocking_gates = _listify(
            acceptance_row.get("blocking_gates") or resolution_row.get("blocking_gates")
        )
        clear_conditions = remediation_actions + global_gate_clear_conditions
        for gate in blocking_gates:
            clear_conditions.append(f"{gate} blocking gate must clear")
        clear_conditions = _listify(clear_conditions)

        followup_lane = str(advisory_row.get("followup_lane") or "").strip()
        if followup_lane == "structure_alignment_advisory_follow_up":
            exit_state = "caveated_pending_structure_alignment_review"
            allowed_current_use = "advisory_only_structure_context"
            next_review_action = "recheck PDB-to-UniProt alignment and adjacent-context separation"
            prohibited_uses = [
                "training-safe acceptance",
                "direct structure grounding claim",
                "governing promotion from adjacent context",
            ]
        else:
            exit_state = "caveated_pending_binding_provenance_review"
            allowed_current_use = "advisory_only_binding_support_context"
            next_review_action = "recheck binding and provenance caveats before any escalation"
            prohibited_uses = [
                "training-safe acceptance",
                "binding-governing promotion",
                "provenance collapse across mixed trust tiers",
            ]

        state_counts[exit_state] += 1
        allowed_counts[allowed_current_use] += 1
        for criterion in clear_conditions:
            criterion_counts[criterion] += 1

        rows.append(
            {
                "accession": accession,
                "advisory_followup_state": advisory_row.get("advisory_followup_state"),
                "followup_lane": followup_lane,
                "resolution_state": resolution_row.get("resolution_state")
                or advisory_row.get("resolution_state"),
                "acceptance_path_state": acceptance_row.get("acceptance_path_state")
                or advisory_row.get("acceptance_path_state"),
                "caveat_exit_state": exit_state,
                "allowed_current_use": allowed_current_use,
                "prohibited_uses": prohibited_uses,
                "blocking_gates": blocking_gates,
                "issue_categories": _listify(
                    advisory_row.get("issue_categories")
                    or acceptance_row.get("issue_categories")
                    or resolution_row.get("issue_categories")
                ),
                "exit_criteria": clear_conditions,
                "clear_when_true": clear_conditions,
                "next_review_action": next_review_action,
                "priority_bucket": advisory_row.get("priority_bucket")
                or acceptance_row.get("priority_bucket"),
                "supporting_artifacts": _listify(advisory_row.get("supporting_artifacts"))
                or [
                    "external_dataset_advisory_followup_register_preview",
                    "external_dataset_acceptance_path_preview",
                    "external_dataset_resolution_preview",
                    "external_dataset_acceptance_gate_preview",
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

    return {
        "artifact_id": "external_dataset_caveat_exit_criteria_preview",
        "schema_id": "proteosphere-external-dataset-caveat-exit-criteria-preview-2026-04-03",
        "status": "report_only",
        "generated_at": advisory_followup_register_preview.get("generated_at")
        or acceptance_path_preview.get("generated_at")
        or resolution_preview.get("generated_at")
        or acceptance_gate_preview.get("generated_at"),
        "summary": {
            "dataset_accession_count": int(
                (advisory_followup_register_preview.get("summary") or {}).get(
                    "dataset_accession_count"
                )
                or 0
            ),
            "caveat_exit_row_count": len(rows),
            "current_exit_state": (
                "caveat_exit_criteria_active"
                if rows
                else "no_caveat_exit_criteria_rows"
            ),
            "structure_alignment_exit_count": state_counts.get(
                "caveated_pending_structure_alignment_review", 0
            ),
            "binding_provenance_exit_count": state_counts.get(
                "caveated_pending_binding_provenance_review", 0
            ),
            "allowed_current_use_counts": [
                {"allowed_current_use": item, "accession_count": count}
                for item, count in allowed_counts.most_common(8)
            ],
            "top_exit_criteria": [
                {"exit_criterion": item, "accession_count": count}
                for item, count in criterion_counts.most_common(8)
            ],
            "advisory_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
        "rows": rows,
        "source_artifacts": {
            "external_dataset_advisory_followup_register_preview": str(
                DEFAULT_ADVISORY_FOLLOWUP_REGISTER_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_acceptance_path_preview": str(
                DEFAULT_ACCEPTANCE_PATH_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_resolution_preview": str(
                DEFAULT_RESOLUTION_PREVIEW
            ).replace("\\", "/"),
            "external_dataset_acceptance_gate_preview": str(
                DEFAULT_ACCEPTANCE_GATE_PREVIEW
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This caveat exit-criteria preview is advisory and fail-closed. "
                "It makes caveat-clearance conditions explicit, but it does not admit "
                "the dataset for training."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
            "training_safe_acceptance_not_implied": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the external-dataset caveat exit criteria preview."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_external_dataset_caveat_exit_criteria_preview(
        _load_payload(DEFAULT_ADVISORY_FOLLOWUP_REGISTER_PREVIEW),
        _load_payload(DEFAULT_ACCEPTANCE_PATH_PREVIEW),
        _load_payload(DEFAULT_RESOLUTION_PREVIEW),
        _load_payload(DEFAULT_ACCEPTANCE_GATE_PREVIEW),
    )
    write_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
