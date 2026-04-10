from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.modality_readiness_ladder import LADDER_ORDER
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from modality_readiness_ladder import LADDER_ORDER

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ELIGIBILITY_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_SCOPE_AUDIT = REPO_ROOT / "artifacts" / "status" / "p29_scope_completeness_audit.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "missing_data_policy_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "missing_data_policy_preview.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_missing_data_policy_preview(
    eligibility_matrix: dict[str, Any],
    scope_audit: dict[str, Any],
) -> dict[str, Any]:
    summary = eligibility_matrix.get("summary", {})
    task_status_counts = summary.get("task_status_counts", {})
    category_counts = summary.get("primary_missing_data_class_counts", {})
    modality_readiness_counts = summary.get("modality_readiness_counts", {})
    top_acquisitions = [
        {
            "rank": row.get("rank"),
            "target": row.get("target"),
            "why": row.get("why"),
        }
        for row in (scope_audit.get("top_next_acquisitions") or [])[:6]
        if isinstance(row, dict)
    ]

    return {
        "artifact_id": "missing_data_policy_preview",
        "schema_id": "proteosphere-missing-data-policy-preview-2026-04-02",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "category_counts": category_counts,
        "task_status_counts": task_status_counts,
        "modality_readiness_counts": modality_readiness_counts,
        "modality_readiness_ladder": [
            {"rank": index + 1, "label": label}
            for index, label in enumerate(LADDER_ORDER)
        ],
        "policy_categories": [
            {
                "category": "eligible_for_task",
                "meaning": (
                    "Safe to include in the emitted cohort for that specific "
                    "task under the current truth surfaces."
                ),
                "rule": (
                    "Only use when required evidence is present in the "
                    "current protected packet state or grounded lightweight "
                    "family."
                ),
            },
            {
                "category": "library_only",
                "meaning": (
                    "Keep the accession in the lightweight library and audits, "
                    "but do not use it for that specific emitted task yet."
                ),
                "rule": (
                    "Use when the broader system likely has data, but the "
                    "current compact family is not yet materialized for "
                    "the task."
                ),
            },
            {
                "category": "audit_only",
                "meaning": (
                    "Retain only for bias measurement, completeness reporting, "
                    "and manual review."
                ),
                "rule": (
                    "Use when the accession is visible in surrounding surfaces "
                    "but not sufficiently represented for task execution."
                ),
            },
            {
                "category": "blocked_pending_acquisition",
                "meaning": (
                    "Do not emit for that task until real upstream data is "
                    "acquired or materialized."
                ),
                "rule": (
                    "Use when the required modality is missing in the "
                    "protected packet latest or absent from grounded "
                    "lightweight evidence."
                ),
            },
            {
                "category": "candidate_only_non_governing",
                "meaning": (
                    "Visible for operator review and library context, but "
                    "cannot govern splits, leakage, or release-grade claims."
                ),
                "rule": (
                    "Use for bridge or preview rows like Q9NZD4 until "
                    "grounded evidence exists."
                ),
            },
        ],
        "policy_rules": [
            {
                "rule_id": "retain_nulls_with_provenance",
                "decision": (
                    "Leave unavailable scientific fields blank/null and keep "
                    "provenance flags explicit."
                ),
            },
            {
                "rule_id": "do_not_delete_from_library_by_default",
                "decision": (
                    "Keep accessions in the lightweight library unless they "
                    "are invalid, orphaned, or exact redundant copies; "
                    "missing modalities alone are not a deletion reason."
                ),
            },
            {
                "rule_id": "gate_emitted_training_sets_by_task",
                "decision": (
                    "Exclude examples from a generated cohort only when the "
                    "selected task requires a modality that is not "
                    "eligible_for_task."
                ),
            },
            {
                "rule_id": "candidate_only_rows_non_governing",
                "decision": (
                    "Never let candidate-only rows govern split, leakage, "
                    "consensus, or release-grade decisions."
                ),
            },
            {
                "rule_id": "scrape_as_provenance_tagged_enrichment",
                "decision": (
                    "Use scraping and web enrichment as a targeted support "
                    "lane for breadth holes, tagging source quality and "
                    "keeping weaker evidence non-governing until validated."
                ),
            },
        ],
        "task_policies": [
            {
                "task_id": "protein_reference",
                "default_behavior": (
                    "retain in library and allow eligibility when a protein "
                    "summary exists"
                ),
                "current_status_counts": task_status_counts.get("protein_reference", {}),
                "examples": {
                    "eligible_for_task": ["P00387", "P04637"],
                    "audit_only": ["Q9UCM0"],
                },
            },
            {
                "task_id": "full_packet_current_latest",
                "default_behavior": "emit only if the current protected packet latest is complete",
                "current_status_counts": task_status_counts.get("full_packet_current_latest", {}),
                "examples": {
                    "eligible_for_task": ["P04637", "P31749", "P69905"],
                    "blocked_pending_acquisition": ["P09105", "Q2TAC2", "Q9UCM0"],
                },
            },
            {
                "task_id": "grounded_ligand_similarity_preview",
                "default_behavior": (
                    "use grounded ligand rows when present; keep "
                    "candidate-only ligand rows visible but non-governing"
                ),
                "current_status_counts": task_status_counts.get(
                    "grounded_ligand_similarity_preview",
                    {},
                ),
                "examples": {
                    "eligible_for_task": ["P00387"],
                    "candidate_only_non_governing": ["Q9NZD4"],
                    "library_only": ["P04637", "P31749", "P69905"],
                    "blocked_pending_acquisition": ["P09105", "Q2TAC2", "Q9UCM0"],
                },
            },
        ],
        "scrape_and_enrichment_priorities": {
            "scope_judgment": scope_audit.get("scope_judgment"),
            "top_next_acquisitions": top_acquisitions,
            "policy_note": (
                "Prefer curated interaction networks, motif channels, "
                "kinetics, and sequence-depth expansion before broad ad hoc "
                "scraping; accession-specific scrape fills should remain "
                "provenance-tagged support lanes first."
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a policy surface for how the lightweight library and training-set "
                "creator should behave around missing data. It does not mutate packets, "
                "it does not delete accessions, and it does not imply that scrape-based "
                "fills are already present."
            ),
            "report_only": True,
            "missing_values_imputed": False,
            "candidate_only_rows_non_governing": True,
            "deletion_default": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Missing Data Policy Preview",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        "",
        "## Category Counts",
        "",
    ]
    for category, count in payload["category_counts"].items():
        lines.append(f"- `{category}`: `{count}`")
    lines.extend(["", "## Core Rules", ""])
    for row in payload["policy_rules"]:
        lines.append(f"- `{row['rule_id']}`: {row['decision']}")
    lines.extend(["", "## Scrape / Enrichment Priorities", ""])
    for row in payload["scrape_and_enrichment_priorities"]["top_next_acquisitions"]:
        lines.append(f"- `{row['rank']}` `{row['target']}`: {row['why']}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the missing-data policy preview.")
    parser.add_argument("--eligibility-matrix", type=Path, default=DEFAULT_ELIGIBILITY_MATRIX)
    parser.add_argument("--scope-audit", type=Path, default=DEFAULT_SCOPE_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = build_missing_data_policy_preview(
        _read_json(args.eligibility_matrix),
        _read_json(args.scope_audit),
    )
    _write_json(args.output, payload)
    _write_text(args.markdown_output, render_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            "Missing-data policy preview exported: "
            f"categories={len(payload['policy_categories'])} "
            f"scrape_priorities={len(payload['scrape_and_enrichment_priorities']['top_next_acquisitions'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
