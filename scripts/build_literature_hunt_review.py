from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_ROOT = Path(
    os.environ.get("PROTEOSPHERE_WAREHOUSE_ROOT", r"D:\ProteoSphere\reference_library")
)
CATALOG_PATH = WAREHOUSE_ROOT / "catalog" / "reference_library.duckdb"
WAREHOUSE_MANIFEST_PATH = WAREHOUSE_ROOT / "warehouse_manifest.json"
SOURCE_REGISTRY_PATH = WAREHOUSE_ROOT / "control" / "source_registry.json"
MANIFEST_PATH = REPO_ROOT / "datasets" / "splits" / "literature_hunt_manifest.json"
OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "literature_hunt_confirmed_dataset_issues.json"
OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "literature_hunt_confirmed_dataset_issues.md"
PER_PAPER_DIR = REPO_ROOT / "artifacts" / "status" / "literature_hunt_confirmed_dataset_issues"


STATUS_LABELS = {
    "confirmed_red_flag": "confirmed red flag",
    "confirmed_blocked_external": "confirmed blocked external benchmark",
    "confirmed_audit_only_noncanonical": "confirmed audit-only / non-canonical",
    "candidate_needs_more_recovery": "candidate needing more recovery",
}

SEVERITY_BY_STATUS = {
    "confirmed_red_flag": "critical",
    "confirmed_blocked_external": "high",
    "confirmed_audit_only_noncanonical": "moderate",
    "candidate_needs_more_recovery": "pending",
}

JOURNAL_WEIGHTS = {
    "Nature Communications": 4.0,
    "Nature Methods": 4.0,
    "Briefings in Bioinformatics": 3.8,
    "Bioinformatics": 3.6,
    "Physical Chemistry Chemical Physics": 3.2,
    "PLOS Computational Biology": 3.2,
    "GigaScience": 3.1,
    "BMC Bioinformatics": 2.9,
    "BMC Genomics": 2.8,
    "Computers in Biology and Medicine": 2.6,
    "International Journal of Biological Macromolecules": 2.5,
    "Cells": 2.3,
}

CLUSTER_TITLES = {
    "direct_split_failure": "Direct Split Failures",
    "blocked_external_validation": "Blocked External Validation",
    "benchmark_family_dependence": "Benchmark-Family Dependence",
    "legacy_benchmark_dependence": "Legacy Benchmark Dependence",
}


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_warehouse_snapshot() -> dict[str, Any]:
    manifest = load_json(WAREHOUSE_MANIFEST_PATH) if WAREHOUSE_MANIFEST_PATH.exists() else {}
    registry = load_json(SOURCE_REGISTRY_PATH) if SOURCE_REGISTRY_PATH.exists() else {}
    default_view = (
        manifest.get("default_view")
        or (manifest.get("logical_defaults") or {}).get("default_view")
        or "best_evidence"
    )
    promoted_families = sorted(
        {
            str(row.get("source_family") or "").strip()
            for row in (registry.get("source_records") or registry.get("records") or [])
            if str(row.get("integration_status") or "").strip().casefold() == "promoted"
            and str(row.get("source_family") or "").strip()
        }
    )
    return {
        "warehouse_root": str(WAREHOUSE_ROOT),
        "catalog_path": str(CATALOG_PATH),
        "manifest_path": str(WAREHOUSE_MANIFEST_PATH),
        "source_registry_path": str(SOURCE_REGISTRY_PATH),
        "default_view": default_view,
        "promoted_source_families": promoted_families,
        "warehouse_manifest_keys": sorted(manifest.keys()),
    }


def normalize_local_artifact(candidate: dict[str, Any]) -> dict[str, Any]:
    row = load_json(Path(candidate["local_artifact_path"]))
    result = {
        "paper_id": candidate["paper_id"],
        "title": candidate["title"],
        "doi": candidate["doi"],
        "journal": candidate["journal"],
        "year": candidate["year"],
        "task_family": candidate["task_family"],
        "benchmark_family": candidate["benchmark_family"],
        "source_mode": candidate["source_mode"],
        "official_evidence_links": candidate["official_evidence_links"],
        "issue_classes": candidate["suspected_issue_classes"],
        "local_evidence_paths": [candidate["local_artifact_path"]],
        "source_row": row,
    }

    verdict = str(row.get("verdict") or "")
    benchmark_family = str(candidate.get("benchmark_family") or "")
    if verdict == "misleading / leakage-prone":
        status = "confirmed_red_flag"
        cluster = "direct_split_failure"
        summary = "Released split logic permits train/test reuse strongly enough that ProteoSphere would block the paper split for training claims."
        consequences = [
            "Performance numbers can be inflated by direct structure or component reuse across partitions.",
            "The split does not support robust claims about independence or generalization.",
        ]
    elif (
        candidate.get("candidate_role") == "main"
        and benchmark_family in {"ppis_train335_family", "hssppi_public_tasks"}
    ):
        status = "confirmed_audit_only_noncanonical"
        cluster = "benchmark_family_dependence"
        summary = "The paper may be paper-faithful within its own benchmark, but the evaluation remains too dependent on a legacy public benchmark family to count as strong evidence of broad generalization."
        consequences = [
            "The paper's main contribution is easier to interpret as within-family leaderboard progress than as an independent benchmark advance.",
            "ProteoSphere would keep this as an audit lane and would ask for at least one out-of-family validation lane before elevating the claim.",
        ]
    elif verdict == "audit-useful but non-canonical":
        status = "confirmed_audit_only_noncanonical"
        cluster = "benchmark_family_dependence"
        summary = "The paper is reproducible and useful for within-family comparison, but the evaluation remains non-canonical because it stays inside an already saturated benchmark family."
        consequences = [
            "Leaderboard gains are easier to interpret as within-family improvements than as evidence of broad external generalization.",
            "ProteoSphere would keep the split as an audit lane rather than a governing benchmark.",
        ]
    elif verdict == "incomplete because required evidence is missing":
        status = "candidate_needs_more_recovery"
        cluster = "legacy_benchmark_dependence"
        summary = "The paper exposes useful benchmark material, but the exact train/test membership is still not fixed enough to audit as a stable held-out split."
        consequences = [
            "Any leakage or independence assessment remains partial until the exact roster is reconstructed.",
            "The benchmark should not be promoted as a stable canonical split yet.",
        ]
    else:
        status = "candidate_needs_more_recovery"
        cluster = "legacy_benchmark_dependence"
        summary = "The current artifact is informative but not strong enough to place the paper on the confirmed shortlist."
        consequences = [
            "Additional split recovery or benchmark mirroring is needed before a stronger claim can be made."
        ]

    result.update(
        {
            "final_status": status,
            "severity": SEVERITY_BY_STATUS[status],
            "issue_cluster": cluster,
            "claimed_split_description": row.get("claimed_split_description", ""),
            "confirmed_issue_summary": summary,
            "overlap_findings": row.get("overlap_findings", {}),
            "leakage_findings": row.get("leakage_findings", {}),
            "source_family_findings": row.get("source_family_findings", []),
            "governed_eligibility_findings": row.get("governed_eligibility_findings", {}),
            "consequences": consequences,
            "recommended_canonical_treatment": row.get("recommended_canonical_treatment", ""),
            "blockers": row.get("blockers", []),
            "warnings": row.get("warnings", []),
            "provenance_notes": row.get("provenance_notes", []),
            "candidate_role": candidate["candidate_role"],
        }
    )
    return result


def normalize_d2cp(candidate: dict[str, Any]) -> dict[str, Any]:
    summary = load_json(Path(candidate["local_artifact_path"]))
    datasets = summary["datasets"]
    direct_overlap = datasets["prodigy78_vs_pdbbind50"]["direct_protein_overlap_count"]
    nanobody_overlap = datasets["prodigy78_vs_nanobody47"]["direct_protein_overlap_count"]
    meta_overlap = datasets["prodigy78_vs_metadynamics19"]["direct_protein_overlap_count"]
    return {
        "paper_id": candidate["paper_id"],
        "title": candidate["title"],
        "doi": candidate["doi"],
        "journal": candidate["journal"],
        "year": candidate["year"],
        "task_family": candidate["task_family"],
        "benchmark_family": candidate["benchmark_family"],
        "source_mode": candidate["source_mode"],
        "official_evidence_links": candidate["official_evidence_links"],
        "issue_classes": candidate["suspected_issue_classes"],
        "local_evidence_paths": [
            candidate["local_artifact_path"],
            str(REPO_ROOT / "docs" / "reports" / "paper_d2cp05644e_forensic_review.md"),
        ],
        "final_status": "confirmed_blocked_external",
        "severity": SEVERITY_BY_STATUS["confirmed_blocked_external"],
        "issue_cluster": "blocked_external_validation",
        "claimed_split_description": (
            "Public materials reconstruct a 78-complex benchmark pool plus three claimed external validation panels: PDBbind-50, nanobody-47, and metadynamics-19."
        ),
        "confirmed_issue_summary": (
            "All three validation lanes fail clean external-benchmark expectations under ProteoSphere logic: the PDBbind panel shows direct protein reuse, the nanobody panel reuses a central antigen target, and the metadynamics panel contains severe exact or near-exact reuse."
        ),
        "overlap_findings": {
            "benchmark_vs_pdbbind50": datasets["prodigy78_vs_pdbbind50"],
            "benchmark_vs_nanobody47": datasets["prodigy78_vs_nanobody47"],
            "benchmark_vs_metadynamics19": datasets["prodigy78_vs_metadynamics19"],
        },
        "leakage_findings": {
            "status": "forensic_audit_confirmed_block",
            "notes": [
                f"PDBbind-50 retains {direct_overlap} direct protein overlaps against the recovered benchmark pool.",
                f"Nanobody-47 retains {nanobody_overlap} direct protein overlaps, concentrated around reused antigen targets.",
                f"Metadynamics-19 retains {meta_overlap} direct protein overlaps and repeated exact complexes, which invalidates it as an independent external panel.",
            ],
        },
        "source_family_findings": [
            "The paper mixes a benchmark pool reconstructed from the authors' public repository with three claimed external validation sources.",
            "Because the external panels are biologically entangled with the training benchmark, the release is useful for forensic auditing but not as a clean canonical benchmark."
        ],
        "governed_eligibility_findings": {
            "status": "audit_only",
            "notes": [
                "ProteoSphere would block all three external panels from governing use without a re-split.",
                "The benchmark pool itself is still under-documented because the paper does not publish a warehouse-native train/test roster."
            ],
        },
        "consequences": [
            "The paper's external validation story overstates independence and likely overstates generalization.",
            "If performance remains modest even under these overlap-contaminated conditions, the real out-of-distribution problem is probably harder than the paper suggests.",
        ],
        "recommended_canonical_treatment": "Treat the paper as a forensic case study. Recover the exact benchmark roster, re-split by accession or family, and keep the original external panels only as blocked audit examples.",
        "blockers": [
            "The paper-internal benchmark split is still under-disclosed even though the effective benchmark pool was reconstructable from the public repository."
        ],
        "warnings": [
            "The paper's supplementary reporting also shows sign-convention ambiguity in some validation tables."
        ],
        "provenance_notes": [
            "Primary evidence came from local forensic recovery artifacts, the paper supplement, and the authors' public repository snapshot.",
            "The warehouse-first policy still governs interpretation, but this paper required deeper recovered public artifacts to resolve the benchmark pool."
        ],
        "candidate_role": candidate["candidate_role"],
    }


def normalize_web_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    role = candidate["candidate_role"]
    if role == "main":
        status = "confirmed_audit_only_noncanonical"
        severity = SEVERITY_BY_STATUS[status]
        cluster = "benchmark_family_dependence"
        consequences = [
            "The paper may still be useful for within-family comparison, but not as strong evidence of external robustness.",
            "ProteoSphere would not treat this as a governing benchmark without at least one out-of-family validation lane."
        ]
    else:
        status = "candidate_needs_more_recovery"
        severity = SEVERITY_BY_STATUS[status]
        cluster = "legacy_benchmark_dependence"
        consequences = [
            "The benchmark dependence is clear, but the exact split mechanics still need more recovery before the paper belongs on the confirmed shortlist."
        ]
    claimed = (
        f"The paper appears to evaluate primarily on the `{candidate['benchmark_family']}` benchmark family rather than on a newly released independent split."
    )
    summary = (
        "Web-verified evidence ties the paper to an already reused benchmark family, which is enough to flag insufficient dataset evaluation for broad generalization claims."
    )
    return {
        "paper_id": candidate["paper_id"],
        "title": candidate["title"],
        "doi": candidate["doi"],
        "journal": candidate["journal"],
        "year": candidate["year"],
        "task_family": candidate["task_family"],
        "benchmark_family": candidate["benchmark_family"],
        "source_mode": candidate["source_mode"],
        "official_evidence_links": candidate["official_evidence_links"],
        "issue_classes": candidate["suspected_issue_classes"],
        "local_evidence_paths": [],
        "final_status": status,
        "severity": severity,
        "issue_cluster": cluster,
        "claimed_split_description": claimed,
        "confirmed_issue_summary": summary,
        "overlap_findings": {
            "status": "benchmark_family_confirmed",
            "notes": candidate.get("web_evidence_snippets", []),
        },
        "leakage_findings": {
            "status": "web_verified_but_not_fully_rostered",
            "notes": [
                "The exact paper roster is not mirrored locally yet, so the confirmation here is benchmark-family dependence rather than exact chain-level overlap counts."
            ]
            + list(candidate.get("web_evidence_snippets", [])),
        },
        "source_family_findings": [
            "The benchmark families cited here are structurally grounded in the warehouse, but the exact paper rosters are not mirrored yet."
        ],
        "governed_eligibility_findings": {
            "status": "audit_only" if role == "main" else "candidate_only",
            "notes": [
                "ProteoSphere would not promote this benchmark story as a governing release benchmark on web evidence alone.",
                "The most defensible current claim is that the paper stays inside a heavily reused benchmark family."
            ],
        },
        "consequences": consequences,
        "recommended_canonical_treatment": (
            "Keep the paper as a benchmark-dependence case study and require at least one independent out-of-family validation split before treating the headline gains as broad generalization evidence."
        ),
        "blockers": [] if role == "main" else ["Exact split membership still needs local recovery or mirrored artifacts."],
        "warnings": [],
        "provenance_notes": [
            "This record was confirmed from official article pages or indexable article snippets plus the known benchmark-family lineage already established in ProteoSphere.",
            "No raw/archive fallback was used for this candidate."
        ],
        "candidate_role": role,
    }


def build_record(candidate: dict[str, Any]) -> dict[str, Any]:
    if candidate["paper_id"] == "d2cp05644e_2023":
        return normalize_d2cp(candidate)
    if candidate["source_mode"] in {"local_artifact", "local_forensic_audit"}:
        return normalize_local_artifact(candidate)
    return normalize_web_candidate(candidate)


def build_controls(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    for item in manifest.get("controls", []):
        row = load_json(Path(item["local_artifact_path"]))
        controls.append(
            {
                "paper_id": item["paper_id"],
                "title": item["title"],
                "doi": item["doi"],
                "journal": item["journal"],
                "year": item["year"],
                "task_family": item["task_family"],
                "reason_for_control": item["reason_for_control"],
                "verdict": row.get("verdict"),
                "project_status": row.get("project_status"),
                "benchmark_family": row.get("benchmark_family"),
                "local_artifact_path": item["local_artifact_path"],
            }
        )
    return controls


def compute_publication_score(row: dict[str, Any]) -> float:
    status_weight = {
        "confirmed_red_flag": 5.0,
        "confirmed_blocked_external": 4.6,
        "confirmed_audit_only_noncanonical": 3.2,
        "candidate_needs_more_recovery": 1.6,
    }[row["final_status"]]
    journal_weight = JOURNAL_WEIGHTS.get(row["journal"], 2.0)
    issue_weight = 0.25 * len(row["issue_classes"])
    return round(status_weight + journal_weight + issue_weight, 2)


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    summary = report["summary"]
    lines.append("# ProteoSphere Literature Hunt: Confirmed Dataset-Quality Failures\n")
    lines.append("## Executive Summary\n")
    lines.append(
        f"This hunt reviewed `{summary['candidate_count']}` candidate papers and promoted `{summary['confirmed_main_shortlist_count']}` to the confirmed shortlist. "
        f"The shortlist includes `{summary['status_counts'].get('confirmed_red_flag', 0)}` direct split failures, "
        f"`{summary['status_counts'].get('confirmed_blocked_external', 0)}` blocked external-validation stories, and "
        f"`{summary['status_counts'].get('confirmed_audit_only_noncanonical', 0)}` benchmark-dependence cases where the paper is publishable and reproducible but still too weak for strong generalization claims under ProteoSphere logic."
    )
    lines.append("")
    lines.append("The core pattern is that respected, peer-reviewed papers can still fail dataset review for different reasons. Some fail because the released split mechanism itself leaks. Others fail because the claimed external set overlaps biologically with training. A large third group fails more quietly: the paper reports large gains, but almost all evaluation remains trapped inside one inherited benchmark family.")
    lines.append("")
    lines.append("## Best Examples For Publication\n")
    for row in report["best_examples"]:
        lines.append(
            f"- `{row['paper_id']}` ({row['journal']}, {row['year']}): {row['title']} — {row['confirmed_issue_summary']}"
        )
    lines.append("")

    grouped = defaultdict(list)
    for row in report["papers"]:
        grouped[row["final_status"]].append(row)

    for status in (
        "confirmed_red_flag",
        "confirmed_blocked_external",
        "confirmed_audit_only_noncanonical",
        "candidate_needs_more_recovery",
    ):
        rows = grouped.get(status, [])
        if not rows:
            continue
        lines.append(f"## {STATUS_LABELS[status].title()}\n")
        rows = sorted(rows, key=lambda item: (-item["publication_score"], item["year"], item["paper_id"]))
        for row in rows:
            lines.append(f"### {row['title']}\n")
            lines.append(f"- DOI: {row['doi']}")
            lines.append(f"- Journal: {row['journal']} ({row['year']})")
            lines.append(f"- Task family: `{row['task_family']}`")
            lines.append(f"- Benchmark family: `{row['benchmark_family']}`")
            lines.append(f"- Issue cluster: `{row['issue_cluster']}`")
            lines.append(f"- Why it is flagged: {row['confirmed_issue_summary']}")
            if row.get("claimed_split_description"):
                lines.append(f"- Claimed split: {row['claimed_split_description']}")
            leakage_notes = (row.get("leakage_findings") or {}).get("notes") or []
            if leakage_notes:
                lines.append(f"- Key evidence: {leakage_notes[0]}")
            if len(leakage_notes) > 1:
                lines.append(f"- Extra evidence: {leakage_notes[1]}")
            if row.get("consequences"):
                lines.append(f"- Consequence: {row['consequences'][0]}")
            if row.get("recommended_canonical_treatment"):
                lines.append(f"- ProteoSphere treatment: {row['recommended_canonical_treatment']}")
            if row.get("blockers"):
                lines.append(f"- Blockers: {'; '.join(row['blockers'])}")
            lines.append("")

    lines.append("## Benchmark-Family Clusters\n")
    for family, count in sorted(report["summary"]["benchmark_family_counts"].items()):
        lines.append(f"- `{family}`: {count} papers")
    lines.append("")

    lines.append("## Non-Failure Controls\n")
    for control in report["controls"]:
        lines.append(
            f"- `{control['paper_id']}` ({control['journal']}, {control['year']}): {control['reason_for_control']} "
            f"Current ProteoSphere verdict: `{control['verdict']}`."
        )
    lines.append("")

    lines.append("## Warehouse Sufficiency Notes\n")
    for note in report["warehouse_sufficiency_notes"]:
        lines.append(f"- {note}")
    lines.append("")
    lines.append("## Raw / Archive Fallback Notes\n")
    for note in report["raw_archive_fallback_notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    os.environ["PROTEOSPHERE_WAREHOUSE_ROOT"] = str(WAREHOUSE_ROOT)
    manifest = load_json(MANIFEST_PATH)
    warehouse = read_warehouse_snapshot()
    papers = [build_record(candidate) for candidate in manifest["candidates"]]
    for row in papers:
        row["publication_score"] = compute_publication_score(row)

    confirmed = [row for row in papers if row["final_status"] != "candidate_needs_more_recovery"]
    best_examples = sorted(confirmed, key=lambda item: (-item["publication_score"], item["paper_id"]))[:8]
    controls = build_controls(manifest)

    status_counts = Counter(row["final_status"] for row in papers)
    issue_counts = Counter(issue for row in papers for issue in row["issue_classes"])
    benchmark_counts = Counter(row["benchmark_family"] for row in papers)
    severity_counts = Counter(row["severity"] for row in papers)
    cluster_counts = Counter(row["issue_cluster"] for row in papers)

    report = {
        "artifact_id": "literature_hunt_confirmed_dataset_issues",
        "schema_id": "proteosphere-literature-hunt-2026-04-13",
        "status": "complete",
        "generated_at": _utc_now(),
        **warehouse,
        "discovery_queries": manifest.get("discovery_queries", []),
        "summary": {
            "candidate_count": len(papers),
            "confirmed_main_shortlist_count": len(confirmed),
            "backlog_count": status_counts.get("candidate_needs_more_recovery", 0),
            "control_count": len(controls),
            "status_counts": dict(status_counts),
            "severity_counts": dict(severity_counts),
            "issue_class_counts": dict(issue_counts),
            "benchmark_family_counts": dict(benchmark_counts),
            "issue_cluster_counts": dict(cluster_counts),
            "confirmed_shortlist_ids": [row["paper_id"] for row in confirmed],
            "best_example_ids": [row["paper_id"] for row in best_examples],
        },
        "warehouse_sufficiency_notes": [
            "The warehouse remains the governing read surface and is strong enough to contextualize benchmark-family reuse, source-family status, and canonical split-policy language.",
            "Exact paper roster overlap is still limited whenever a paper inherits a public benchmark but does not mirror the concrete split files into the local audit workspace.",
            "That limitation is precisely why benchmark-family dependence is reported separately from direct overlap: ProteoSphere should not over-claim what the evidence surface cannot yet prove."
        ],
        "raw_archive_fallback_notes": [
            "No raw or archive fallback was needed for the main shortlist in this run.",
            "The D2CP05644E case relies on previously recovered public artifacts already materialized into the audit workspace, not on an unrestricted crawl of raw source trees."
        ],
        "controls": controls,
        "best_examples": best_examples,
        "papers": papers,
    }

    write_json(OUTPUT_JSON, report)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(render_markdown(report), encoding="utf-8")
    PER_PAPER_DIR.mkdir(parents=True, exist_ok=True)
    for row in papers:
        write_json(PER_PAPER_DIR / f"{row['paper_id']}.json", row)

    confirmed_ids = set(report["summary"]["confirmed_shortlist_ids"])
    assert "baranwal2022struct2graph" in confirmed_ids
    assert "d2cp05644e_2023" in confirmed_ids
    assert "graphppis2021" not in confirmed_ids

    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_MD}")
    print(f"Wrote {len(papers)} per-paper artifacts to {PER_PAPER_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
