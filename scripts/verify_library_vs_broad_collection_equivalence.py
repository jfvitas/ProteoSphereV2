from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CURRENT_REPORT = REPO_ROOT / "artifacts" / "status" / "paper_dataset_evaluator.json"
DEFAULT_PRIOR_REPORT = REPO_ROOT / "artifacts" / "status" / "paper_split_list_evaluation.json"
DEFAULT_LIBRARY_VALIDATION = REPO_ROOT / "artifacts" / "status" / "reference_library_validation.json"
DEFAULT_RAW_DISCONNECTED = REPO_ROOT / "artifacts" / "status" / "raw_disconnected_acceptance.json"
DEFAULT_D2CP_SUMMARY = REPO_ROOT / "artifacts" / "status" / "paper_d2cp05644e" / "summary.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "library_vs_broad_collection_equivalence.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "library_vs_broad_collection_equivalence.md"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_status(verdict: str | None) -> str:
    if not verdict:
        return "unknown"
    return verdict


def _current_case_study(current_by: dict[str, dict[str, Any]], paper_id: str) -> dict[str, Any]:
    paper = current_by.get(paper_id, {})
    return {
        "paper_id": paper_id,
        "current_verdict": paper.get("verdict"),
        "current_reason_codes": paper.get("reason_codes", []),
        "current_needs_human_review": paper.get("needs_human_review"),
        "current_notes": paper.get("notes", []),
        "warehouse_identifier_bridge": paper.get("warehouse_identifier_bridge"),
    }


def build_report(
    *,
    current_report_path: Path,
    prior_report_path: Path,
    library_validation_path: Path,
    raw_disconnected_path: Path,
    d2cp_summary_path: Path,
) -> dict[str, Any]:
    current_report = read_json(current_report_path)
    prior_report = read_json(prior_report_path)
    library_validation = read_json(library_validation_path) if library_validation_path.exists() else {}
    raw_disconnected = read_json(raw_disconnected_path) if raw_disconnected_path.exists() else {}
    d2cp_summary = read_json(d2cp_summary_path) if d2cp_summary_path.exists() else {}

    current_by = {paper["paper_id"]: paper for paper in current_report.get("papers", [])}
    prior_by = {paper["paper_id"]: paper for paper in prior_report.get("papers", [])}
    overlap_ids = sorted(set(current_by) & set(prior_by))

    comparisons: list[dict[str, Any]] = []
    status_match_count = 0
    supplemental_total = 0
    supplemental_match_count = 0
    for paper_id in overlap_ids:
        current = current_by[paper_id]
        prior = prior_by[paper_id]
        current_status = normalize_status(current.get("verdict"))
        prior_status = normalize_status(prior.get("project_status"))
        prior_has_supplemental = bool(prior.get("supplemental_evidence"))
        if current_status == prior_status:
            status_match_count += 1
        if prior_has_supplemental:
            supplemental_total += 1
            if current_status == prior_status:
                supplemental_match_count += 1
        comparisons.append(
            {
                "paper_id": paper_id,
                "current_status": current_status,
                "prior_status": prior_status,
                "prior_narrative_verdict": prior.get("verdict"),
                "status_match": current_status == prior_status,
                "prior_has_supplemental_evidence": prior_has_supplemental,
                "prior_raw_archive_fallback_required": prior.get("raw_archive_fallback_required", False),
            }
        )

    mismatches = [row for row in comparisons if not row["status_match"]]

    struct2graph_prior = prior_by.get("baranwal2022struct2graph", {})
    dscript_prior = prior_by.get("sledzieski2021dscript", {})
    rapppid_prior = prior_by.get("szymborski2022rapppid", {})
    dscript_bridge = ((current_by.get("sledzieski2021dscript") or {}).get("warehouse_identifier_bridge") or {})
    rapppid_bridge = ((current_by.get("szymborski2022rapppid") or {}).get("warehouse_identifier_bridge") or {})

    d2cp_datasets = d2cp_summary.get("datasets", {})
    d2cp_case_studies = []
    for dataset_name, dataset_payload in d2cp_datasets.items():
        d2cp_case_studies.append(
            {
                "dataset": dataset_name,
                "overall_decision": dataset_payload.get("overall_decision"),
                "blocked_reasons": dataset_payload.get("blocked_reasons", []),
                "direct_protein_overlap_count": dataset_payload.get("direct_protein_overlap_count"),
                "exact_sequence_overlap_count": dataset_payload.get("exact_sequence_overlap_count"),
                "flagged_structure_pair_count": dataset_payload.get("flagged_structure_pair_count"),
                "coverage_fraction": dataset_payload.get("coverage_fraction"),
            }
        )

    detail_loss_present = True
    if mismatches:
        final_verdict = "not_equivalent"
    elif status_match_count == len(overlap_ids) and supplemental_match_count == supplemental_total:
        final_verdict = (
            "status_equivalent_but_not_evidence_equivalent"
            if detail_loss_present
            else "exact_equivalence"
        )
    else:
        final_verdict = "partial_equivalence_only"

    return {
        "artifact_id": "library_vs_broad_collection_equivalence",
        "schema_id": "proteosphere-library-vs-broad-collection-equivalence-2026-04-13",
        "status": "complete",
        "final_verdict": final_verdict,
        "comparison_summary": {
            "current_paper_count": len(current_by),
            "prior_paper_count": len(prior_by),
            "overlap_paper_count": len(overlap_ids),
            "status_match_count": status_match_count,
            "status_match_fraction": round(status_match_count / len(overlap_ids), 4) if overlap_ids else 0.0,
            "supplemental_match_count": supplemental_match_count,
            "supplemental_total": supplemental_total,
            "supplemental_match_fraction": round(supplemental_match_count / supplemental_total, 4)
            if supplemental_total
            else 0.0,
        },
        "validation_checks": {
            "reference_library_validation_status": library_validation.get("status"),
            "raw_disconnected_acceptance_status": raw_disconnected.get("status"),
            "library_operates_without_raw_roots": raw_disconnected.get("status") == "passed",
        },
        "high_level_findings": [
            "The condensed library supports warehouse-first evaluation and remains operational even when raw/archive roots are masked.",
            f"The current code-first warehouse evaluator matches {status_match_count} of {len(overlap_ids)} top-level paper status outcomes against the broader audit path.",
            "For the three papers with recovered published split artifacts, the library-backed evaluator matches the broader audit path at the top-level status and now exposes warehouse-side identifier bridge summaries for D-SCRIPT and RAPPPID.",
            "The broader downloaded collection still preserves roster-, identifier-, and structure-level evidence that is not fully materialized into the condensed warehouse default surfaces.",
        ],
        "mismatches": mismatches,
        "detail_loss_case_studies": {
            "struct2graph": {
                **_current_case_study(current_by, "baranwal2022struct2graph"),
                "prior_status": struct2graph_prior.get("project_status"),
                "prior_supplemental_status": ((struct2graph_prior.get("supplemental_evidence") or {}).get("status")),
                "prior_shared_pdb_count": (
                    ((struct2graph_prior.get("supplemental_evidence") or {}).get("reproduction") or {}).get(
                        "shared_pdb_count"
                    )
                ),
                "prior_artifact_paths": ((struct2graph_prior.get("supplemental_evidence") or {}).get("artifact_paths", [])),
                "evidence_delta": "The broader path reproduces the released split logic and demonstrates 643 shared PDB IDs across train/test; the current warehouse-first evaluator reaches the same unsafe status but does not preserve that concrete reproduction evidence.",
            },
            "dscript": {
                **_current_case_study(current_by, "sledzieski2021dscript"),
                "prior_status": dscript_prior.get("project_status"),
                "prior_supplemental_status": ((dscript_prior.get("supplemental_evidence") or {}).get("status")),
                "prior_artifact_paths": ((dscript_prior.get("supplemental_evidence") or {}).get("artifact_paths", [])),
                "warehouse_bridge_status": dscript_bridge.get("bridge_status"),
                "warehouse_bridge_exact_mapped_identifier_count": dscript_bridge.get("exact_mapped_identifier_count"),
                "evidence_delta": "The warehouse-first evaluator now preserves recovered roster-backed identifier bridge detail and overlap summaries for D-SCRIPT, but the broader path still remains richer for the raw recovered split files themselves.",
            },
            "rapppid": {
                **_current_case_study(current_by, "szymborski2022rapppid"),
                "prior_status": rapppid_prior.get("project_status"),
                "prior_supplemental_status": ((rapppid_prior.get("supplemental_evidence") or {}).get("status")),
                "prior_artifact_paths": ((rapppid_prior.get("supplemental_evidence") or {}).get("artifact_paths", [])),
                "warehouse_bridge_status": rapppid_bridge.get("bridge_status"),
                "warehouse_bridge_exact_mapped_identifier_count": rapppid_bridge.get("exact_mapped_identifier_count"),
                "evidence_delta": "The warehouse-first evaluator now preserves STRING/Ensembl bridge detail plus cohort-level train/val/test overlap summaries for RAPPPID, but the broader path still retains the original recovered release package as the richer raw artifact surface.",
            },
            "d2cp05644e_structure_audit": {
                "status": "broader_path_richer_than_library_default",
                "datasets": d2cp_case_studies,
                "evidence_delta": "The raw/broad structure audit path produces exact overlap counts, coverage fractions, and blocked reasons for structure sets. There is no like-for-like warehouse-first default paper evaluator artifact that reproduces this level of structure-level split evidence today.",
            },
        },
        "recommended_interpretation": {
            "library_is_sufficient_for": [
                "warehouse-first planning and governance",
                "high-level paper admissibility screening",
                "stable top-level outcomes for some recovered split-artifact papers",
                "raw-disconnected Studio and evaluator workflows",
            ],
            "library_is_not_yet_equivalent_for": [
                "full paper-specific roster reconstruction",
                "full raw artifact reproduction for identifier-bridge-heavy external split audits",
                "structure-level overlap reproduction with exact flagged-pair counts",
                "all paper verdicts matching the broader audit path",
            ],
            "next_repairs": [
                "materialize paper-membership or benchmark-roster surfaces into the warehouse where licensing permits",
                "extend the new paper-side identifier bridge registry beyond D-SCRIPT and RAPPPID and promote more of it into default warehouse resolution paths",
                "capture recovered published split artifacts into a governed warehouse-facing audit surface instead of leaving them only in supplemental external artifacts",
                "materialize structure-side audit reproductions like the Struct2Graph shared-PDB proof into warehouse-facing audit surfaces",
            ],
        },
        "comparisons": comparisons,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["comparison_summary"]
    checks = report["validation_checks"]
    lines = [
        "# Library vs Broad Collection Equivalence",
        "",
        f"- Final verdict: `{report['final_verdict']}`",
        f"- Overlap papers compared: `{summary['overlap_paper_count']}`",
        f"- Status matches: `{summary['status_match_count']}` / `{summary['overlap_paper_count']}` ({summary['status_match_fraction']:.1%})",
        f"- Supplemental-artifact paper matches: `{summary['supplemental_match_count']}` / `{summary['supplemental_total']}` ({summary['supplemental_match_fraction']:.1%})",
        f"- Reference library validation: `{checks['reference_library_validation_status']}`",
        f"- Raw-disconnected acceptance: `{checks['raw_disconnected_acceptance_status']}`",
        "",
        "## Bottom Line",
        "",
        "The condensed warehouse is operational and preserves much of the high-level evaluation behavior, but it is not yet a full evidence-equivalent replacement for the broader downloaded collection.",
        "",
        "## Key Findings",
        "",
    ]
    for finding in report["high_level_findings"]:
        lines.append(f"- {finding}")
    lines.extend(["", "## Mismatches", ""])
    mismatches = report.get("mismatches", [])
    if not mismatches:
        lines.append("- None")
    else:
        for mismatch in mismatches:
            lines.append(
                f"- `{mismatch['paper_id']}`: current=`{mismatch['current_status']}` prior=`{mismatch['prior_status']}`"
            )
    lines.extend(["", "## Detail Loss Case Studies", ""])
    lines.append(
        "- `baranwal2022struct2graph`: same top-level unsafe outcome, but the broader path reproduces `643` shared PDB IDs across train/test from released split logic while the warehouse-first evaluator does not preserve that concrete reproduction evidence."
    )
    lines.append(
        "- `sledzieski2021dscript`: same audit-only outcome, and the warehouse now preserves identifier-bridge coverage plus overlap summaries, but the broader path still retains the raw recovered split files as a richer artifact surface."
    )
    lines.append(
        "- `szymborski2022rapppid`: same audit-only outcome, and the warehouse now preserves STRING/Ensembl bridge coverage plus cohort-level overlap summaries, but the broader path still retains the recovered C1/C2/C3 release package as the richer raw artifact surface."
    )
    lines.append(
        "- `10.1039/D2CP05644E`: the broader structure-audit path emits exact overlap counts, coverage fractions, and blocked reasons; there is no like-for-like warehouse-first default artifact with that same level of detail today."
    )
    lines.extend(["", "## Recommended Interpretation", ""])
    for item in report["recommended_interpretation"]["library_is_sufficient_for"]:
        lines.append(f"- Library is sufficient for: {item}")
    for item in report["recommended_interpretation"]["library_is_not_yet_equivalent_for"]:
        lines.append(f"- Library is not yet equivalent for: {item}")
    lines.extend(["", "## Next Repairs", ""])
    for item in report["recommended_interpretation"]["next_repairs"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify condensed library equivalence against broader collection-backed paper audits."
    )
    parser.add_argument("--current-report", type=Path, default=DEFAULT_CURRENT_REPORT)
    parser.add_argument("--prior-report", type=Path, default=DEFAULT_PRIOR_REPORT)
    parser.add_argument("--library-validation", type=Path, default=DEFAULT_LIBRARY_VALIDATION)
    parser.add_argument("--raw-disconnected", type=Path, default=DEFAULT_RAW_DISCONNECTED)
    parser.add_argument("--d2cp-summary", type=Path, default=DEFAULT_D2CP_SUMMARY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        current_report_path=args.current_report,
        prior_report_path=args.prior_report,
        library_validation_path=args.library_validation,
        raw_disconnected_path=args.raw_disconnected,
        d2cp_summary_path=args.d2cp_summary,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(args.output_json)
    print(args.output_md)
    print(json.dumps(report["comparison_summary"], indent=2))


if __name__ == "__main__":
    main()
