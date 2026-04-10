from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRAPE_GAP_MATRIX = REPO_ROOT / "artifacts" / "status" / "scrape_gap_matrix_preview.json"
DEFAULT_OVERNIGHT_QUEUE_BACKLOG = (
    REPO_ROOT / "artifacts" / "status" / "overnight_queue_backlog_preview.json"
)
DEFAULT_TARGETED_PAGE_SCRAPE_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_registry_preview.json"
)
DEFAULT_TARGETED_PAGE_SCRAPE_EXECUTION = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_execution_preview.json"
)
DEFAULT_PROCUREMENT_PROCESS_DIAGNOSTICS = (
    REPO_ROOT / "artifacts" / "status" / "procurement_process_diagnostics_preview.json"
)
DEFAULT_PROCUREMENT_SOURCE_COMPLETION = (
    REPO_ROOT / "artifacts" / "status" / "procurement_source_completion_preview.json"
)
DEFAULT_SCRAPE_READINESS_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "scrape_readiness_registry_preview.json"
)
DEFAULT_PRE_TAIL_EXECUTION = (
    REPO_ROOT / "artifacts" / "status" / "pre_tail_scrape_wave_execution_preview.json"
)
DEFAULT_STRING_MATERIALIZATION = (
    REPO_ROOT / "artifacts" / "status" / "string_interaction_materialization_preview.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "scrape_execution_wave_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "scrape_execution_wave_preview.md"

READINESS_TARGET_TO_LANES: dict[str, list[str]] = {
    "motif_active_site_enrichment": [
        "interpro_motif_backbone",
        "elm_motif_backbone",
    ],
    "interaction_context_enrichment": [
        "biogrid_interaction_backbone",
        "intact_interaction_backbone",
        "string_interaction_backbone",
    ],
    "kinetics_pathway_metadata_enrichment": [
        "sabio_rk_kinetics_backbone",
    ],
}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    seen: dict[str, str] = {}
    for value in values:
        text = _normalize_text(value)
        if text:
            seen.setdefault(text.casefold(), text)
    return list(seen.values())


def _lane_rows(scrape_gap_matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = scrape_gap_matrix.get("rows") or []
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        lane_id = _normalize_text(row.get("lane_id"))
        if lane_id:
            indexed[lane_id] = dict(row)
    return indexed


def _readiness_rows(scrape_readiness_registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = scrape_readiness_registry.get("rows") or []
    return [dict(row) for row in rows if isinstance(row, dict)]


def _score_structured_job(
    lane_row: dict[str, Any],
    readiness_target: dict[str, Any] | None,
    target_rank: int,
) -> tuple[int, int, str]:
    lane_state = _normalize_text(lane_row.get("lane_state"))
    state_weight = {"implemented": 300, "partial": 220, "missing": 0}.get(lane_state, 0)
    target_weight = max(0, 120 - target_rank * 10)
    blocker_penalty = 0 if _normalize_text(lane_row.get("manual_blocker")) in {"", "none"} else -15
    readiness_bonus = 0
    if readiness_target:
        readiness_status = _normalize_text(readiness_target.get("status"))
        if "waiting" in readiness_status:
            readiness_bonus = 20
        elif "complete" in readiness_status:
            readiness_bonus = 10
    why_now = _normalize_text(lane_row.get("why_now"))
    if readiness_target:
        why_now = _normalize_text(readiness_target.get("why_now")) or why_now
    return state_weight + target_weight + blocker_penalty + readiness_bonus, target_rank, why_now


def _structured_jobs(
    scrape_gap_matrix: dict[str, Any],
    scrape_readiness_registry: dict[str, Any],
) -> list[dict[str, Any]]:
    lane_map = _lane_rows(scrape_gap_matrix)
    readiness_rows = _readiness_rows(scrape_readiness_registry)
    target_index = {
        _normalize_text(row.get("target_id")): dict(row)
        for row in readiness_rows
        if _normalize_text(row.get("target_id"))
    }

    candidates: list[dict[str, Any]] = []
    for target_rank, target_id in enumerate(
        _normalize_list(scrape_readiness_registry.get("summary", {}).get("top_scrape_targets")),
        start=1,
    ):
        readiness_target = target_index.get(target_id)
        for lane_id in READINESS_TARGET_TO_LANES.get(target_id, []):
            lane_row = lane_map.get(lane_id)
            if not lane_row:
                continue
            if _normalize_text(lane_row.get("lane_state")) not in {"implemented", "partial"}:
                continue
            score, source_rank, why_now = _score_structured_job(
                lane_row,
                readiness_target,
                target_rank,
            )
            candidate_sources = _normalize_list(
                readiness_target.get("candidate_sources") if readiness_target else []
            )
            if not candidate_sources:
                candidate_sources = _normalize_list(lane_row.get("source_names"))
            candidates.append(
                {
                    "rank_score": score,
                    "target_rank": source_rank,
                    "job_id": target_id,
                    "lane_id": lane_id,
                    "lane_label": lane_row.get("lane_label"),
                    "job_category": "structured",
                    "lane_state": lane_row.get("lane_state"),
                    "default_ingest_status": readiness_target.get("default_ingest_status")
                    if readiness_target
                    else None,
                    "candidate_sources": candidate_sources,
                    "provenance_tags": _normalize_list(
                        readiness_target.get("provenance_tags") if readiness_target else []
                    ),
                    "supporting_scripts": _normalize_list(lane_row.get("supporting_scripts")),
                    "evidence_artifacts": _normalize_list(lane_row.get("evidence_artifacts")),
                    "manual_blocker": _normalize_text(lane_row.get("manual_blocker")),
                    "why_now": why_now or _normalize_text(lane_row.get("why_now")),
                    "recommended_action": (
                        "harvest_now"
                        if lane_row.get("lane_state") == "implemented"
                        else "stage_now"
                    ),
                    "page_scraping_started": None,
                    "blocked_by_tail": False,
                    "blocked_by_files": [],
                }
            )

    # Add high-leverage implemented/support lanes that are not yet represented by readiness targets.
    extra_lanes = [
        "rcsb_pdbe_sifts_structure_backbone",
        "bindingdb_assay_bridge_backbone",
        "pdbbind_measurement_backbone",
    ]
    for lane_id in extra_lanes:
        lane_row = lane_map.get(lane_id)
        if not lane_row:
            continue
        lane_state = _normalize_text(lane_row.get("lane_state"))
        if lane_state not in {"implemented", "partial"}:
            continue
        score = {"implemented": 240, "partial": 180}.get(lane_state, 0)
        candidates.append(
            {
                "rank_score": score,
                "target_rank": 99,
                "job_id": lane_id,
                "lane_id": lane_id,
                "lane_label": lane_row.get("lane_label"),
                "job_category": "structured",
                "lane_state": lane_state,
                "default_ingest_status": "support-only"
                if lane_state == "implemented"
                else "candidate_only_non_governing",
                "candidate_sources": _normalize_list(lane_row.get("source_names")),
                "provenance_tags": [],
                "supporting_scripts": _normalize_list(lane_row.get("supporting_scripts")),
                "evidence_artifacts": _normalize_list(lane_row.get("evidence_artifacts")),
                "manual_blocker": _normalize_text(lane_row.get("manual_blocker")),
                "why_now": _normalize_text(lane_row.get("why_now")),
                    "recommended_action": (
                        "harvest_now"
                        if lane_state == "implemented"
                        else "stage_now"
                    ),
                "page_scraping_started": None,
                "blocked_by_tail": False,
                "blocked_by_files": [],
            }
        )

    candidates.sort(
        key=lambda row: (
            -int(row["rank_score"]),
            int(row["target_rank"]),
            _normalize_text(row["job_id"]).casefold(),
            _normalize_text(row["lane_id"]).casefold(),
        )
    )
    for rank, row in enumerate(candidates, start=1):
        row["rank"] = rank
        row.pop("rank_score", None)
        row.pop("target_rank", None)
    return candidates


def _page_jobs(targeted_page_scrape_registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = targeted_page_scrape_registry.get("rows") or []
    candidates: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        accession = _normalize_text(row.get("accession"))
        if not accession:
            continue
        candidates.append(
            {
                "job_id": f"page:{accession}",
                "lane_id": _normalize_text(row.get("target_family")) or "targeted_page_scrape",
                "lane_label": f"Targeted page scrape for {accession}",
                "job_category": "page",
                "accession": accession,
                "target_family": row.get("target_family"),
                "candidate_pages": _normalize_list(row.get("candidate_pages")),
                "page_scraping_started": bool(row.get("page_scraping_started")),
                "default_ingest_status": row.get("default_ingest_status"),
                "why_now": (
                    "High-value targeted page scraping candidate. Keep page-level data "
                    "candidate-only non-governing until separately normalized."
                ),
                "recommended_action": "stage_now",
                "blocked_by_tail": False,
                "blocked_by_files": [],
                "lane_state": "candidate",
            }
        )

    candidates.sort(key=lambda row: (_normalize_text(row["accession"]).casefold(), row["job_id"]))
    for rank, row in enumerate(candidates, start=1):
        row["rank"] = rank
    return candidates


def _tail_blocked_jobs(
    procurement_process_diagnostics: dict[str, Any],
    procurement_source_completion: dict[str, Any],
    scrape_gap_matrix: dict[str, Any],
    scrape_readiness_registry: dict[str, Any],
) -> list[dict[str, Any]]:
    if bool(procurement_source_completion.get("string_completion_ready")):
        return []
    authoritative_tail_files = procurement_process_diagnostics.get("authoritative_tail_files") or []
    blocked_files = [
        _normalize_text(row.get("filename"))
        for row in authoritative_tail_files
        if isinstance(row, dict) and _normalize_text(row.get("filename"))
    ]
    tail_blocked_rows: list[dict[str, Any]] = []
    lane_map = _lane_rows(scrape_gap_matrix)
    readiness_rows = _readiness_rows(scrape_readiness_registry)
    interaction_target = next(
        (
            dict(row)
            for row in readiness_rows
            if _normalize_text(row.get("target_id")) == "interaction_context_enrichment"
        ),
        {},
    )
    string_lane = lane_map.get("string_interaction_backbone") or {}
    if blocked_files or string_lane:
        tail_blocked_rows.append(
            {
                "job_id": "interaction_context_enrichment",
                "lane_id": "string_interaction_backbone",
                "lane_label": string_lane.get("lane_label") or "STRING interaction backbone",
                "job_category": "tail_blocked",
                "status": "blocked_waiting_on_string_tail",
                "default_ingest_status": interaction_target.get("default_ingest_status")
                or "candidate_only_non_governing",
                "candidate_sources": _normalize_list(interaction_target.get("candidate_sources")),
                "blocked_by_files": blocked_files,
                "blocked_by_tail": True,
                "page_scraping_started": None,
                "why_now": interaction_target.get("why_now")
                or (
                    "Interaction context is staged for non-governing materialization, "
                    "but the STRING completion gate is still unresolved."
                ),
                "recommended_action": "wait_for_tail_unlock",
                "lane_state": string_lane.get("lane_state") or "missing",
            }
        )

    for rank, row in enumerate(tail_blocked_rows, start=1):
        row["rank"] = rank
    return tail_blocked_rows


def _execution_index(pre_tail_execution: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    aliases = {
        ("interaction_context_enrichment_biogrid", "biogrid_interaction_backbone"): (
            "interaction_context_enrichment",
            "biogrid_interaction_backbone",
        ),
        ("interaction_context_enrichment_intact", "intact_interaction_backbone"): (
            "interaction_context_enrichment",
            "intact_interaction_backbone",
        ),
        ("elm_motif_backbone", "elm_motif_backbone"): (
            "motif_active_site_enrichment",
            "elm_motif_backbone",
        ),
        ("sabio_rk_kinetics_backbone", "sabio_rk_kinetics_backbone"): (
            "kinetics_pathway_metadata_enrichment",
            "sabio_rk_kinetics_backbone",
        ),
    }
    for row in pre_tail_execution.get("rows") or []:
        if not isinstance(row, dict):
            continue
        key = (
            _normalize_text(row.get("job_id")),
            _normalize_text(row.get("lane_id")),
        )
        key = aliases.get(key, key)
        if key[0] and key[1]:
            indexed[key] = dict(row)
    return indexed


def _augment_execution_index_with_string_materialization(
    execution_map: dict[tuple[str, str], dict[str, Any]],
    procurement_source_completion: dict[str, Any],
    string_materialization: dict[str, Any] | None,
) -> dict[tuple[str, str], dict[str, Any]]:
    if not bool(procurement_source_completion.get("string_completion_ready")):
        return execution_map
    payload = string_materialization or {}
    summary = payload.get("summary") or {}
    if (
        _normalize_text(summary.get("materialization_state"))
        != "string_complete_materialized_non_governing"
        or int(summary.get("normalized_row_count") or 0) <= 0
    ):
        return execution_map
    updated = dict(execution_map)
    updated.setdefault(
        ("interaction_context_enrichment", "string_interaction_backbone"),
        {
            "job_id": "interaction_context_enrichment",
            "lane_id": "string_interaction_backbone",
            "execution_status": "completed",
            "completed_at": payload.get("generated_at"),
            "artifact_paths": [str(DEFAULT_STRING_MATERIALIZATION).replace("\\", "/")],
        },
    )
    return updated


def _page_execution_index(
    targeted_page_scrape_execution: dict[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for row in targeted_page_scrape_execution.get("rows") or []:
        if not isinstance(row, dict):
            continue
        key = (
            _normalize_text(row.get("accession")),
            _normalize_text(row.get("target_family")),
        )
        if key[0] and key[1]:
            indexed[key] = dict(row)
    return indexed


def _apply_execution_state(
    rows: list[dict[str, Any]],
    execution_map: dict[tuple[str, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, int]:
    executed_count = 0
    failed_count = 0
    updated: list[dict[str, Any]] = []
    for row in rows:
        key = (_normalize_text(row.get("job_id")), _normalize_text(row.get("lane_id")))
        execution = execution_map.get(key)
        emitted = dict(row)
        if execution:
            emitted["execution_status"] = execution.get("execution_status")
            emitted["last_executed_at"] = execution.get("completed_at")
            emitted["executed_artifact_paths"] = _normalize_list(execution.get("artifact_paths"))
            executed_count += 1
            if _normalize_text(execution.get("execution_status")) == "failed":
                failed_count += 1
        else:
            emitted["execution_status"] = "staged_not_executed"
            emitted["last_executed_at"] = None
            emitted["executed_artifact_paths"] = []
        updated.append(emitted)
    return updated, executed_count, failed_count


def _apply_page_execution_state(
    rows: list[dict[str, Any]],
    page_execution_map: dict[tuple[str, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    updated: list[dict[str, Any]] = []
    captured_count = 0
    for row in rows:
        key = (_normalize_text(row.get("accession")), _normalize_text(row.get("target_family")))
        execution = page_execution_map.get(key)
        emitted = dict(row)
        if execution:
            emitted["execution_status"] = _normalize_text(
                execution.get("execution_status")
            ) or "captured_candidate_only_payloads"
            emitted["page_scraping_started"] = bool(execution.get("page_scraping_started"))
            emitted["payload_capture_started"] = bool(execution.get("payload_capture_started"))
            emitted["captured_payload_count"] = int(execution.get("captured_payload_count") or 0)
            emitted["last_executed_at"] = execution.get("generated_at")
            if emitted["captured_payload_count"] > 0:
                emitted["recommended_action"] = "review_candidate_only_payloads"
            captured_count += 1
        else:
            emitted["execution_status"] = "staged_not_executed"
            emitted["payload_capture_started"] = False
            emitted["captured_payload_count"] = 0
            emitted["last_executed_at"] = None
        updated.append(emitted)
    return updated, captured_count


def build_scrape_execution_wave_preview(
    scrape_gap_matrix: dict[str, Any],
    overnight_queue_backlog: dict[str, Any],
    targeted_page_scrape_registry: dict[str, Any],
    targeted_page_scrape_execution: dict[str, Any] | None,
    procurement_process_diagnostics: dict[str, Any],
    procurement_source_completion: dict[str, Any],
    scrape_readiness_registry: dict[str, Any],
    pre_tail_execution: dict[str, Any] | None = None,
    string_materialization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    structured_jobs = _structured_jobs(scrape_gap_matrix, scrape_readiness_registry)
    page_jobs = _page_jobs(targeted_page_scrape_registry)
    tail_blocked_jobs = _tail_blocked_jobs(
        procurement_process_diagnostics,
        procurement_source_completion,
        scrape_gap_matrix,
        scrape_readiness_registry,
    )
    execution_map = _execution_index(pre_tail_execution or {})
    execution_map = _augment_execution_index_with_string_materialization(
        execution_map,
        procurement_source_completion,
        string_materialization,
    )
    structured_jobs, executed_structured_count, failed_structured_count = _apply_execution_state(
        structured_jobs,
        execution_map,
    )
    page_execution_map = _page_execution_index(targeted_page_scrape_execution or {})
    page_jobs, captured_page_count = _apply_page_execution_state(page_jobs, page_execution_map)
    ranked_jobs = []
    for row in structured_jobs + page_jobs + tail_blocked_jobs:
        ranked_jobs.append(dict(row))
    for rank, row in enumerate(ranked_jobs, start=1):
        row["wave_rank"] = rank

    queue_summary = overnight_queue_backlog.get("summary") or {}
    proc_summary = procurement_process_diagnostics.get("summary") or {}
    gap_summary = scrape_gap_matrix.get("summary") or {}
    readiness_summary = scrape_readiness_registry.get("summary") or {}

    return {
        "artifact_id": "scrape_execution_wave_preview",
        "schema_id": "proteosphere-scrape-execution-wave-preview-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "structured_job_count": len(structured_jobs),
            "page_job_count": len(page_jobs),
            "captured_page_job_count": captured_page_count,
            "tail_blocked_job_count": len(tail_blocked_jobs),
            "wave_rank_count": len(ranked_jobs),
            "executed_structured_job_count": executed_structured_count,
            "failed_structured_job_count": failed_structured_count,
            "top_structured_job_ids": [row["job_id"] for row in structured_jobs[:5]],
            "top_page_accessions": [row["accession"] for row in page_jobs[:5]],
            "tail_blocked_job_ids": [row["job_id"] for row in tail_blocked_jobs],
            "active_download_count": int(proc_summary.get("authoritative_tail_file_count") or 0),
            "string_completion_ready": bool(
                procurement_source_completion.get("string_completion_ready")
            ),
            "uniref_completion_ready": bool(
                procurement_source_completion.get("uniprot_completion_ready")
            ),
            "raw_process_table_active_count": int(
                proc_summary.get("raw_process_table_active_count") or 0
            ),
            "queue_active_now_count": int(
                queue_summary.get("lane_counts", {}).get("active_now") or 0
            ),
            "queue_supervisor_pending_count": int(
                queue_summary.get("lane_counts", {}).get("supervisor_pending") or 0
            ),
            "queue_catalog_count": int(
                queue_summary.get("lane_counts", {}).get("overnight_catalog") or 0
            ),
            "remaining_gap_file_count": int(gap_summary.get("remaining_gap_file_count") or 0),
            "readiness_targets": _normalize_list(readiness_summary.get("top_scrape_targets")),
            "observed_active_source_keys": _normalize_list(
                queue_summary.get("observed_active_source_keys")
            ),
            "page_scraping_started": any(
                bool(row.get("page_scraping_started")) for row in page_jobs
            ),
            "payload_capture_started": any(
                bool(row.get("payload_capture_started")) for row in page_jobs
            ),
        },
        "wave_order": ranked_jobs,
        "structured_jobs": structured_jobs,
        "page_jobs": page_jobs,
        "tail_blocked_jobs": tail_blocked_jobs,
        "truth_boundary": {
            "summary": (
                "This scrape wave preview is report-only. It ranks structured, page, "
                "and tail-blocked jobs from existing artifacts, but it does not launch "
                "scraping or mutate curated truth."
            ),
            "report_only": True,
            "non_mutating": True,
            "launch_blocked_for_active_jobs": True,
            "duplicate_launches_forbidden": True,
            "scraping_started": executed_structured_count > 0,
            "page_scraping_started": any(
                bool(row.get("page_scraping_started")) for row in page_jobs
            ),
            "payload_capture_started": any(
                bool(row.get("payload_capture_started")) for row in page_jobs
            ),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Scrape Execution Wave Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Structured jobs: `{summary.get('structured_job_count')}`",
        f"- Page jobs: `{summary.get('page_job_count')}`",
        f"- Tail-blocked jobs: `{summary.get('tail_blocked_job_count')}`",
        f"- Active downloads: `{summary.get('active_download_count')}`",
        "",
        "## Structured Jobs",
        "",
    ]
    for row in payload.get("structured_jobs") or []:
        lines.append(
            f"- `{row['rank']}` `{row['job_id']}` / `{row['lane_id']}` "
            f"status `{row['lane_state']}` / `{row['recommended_action']}`"
        )
        lines.append(f"  sources: {', '.join(row.get('candidate_sources') or []) or 'none'}")
    lines.extend(
        [
            "",
            "## Page Jobs",
            "",
        ]
    )
    for row in payload.get("page_jobs") or []:
        lines.append(
            f"- `{row['rank']}` `{row['accession']}` / `{row['lane_label']}` "
            f"/ `{row['default_ingest_status']}`"
        )
    lines.extend(
        [
            "",
            "## Tail-Blocked Jobs",
            "",
        ]
    )
    for row in payload.get("tail_blocked_jobs") or []:
        lines.append(
            f"- `{row['rank']}` `{row['job_id']}` / `{row['lane_id']}` "
            f"blocked by `{', '.join(row.get('blocked_by_files') or []) or 'unknown'}`"
        )
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}", ""])
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only scrape execution wave preview."
    )
    parser.add_argument("--scrape-gap-matrix", type=Path, default=DEFAULT_SCRAPE_GAP_MATRIX)
    parser.add_argument(
        "--overnight-queue-backlog",
        type=Path,
        default=DEFAULT_OVERNIGHT_QUEUE_BACKLOG,
    )
    parser.add_argument(
        "--targeted-page-scrape-registry",
        type=Path,
        default=DEFAULT_TARGETED_PAGE_SCRAPE_REGISTRY,
    )
    parser.add_argument(
        "--targeted-page-scrape-execution",
        type=Path,
        default=DEFAULT_TARGETED_PAGE_SCRAPE_EXECUTION,
    )
    parser.add_argument(
        "--procurement-process-diagnostics",
        type=Path,
        default=DEFAULT_PROCUREMENT_PROCESS_DIAGNOSTICS,
    )
    parser.add_argument(
        "--procurement-source-completion",
        type=Path,
        default=DEFAULT_PROCUREMENT_SOURCE_COMPLETION,
    )
    parser.add_argument(
        "--scrape-readiness-registry",
        type=Path,
        default=DEFAULT_SCRAPE_READINESS_REGISTRY,
    )
    parser.add_argument(
        "--pre-tail-execution",
        type=Path,
        default=DEFAULT_PRE_TAIL_EXECUTION,
    )
    parser.add_argument(
        "--string-materialization",
        type=Path,
        default=DEFAULT_STRING_MATERIALIZATION,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scrape_gap_matrix = _read_json(args.scrape_gap_matrix)
    overnight_queue_backlog = _read_json(args.overnight_queue_backlog)
    targeted_page_scrape_registry = _read_json(args.targeted_page_scrape_registry)
    targeted_page_scrape_execution = (
        _read_json(args.targeted_page_scrape_execution)
        if args.targeted_page_scrape_execution.exists()
        else {}
    )
    procurement_process_diagnostics = _read_json(args.procurement_process_diagnostics)
    procurement_source_completion = _read_json(args.procurement_source_completion)
    scrape_readiness_registry = _read_json(args.scrape_readiness_registry)
    pre_tail_execution = (
        _read_json(args.pre_tail_execution) if args.pre_tail_execution.exists() else {}
    )
    string_materialization = (
        _read_json(args.string_materialization) if args.string_materialization.exists() else {}
    )
    payload = build_scrape_execution_wave_preview(
        scrape_gap_matrix,
        overnight_queue_backlog,
        targeted_page_scrape_registry,
        targeted_page_scrape_execution,
        procurement_process_diagnostics,
        procurement_source_completion,
        scrape_readiness_registry,
        pre_tail_execution,
        string_materialization,
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
