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
    REPO_ROOT / "artifacts" / "status" / "external_dataset_issue_matrix_preview.json"
)

SEVERITY_RANK = {
    "high": 3,
    "medium": 2,
    "low": 1,
}

VERDICT_RANK = {
    "blocked_pending_cleanup": 4,
    "blocked_pending_mapping": 3,
    "blocked_pending_acquisition": 2,
    "audit_only": 1,
    "usable_with_caveats": 0,
}

ISSUE_CATEGORY_ACTIONS = {
    "leakage": "remove duplicate or cross-split rows before training",
    "modality": "resolve mapping or acquisition blockers before training",
    "binding": "keep binding rows support-only until case-specific validation passes",
    "structure": "preserve PDB-to-UniProt alignment and keep adjacent context separate",
    "provenance": "keep provenance explicit and avoid collapsing mixed trust tiers",
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


def _rank_issue_summary(verdict: str, severity: str) -> tuple[int, int]:
    return (_rank_verdict(verdict), SEVERITY_RANK.get(severity, 0))


def _collect_accessions(*groups: Any) -> list[str]:
    accessions: dict[str, str] = {}
    for group in groups:
        if isinstance(group, dict):
            for value in group.values():
                if isinstance(value, list):
                    for accession in value:
                        text = str(accession or "").strip()
                        if text:
                            accessions.setdefault(text.casefold(), text)
        else:
            for accession in _listify(group):
                accessions.setdefault(accession.casefold(), accession)
    return sorted(accessions.values(), key=str.casefold)


def _issue_row(
    accession: str,
    issue_category: str,
    *,
    verdict: str,
    severity: str,
    issue_summary: str,
    remediation_action: str,
    source_artifacts: list[str],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "accession": accession,
        "issue_category": issue_category,
        "verdict": verdict,
        "severity": severity,
        "issue_summary": issue_summary,
        "remediation_action": remediation_action,
        "source_artifacts": source_artifacts,
        "evidence": evidence,
    }


def _parse_assessment_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return dict(payload.get("summary") or {})


def build_external_dataset_issue_matrix_preview(
    assessment_preview: dict[str, Any],
    leakage_audit: dict[str, Any],
    modality_audit: dict[str, Any],
    binding_audit: dict[str, Any],
    structure_audit: dict[str, Any],
    provenance_audit: dict[str, Any],
) -> dict[str, Any]:
    assessment_summary = _parse_assessment_summary(assessment_preview)
    leakage_summary = dict(leakage_audit.get("summary") or {})
    leakage_findings = dict(leakage_audit.get("findings") or {})
    modality_findings = dict(modality_audit.get("findings") or {})
    binding_summary = dict(binding_audit.get("summary") or {})
    structure_summary = dict(structure_audit.get("summary") or {})
    structure_findings = dict(structure_audit.get("findings") or {})
    provenance_summary = dict(provenance_audit.get("summary") or {})
    provenance_findings = dict(provenance_audit.get("findings") or {})

    duplicate_accessions = _sorted_unique(
        leakage_findings.get("duplicate_accessions"),
        leakage_summary.get("duplicate_accessions"),
    )
    cross_split_duplicates = _sorted_unique(leakage_summary.get("cross_split_duplicates"))
    blocked_accessions = _sorted_unique(leakage_summary.get("blocked_accessions"))
    candidate_only_accessions = _sorted_unique(modality_findings.get("candidate_only_accessions"))
    missing_accessions = _sorted_unique(modality_findings.get("missing_accessions"))
    modality_blocked_accessions = _sorted_unique(modality_findings.get("blocked_accessions"))
    measured_accessions = _sorted_unique(
        binding_summary.get("supported_measurement_accessions")
    )
    structure_overlap_accessions = _sorted_unique(
        structure_summary.get("seed_structure_overlap_accessions")
    )
    provenance_missing_accessions = _sorted_unique(provenance_findings.get("missing_accessions"))
    external_accessions = _collect_accessions(
        duplicate_accessions,
        cross_split_duplicates,
        blocked_accessions,
        candidate_only_accessions,
        missing_accessions,
        modality_blocked_accessions,
        measured_accessions,
        structure_overlap_accessions,
        provenance_missing_accessions,
    )

    rows: list[dict[str, Any]] = []

    for accession in duplicate_accessions:
        rows.append(
            _issue_row(
                accession,
                "leakage",
                verdict="blocked_pending_cleanup",
                severity="high",
                issue_summary="Duplicate accession appears in the external dataset.",
                remediation_action=ISSUE_CATEGORY_ACTIONS["leakage"],
                source_artifacts=[leakage_audit.get("artifact_id") or ""],
                evidence={
                    "duplicate_accessions": duplicate_accessions,
                    "cross_split_duplicates": cross_split_duplicates,
                },
            )
        )

    for accession in cross_split_duplicates:
        rows.append(
            _issue_row(
                accession,
                "leakage",
                verdict="blocked_pending_cleanup",
                severity="high",
                issue_summary="Cross-split duplicate must be cleared before training.",
                remediation_action=ISSUE_CATEGORY_ACTIONS["leakage"],
                source_artifacts=[leakage_audit.get("artifact_id") or ""],
                evidence={"cross_split_duplicates": cross_split_duplicates},
            )
        )

    for accession in sorted(
        set(candidate_only_accessions)
        | set(missing_accessions)
        | set(modality_blocked_accessions)
    ):
        if accession in missing_accessions:
            verdict = "blocked_pending_mapping"
            severity = "high"
            summary = "Accession is missing mapping coverage needed for training."
            action = "resolve accession mapping before training"
        elif accession in modality_blocked_accessions:
            verdict = "blocked_pending_acquisition"
            severity = "high"
            summary = "Accession is blocked pending upstream acquisition."
            action = ISSUE_CATEGORY_ACTIONS["modality"]
        else:
            verdict = "audit_only"
            severity = "low"
            summary = "Accession is candidate-only non-governing in the current preview."
            action = "keep the accession non-governing until grounded rows exist"
        rows.append(
            _issue_row(
                accession,
                "modality",
                verdict=verdict,
                severity=severity,
                issue_summary=summary,
                remediation_action=action,
                source_artifacts=[modality_audit.get("artifact_id") or ""],
                evidence={
                    "candidate_only_accessions": candidate_only_accessions,
                    "missing_accessions": missing_accessions,
                    "blocked_accessions": modality_blocked_accessions,
                },
            )
        )

    for accession in measured_accessions:
        rows.append(
            _issue_row(
                accession,
                "binding",
                verdict="usable_with_caveats",
                severity="low",
                issue_summary="Accession has binding coverage in the current preview.",
                remediation_action=ISSUE_CATEGORY_ACTIONS["binding"],
                source_artifacts=[binding_audit.get("artifact_id") or ""],
                evidence={
                    "measurement_type_counts": dict(
                        binding_summary.get("measurement_type_counts") or {}
                    ),
                    "complex_type_counts": dict(binding_summary.get("complex_type_counts") or {}),
                },
            )
        )

    for accession in structure_overlap_accessions:
        rows.append(
            _issue_row(
                accession,
                "structure",
                verdict="usable_with_caveats",
                severity="medium",
                issue_summary="Seed structure overlap is present and should remain alignment-safe.",
                remediation_action=ISSUE_CATEGORY_ACTIONS["structure"],
                source_artifacts=[structure_audit.get("artifact_id") or ""],
                evidence={
                    "seed_structure_overlap_accessions": structure_overlap_accessions,
                    "mismatch_risk": structure_findings.get("mismatch_risk"),
                },
            )
        )

    for accession in external_accessions:
        rows.append(
            _issue_row(
                accession,
                "provenance",
                verdict="usable_with_caveats",
                severity="low",
                issue_summary="Keep source provenance and trust tiers explicit.",
                remediation_action=ISSUE_CATEGORY_ACTIONS["provenance"],
                source_artifacts=[provenance_audit.get("artifact_id") or ""],
                evidence={
                    "library_contract_status": provenance_summary.get("contract_status"),
                    "binding_registry_source_counts": dict(
                        provenance_summary.get("binding_registry_source_counts") or {}
                    ),
                },
            )
        )

    rows.sort(
        key=lambda row: (
            -_rank_issue_summary(row["verdict"], row["severity"])[0],
            -_rank_issue_summary(row["verdict"], row["severity"])[1],
            row["issue_category"],
            row["accession"],
        )
    )

    grouped_by_accession: list[dict[str, Any]] = []
    rows_by_accession: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_accession[row["accession"]].append(row)
    for accession in sorted(rows_by_accession, key=str.casefold):
        accession_rows = rows_by_accession[accession]
        verdict_counts = Counter(row["verdict"] for row in accession_rows)
        grouped_by_accession.append(
            {
                "accession": accession,
                "issue_row_count": len(accession_rows),
                "issue_categories": sorted(
                    {row["issue_category"] for row in accession_rows},
                    key=str.casefold,
                ),
                "worst_verdict": max(accession_rows, key=lambda row: _rank_verdict(row["verdict"]))[
                    "verdict"
                ],
                "verdict_counts": dict(verdict_counts),
                "remediation_actions": _sorted_unique(
                    row["remediation_action"] for row in accession_rows
                ),
            }
        )

    grouped_by_category: list[dict[str, Any]] = []
    rows_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_category[row["issue_category"]].append(row)
    for category in sorted(rows_by_category, key=str.casefold):
        category_rows = rows_by_category[category]
        verdict_counts = Counter(row["verdict"] for row in category_rows)
        grouped_by_category.append(
            {
                "issue_category": category,
                "issue_row_count": len(category_rows),
                "affected_accessions": sorted(
                    {row["accession"] for row in category_rows}, key=str.casefold
                ),
                "worst_verdict": max(
                    category_rows, key=lambda row: _rank_verdict(row["verdict"])
                )["verdict"],
                "verdict_counts": dict(verdict_counts),
                "remediation_action": ISSUE_CATEGORY_ACTIONS.get(category, "review manually"),
            }
        )

    verdict_counts = Counter(row["verdict"] for row in rows)
    if verdict_counts.get("blocked_pending_cleanup"):
        overall_verdict = "blocked_pending_cleanup"
    elif verdict_counts.get("blocked_pending_mapping"):
        overall_verdict = "blocked_pending_mapping"
    elif verdict_counts.get("blocked_pending_acquisition"):
        overall_verdict = "blocked_pending_acquisition"
    elif verdict_counts.get("audit_only"):
        overall_verdict = "audit_only"
    else:
        overall_verdict = "usable_with_caveats"

    remediation_priority_view = [
        {
            "issue_category": item["issue_category"],
            "affected_accession_count": len(item["affected_accessions"]),
            "worst_verdict": item["worst_verdict"],
            "next_action": item["remediation_action"],
        }
        for item in sorted(
        grouped_by_category,
        key=lambda item: (
            -_rank_verdict(item["worst_verdict"]),
            -len(item["affected_accessions"]),
            item["issue_category"],
        ),
    )
    ]

    compact_verdict_view = {
        "overall_verdict": overall_verdict,
        "issue_row_count": len(rows),
        "affected_accession_count": len(rows_by_accession),
        "verdict_counts": dict(verdict_counts),
        "issue_category_counts": {
            item["issue_category"]: item["issue_row_count"] for item in grouped_by_category
        },
        "top_remediation_actions": remediation_priority_view[:5],
    }

    return {
        "artifact_id": "external_dataset_issue_matrix_preview",
        "schema_id": "proteosphere-external-dataset-issue-matrix-preview-2026-04-03",
        "status": "report_only",
        "generated_at": assessment_preview.get("generated_at") or "",
        "summary": {
            "dataset_accession_count": int(assessment_summary.get("dataset_accession_count") or 0),
            "issue_row_count": len(rows),
            "affected_accession_count": len(rows_by_accession),
            "overall_verdict": overall_verdict,
            "verdict_counts": dict(verdict_counts),
            "issue_category_counts": {
                item["issue_category"]: item["issue_row_count"] for item in grouped_by_category
            },
        },
        "compact_verdict_view": compact_verdict_view,
        "rows": rows,
        "grouped_by_accession": grouped_by_accession,
        "grouped_by_issue_category": grouped_by_category,
        "source_artifacts": {
            "assessment_preview": assessment_preview.get("artifact_id"),
            "sub_audits": {
                "leakage": leakage_audit.get("artifact_id"),
                "modality": modality_audit.get("artifact_id"),
                "binding": binding_audit.get("artifact_id"),
                "structure": structure_audit.get("artifact_id"),
                "provenance": provenance_audit.get("artifact_id"),
            },
        },
        "truth_boundary": {
            "summary": (
                "This issue matrix is advisory and fail-closed. It organizes existing "
                "external dataset assessment outputs into remediation-oriented rows, "
                "but it does not bless the dataset for training or mutate any source "
                "artifacts."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export an advisory external dataset issue matrix preview."
    )
    parser.add_argument("--assessment-preview", type=Path, default=DEFAULT_ASSESSMENT_PREVIEW)
    parser.add_argument("--leakage-audit", type=Path, default=DEFAULT_LEAKAGE_AUDIT_PREVIEW)
    parser.add_argument("--modality-audit", type=Path, default=DEFAULT_MODALITY_AUDIT_PREVIEW)
    parser.add_argument("--binding-audit", type=Path, default=DEFAULT_BINDING_AUDIT_PREVIEW)
    parser.add_argument("--structure-audit", type=Path, default=DEFAULT_STRUCTURE_AUDIT_PREVIEW)
    parser.add_argument("--provenance-audit", type=Path, default=DEFAULT_PROVENANCE_AUDIT_PREVIEW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_external_dataset_issue_matrix_preview(
        read_json(args.assessment_preview),
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
