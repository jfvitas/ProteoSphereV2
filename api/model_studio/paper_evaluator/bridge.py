from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any

from .pipeline import CANONICAL_REASON_CODES

ALLOWED_POLICIES = (
    "accession_grouped",
    "uniref_grouped",
    "paper_faithful_external",
    "protein_ligand_component_grouped",
    "unresolved_policy",
)

ALLOWED_VERDICTS = (
    "usable",
    "usable_with_caveats",
    "audit_only",
    "blocked_pending_mapping",
    "blocked_pending_cleanup",
    "unsafe_for_training",
)


def build_llm_gap_packet(report: dict[str, Any]) -> dict[str, Any]:
    papers = []
    for row in report.get("papers", []):
        if not isinstance(row, dict):
            continue
        reasons = list(row.get("reason_codes") or [])
        resolved_policy = row.get("resolved_split_policy") or {}
        resolved_policy_value = (
            resolved_policy.get("policy") if isinstance(resolved_policy, dict) else resolved_policy
        )
        needs_review = bool(row.get("needs_human_review"))
        if not needs_review and resolved_policy_value != "unresolved_policy":
            continue
        papers.append(
            {
                "paper_id": str(row.get("paper_id") or ""),
                "current_verdict": str(row.get("verdict") or ""),
                "current_reason_codes": reasons,
                "current_resolved_split_policy": str(resolved_policy_value or ""),
                "current_needs_human_review": needs_review,
                "escalation_reasons": _escalation_reasons(row),
                "allowed_decisions": {
                    "resolved_split_policy": list(ALLOWED_POLICIES),
                    "verdict": list(ALLOWED_VERDICTS),
                    "reason_codes": list(CANONICAL_REASON_CODES),
                    "needs_human_review": [True, False],
                },
                "questions": _gap_questions(row),
            }
        )
    return {
        "artifact_id": "paper_dataset_evaluator_llm_gap_packet",
        "schema_id": "proteosphere-paper-dataset-evaluator-gap-packet-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_report_artifact_id": str(report.get("artifact_id") or ""),
        "paper_count": len(papers),
        "papers": papers,
    }


def apply_llm_gap_decisions(
    base_report: dict[str, Any],
    decisions_payload: dict[str, Any],
) -> dict[str, Any]:
    merged = copy.deepcopy(base_report)
    decision_rows = {
        str(item.get("paper_id") or ""): item
        for item in (decisions_payload.get("papers") or [])
        if isinstance(item, dict) and str(item.get("paper_id") or "").strip()
    }
    papers = []
    for row in merged.get("papers", []):
        if not isinstance(row, dict):
            continue
        paper_id = str(row.get("paper_id") or "")
        decision = decision_rows.get(paper_id)
        if decision:
            _apply_single_decision(row, decision)
        papers.append(row)
    merged["papers"] = papers
    merged["artifact_id"] = "paper_dataset_evaluator_bridged_report"
    merged["schema_id"] = "proteosphere-paper-dataset-evaluator-bridged-report-v1"
    merged["bridge_metadata"] = {
        "base_report_artifact_id": str(base_report.get("artifact_id") or ""),
        "decision_artifact_id": str(decisions_payload.get("artifact_id") or ""),
        "decision_model": str(decisions_payload.get("decision_model") or ""),
        "applied_at": datetime.now(UTC).isoformat(),
    }
    return merged


def _apply_single_decision(row: dict[str, Any], decision: dict[str, Any]) -> None:
    if "resolved_split_policy" in decision:
        policy = str(decision["resolved_split_policy"])
        if policy not in ALLOWED_POLICIES:
            raise ValueError(f"Unsupported resolved_split_policy override: {policy}")
        current = row.get("resolved_split_policy")
        if isinstance(current, dict):
            current["policy"] = policy
        else:
            row["resolved_split_policy"] = policy
    if "verdict" in decision:
        verdict = str(decision["verdict"])
        if verdict not in ALLOWED_VERDICTS:
            raise ValueError(f"Unsupported verdict override: {verdict}")
        row["verdict"] = verdict
    if "reason_codes" in decision:
        reason_codes = sorted({str(item) for item in (decision.get("reason_codes") or [])})
        unknown = [code for code in reason_codes if code not in CANONICAL_REASON_CODES]
        if unknown:
            raise ValueError(f"Unsupported reason code(s): {', '.join(unknown)}")
        row["reason_codes"] = reason_codes
    if "needs_human_review" in decision:
        row["needs_human_review"] = bool(decision["needs_human_review"])
    if "llm_rationale" in decision:
        row.setdefault("provenance_notes", []).append(
            f"LLM bridge rationale: {str(decision['llm_rationale']).strip()}"
        )


def _escalation_reasons(row: dict[str, Any]) -> list[str]:
    reasons = []
    if bool(row.get("needs_human_review")):
        reasons.append("base_evaluator_requested_human_review")
    resolved_policy = row.get("resolved_split_policy") or {}
    resolved_policy_value = (
        resolved_policy.get("policy") if isinstance(resolved_policy, dict) else resolved_policy
    )
    if resolved_policy_value == "unresolved_policy":
        reasons.append("resolved_policy_unresolved")
    if "UNRESOLVED_SPLIT_MEMBERSHIP" in set(row.get("reason_codes") or []):
        reasons.append("split_membership_not_materialized")
    return reasons


def _gap_questions(row: dict[str, Any]) -> list[str]:
    questions = [
        "Should the current resolved split policy remain as-is, or should it be changed to another allowed canonical policy?",
        "Should the verdict remain as-is once the paper wording is interpreted conservatively under ProteoSphere logic?",
        "Should `needs_human_review` remain true after examining the supplied paper wording and warehouse evidence surfaces?",
    ]
    if "UNRESOLVED_SPLIT_MEMBERSHIP" in set(row.get("reason_codes") or []):
        questions.append(
            "Does the paper wording justify keeping this in audit mode, or should the absence of roster evidence block it pending mapping?"
        )
    return questions
