from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def _paper_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("papers") if isinstance(payload, dict) else None
    if isinstance(rows, list):
        return [dict(item) for item in rows if isinstance(item, dict)]
    return []


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    resolved_policy = row.get("resolved_split_policy")
    if isinstance(resolved_policy, dict):
        resolved_policy = resolved_policy.get("policy")
    return {
        "paper_id": str(row.get("paper_id") or ""),
        "verdict": str(row.get("verdict") or ""),
        "reason_codes": sorted(
            {
                str(item)
                for item in (row.get("reason_codes") or [])
                if str(item).strip()
            }
        ),
        "resolved_split_policy": str(resolved_policy or ""),
        "needs_human_review": bool(row.get("needs_human_review")),
    }


def compare_evaluator_reports(
    code_report: dict[str, Any],
    llm_report: dict[str, Any],
    *,
    cohorts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    code_rows = {
        _normalize_row(item)["paper_id"]: _normalize_row(item)
        for item in _paper_rows(code_report)
    }
    llm_rows = {
        _normalize_row(item)["paper_id"]: _normalize_row(item)
        for item in _paper_rows(llm_report)
    }
    paper_ids = sorted(set(code_rows) | set(llm_rows))
    paper_comparisons: list[dict[str, Any]] = []
    mismatch_counter: Counter[str] = Counter()
    cohort_lookup: dict[str, str] = {}
    for cohort_name, paper_list in dict(cohorts or {}).items():
        for paper_id in paper_list if isinstance(paper_list, list) else []:
            cohort_lookup[str(paper_id)] = str(cohort_name)
    for paper_id in paper_ids:
        code_row = code_rows.get(paper_id)
        llm_row = llm_rows.get(paper_id)
        if code_row is None or llm_row is None:
            mismatch_counter["missing_paper"] += 1
            paper_comparisons.append(
                {
                    "paper_id": paper_id,
                    "comparison_status": "missing_paper",
                    "verdict_match": False,
                    "reason_code_match": False,
                    "resolved_policy_match": False,
                    "human_review_match": False,
                    "drift_summary": "Paper is missing from one evaluator output.",
                    "cohort": cohort_lookup.get(paper_id, "unassigned"),
                }
            )
            continue
        verdict_match = code_row["verdict"] == llm_row["verdict"]
        reason_code_match = code_row["reason_codes"] == llm_row["reason_codes"]
        resolved_policy_match = (
            code_row["resolved_split_policy"] == llm_row["resolved_split_policy"]
        )
        human_review_match = (
            code_row["needs_human_review"] == llm_row["needs_human_review"]
        )
        mismatches: list[str] = []
        if not verdict_match:
            mismatches.append("verdict")
            mismatch_counter["verdict"] += 1
        if not reason_code_match:
            mismatches.append("reason_codes")
            mismatch_counter["reason_codes"] += 1
        if not resolved_policy_match:
            mismatches.append("resolved_policy")
            mismatch_counter["resolved_policy"] += 1
        if not human_review_match:
            mismatches.append("needs_human_review")
            mismatch_counter["needs_human_review"] += 1
        paper_comparisons.append(
            {
                "paper_id": paper_id,
                "comparison_status": "exact_match" if not mismatches else "drift_detected",
                "verdict_match": verdict_match,
                "reason_code_match": reason_code_match,
                "resolved_policy_match": resolved_policy_match,
                "human_review_match": human_review_match,
                "drift_summary": (
                    "No drift detected."
                    if not mismatches
                    else f"Mismatch in {', '.join(mismatches)}."
                ),
                "cohort": cohort_lookup.get(paper_id, "unassigned"),
            }
        )
    cohort_summary: dict[str, dict[str, int]] = defaultdict(
        lambda: {"paper_count": 0, "exact_match_count": 0}
    )
    for row in paper_comparisons:
        cohort = row["cohort"]
        cohort_summary[cohort]["paper_count"] += 1
        if row["comparison_status"] == "exact_match":
            cohort_summary[cohort]["exact_match_count"] += 1
    exact_match_count = sum(
        1 for item in paper_comparisons if item["comparison_status"] == "exact_match"
    )
    comparison_status = (
        "passed" if exact_match_count == len(paper_comparisons) else "drift_detected"
    )
    return {
        "artifact_id": "paper_dataset_evaluator_comparison",
        "schema_id": "proteosphere-paper-dataset-evaluator-comparison-v1",
        "comparison_status": comparison_status,
        "summary": {
            "paper_count": len(paper_comparisons),
            "exact_match_count": exact_match_count,
            "mismatch_counts": dict(sorted(mismatch_counter.items())),
            "cohorts": dict(cohort_summary),
        },
        "paper_comparisons": paper_comparisons,
    }


def render_comparison_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Paper Dataset Evaluator Comparison",
        "",
        f"- Status: `{report.get('comparison_status', 'unknown')}`",
        f"- Paper count: `{report.get('summary', {}).get('paper_count', 0)}`",
        f"- Exact matches: `{report.get('summary', {}).get('exact_match_count', 0)}`",
        "",
        "## Comparison Table",
        "",
        "| Paper | Status | Verdict | Reasons | Policy | Human review |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report.get("paper_comparisons", []):
        lines.append(
            f"| `{row['paper_id']}` | `{row['comparison_status']}` | `{str(bool(row['verdict_match'])).lower()}` | `{str(bool(row['reason_code_match'])).lower()}` | `{str(bool(row['resolved_policy_match'])).lower()}` | `{str(bool(row['human_review_match'])).lower()}` |"
        )
    return "\n".join(lines) + "\n"
