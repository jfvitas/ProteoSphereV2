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
DEFAULT_REMEDIATION_QUEUE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_remediation_queue_preview.json"
)
DEFAULT_RESOLUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)
DEFAULT_ACCEPTANCE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json"
)
DEFAULT_MANIFEST_LINT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_manifest_lint_preview.json"
)
DEFAULT_BINDING_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_binding_audit_preview.json"
)
DEFAULT_STRUCTURE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_structure_audit_preview.json"
)
DEFAULT_PROVENANCE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_provenance_audit_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_flaw_taxonomy_preview.json"
)

VERDICT_RANK = {
    "blocked_pending_cleanup": 4,
    "blocked_pending_mapping": 3,
    "blocked_pending_acquisition": 2,
    "audit_only": 1,
    "usable_with_caveats": 0,
}


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


def _sorted_unique(*values: Any) -> list[str]:
    normalized: dict[str, str] = {}
    for value in values:
        for text in _listify(value):
            normalized.setdefault(text.casefold(), text)
    return sorted(normalized.values(), key=str.casefold)


def _rank_verdict(verdict: str) -> int:
    return VERDICT_RANK.get(verdict, -1)


def _worst_verdict(*verdicts: str) -> str:
    ranked = [verdict for verdict in verdicts if verdict]
    if not ranked:
        return "audit_only"
    return max(ranked, key=_rank_verdict)


def _category_name(report: dict[str, Any]) -> str:
    return str(report.get("category") or report.get("issue_category") or "").strip()


def _count_from_report(report: dict[str, Any]) -> int:
    for key in (
        "affected_accession_count",
        "queue_row_count",
        "issue_row_count",
        "count",
    ):
        value = report.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    if isinstance(report.get("affected_accessions"), list):
        return len(report["affected_accessions"])
    return 0


def _load_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _category_reports(resolution_preview: dict[str, Any]) -> list[dict[str, Any]]:
    summary = dict(resolution_preview.get("summary") or {})
    reports = [
        dict(report)
        for report in (summary.get("top_issue_categories") or [])
        if isinstance(report, dict)
    ]
    if reports:
        return reports
    rows = [
        dict(row)
        for row in (resolution_preview.get("issue_resolution_rows") or [])
        if isinstance(row, dict)
    ]
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        category = str(row.get("issue_category") or "").strip()
        if not category:
            continue
        entry = grouped.setdefault(
            category,
            {
                "issue_category": category,
                "affected_accession_count": 0,
                "resolution_state": row.get("resolution_state") or "caveated",
                "worst_verdict": row.get("worst_verdict") or "usable_with_caveats",
                "remediation_action": None,
            },
        )
        entry["affected_accession_count"] += len(_sorted_unique(row.get("affected_accessions")))
        entry["worst_verdict"] = _worst_verdict(
            str(entry.get("worst_verdict") or ""),
            str(row.get("worst_verdict") or ""),
        )
        if row.get("remediation_actions"):
            entry["remediation_action"] = _sorted_unique(
                entry.get("remediation_action"), row.get("remediation_actions")
            )[0]
    return list(grouped.values())


def _acceptance_gate_failures(acceptance_gate_preview: dict[str, Any]) -> list[dict[str, Any]]:
    summary = dict(acceptance_gate_preview.get("summary") or {})
    failures: list[dict[str, Any]] = []
    for gate in acceptance_gate_preview.get("gate_reports") or []:
        if not isinstance(gate, dict):
            continue
        verdict = str(gate.get("verdict") or "").strip()
        if verdict.startswith("blocked"):
            failures.append(
                {
                    "gate_name": gate.get("gate_name"),
                    "verdict": verdict,
                    "impacted_accession_count": int(
                        (gate.get("impact") or {}).get("impacted_accession_count") or 0
                    ),
                }
            )
    if failures:
        return failures
    for gate in summary.get("must_clear") or []:
        if isinstance(gate, dict) and str(gate.get("verdict") or "").startswith("blocked"):
            failures.append(
                {
                    "gate_name": gate.get("gate_name"),
                    "verdict": gate.get("verdict"),
                    "impacted_accession_count": int(gate.get("impacted_accession_count") or 0),
                }
            )
    return failures


def _normalize_category_row(
    report: dict[str, Any],
    *,
    blocking_actions: dict[str, str],
) -> dict[str, Any]:
    category = _category_name(report)
    resolution_state = str(report.get("resolution_state") or "caveated").strip()
    worst_verdict = str(report.get("worst_verdict") or "").strip()
    if resolution_state == "blocked":
        worst_verdict = "blocked_pending_acquisition"
    elif not worst_verdict:
        worst_verdict = "usable_with_caveats"

    remediation_action = str(report.get("remediation_action") or "").strip()
    if not remediation_action:
        remediation_action = blocking_actions.get(category) or "review manually before training"

    return {
        "category": category,
        "affected_accession_count": _count_from_report(report),
        "resolution_state": resolution_state,
        "worst_verdict": worst_verdict,
        "remediation_action": remediation_action,
    }


def build_external_dataset_flaw_taxonomy_preview(
    assessment_preview: dict[str, Any],
    remediation_queue_preview: dict[str, Any],
    resolution_preview: dict[str, Any],
    acceptance_gate_preview: dict[str, Any],
    manifest_lint_preview: dict[str, Any],
    binding_audit_preview: dict[str, Any],
    structure_audit_preview: dict[str, Any],
    provenance_audit_preview: dict[str, Any],
) -> dict[str, Any]:
    assessment_summary = dict(assessment_preview.get("summary") or {})
    remediation_summary = dict(remediation_queue_preview.get("summary") or {})
    resolution_summary = dict(resolution_preview.get("summary") or {})
    acceptance_summary = dict(acceptance_gate_preview.get("summary") or {})
    lint_summary = dict(manifest_lint_preview.get("summary") or {})
    binding_summary = dict(binding_audit_preview.get("summary") or {})
    structure_summary = dict(structure_audit_preview.get("summary") or {})
    provenance_summary = dict(provenance_audit_preview.get("summary") or {})

    category_reports = _category_reports(resolution_preview)
    blocking_actions = {
        str(gate.get("gate_name") or "").strip(): str(gate.get("remediation_action") or "").strip()
        for gate in (resolution_summary.get("top_blocking_gates") or [])
        if isinstance(gate, dict)
        and str(gate.get("gate_name") or "").strip()
        and str(gate.get("remediation_action") or "").strip()
    }
    blocking_categories = [
        report
        for report in category_reports
        if str(report.get("resolution_state") or "").strip() == "blocked"
    ]
    resolved_categories = [
        report
        for report in category_reports
        if str(report.get("resolution_state") or "").strip() in {"caveated", "resolved"}
    ]
    category_counts = {
        _category_name(report): _count_from_report(report) for report in category_reports
    }
    blocking_category_counts = {
        _category_name(report): _count_from_report(report) for report in blocking_categories
    }
    resolved_category_counts = {
        _category_name(report): _count_from_report(report) for report in resolved_categories
    }

    top_blocking_categories = sorted(
        (
            _normalize_category_row(report, blocking_actions=blocking_actions)
            for report in blocking_categories
        ),
        key=lambda item: (
            -item["affected_accession_count"],
            str(item["category"] or "").casefold(),
        ),
    )

    lint_failures_present = bool(lint_summary.get("missing_required_field_count") or 0) > 0
    lint_failures_present = lint_failures_present or bool(
        lint_summary.get("missing_required_top_level_field_count") or 0
    )
    lint_failures_present = lint_failures_present or bool(
        lint_summary.get("missing_required_row_field_count") or 0
    )
    lint_failures_present = lint_failures_present or any(
        str(report.get("verdict") or "") == "unsafe_for_training"
        for report in (manifest_lint_preview.get("per_shape_verdicts") or [])
        if isinstance(report, dict)
    )

    source_artifacts = {
        "assessment_preview": assessment_preview.get("artifact_id") or "",
        "remediation_queue_preview": remediation_queue_preview.get("artifact_id") or "",
        "resolution_preview": resolution_preview.get("artifact_id") or "",
        "acceptance_gate_preview": acceptance_gate_preview.get("artifact_id") or "",
        "manifest_lint_preview": manifest_lint_preview.get("artifact_id") or "",
        "binding_audit_preview": binding_audit_preview.get("artifact_id") or "",
        "structure_audit_preview": structure_audit_preview.get("artifact_id") or "",
        "provenance_audit_preview": provenance_audit_preview.get("artifact_id") or "",
    }

    missing_inputs = sorted(
        [
            name
            for name, artifact_id in source_artifacts.items()
            if not str(artifact_id or "").strip()
        ],
        key=str.casefold,
    )

    worst_verdict = _worst_verdict(
        str(assessment_summary.get("overall_verdict") or ""),
        str(remediation_summary.get("overall_queue_verdict") or ""),
        str(resolution_summary.get("overall_resolution_verdict") or ""),
        str(acceptance_summary.get("overall_gate_verdict") or ""),
        "blocked_pending_mapping" if missing_inputs else "",
        *(
            str(report.get("worst_verdict") or "")
            for report in category_reports
            if isinstance(report, dict)
        ),
    )

    if missing_inputs:
        worst_verdict = _worst_verdict(worst_verdict, "blocked_pending_mapping")

    top_blocking_category_rows = [
        {
            "category": item["category"],
            "affected_accession_count": item["affected_accession_count"],
            "resolution_state": item["resolution_state"],
            "worst_verdict": item["worst_verdict"],
            "remediation_action": item["remediation_action"],
        }
        for item in top_blocking_categories
    ]

    remediation_priority_categories = [
        {
            "category": item["category"],
            "affected_accession_count": item["affected_accession_count"],
            "worst_verdict": item["worst_verdict"],
            "remediation_action": item["remediation_action"],
        }
        for item in sorted(
            (
                _normalize_category_row(report, blocking_actions=blocking_actions)
                for report in category_reports
                if isinstance(report, dict)
            ),
            key=lambda item: (
                -_rank_verdict(item["worst_verdict"]),
                -item["affected_accession_count"],
                str(item["category"] or "").casefold(),
            ),
        )
    ]

    summary = {
        "dataset_accession_count": int(assessment_summary.get("dataset_accession_count") or 0),
        "overall_verdict": worst_verdict,
        "worst_verdict": worst_verdict,
        "category_counts": category_counts,
        "blocking_category_counts": blocking_category_counts,
        "resolved_category_counts": resolved_category_counts,
        "top_blocking_categories": top_blocking_category_rows,
        "lint_failures_present": lint_failures_present,
        "non_mutating": True,
        "blocked_accession_count": int(remediation_summary.get("blocked_accession_count") or 0),
        "caveated_accession_count": int(
            resolution_summary.get("caveated_accession_count") or 0
        ),
        "resolved_accession_count": int(
            resolution_summary.get("resolved_accession_count") or 0
        ),
        "blocking_gate_count": int(acceptance_summary.get("blocked_gate_count") or 0),
        "supported_measurement_accession_count": int(
            binding_summary.get("measured_accession_count") or 0
        ),
        "seed_structure_overlap_accession_count": int(
            structure_summary.get("seed_structure_overlap_accession_count") or 0
        ),
        "provenance_row_level_resolution_supported": bool(
            provenance_summary.get("row_level_resolution_supported")
        ),
        "binding_registry_source_count": len(
            dict(provenance_summary.get("binding_registry_source_counts") or {})
        ),
        "missing_required_field_count": int(
            lint_summary.get("missing_required_field_count") or 0
        ),
        "missing_inputs": missing_inputs,
    }

    return {
        "artifact_id": "external_dataset_flaw_taxonomy_preview",
        "schema_id": "proteosphere-external-dataset-flaw-taxonomy-preview-2026-04-03",
        "status": "report_only",
        "generated_at": assessment_preview.get("generated_at")
        or remediation_queue_preview.get("generated_at")
        or resolution_preview.get("generated_at")
        or acceptance_gate_preview.get("generated_at")
        or lint_summary.get("generated_at")
        or binding_audit_preview.get("generated_at")
        or structure_audit_preview.get("generated_at")
        or provenance_audit_preview.get("generated_at")
        or "",
        "summary": summary,
        "category_rows": [
            _normalize_category_row(report, blocking_actions=blocking_actions)
            for report in category_reports
        ],
        "remediation_priority_categories": remediation_priority_categories,
        "source_artifacts": source_artifacts,
        "supporting_artifacts": {
            "assessment_verdict": assessment_summary.get("overall_verdict") or "",
            "remediation_queue_verdict": remediation_summary.get("overall_queue_verdict") or "",
            "resolution_verdict": resolution_summary.get("overall_resolution_verdict") or "",
            "acceptance_gate_verdict": acceptance_summary.get("overall_gate_verdict") or "",
            "manifest_lint_verdict": lint_summary.get("overall_verdict") or "",
            "binding_verdict": binding_audit_preview.get("verdict") or "",
            "structure_verdict": structure_audit_preview.get("verdict") or "",
            "provenance_verdict": provenance_audit_preview.get("verdict") or "",
        },
        "truth_boundary": {
            "summary": (
                "This taxonomy preview is advisory and fail-closed. It only "
                "summarizes existing external-assessment artifacts, does not "
                "mutate source artifacts, and does not imply training-safe acceptance."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a fail-closed external dataset flaw taxonomy preview."
    )
    parser.add_argument("--assessment-preview", type=Path, default=DEFAULT_ASSESSMENT_PREVIEW)
    parser.add_argument(
        "--remediation-queue-preview", type=Path, default=DEFAULT_REMEDIATION_QUEUE_PREVIEW
    )
    parser.add_argument("--resolution-preview", type=Path, default=DEFAULT_RESOLUTION_PREVIEW)
    parser.add_argument(
        "--acceptance-gate-preview", type=Path, default=DEFAULT_ACCEPTANCE_GATE_PREVIEW
    )
    parser.add_argument("--manifest-lint-preview", type=Path, default=DEFAULT_MANIFEST_LINT_PREVIEW)
    parser.add_argument("--binding-audit-preview", type=Path, default=DEFAULT_BINDING_AUDIT_PREVIEW)
    parser.add_argument(
        "--structure-audit-preview", type=Path, default=DEFAULT_STRUCTURE_AUDIT_PREVIEW
    )
    parser.add_argument(
        "--provenance-audit-preview", type=Path, default=DEFAULT_PROVENANCE_AUDIT_PREVIEW
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_external_dataset_flaw_taxonomy_preview(
        _load_payload(args.assessment_preview),
        _load_payload(args.remediation_queue_preview),
        _load_payload(args.resolution_preview),
        _load_payload(args.acceptance_gate_preview),
        _load_payload(args.manifest_lint_preview),
        _load_payload(args.binding_audit_preview),
        _load_payload(args.structure_audit_preview),
        _load_payload(args.provenance_audit_preview),
    )
    write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
