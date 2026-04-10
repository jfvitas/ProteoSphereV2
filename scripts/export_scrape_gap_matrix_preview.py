from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.overnight_planning_common import (  # noqa: E402
    REPO_ROOT as COMMON_REPO_ROOT,
)
from scripts.overnight_planning_common import (  # noqa: E402
    load_procurement_status_board,
    load_scrape_readiness_registry,
    load_source_coverage_matrix,
    normalize_list,
    source_row_map,
    status_rank,
    write_json,
    write_text,
)

assert REPO_ROOT == COMMON_REPO_ROOT

DEFAULT_SOURCE_COVERAGE_MATRIX = REPO_ROOT / "artifacts" / "status" / "source_coverage_matrix.json"
DEFAULT_SCRAPE_READINESS_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "scrape_readiness_registry_preview.json"
)
DEFAULT_PROCUREMENT_STATUS_BOARD = (
    REPO_ROOT / "artifacts" / "status" / "procurement_status_board.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "scrape_gap_matrix_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "scrape_gap_matrix_preview.md"
DEFAULT_STRING_MATERIALIZATION = (
    REPO_ROOT / "artifacts" / "status" / "string_interaction_materialization_preview.json"
)
DEFAULT_PDBBIND_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "pdbbind_registry_preview.json"
)
DEFAULT_PDBBIND_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "pdbbind_validation_preview.json"
)
DEFAULT_ELM_SUPPORT = REPO_ROOT / "artifacts" / "status" / "elm_support_preview.json"
DEFAULT_ELM_SUPPORT_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "elm_support_validation_preview.json"
)
DEFAULT_SABIO_SUPPORT = REPO_ROOT / "artifacts" / "status" / "sabio_rk_support_preview.json"
DEFAULT_SABIO_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "sabio_rk_support_validation.json"
)


LANE_SPECS: list[dict[str, Any]] = [
    {
        "lane_id": "uniprot_sequence_backbone",
        "lane_label": "UniProt / UniRef / ID mapping backbone",
        "source_names": ["uniprot"],
        "supporting_scripts": [
            "execution/acquire/uniprot_snapshot.py",
            "scripts/watch_uniprot_direct_completion.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/source_coverage_matrix.json",
            "artifacts/runtime/procurement_supervisor_state.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "This lane is already backed by real acquisition and direct completion "
            "watching, so it is fully implemented rather than planned."
        ),
    },
    {
        "lane_id": "rcsb_pdbe_sifts_structure_backbone",
        "lane_label": "RCSB / PDBe / SIFTS structure backbone",
        "source_names": ["rcsb_pdbe"],
        "supporting_scripts": [
            "execution/acquire/rcsb_pdbe_snapshot.py",
            "scripts/export_pdb_enrichment_scrape_registry_preview.py",
            "scripts/export_pdb_enrichment_harvest_preview.py",
            "scripts/export_pdb_enrichment_validation_preview.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/pdb_enrichment_scrape_registry_preview.json",
            "artifacts/status/pdb_enrichment_harvest_preview.json",
            "artifacts/status/pdb_enrichment_validation_preview.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "The structure enrichment lane already has scrape registry, harvest, "
            "and validation surfaces, so it is implemented end to end."
        ),
    },
    {
        "lane_id": "bindingdb_assay_bridge_backbone",
        "lane_label": "BindingDB assay / bridge backbone",
        "source_names": ["bindingdb"],
        "supporting_scripts": [
            "execution/acquire/bindingdb_snapshot.py",
            "execution/acquire/bindingdb_dump_extract.py",
            "scripts/export_binding_measurement_registry_preview.py",
            "scripts/export_binding_measurement_validation_preview.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/binding_measurement_registry_preview.json",
            "artifacts/status/binding_measurement_validation_preview.json",
            "artifacts/status/bindingdb_structure_bridge_preview.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "BindingDB has a real acquisition lane plus bridge and measurement "
            "previews, so the backbone is implemented."
        ),
    },
    {
        "lane_id": "biogrid_interaction_backbone",
        "lane_label": "BioGRID interaction backbone",
        "source_names": ["biogrid"],
        "supporting_scripts": [
            "execution/acquire/biogrid_snapshot.py",
            "execution/acquire/biogrid_cohort_slice.py",
            "scripts/export_interaction_similarity_signature_preview.py",
            "scripts/validate_interaction_similarity_signature_preview.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/interaction_similarity_signature_preview.json",
            "artifacts/status/interaction_similarity_signature_validation.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "BioGRID is already feeding the interaction preview family, so this lane "
            "is implemented even though bundle inclusion stays report-only."
        ),
    },
    {
        "lane_id": "intact_interaction_backbone",
        "lane_label": "IntAct interaction backbone",
        "source_names": ["intact"],
        "supporting_scripts": [
            "execution/acquire/intact_snapshot.py",
            "execution/acquire/intact_cohort_slice.py",
            "scripts/export_interaction_context_preview.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/interaction_context_preview.json",
            "artifacts/runtime/procurement_supervisor_state.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "IntAct has both acquisition and cohort-slice support, so it is already "
            "implemented as an enrichment lane."
        ),
    },
    {
        "lane_id": "interpro_motif_backbone",
        "lane_label": "InterPro / PROSITE / Complex Portal motif backbone",
        "source_names": ["interpro", "prosite", "complex_portal"],
        "supporting_scripts": [
            "execution/acquire/interpro_motif_snapshot.py",
            "execution/acquire/prosite_snapshot.py",
            "scripts/resolve_interpro_complexportal.py",
            "scripts/export_motif_domain_compact_preview_family.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/motif_domain_compact_preview_family.json",
            "artifacts/status/p28_interpro_complexportal_resolver.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "The motif lane already has acquisition, resolver, and compact preview "
            "surfaces, so it is implemented."
        ),
    },
    {
        "lane_id": "alphafold_structure_backbone",
        "lane_label": "AlphaFold structure backbone",
        "source_names": ["alphafold"],
        "supporting_scripts": [
            "execution/acquire/alphafold_snapshot.py",
            "scripts/export_structure_entry_context_preview.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/structure_entry_context_preview.json",
            "artifacts/status/structure_similarity_signature_preview.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "AlphaFold is already present in the local registry and the structure "
            "preview surfaces consume it directly."
        ),
    },
    {
        "lane_id": "reactome_pathway_backbone",
        "lane_label": "Reactome pathway backbone",
        "source_names": ["reactome"],
        "supporting_scripts": [
            "execution/acquire/reactome_snapshot.py",
            "scripts/export_structure_followup_payload_preview.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/source_coverage_matrix.json",
            "artifacts/status/structure_followup_payload_preview.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "Reactome is present in the local registry and has an acquisition lane, "
            "so it is implemented rather than missing."
        ),
    },
    {
        "lane_id": "disprot_disorder_backbone",
        "lane_label": "DisProt disorder backbone",
        "source_names": ["disprot"],
        "supporting_scripts": [
            "execution/acquire/disprot_snapshot.py",
            "scripts/export_structure_variant_bridge_summary.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/source_coverage_matrix.json",
            "artifacts/status/structure_variant_bridge_summary.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "DisProt has an acquisition lane and is already part of the local source "
            "coverage matrix, so it is implemented."
        ),
        "force_state": "implemented",
    },
    {
        "lane_id": "evolutionary_corpus_backbone",
        "lane_label": "Evolutionary corpus backbone",
        "source_names": ["evolutionary"],
        "supporting_scripts": [
            "execution/acquire/evolutionary_snapshot.py",
            "scripts/export_uniref_cluster_context_preview.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/uniref_cluster_context_preview.json",
            "artifacts/status/source_coverage_matrix.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "The evolutionary corpus lane has a dedicated acquisition path and local "
            "supporting previews, so it is implemented."
        ),
        "force_state": "implemented",
    },
    {
        "lane_id": "pdbbind_measurement_backbone",
        "lane_label": "PDBbind measurement backbone",
        "source_names": ["pdbbind"],
        "supporting_scripts": [
            "execution/acquire/pdbbind_snapshot.py",
            "scripts/export_pdbbind_registry_preview.py",
            "scripts/export_pdbbind_validation_preview.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/pdbbind_registry_preview.json",
            "artifacts/status/pdbbind_validation_preview.json",
            "artifacts/status/pdbbind_local_snapshot_preview.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "PDBbind now has a standalone local acquisition and validation lane over the "
            "full index set, so the measurement backbone is implemented as a local-only "
            "non-governing scrape family."
        ),
    },
    {
        "lane_id": "elm_motif_backbone",
        "lane_label": "ELM motif backbone",
        "source_names": ["elm"],
        "supporting_scripts": [
            "execution/acquire/elm_snapshot.py",
            "scripts/export_elm_accession_cache_preview.py",
            "scripts/export_elm_support_preview.py",
            "scripts/export_elm_support_validation_preview.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/elm_accession_cache_preview.json",
            "artifacts/status/elm_support_preview.json",
            "artifacts/status/elm_support_validation_preview.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "ELM now has accession-scoped local TSV parsing plus validation over the live "
            "snapshot files, so the motif lane is implemented as candidate-only support."
        ),
    },
    {
        "lane_id": "sabio_rk_kinetics_backbone",
        "lane_label": "SABIO-RK kinetics backbone",
        "source_names": ["sabio_rk"],
        "supporting_scripts": [
            "execution/acquire/sabio_rk_snapshot.py",
            "scripts/export_sabio_rk_accession_cache_preview.py",
            "scripts/export_sabio_rk_support_preview.py",
            "scripts/validate_sabio_rk_support_preview.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/sabio_rk_accession_cache_preview.json",
            "artifacts/status/sabio_rk_support_preview.json",
            "artifacts/status/sabio_rk_support_validation.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "SABIO-RK now has accession-scoped seed/cache, support, and validation surfaces, "
            "so the kinetics lane is implemented as query-scoped support-only enrichment."
        ),
    },
    {
        "lane_id": "string_interaction_backbone",
        "lane_label": "STRING interaction backbone",
        "source_names": ["string"],
        "supporting_scripts": [
            "scripts/export_string_interaction_materialization_preview.py",
            "scripts/export_interaction_similarity_signature_preview.py",
            "scripts/validate_interaction_similarity_signature_preview.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/string_interaction_materialization_preview.json",
            "artifacts/status/procurement_status_board.json",
            "artifacts/status/interaction_similarity_signature_preview.json",
        ],
        "manual_blocker": "none",
        "why_now": (
            "STRING now has a completed mirror plus a non-governing materialization lane, "
            "so the interaction backbone can be harvested without promoting release truth."
        ),
    },
    {
        "lane_id": "mega_motif_base_backbone",
        "lane_label": "Mega motif base backbone",
        "source_names": ["mega_motif_base"],
        "supporting_scripts": [
            "scripts/export_missing_scrape_family_contracts_preview.py",
            "scripts/export_scrape_readiness_registry_preview.py",
            "scripts/export_procurement_status_board.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/source_coverage_matrix.json",
            "artifacts/status/scrape_readiness_registry_preview.json",
            "artifacts/status/missing_scrape_family_contracts_preview.json",
        ],
        "manual_blocker": "No implemented acquisition lane or targeted preview lane yet.",
        "why_now": (
            "This source is still missing in the coverage matrix, but the post-drive procurement "
            "and normalization contract is now pinned in code rather than living only in notes."
        ),
        "force_state": "missing",
    },
    {
        "lane_id": "motivated_proteins_backbone",
        "lane_label": "Motivated proteins backbone",
        "source_names": ["motivated_proteins"],
        "supporting_scripts": [
            "scripts/export_missing_scrape_family_contracts_preview.py",
            "scripts/export_scrape_readiness_registry_preview.py",
            "scripts/export_procurement_status_board.py",
        ],
        "evidence_artifacts": [
            "artifacts/status/source_coverage_matrix.json",
            "artifacts/status/scrape_readiness_registry_preview.json",
            "artifacts/status/missing_scrape_family_contracts_preview.json",
        ],
        "manual_blocker": "No implemented acquisition lane or targeted preview lane yet.",
        "why_now": (
            "This source is still missing in the coverage matrix, but the post-drive lookup/export "
            "capture contract is now pinned in code rather than living only in notes."
        ),
        "force_state": "missing",
    },
]


def _supporting_scripts_exist(paths: list[str]) -> bool:
    return all((REPO_ROOT / path).exists() for path in paths)


def _lane_state(spec: dict[str, Any], coverage_map: dict[str, dict[str, Any]]) -> str:
    if spec.get("force_state"):
        return str(spec["force_state"])
    statuses = []
    for name in spec.get("source_names") or []:
        row = coverage_map.get(str(name).casefold())
        if row:
            statuses.append(str(row.get("effective_status") or "").casefold())
        else:
            statuses.append("missing")
    if not statuses or "missing" in statuses:
        return "missing"
    if "partial" in statuses:
        return "partial"
    if not _supporting_scripts_exist(spec.get("supporting_scripts") or []):
        return "partial"
    return "implemented"


def _string_materialization_ready(procurement_status_board: dict[str, Any]) -> bool:
    if str(procurement_status_board.get("status") or "").strip().casefold() != "green":
        return False
    summary = procurement_status_board.get("summary") or {}
    if int(summary.get("remaining_transfer_total_gap_files") or 0) != 0:
        return False
    if not DEFAULT_STRING_MATERIALIZATION.exists():
        return False
    payload = json.loads(DEFAULT_STRING_MATERIALIZATION.read_text(encoding="utf-8"))
    materialization_summary = payload.get("summary") or {}
    return (
        str(materialization_summary.get("materialization_state") or "").strip()
        == "string_complete_materialized_non_governing"
        and int(materialization_summary.get("normalized_row_count") or 0) > 0
    )


def _pdbbind_ready() -> bool:
    if not DEFAULT_PDBBIND_REGISTRY.exists() or not DEFAULT_PDBBIND_VALIDATION.exists():
        return False
    registry = json.loads(DEFAULT_PDBBIND_REGISTRY.read_text(encoding="utf-8"))
    validation = json.loads(DEFAULT_PDBBIND_VALIDATION.read_text(encoding="utf-8"))
    registry_summary = registry.get("summary") or {}
    validation_summary = validation.get("validation") or {}
    return (
        registry.get("status") == "complete"
        and int(registry_summary.get("row_count") or 0) > 0
        and validation.get("status") == "aligned"
        and int(validation_summary.get("issue_count") or 0) == 0
    )


def _elm_ready() -> bool:
    if not DEFAULT_ELM_SUPPORT.exists() or not DEFAULT_ELM_SUPPORT_VALIDATION.exists():
        return False
    support = json.loads(DEFAULT_ELM_SUPPORT.read_text(encoding="utf-8"))
    validation = json.loads(DEFAULT_ELM_SUPPORT_VALIDATION.read_text(encoding="utf-8"))
    summary = support.get("summary") or {}
    validation_summary = validation.get("validation") or {}
    return (
        support.get("status") == "complete"
        and int(summary.get("elm_class_catalog_count") or 0) > 0
        and int(summary.get("elm_interaction_row_count") or 0) > 0
        and validation.get("status") == "aligned"
        and int(validation_summary.get("issue_count") or 0) == 0
    )


def _sabio_ready() -> bool:
    if not DEFAULT_SABIO_SUPPORT.exists() or not DEFAULT_SABIO_VALIDATION.exists():
        return False
    support = json.loads(DEFAULT_SABIO_SUPPORT.read_text(encoding="utf-8"))
    validation = json.loads(DEFAULT_SABIO_VALIDATION.read_text(encoding="utf-8"))
    support_summary = support.get("summary") or {}
    validation_summary = validation.get("validation") or {}
    return (
        support.get("status") == "complete"
        and int(support_summary.get("matrix_accession_count") or 0) > 0
        and bool(support_summary.get("query_scope_field_present"))
        and validation.get("status") == "aligned"
        and int(validation_summary.get("issue_count") or 0) == 0
    )


def build_scrape_gap_matrix_preview(
    source_coverage_matrix: dict[str, Any],
    scrape_readiness_registry: dict[str, Any],
    procurement_status_board: dict[str, Any],
) -> dict[str, Any]:
    coverage_map = source_row_map(source_coverage_matrix)
    string_materialization_ready = _string_materialization_ready(procurement_status_board)
    pdbbind_ready = _pdbbind_ready()
    elm_ready = _elm_ready()
    sabio_ready = _sabio_ready()
    rows: list[dict[str, Any]] = []
    for rank, spec in enumerate(LANE_SPECS, start=1):
        source_rows = [
            coverage_map.get(str(source_name).casefold())
            for source_name in normalize_list(spec.get("source_names"))
        ]
        source_rows = [row for row in source_rows if isinstance(row, dict)]
        source_statuses = [str(row.get("effective_status") or "").casefold() for row in source_rows]
        lane_state = _lane_state(spec, coverage_map)
        if not source_statuses and spec.get("force_state"):
            source_statuses = [str(spec["force_state"]).casefold()]
        rows.append(
            {
                "rank": rank,
                "lane_id": spec["lane_id"],
                "lane_label": spec["lane_label"],
                "lane_state": lane_state,
                "source_names": normalize_list(spec.get("source_names")),
                "source_statuses": source_statuses,
                "supporting_scripts": normalize_list(spec.get("supporting_scripts")),
                "evidence_artifacts": normalize_list(spec.get("evidence_artifacts")),
                "manual_blocker": spec["manual_blocker"],
                "why_now": spec["why_now"],
                "source_status_summary": " / ".join(source_statuses)
                if source_statuses
                else "missing",
            }
        )
    if string_materialization_ready:
        for row in rows:
            if row.get("lane_id") != "string_interaction_backbone":
                continue
            row["lane_state"] = "implemented"
            row["source_statuses"] = ["materialized_complete"]
            row["source_status_summary"] = "materialized_complete"
            break
    lane_overrides = {
        "pdbbind_measurement_backbone": pdbbind_ready,
        "elm_motif_backbone": elm_ready,
        "sabio_rk_kinetics_backbone": sabio_ready,
    }
    for row in rows:
        if not lane_overrides.get(str(row.get("lane_id") or "")):
            continue
        row["lane_state"] = "implemented"
        row["source_statuses"] = ["local_support_complete"]
        row["source_status_summary"] = "local_support_complete"
    rows.sort(
        key=lambda row: (
            status_rank(row["lane_state"]),
            row["rank"],
            row["lane_id"].casefold(),
        )
    )
    implemented_lane_count = sum(1 for row in rows if row["lane_state"] == "implemented")
    partial_lane_count = sum(1 for row in rows if row["lane_state"] == "partial")
    missing_lane_count = sum(1 for row in rows if row["lane_state"] == "missing")
    gap_rows = procurement_status_board.get("top_remaining_gaps") or []
    top_gap_sources = [
        {
            "source_id": row.get("source_id"),
            "status": row.get("status"),
            "coverage_percent": row.get("coverage_percent"),
            "missing_file_count": row.get("missing_file_count"),
            "partial_file_count": row.get("partial_file_count"),
            "rationale": row.get("rationale"),
        }
        for row in gap_rows
        if isinstance(row, dict)
    ]
    source_status_counts = source_coverage_matrix.get("summary", {}).get("status_counts") or {}
    readiness_targets = scrape_readiness_registry.get("summary", {}).get("top_scrape_targets") or []
    return {
        "artifact_id": "scrape_gap_matrix_preview",
        "schema_id": "proteosphere-scrape-gap-matrix-preview-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "implemented_lane_count": implemented_lane_count,
            "partial_lane_count": partial_lane_count,
            "missing_lane_count": missing_lane_count,
            "status_counts": {
                "implemented": implemented_lane_count,
                "partial": partial_lane_count,
                "missing": missing_lane_count,
            },
            "focused_lane_states": {
                "implemented": [
                    row["lane_id"] for row in rows if row["lane_state"] == "implemented"
                ],
                "partial": [row["lane_id"] for row in rows if row["lane_state"] == "partial"],
                "missing": [row["lane_id"] for row in rows if row["lane_state"] == "missing"],
            },
            "source_coverage_status_counts": source_status_counts,
            "top_gap_sources": top_gap_sources[:5],
            "readiness_targets": readiness_targets[:3],
            "gate_status": (procurement_status_board.get("status") or "blocked_pending_zero_gap"),
            "remaining_gap_file_count": int(
                procurement_status_board.get("summary", {}).get("remaining_gap_file_count")
                or len(gap_rows)
            ),
            "tail_blocked_lanes": [
                row["lane_id"] for row in rows if row["lane_state"] in {"partial", "missing"}
            ],
        },
        "truth_boundary": {
            "summary": (
                "This matrix is report-only. It classifies scrape lanes as "
                "implemented, partial, or missing using existing artifacts and "
                "supporting scripts; it does not start scraping."
            ),
            "report_only": True,
            "scraping_started": bool(
                (scrape_readiness_registry.get("truth_boundary") or {}).get("scraping_started")
            ),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Scrape Gap Matrix Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Row count: `{payload['row_count']}`",
        f"- Implemented lanes: `{payload['summary']['implemented_lane_count']}`",
        f"- Partial lanes: `{payload['summary']['partial_lane_count']}`",
        f"- Missing lanes: `{payload['summary']['missing_lane_count']}`",
        "",
        "## Lane Rows",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['rank']}` `{row['lane_id']}` -> `{row['lane_state']}` "
            f"({', '.join(row['source_names'])})"
        )
        lines.append(f"  blocker: {row['manual_blocker']}")
    lines.extend(["", "## Top Gap Sources", ""])
    for row in payload["summary"]["top_gap_sources"]:
        lines.append(
            f"- `{row['source_id']}` / `{row['status']}` / coverage `{row['coverage_percent']}`"
        )
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}", ""])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a report-only scrape gap matrix preview.")
    parser.add_argument(
        "--source-coverage-matrix",
        type=Path,
        default=DEFAULT_SOURCE_COVERAGE_MATRIX,
    )
    parser.add_argument(
        "--scrape-readiness-registry",
        type=Path,
        default=DEFAULT_SCRAPE_READINESS_REGISTRY,
    )
    parser.add_argument(
        "--procurement-status-board",
        type=Path,
        default=DEFAULT_PROCUREMENT_STATUS_BOARD,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_coverage_matrix = (
        load_source_coverage_matrix()
        if args.source_coverage_matrix == DEFAULT_SOURCE_COVERAGE_MATRIX
        else json.loads(args.source_coverage_matrix.read_text(encoding="utf-8"))
    )
    scrape_readiness_registry = (
        load_scrape_readiness_registry()
        if args.scrape_readiness_registry == DEFAULT_SCRAPE_READINESS_REGISTRY
        else json.loads(args.scrape_readiness_registry.read_text(encoding="utf-8"))
    )
    procurement_status_board = (
        load_procurement_status_board()
        if args.procurement_status_board == DEFAULT_PROCUREMENT_STATUS_BOARD
        else json.loads(args.procurement_status_board.read_text(encoding="utf-8"))
    )
    payload = build_scrape_gap_matrix_preview(
        source_coverage_matrix,
        scrape_readiness_registry,
        procurement_status_board,
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
