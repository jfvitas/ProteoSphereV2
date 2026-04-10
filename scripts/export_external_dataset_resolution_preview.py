from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
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
DEFAULT_ISSUE_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_issue_matrix_preview.json"
)
DEFAULT_ACCEPTANCE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json"
)
DEFAULT_LEAKAGE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_leakage_audit_preview.json"
)
DEFAULT_MODALITY_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_modality_audit_preview.json"
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
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)

BLOCKING_VERDICTS = {
    "blocked_pending_acquisition",
    "blocked_pending_cleanup",
    "blocked_pending_mapping",
    "unsafe_for_training",
}
CAVEATED_VERDICTS = {"usable_with_caveats", "audit_only"}

CATEGORY_ARTIFACTS = {
    "leakage": "external_dataset_leakage_audit_preview",
    "modality": "external_dataset_modality_audit_preview",
    "binding": "external_dataset_binding_audit_preview",
    "structure": "external_dataset_structure_audit_preview",
    "provenance": "external_dataset_provenance_audit_preview",
}

SOURCE_ARTIFACT_FALLBACKS = {
    "assessment_preview": "external_dataset_assessment_preview",
    "issue_matrix_preview": "external_dataset_issue_matrix_preview",
    "acceptance_gate_preview": "external_dataset_acceptance_gate_preview",
    "leakage": "external_dataset_leakage_audit_preview",
    "modality": "external_dataset_modality_audit_preview",
    "binding": "external_dataset_binding_audit_preview",
    "structure": "external_dataset_structure_audit_preview",
    "provenance": "external_dataset_provenance_audit_preview",
}


def _ensure_dict(payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


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
    if verdict in BLOCKING_VERDICTS:
        return 3
    if verdict == "usable_with_caveats":
        return 2
    if verdict == "audit_only":
        return 1
    return 0


def _artifact_id(payload: dict[str, Any], fallback: str) -> str:
    return str(payload.get("artifact_id") or fallback).strip()


def _issue_rows(issue_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows = issue_matrix.get("rows")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def _group_rows_by_accession(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        accession = str(row.get("accession") or "").strip()
        if accession:
            grouped[accession].append(row)
    return grouped


def _group_rows_by_category(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        category = str(row.get("issue_category") or "").strip()
        if category:
            grouped[category].append(row)
    return grouped


def _resolution_state(*, worst_verdict: str, mapping_incomplete: bool, has_rows: bool) -> str:
    if mapping_incomplete:
        return "mapping-incomplete"
    if worst_verdict in BLOCKING_VERDICTS:
        return "blocked"
    if has_rows:
        return "caveated"
    return "resolved"


def _supporting_artifacts(
    *,
    issue_categories: list[str],
    source_artifacts: dict[str, str],
) -> list[str]:
    supporting = [
        source_artifacts["assessment_preview"],
        source_artifacts["issue_matrix_preview"],
        source_artifacts["acceptance_gate_preview"],
    ]
    for category in issue_categories:
        artifact_id = CATEGORY_ARTIFACTS.get(category)
        if artifact_id:
            supporting.append(source_artifacts[category])
    return _sorted_unique(supporting)


def _blocking_gates_for_rows(
    rows: list[dict[str, Any]],
    *,
    modality_missing: set[str],
) -> list[str]:
    blocking: set[str] = set()
    for row in rows:
        accession = str(row.get("accession") or "").strip()
        verdict = str(row.get("verdict") or "").strip()
        category = str(row.get("issue_category") or "").strip()
        if verdict in BLOCKING_VERDICTS:
            blocking.add(category or "issue_matrix")
        if accession in modality_missing:
            blocking.add("modality")
    return sorted(blocking, key=str.casefold)


def _row_remediation_actions(rows: list[dict[str, Any]]) -> list[str]:
    return _sorted_unique(row.get("remediation_action") for row in rows)


def build_external_dataset_resolution_preview(
    assessment_preview: dict[str, Any],
    issue_matrix_preview: dict[str, Any],
    acceptance_gate_preview: dict[str, Any],
    leakage_audit: dict[str, Any],
    modality_audit: dict[str, Any],
    binding_audit: dict[str, Any],
    structure_audit: dict[str, Any],
    provenance_audit: dict[str, Any],
) -> dict[str, Any]:
    assessment_preview = _ensure_dict(assessment_preview, "assessment preview")
    issue_matrix_preview = _ensure_dict(issue_matrix_preview, "issue matrix preview")
    acceptance_gate_preview = _ensure_dict(acceptance_gate_preview, "acceptance gate preview")
    leakage_audit = _ensure_dict(leakage_audit, "leakage audit")
    modality_audit = _ensure_dict(modality_audit, "modality audit")
    binding_audit = _ensure_dict(binding_audit, "binding audit")
    structure_audit = _ensure_dict(structure_audit, "structure audit")
    provenance_audit = _ensure_dict(provenance_audit, "provenance audit")

    assessment_summary = _ensure_dict(assessment_preview.get("summary") or {}, "assessment summary")
    issue_summary = _ensure_dict(issue_matrix_preview.get("summary") or {}, "issue matrix summary")
    acceptance_summary = _ensure_dict(
        acceptance_gate_preview.get("summary") or {}, "acceptance gate summary"
    )
    modality_summary = _ensure_dict(modality_audit.get("summary") or {}, "modality summary")
    modality_findings = _ensure_dict(modality_audit.get("findings") or {}, "modality findings")
    leakage_summary = _ensure_dict(leakage_audit.get("summary") or {}, "leakage summary")
    leakage_findings = _ensure_dict(leakage_audit.get("findings") or {}, "leakage findings")
    binding_summary = _ensure_dict(binding_audit.get("summary") or {}, "binding summary")
    structure_summary = _ensure_dict(structure_audit.get("summary") or {}, "structure summary")
    structure_findings = _ensure_dict(structure_audit.get("findings") or {}, "structure findings")
    provenance_summary = _ensure_dict(
        provenance_audit.get("summary") or {}, "provenance summary"
    )
    provenance_findings = _ensure_dict(
        provenance_audit.get("findings") or {}, "provenance findings"
    )

    issue_rows = _issue_rows(issue_matrix_preview)
    accession_groups = _group_rows_by_accession(issue_rows)
    category_groups = _group_rows_by_category(issue_rows)
    modality_missing = {
        str(value or "").strip()
        for value in _listify(modality_findings.get("missing_accessions"))
        if str(value or "").strip()
    }

    source_artifacts = {
        name: _artifact_id(payload, fallback)
        for name, payload, fallback in [
            (
                "assessment_preview",
                assessment_preview,
                SOURCE_ARTIFACT_FALLBACKS["assessment_preview"],
            ),
            (
                "issue_matrix_preview",
                issue_matrix_preview,
                SOURCE_ARTIFACT_FALLBACKS["issue_matrix_preview"],
            ),
            (
                "acceptance_gate_preview",
                acceptance_gate_preview,
                SOURCE_ARTIFACT_FALLBACKS["acceptance_gate_preview"],
            ),
            ("leakage", leakage_audit, SOURCE_ARTIFACT_FALLBACKS["leakage"]),
            ("modality", modality_audit, SOURCE_ARTIFACT_FALLBACKS["modality"]),
            ("binding", binding_audit, SOURCE_ARTIFACT_FALLBACKS["binding"]),
            ("structure", structure_audit, SOURCE_ARTIFACT_FALLBACKS["structure"]),
            ("provenance", provenance_audit, SOURCE_ARTIFACT_FALLBACKS["provenance"]),
        ]
    }

    gate_reports = {
        str(item.get("gate_name") or "").strip(): dict(item)
        for item in acceptance_gate_preview.get("gate_reports") or []
        if isinstance(item, dict) and str(item.get("gate_name") or "").strip()
    }

    accession_rows: list[dict[str, Any]] = []
    for accession in sorted(accession_groups, key=str.casefold):
        rows = accession_groups[accession]
        issue_categories = _sorted_unique(row.get("issue_category") for row in rows)
        worst_verdict = max(rows, key=lambda row: _rank_verdict(str(row.get("verdict") or ""))).get(
            "verdict"
        )
        blocking_gates = _blocking_gates_for_rows(rows, modality_missing=modality_missing)
        resolution_state = _resolution_state(
            worst_verdict=str(worst_verdict or ""),
            mapping_incomplete=any(
                str(row.get("verdict") or "") == "blocked_pending_mapping"
                for row in rows
            )
            or accession in modality_missing,
            has_rows=True,
        )
        accession_rows.append(
            {
                "accession": accession,
                "resolution_state": resolution_state,
                "worst_verdict": worst_verdict,
                "issue_categories": issue_categories,
                "blocking_gates": blocking_gates,
                "remediation_actions": _row_remediation_actions(rows),
                "supporting_artifacts": _supporting_artifacts(
                    issue_categories=issue_categories,
                    source_artifacts=source_artifacts,
                ),
            }
        )

    category_rows: list[dict[str, Any]] = []
    for category in sorted(category_groups, key=str.casefold):
        rows = category_groups[category]
        affected_accessions = sorted(
            {str(row.get("accession") or "").strip() for row in rows if row.get("accession")},
            key=str.casefold,
        )
        worst_verdict = max(rows, key=lambda row: _rank_verdict(str(row.get("verdict") or ""))).get(
            "verdict"
        )
        mapping_incomplete = category == "modality" and (
            any(str(row.get("verdict") or "") == "blocked_pending_mapping" for row in rows)
            or bool(modality_missing)
        )
        blocking_gates = []
        if mapping_incomplete:
            blocking_gates = ["modality"]
        elif str(worst_verdict or "") in BLOCKING_VERDICTS:
            blocking_gates = [category]
        resolution_state = _resolution_state(
            worst_verdict=str(worst_verdict or ""),
            mapping_incomplete=mapping_incomplete,
            has_rows=True,
        )
        category_rows.append(
            {
                "issue_category": category,
                "resolution_state": resolution_state,
                "worst_verdict": worst_verdict,
                "affected_accessions": affected_accessions,
                "blocking_gates": blocking_gates,
                "remediation_actions": _row_remediation_actions(rows),
                "supporting_artifacts": _supporting_artifacts(
                    issue_categories=[category],
                    source_artifacts=source_artifacts,
                ),
            }
        )

    accession_state_counts = Counter(row["resolution_state"] for row in accession_rows)
    issue_state_counts = Counter(row["resolution_state"] for row in category_rows)
    impacted_accession_count = len(accession_rows)
    resolved_accession_count = max(
        int(assessment_summary.get("dataset_accession_count") or 0) - impacted_accession_count,
        0,
    )
    accession_state_counts["resolved"] += resolved_accession_count

    top_blocking_gates = [
        {
            "gate_name": gate_name,
            "affected_accession_count": count,
            "remediation_action": gate_reports.get(gate_name, {}).get("remediation_action", ""),
        }
        for gate_name, count in Counter(
            gate_name
            for row in accession_rows
            for gate_name in row["blocking_gates"]
        ).most_common(5)
    ]
    top_issue_categories = [
        {
            "issue_category": item["issue_category"],
            "affected_accession_count": len(item["affected_accessions"]),
            "resolution_state": item["resolution_state"],
        }
        for item in sorted(
            category_rows,
            key=lambda item: (
                -_rank_verdict(str(item.get("worst_verdict") or "")),
                -(len(item.get("affected_accessions") or [])),
                str(item.get("issue_category") or "").casefold(),
            ),
        )[:5]
    ]

    overall_resolution_verdict = str(issue_summary.get("overall_verdict") or "usable_with_caveats")
    if str(acceptance_summary.get("overall_gate_verdict") or "") in BLOCKING_VERDICTS:
        overall_resolution_verdict = str(acceptance_summary.get("overall_gate_verdict"))

    return {
        "artifact_id": "external_dataset_resolution_preview",
        "schema_id": "proteosphere-external-dataset-resolution-preview-2026-04-03",
        "status": "report_only",
        "generated_at": (
            assessment_preview.get("generated_at")
            or issue_matrix_preview.get("generated_at")
            or acceptance_gate_preview.get("generated_at")
            or ""
        ),
        "summary": {
            "dataset_accession_count": int(assessment_summary.get("dataset_accession_count") or 0),
            "issue_row_count": len(issue_rows),
            "accession_row_count": len(accession_rows),
            "issue_category_row_count": len(category_rows),
            "overall_resolution_verdict": overall_resolution_verdict,
            "acceptance_gate_verdict": acceptance_summary.get("overall_gate_verdict"),
            "resolution_state_counts": dict(accession_state_counts),
            "issue_resolution_state_counts": dict(issue_state_counts),
            "resolved_accession_count": resolved_accession_count,
            "caveated_accession_count": int(accession_state_counts.get("caveated") or 0),
            "blocked_accession_count": int(accession_state_counts.get("blocked") or 0),
            "mapping_incomplete_accession_count": int(
                accession_state_counts.get("mapping-incomplete") or 0
            ),
            "top_blocking_gates": top_blocking_gates,
            "top_issue_categories": top_issue_categories,
        },
        "accession_resolution_rows": accession_rows,
        "issue_resolution_rows": category_rows,
        "source_artifacts": source_artifacts,
        "supporting_artifacts": {
            "assessment_verdict": assessment_summary.get("overall_verdict"),
            "issue_matrix_verdict": issue_summary.get("overall_verdict"),
            "acceptance_gate_verdict": acceptance_summary.get("overall_gate_verdict"),
            "sub_audits": {
                "leakage": leakage_findings.get("duplicate_accessions")
                or leakage_summary.get("duplicate_accession_count"),
                "modality": modality_summary.get("blocked_full_packet_accession_count"),
                "binding": binding_summary.get("measured_accession_count"),
                "structure": structure_findings.get("mismatch_risk") or structure_summary.get(
                    "seed_structure_overlap_accession_count"
                ),
                "provenance": provenance_findings.get("missing_accessions")
                or provenance_summary.get("row_level_resolution_supported"),
            },
        },
        "truth_boundary": {
            "summary": (
                "This resolution preview is advisory and fail-closed. It only summarizes "
                "current external-assessment artifacts, does not mutate them, and does "
                "not imply training-safe acceptance."
            ),
            "report_only": True,
            "non_mutating": True,
            "training_safe_acceptance_not_implied": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export an advisory external dataset resolution preview."
    )
    parser.add_argument("--assessment-preview", type=Path, default=DEFAULT_ASSESSMENT_PREVIEW)
    parser.add_argument("--issue-matrix-preview", type=Path, default=DEFAULT_ISSUE_MATRIX_PREVIEW)
    parser.add_argument(
        "--acceptance-gate-preview", type=Path, default=DEFAULT_ACCEPTANCE_GATE_PREVIEW
    )
    parser.add_argument("--leakage-audit", type=Path, default=DEFAULT_LEAKAGE_AUDIT_PREVIEW)
    parser.add_argument("--modality-audit", type=Path, default=DEFAULT_MODALITY_AUDIT_PREVIEW)
    parser.add_argument("--binding-audit", type=Path, default=DEFAULT_BINDING_AUDIT_PREVIEW)
    parser.add_argument("--structure-audit", type=Path, default=DEFAULT_STRUCTURE_AUDIT_PREVIEW)
    parser.add_argument("--provenance-audit", type=Path, default=DEFAULT_PROVENANCE_AUDIT_PREVIEW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_external_dataset_resolution_preview(
        read_json(args.assessment_preview),
        read_json(args.issue_matrix_preview),
        read_json(args.acceptance_gate_preview),
        read_json(args.leakage_audit),
        read_json(args.modality_audit),
        read_json(args.binding_audit),
        read_json(args.structure_audit),
        read_json(args.provenance_audit),
    )
    write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
