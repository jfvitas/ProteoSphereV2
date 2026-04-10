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

DEFAULT_ASSESSMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_assessment_preview.json"
)
DEFAULT_ISSUE_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_issue_matrix_preview.json"
)
DEFAULT_MANIFEST_LINT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_manifest_lint_preview.json"
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
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json"
)

VERDICT_RANK = {
    "blocked_pending_acquisition": 4,
    "unsafe_for_training": 3,
    "blocked_pending_cleanup": 2,
    "blocked_pending_mapping": 1,
    "audit_only": 0,
    "usable_with_caveats": -1,
}

GATE_ACTIONS = {
    "leakage": "keep the dataset duplicate-free and cross-split clean",
    "modality": "resolve mapping or acquisition blockers before training",
    "binding": "keep binding rows support-only until case-specific validation passes",
    "structure": "preserve PDB-to-UniProt alignment and keep adjacent context separate",
    "provenance": "keep provenance explicit and avoid collapsing mixed trust tiers",
    "manifest_lint": "restore missing manifest or row fields before accepting the intake package",
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
    return VERDICT_RANK.get(verdict, -1)


def _artifact_id(payload: dict[str, Any], fallback: str) -> str:
    return str(payload.get("artifact_id") or fallback).strip()


def _issue_rows(issue_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows = issue_matrix.get("rows")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def _grouped_by_accession(issue_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    grouped = issue_matrix.get("grouped_by_accession")
    if isinstance(grouped, list):
        return [row for row in grouped if isinstance(row, dict)]

    rows = _issue_rows(issue_matrix)
    rows_by_accession: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        accession = str(row.get("accession") or "").strip()
        if accession:
            rows_by_accession.setdefault(accession, []).append(row)

    fallback_grouped: list[dict[str, Any]] = []
    for accession in sorted(rows_by_accession, key=str.casefold):
        accession_rows = rows_by_accession[accession]
        fallback_grouped.append(
            {
                "accession": accession,
                "issue_row_count": len(accession_rows),
                "issue_categories": sorted(
                    {
                        str(row.get("issue_category") or "")
                        for row in accession_rows
                        if row.get("issue_category")
                    },
                    key=str.casefold,
                ),
                "worst_verdict": max(
                    accession_rows,
                    key=lambda row: _rank_verdict(str(row.get("verdict") or "")),
                ).get("verdict"),
                "verdict_counts": dict(
                    Counter(str(row.get("verdict") or "") for row in accession_rows)
                ),
                "remediation_actions": _sorted_unique(
                    row.get("remediation_action") for row in accession_rows
                ),
            }
        )
    return fallback_grouped


def _grouped_by_issue_category(issue_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    grouped = issue_matrix.get("grouped_by_issue_category")
    if isinstance(grouped, list):
        return [row for row in grouped if isinstance(row, dict)]

    rows = _issue_rows(issue_matrix)
    rows_by_category: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        category = str(row.get("issue_category") or "").strip()
        if category:
            rows_by_category.setdefault(category, []).append(row)

    fallback_grouped: list[dict[str, Any]] = []
    for category in sorted(rows_by_category, key=str.casefold):
        category_rows = rows_by_category[category]
        fallback_grouped.append(
            {
                "issue_category": category,
                "issue_row_count": len(category_rows),
                "affected_accessions": sorted(
                    {
                        str(row.get("accession") or "")
                        for row in category_rows
                        if row.get("accession")
                    },
                    key=str.casefold,
                ),
                "worst_verdict": max(
                    category_rows,
                    key=lambda row: _rank_verdict(str(row.get("verdict") or "")),
                ).get("verdict"),
                "verdict_counts": dict(
                    Counter(str(row.get("verdict") or "") for row in category_rows)
                ),
                "remediation_action": GATE_ACTIONS.get(category, "review manually"),
            }
        )
    return fallback_grouped


def _manifest_gate_verdict(manifest_lint: dict[str, Any]) -> str:
    summary = _ensure_dict(manifest_lint.get("summary") or {}, "manifest lint summary")
    missing_required_field_count = int(summary.get("missing_required_field_count") or 0)
    if missing_required_field_count > 0:
        return "unsafe_for_training"
    return str(summary.get("overall_verdict") or "usable_with_caveats")


def _gate_report(
    name: str,
    *,
    artifact_id: str,
    verdict: str,
    impacted_accessions: list[str],
    remediation_action: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "gate_name": name,
        "artifact_id": artifact_id,
        "verdict": verdict,
        "impact": {
            "impacted_accession_count": len(impacted_accessions),
            "impacted_accessions": impacted_accessions,
        },
        "remediation_action": remediation_action,
        "evidence": evidence,
    }


def build_external_dataset_acceptance_gate_preview(
    assessment_preview: dict[str, Any],
    issue_matrix_preview: dict[str, Any],
    manifest_lint_preview: dict[str, Any],
    leakage_audit: dict[str, Any],
    modality_audit: dict[str, Any],
    binding_audit: dict[str, Any],
    structure_audit: dict[str, Any],
    provenance_audit: dict[str, Any],
) -> dict[str, Any]:
    assessment_preview = _ensure_dict(assessment_preview, "assessment preview")
    issue_matrix_preview = _ensure_dict(issue_matrix_preview, "issue matrix preview")
    manifest_lint_preview = _ensure_dict(manifest_lint_preview, "manifest lint preview")
    leakage_audit = _ensure_dict(leakage_audit, "leakage audit")
    modality_audit = _ensure_dict(modality_audit, "modality audit")
    binding_audit = _ensure_dict(binding_audit, "binding audit")
    structure_audit = _ensure_dict(structure_audit, "structure audit")
    provenance_audit = _ensure_dict(provenance_audit, "provenance audit")

    assessment_summary = _ensure_dict(assessment_preview.get("summary") or {}, "assessment summary")
    issue_summary = _ensure_dict(issue_matrix_preview.get("summary") or {}, "issue matrix summary")
    manifest_summary = _ensure_dict(
        manifest_lint_preview.get("summary") or {}, "manifest lint summary"
    )
    leakage_summary = _ensure_dict(leakage_audit.get("summary") or {}, "leakage summary")
    leakage_findings = _ensure_dict(leakage_audit.get("findings") or {}, "leakage findings")
    modality_summary = _ensure_dict(modality_audit.get("summary") or {}, "modality summary")
    modality_findings = _ensure_dict(modality_audit.get("findings") or {}, "modality findings")
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
    grouped_by_accession = _grouped_by_accession(issue_matrix_preview)
    grouped_by_issue_category = _grouped_by_issue_category(issue_matrix_preview)

    blocked_accessions = sorted(
        {
            str(row.get("accession") or "").strip()
            for row in grouped_by_accession
            if str(row.get("worst_verdict") or "") != "usable_with_caveats" and row.get("accession")
        },
        key=str.casefold,
    )
    caveated_accessions = sorted(
        {
            str(row.get("accession") or "").strip()
            for row in grouped_by_accession
            if str(row.get("worst_verdict") or "") == "usable_with_caveats" and row.get("accession")
        },
        key=str.casefold,
    )

    top_remediation_categories = [
        {
            "issue_category": item["issue_category"],
            "affected_accession_count": len(item.get("affected_accessions") or []),
            "worst_verdict": item.get("worst_verdict"),
            "remediation_action": item.get("remediation_action")
            or GATE_ACTIONS.get(str(item.get("issue_category") or ""), "review manually"),
        }
        for item in sorted(
            grouped_by_issue_category,
            key=lambda item: (
                -_rank_verdict(str(item.get("worst_verdict") or "")),
                -(len(item.get("affected_accessions") or [])),
                str(item.get("issue_category") or "").casefold(),
            ),
        )
        if (item.get("affected_accessions") or [])
    ]

    issue_category_reports = []
    for item in sorted(
        grouped_by_issue_category,
        key=lambda item: (
            -_rank_verdict(str(item.get("worst_verdict") or "")),
            -(len(item.get("affected_accessions") or [])),
            str(item.get("issue_category") or "").casefold(),
        ),
    ):
        impacted_accessions = _sorted_unique(item.get("affected_accessions"))
        issue_category_reports.append(
            _gate_report(
                str(item.get("issue_category") or ""),
                artifact_id=_artifact_id(
                    issue_matrix_preview,
                    "external_dataset_issue_matrix_preview",
                ),
                verdict=str(item.get("worst_verdict") or "usable_with_caveats"),
                impacted_accessions=impacted_accessions,
                remediation_action=str(
                    item.get("remediation_action")
                    or GATE_ACTIONS.get(str(item.get("issue_category") or ""), "review manually")
                ),
                evidence={
                    "issue_row_count": int(item.get("issue_row_count") or 0),
                    "verdict_counts": dict(item.get("verdict_counts") or {}),
                },
            )
        )

    assessment_gate = _gate_report(
        "assessment",
        artifact_id=_artifact_id(
            assessment_preview, "external_dataset_assessment_preview"
        ),
        verdict=str(assessment_summary.get("overall_verdict") or "usable_with_caveats"),
        impacted_accessions=sorted(
            {
                str(row.get("accession") or "").strip()
                for row in grouped_by_accession
                if row.get("accession")
            },
            key=str.casefold,
        ),
        remediation_action="treat the assessment as advisory until all hard blockers clear",
        evidence={
            "dataset_accession_count": int(assessment_summary.get("dataset_accession_count") or 0),
            "split_policy": assessment_summary.get("split_policy"),
            "sub_audits": dict(assessment_preview.get("sub_audits") or {}),
        },
    )

    manifest_gate = _gate_report(
        "manifest_lint",
        artifact_id=_artifact_id(
            manifest_lint_preview, "external_dataset_manifest_lint_preview"
        ),
        verdict=_manifest_gate_verdict(manifest_lint_preview),
        impacted_accessions=[],
        remediation_action=GATE_ACTIONS["manifest_lint"],
        evidence={
            "accepted_shape_count": int(manifest_summary.get("accepted_shape_count") or 0),
            "missing_required_field_count": int(
                manifest_summary.get("missing_required_field_count") or 0
            ),
            "missing_required_top_level_field_count": int(
                manifest_summary.get("missing_required_top_level_field_count") or 0
            ),
            "missing_required_row_field_count": int(
                manifest_summary.get("missing_required_row_field_count") or 0
            ),
        },
    )

    issue_matrix_verdict = str(issue_summary.get("overall_verdict") or "usable_with_caveats")
    issue_matrix_gate = _gate_report(
        "issue_matrix",
        artifact_id=_artifact_id(
            issue_matrix_preview, "external_dataset_issue_matrix_preview"
        ),
        verdict=issue_matrix_verdict,
        impacted_accessions=blocked_accessions,
        remediation_action=(
            "clear the blocked category rows before claiming "
            "training-safe acceptance"
        ),
        evidence={
            "issue_row_count": len(issue_rows),
            "affected_accession_count": len(grouped_by_accession),
            "blocked_accession_count": len(blocked_accessions),
            "usable_with_caveats_accession_count": len(caveated_accessions),
            "verdict_counts": dict(Counter()),
        },
    )
    issue_matrix_gate["evidence"]["verdict_counts"] = dict(
        Counter(str(row.get("verdict") or "") for row in issue_rows if row.get("verdict"))
    )

    leakage_blocked_accessions = _sorted_unique(
        leakage_summary.get("blocked_accessions"),
        leakage_findings.get("duplicate_accessions"),
        leakage_findings.get("cross_split_duplicates"),
    )
    leakage_gate = _gate_report(
        "leakage",
        artifact_id=_artifact_id(
            leakage_audit, "external_dataset_leakage_audit_preview"
        ),
        verdict=str(leakage_audit.get("verdict") or "usable_with_caveats"),
        impacted_accessions=leakage_blocked_accessions,
        remediation_action=GATE_ACTIONS["leakage"],
        evidence={
            "duplicate_accession_count": int(leakage_summary.get("duplicate_accession_count") or 0),
            "cross_split_duplicate_count": len(
                _sorted_unique(leakage_summary.get("cross_split_duplicates"))
            ),
        },
    )

    modality_gate = _gate_report(
        "modality",
        artifact_id=_artifact_id(
            modality_audit, "external_dataset_modality_audit_preview"
        ),
        verdict=str(modality_audit.get("verdict") or "usable_with_caveats"),
        impacted_accessions=_sorted_unique(modality_findings.get("blocked_accessions")),
        remediation_action=GATE_ACTIONS["modality"],
        evidence={
            "candidate_only_accession_count": int(
                modality_summary.get("candidate_only_accession_count") or 0
            ),
            "missing_mapping_accession_count": int(
                modality_summary.get("missing_mapping_accession_count") or 0
            ),
            "blocked_full_packet_accession_count": int(
                modality_summary.get("blocked_full_packet_accession_count") or 0
            ),
            "candidate_only_accessions": _sorted_unique(
                modality_findings.get("candidate_only_accessions")
            ),
        },
    )

    binding_gate = _gate_report(
        "binding",
        artifact_id=_artifact_id(
            binding_audit, "external_dataset_binding_audit_preview"
        ),
        verdict=str(binding_audit.get("verdict") or "usable_with_caveats"),
        impacted_accessions=_sorted_unique(
            binding_summary.get("supported_measurement_accessions")
        ),
        remediation_action=GATE_ACTIONS["binding"],
        evidence={
            "measured_accession_count": int(binding_summary.get("measured_accession_count") or 0),
            "measurement_type_counts": dict(binding_summary.get("measurement_type_counts") or {}),
            "complex_type_counts": dict(binding_summary.get("complex_type_counts") or {}),
        },
    )

    structure_gate = _gate_report(
        "structure",
        artifact_id=_artifact_id(
            structure_audit, "external_dataset_structure_audit_preview"
        ),
        verdict=str(structure_audit.get("verdict") or "usable_with_caveats"),
        impacted_accessions=_sorted_unique(structure_summary.get("seed_structure_overlap_accessions")),
        remediation_action=GATE_ACTIONS["structure"],
        evidence={
            "seed_structure_overlap_accession_count": int(
                structure_summary.get("seed_structure_overlap_accession_count") or 0
            ),
            "future_off_target_adjacent_context_only_count": int(
                structure_summary.get("future_off_target_adjacent_context_only_count") or 0
            ),
            "mismatch_risk": structure_findings.get("mismatch_risk"),
        },
    )

    provenance_gate = _gate_report(
        "provenance",
        artifact_id=_artifact_id(
            provenance_audit, "external_dataset_provenance_audit_preview"
        ),
        verdict=str(provenance_audit.get("verdict") or "usable_with_caveats"),
        impacted_accessions=_sorted_unique(provenance_findings.get("missing_accessions")),
        remediation_action=GATE_ACTIONS["provenance"],
        evidence={
            "contract_status": provenance_summary.get("contract_status"),
            "row_level_resolution_supported": provenance_summary.get(
                "row_level_resolution_supported"
            ),
            "binding_registry_source_counts": dict(
                provenance_summary.get("binding_registry_source_counts") or {}
            ),
        },
    )

    gate_reports = [
        assessment_gate,
        manifest_gate,
        issue_matrix_gate,
        leakage_gate,
        modality_gate,
        binding_gate,
        structure_gate,
        provenance_gate,
    ]

    issue_verdict_counts = Counter(
        str(row.get("verdict") or "") for row in issue_rows if row.get("verdict")
    )
    blocked_gate_count = sum(
        1
        for gate in gate_reports
        if _rank_verdict(str(gate.get("verdict") or ""))
        >= _rank_verdict("blocked_pending_mapping")
    )
    usable_with_caveats_gate_count = sum(
        1 for gate in gate_reports if str(gate.get("verdict") or "") == "usable_with_caveats"
    )
    overall_gate_verdict = str(issue_summary.get("overall_verdict") or "usable_with_caveats")
    if _manifest_gate_verdict(manifest_lint_preview) == "unsafe_for_training":
        overall_gate_verdict = "unsafe_for_training"

    training_safe_acceptance = {
        "must_clear": [
            {
                "gate_name": gate["gate_name"],
                "verdict": gate["verdict"],
                "impacted_accession_count": gate["impact"]["impacted_accession_count"],
                "clear_condition": gate["remediation_action"],
            }
            for gate in gate_reports
            if str(gate["verdict"]) not in {"usable_with_caveats", "audit_only"}
        ],
        "must_remain_non_governing_or_be_formally_rescoped": [
            {
                "gate_name": gate["gate_name"],
                "verdict": gate["verdict"],
                "impacted_accession_count": gate["impact"]["impacted_accession_count"],
                "clear_condition": gate["remediation_action"],
            }
            for gate in gate_reports
            if str(gate["verdict"]) == "usable_with_caveats"
            and gate["gate_name"] not in {"assessment", "leakage", "manifest_lint"}
        ],
    }

    return {
        "artifact_id": "external_dataset_acceptance_gate_preview",
        "schema_id": "proteosphere-external-dataset-acceptance-gate-preview-2026-04-03",
        "status": "report_only",
        "generated_at": assessment_preview.get("generated_at")
        or issue_matrix_preview.get("generated_at")
        or manifest_lint_preview.get("generated_at")
        or "",
        "summary": {
            "dataset_accession_count": int(assessment_summary.get("dataset_accession_count") or 0),
            "issue_row_count": len(issue_rows),
            "blocked_accession_count": len(blocked_accessions),
            "usable_with_caveats_accession_count": len(caveated_accessions),
            "overall_gate_verdict": overall_gate_verdict,
            "gate_verdict_counts": dict(issue_verdict_counts),
            "blocked_gate_count": blocked_gate_count,
            "usable_with_caveats_gate_count": usable_with_caveats_gate_count,
            "top_remediation_categories": top_remediation_categories,
            "training_safe_acceptance": training_safe_acceptance,
        },
        "gate_reports": gate_reports,
        "issue_category_reports": issue_category_reports,
        "source_artifacts": {
            "assessment_preview": _artifact_id(
                assessment_preview, "external_dataset_assessment_preview"
            ),
            "issue_matrix_preview": _artifact_id(
                issue_matrix_preview, "external_dataset_issue_matrix_preview"
            ),
            "manifest_lint_preview": _artifact_id(
                manifest_lint_preview, "external_dataset_manifest_lint_preview"
            ),
            "sub_audits": {
                "leakage": _artifact_id(leakage_audit, "external_dataset_leakage_audit_preview"),
                "modality": _artifact_id(
                    modality_audit,
                    "external_dataset_modality_audit_preview",
                ),
                "binding": _artifact_id(
                    binding_audit,
                    "external_dataset_binding_audit_preview",
                ),
                "structure": _artifact_id(
                    structure_audit, "external_dataset_structure_audit_preview"
                ),
                "provenance": _artifact_id(
                    provenance_audit, "external_dataset_provenance_audit_preview"
                ),
            },
        },
        "truth_boundary": {
            "summary": (
                "This acceptance gate preview is advisory and fail-closed. It only "
                "summarizes existing external-assessment artifacts, does not mutate "
                "them, and does not bless the dataset for training."
            ),
            "report_only": True,
            "non_mutating": True,
            "training_safe_acceptance_not_implied": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export an advisory external dataset acceptance gate preview."
    )
    parser.add_argument(
        "--assessment-preview",
        type=Path,
        default=DEFAULT_ASSESSMENT_PREVIEW,
    )
    parser.add_argument(
        "--issue-matrix-preview", type=Path, default=DEFAULT_ISSUE_MATRIX_PREVIEW
    )
    parser.add_argument(
        "--manifest-lint-preview", type=Path, default=DEFAULT_MANIFEST_LINT_PREVIEW
    )
    parser.add_argument(
        "--leakage-audit",
        type=Path,
        default=DEFAULT_LEAKAGE_AUDIT_PREVIEW,
    )
    parser.add_argument(
        "--modality-audit",
        type=Path,
        default=DEFAULT_MODALITY_AUDIT_PREVIEW,
    )
    parser.add_argument(
        "--binding-audit",
        type=Path,
        default=DEFAULT_BINDING_AUDIT_PREVIEW,
    )
    parser.add_argument(
        "--structure-audit",
        type=Path,
        default=DEFAULT_STRUCTURE_AUDIT_PREVIEW,
    )
    parser.add_argument(
        "--provenance-audit",
        type=Path,
        default=DEFAULT_PROVENANCE_AUDIT_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_external_dataset_acceptance_gate_preview(
        read_json(args.assessment_preview),
        read_json(args.issue_matrix_preview),
        read_json(args.manifest_lint_preview),
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
