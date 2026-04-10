from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from external_dataset_assessment_support import read_json, write_json  # noqa: E402

DEFAULT_ASSESSMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_assessment_preview.json"
)
DEFAULT_ADMISSION_DECISION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_admission_decision_preview.json"
)
DEFAULT_ACCEPTANCE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json"
)
DEFAULT_RESOLUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)
DEFAULT_CONFLICT_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_conflict_register_preview.json"
)
DEFAULT_FLAW_TAXONOMY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_flaw_taxonomy_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_clearance_delta_preview.json"
)

VERDICT_RANK = {
    "blocked_pending_cleanup": 5,
    "blocked_pending_mapping": 4,
    "blocked_pending_acquisition": 3,
    "unsafe_for_training": 2,
    "audit_only": 1,
    "usable_with_caveats": 0,
}


def _load_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


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


def _ordered_unique(*values: Any) -> list[str]:
    normalized: dict[str, str] = {}
    for value in values:
        for text in _listify(value):
            normalized.setdefault(text.casefold(), text)
    return list(normalized.values())


def _summary_int(summary: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = summary.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return 0


def _rank_verdict(verdict: str) -> int:
    return VERDICT_RANK.get(verdict, -1)


def _worst_verdict(*verdicts: str) -> str:
    ranked = [verdict for verdict in verdicts if verdict]
    if not ranked:
        return "audit_only"
    return max(ranked, key=_rank_verdict)


def _payload_id(payload: dict[str, Any], fallback: str) -> str:
    return str(payload.get("artifact_id") or fallback).strip()


def _remediation_text(value: Any) -> list[str]:
    remediations: list[str] = []
    for text in _listify(value):
        remediations.append(text)
    return remediations


def _source_rows(
    *,
    assessment_summary: dict[str, Any],
    admission_summary: dict[str, Any],
    acceptance_summary: dict[str, Any],
    resolution_summary: dict[str, Any],
    conflict_summary: dict[str, Any],
    flaw_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "source": "assessment",
            "artifact_id": "",
            "verdict": str(assessment_summary.get("overall_verdict") or "").strip(),
            "delta_state": "advisory_only" if assessment_summary else "missing",
            "impacted_accession_count": _summary_int(
                assessment_summary,
                "dataset_accession_count",
            ),
            "required_changes": [],
            "evidence": {
                "missing_mapping_accession_count": _summary_int(
                    assessment_summary,
                    "missing_mapping_accession_count",
                ),
                "candidate_only_accession_count": _summary_int(
                    assessment_summary,
                    "candidate_only_accession_count",
                ),
                "measured_accession_count": _summary_int(
                    assessment_summary,
                    "measured_accession_count",
                ),
                "seed_structure_overlap_accession_count": _summary_int(
                    assessment_summary,
                    "seed_structure_overlap_accession_count",
                ),
            },
        },
        {
            "source": "admission",
            "artifact_id": "",
            "verdict": str(admission_summary.get("overall_verdict") or "").strip(),
            "delta_state": (
                str(admission_summary.get("overall_decision") or "").strip() or "blocked"
            ),
            "impacted_accession_count": _summary_int(
                admission_summary,
                "dataset_accession_count",
            ),
            "required_changes": _ordered_unique(
                admission_summary.get("top_required_remediations"),
                admission_summary.get("decision_reasons"),
            ),
            "evidence": {
                "blocking_gate_count": _summary_int(
                    admission_summary,
                    "blocking_gate_count",
                    "blocked_gate_count",
                ),
                "advisory_only": bool(admission_summary.get("advisory_only")),
            },
        },
        {
            "source": "acceptance",
            "artifact_id": "",
            "verdict": str(acceptance_summary.get("overall_gate_verdict") or "").strip(),
            "delta_state": (
                "blocked"
                if _summary_int(acceptance_summary, "blocked_gate_count") > 0
                or str(acceptance_summary.get("overall_gate_verdict") or "").startswith("blocked")
                else "advisory_only"
            ),
            "impacted_accession_count": _summary_int(
                acceptance_summary,
                "dataset_accession_count",
            ),
            "required_changes": _ordered_unique(
                acceptance_summary.get("top_remediation_categories"),
                acceptance_summary.get("training_safe_acceptance"),
            ),
            "evidence": {
                "blocked_gate_count": _summary_int(
                    acceptance_summary,
                    "blocked_gate_count",
                ),
                "usable_with_caveats_gate_count": _summary_int(
                    acceptance_summary,
                    "usable_with_caveats_gate_count",
                ),
            },
        },
        {
            "source": "resolution",
            "artifact_id": "",
            "verdict": str(resolution_summary.get("overall_resolution_verdict") or "").strip(),
            "delta_state": (
                "blocked"
                if str(resolution_summary.get("overall_resolution_verdict") or "").startswith(
                    "blocked"
                )
                else "advisory_only"
            ),
            "impacted_accession_count": _summary_int(
                resolution_summary,
                "dataset_accession_count",
            ),
            "required_changes": _ordered_unique(
                resolution_summary.get("top_blocking_gates"),
                resolution_summary.get("top_issue_categories"),
            ),
            "evidence": {
                "blocked_accession_count": _summary_int(
                    resolution_summary,
                    "blocked_accession_count",
                ),
                "mapping_incomplete_accession_count": _summary_int(
                    resolution_summary,
                    "mapping_incomplete_accession_count",
                ),
            },
        },
        {
            "source": "conflict",
            "artifact_id": "",
            "verdict": str(conflict_summary.get("overall_verdict") or "").strip(),
            "delta_state": (
                "blocked"
                if str(conflict_summary.get("overall_verdict") or "").startswith("blocked")
                else "advisory_only"
            ),
            "impacted_accession_count": _summary_int(
                conflict_summary,
                "dataset_accession_count",
            ),
            "required_changes": _ordered_unique(
                conflict_summary.get("top_conflict_rows"),
                conflict_summary.get("top_conflict_categories"),
            ),
            "evidence": {
                "blocked_gate_count": _summary_int(
                    conflict_summary,
                    "blocked_gate_count",
                ),
                "mapping_conflict_present": bool(conflict_summary.get("mapping_conflict_present")),
                "provenance_conflict_present": bool(
                    conflict_summary.get("provenance_conflict_present")
                ),
            },
        },
        {
            "source": "flaw",
            "artifact_id": "",
            "verdict": str(flaw_summary.get("overall_verdict") or "").strip(),
            "delta_state": (
                "blocked"
                if str(flaw_summary.get("overall_verdict") or "").startswith("blocked")
                else "advisory_only"
            ),
            "impacted_accession_count": _summary_int(
                flaw_summary,
                "dataset_accession_count",
            ),
            "required_changes": _ordered_unique(
                flaw_summary.get("top_blocking_categories"),
                flaw_summary.get("remediation_priority_categories"),
            ),
            "evidence": {
                "blocked_accession_count": _summary_int(
                    flaw_summary,
                    "blocked_accession_count",
                ),
                "blocking_category_counts": dict(
                    flaw_summary.get("blocking_category_counts") or {}
                ),
                "missing_required_field_count": _summary_int(
                    flaw_summary,
                    "missing_required_field_count",
                ),
            },
        },
    ]


def build_external_dataset_clearance_delta_preview(
    assessment_preview: dict[str, Any],
    admission_decision_preview: dict[str, Any],
    acceptance_gate_preview: dict[str, Any],
    resolution_preview: dict[str, Any],
    conflict_register_preview: dict[str, Any],
    flaw_taxonomy_preview: dict[str, Any],
) -> dict[str, Any]:
    assessment_summary = dict(assessment_preview.get("summary") or {})
    admission_summary = dict(admission_decision_preview.get("summary") or {})
    acceptance_summary = dict(acceptance_gate_preview.get("summary") or {})
    resolution_summary = dict(resolution_preview.get("summary") or {})
    conflict_summary = dict(conflict_register_preview.get("summary") or {})
    flaw_summary = dict(flaw_taxonomy_preview.get("summary") or {})

    source_artifacts = {
        "assessment_preview": _payload_id(
            assessment_preview, "external_dataset_assessment_preview"
        ),
        "admission_decision_preview": _payload_id(
            admission_decision_preview, "external_dataset_admission_decision_preview"
        ),
        "acceptance_gate_preview": _payload_id(
            acceptance_gate_preview, "external_dataset_acceptance_gate_preview"
        ),
        "resolution_preview": _payload_id(
            resolution_preview, "external_dataset_resolution_preview"
        ),
        "conflict_register_preview": _payload_id(
            conflict_register_preview, "external_dataset_conflict_register_preview"
        ),
        "flaw_taxonomy_preview": _payload_id(
            flaw_taxonomy_preview, "external_dataset_flaw_taxonomy_preview"
        ),
    }
    missing_inputs = sorted(
        name for name, artifact_id in source_artifacts.items() if not str(artifact_id or "").strip()
    )

    dataset_accession_count = 0
    for summary in (
        assessment_summary,
        admission_summary,
        acceptance_summary,
        resolution_summary,
        conflict_summary,
        flaw_summary,
    ):
        dataset_accession_count = _summary_int(summary, "dataset_accession_count")
        if dataset_accession_count:
            break

    blocking_gate_count = max(
        _summary_int(admission_summary, "blocking_gate_count", "blocked_gate_count"),
        _summary_int(acceptance_summary, "blocked_gate_count"),
        _summary_int(resolution_summary, "blocked_gate_count"),
        _summary_int(conflict_summary, "blocked_gate_count"),
    )
    if missing_inputs:
        blocking_gate_count = max(blocking_gate_count, 1)

    current_clearance_verdict = _worst_verdict(
        str(assessment_summary.get("overall_verdict") or ""),
        str(admission_summary.get("overall_verdict") or ""),
        str(acceptance_summary.get("overall_gate_verdict") or ""),
        str(resolution_summary.get("overall_resolution_verdict") or ""),
        str(conflict_summary.get("overall_verdict") or ""),
        str(flaw_summary.get("overall_verdict") or ""),
    )
    if missing_inputs:
        current_clearance_verdict = _worst_verdict(
            current_clearance_verdict,
            "blocked_pending_mapping",
        )

    source_rows = _source_rows(
        assessment_summary=assessment_summary,
        admission_summary=admission_summary,
        acceptance_summary=acceptance_summary,
        resolution_summary=resolution_summary,
        conflict_summary=conflict_summary,
        flaw_summary=flaw_summary,
    )

    required_changes = _ordered_unique(
        admission_summary.get("top_required_remediations"),
        acceptance_summary.get("top_remediation_categories"),
        resolution_summary.get("top_blocking_gates"),
        resolution_summary.get("top_issue_categories"),
        conflict_summary.get("top_conflict_rows"),
        conflict_summary.get("top_conflict_categories"),
        flaw_summary.get("top_blocking_categories"),
        flaw_summary.get("remediation_priority_categories"),
    )
    if missing_inputs:
        required_changes = _ordered_unique(
            "restore missing source artifacts before clearance can be judged",
            required_changes,
        )
    if not required_changes:
        required_changes = [
            "review source artifacts before accepting the dataset",
        ]

    source_priority_rows = sorted(
        source_rows,
        key=lambda row: (
            -_rank_verdict(str(row.get("verdict") or "")),
            0 if str(row.get("delta_state") or "") == "blocked" else 1,
            -int(row.get("impacted_accession_count") or 0),
            str(row.get("source") or "").casefold(),
        ),
    )

    current_clearance_state = "advisory_only"
    if blocking_gate_count or current_clearance_verdict.startswith("blocked") or missing_inputs:
        current_clearance_state = "blocked"

    top_delta_rows = []
    for row in source_priority_rows:
        changes = row.get("required_changes") or []
        top_delta_rows.append(
            {
                "source": row["source"],
                "verdict": row["verdict"],
                "delta_state": row["delta_state"],
                "impacted_accession_count": row["impacted_accession_count"],
                "required_changes": changes[:4],
                "evidence": row["evidence"],
            }
        )

    clearance_priority = [
        {
            "source": row["source"],
            "delta_state": row["delta_state"],
            "required_change_count": len(row.get("required_changes") or []),
            "impacted_accession_count": row["impacted_accession_count"],
        }
        for row in source_priority_rows
        if row.get("delta_state") == "blocked" or row.get("required_changes")
    ]

    return {
        "artifact_id": "external_dataset_clearance_delta_preview",
        "schema_id": "proteosphere-external-dataset-clearance-delta-preview-2026-04-03",
        "status": "report_only",
        "generated_at": (
            assessment_preview.get("generated_at")
            or admission_decision_preview.get("generated_at")
            or acceptance_gate_preview.get("generated_at")
            or resolution_preview.get("generated_at")
            or conflict_register_preview.get("generated_at")
            or flaw_taxonomy_preview.get("generated_at")
            or ""
        ),
        "summary": {
            "dataset_accession_count": dataset_accession_count,
            "current_clearance_state": current_clearance_state,
            "current_clearance_verdict": current_clearance_verdict,
            "blocking_gate_count": blocking_gate_count,
            "required_change_count": len(required_changes),
            "required_changes": required_changes[:12],
            "clearance_priority": clearance_priority[:6],
            "advisory_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
        "clearance_delta_rows": top_delta_rows,
        "source_artifacts": source_artifacts,
        "truth_boundary": {
            "summary": (
                "This clearance delta preview is advisory and fail-closed. It compacts "
                "existing external-assessment, admission, acceptance, resolution, conflict, "
                "and flaw previews without mutating source truth or implying training-safe "
                "acceptance."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export an advisory external dataset clearance delta preview."
    )
    parser.add_argument("--assessment-preview", type=Path, default=DEFAULT_ASSESSMENT_PREVIEW)
    parser.add_argument(
        "--admission-decision-preview",
        type=Path,
        default=DEFAULT_ADMISSION_DECISION_PREVIEW,
    )
    parser.add_argument(
        "--acceptance-gate-preview",
        type=Path,
        default=DEFAULT_ACCEPTANCE_GATE_PREVIEW,
    )
    parser.add_argument("--resolution-preview", type=Path, default=DEFAULT_RESOLUTION_PREVIEW)
    parser.add_argument(
        "--conflict-register-preview",
        type=Path,
        default=DEFAULT_CONFLICT_REGISTER_PREVIEW,
    )
    parser.add_argument("--flaw-taxonomy-preview", type=Path, default=DEFAULT_FLAW_TAXONOMY_PREVIEW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_external_dataset_clearance_delta_preview(
        _load_payload(args.assessment_preview),
        _load_payload(args.admission_decision_preview),
        _load_payload(args.acceptance_gate_preview),
        _load_payload(args.resolution_preview),
        _load_payload(args.conflict_register_preview),
        _load_payload(args.flaw_taxonomy_preview),
    )
    write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
