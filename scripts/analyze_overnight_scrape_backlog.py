from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.overnight_planning_common import read_json, write_json  # noqa: E402

DEFAULT_SCRAPE_GAP_MATRIX = REPO_ROOT / "artifacts" / "status" / "scrape_gap_matrix_preview.json"
DEFAULT_OVERNIGHT_BACKLOG = (
    REPO_ROOT / "artifacts" / "status" / "overnight_queue_backlog_preview.json"
)
DEFAULT_SCRAPE_READINESS_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "scrape_readiness_registry_preview.json"
)
DEFAULT_TARGETED_PAGE_SCRAPE_EXECUTION = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_execution_preview.json"
)
DEFAULT_TARGETED_PAGE_SCRAPE_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_registry_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "overnight_scrape_wave_analysis.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def _listify(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "").strip()
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _scrape_prep_rows(scrape_readiness_registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in scrape_readiness_registry.get("rows") or []:
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "rank": int(row.get("rank") or 0),
                "action_id": str(row.get("target_id") or "").strip(),
                "title": str(row.get("target_id") or "").strip(),
                "wave_stage": "report_only_scrape_prep",
                "kind": "scrape_readiness_target",
                "status": str(row.get("status") or "").strip(),
                "default_ingest_status": str(row.get("default_ingest_status") or "").strip(),
                "candidate_sources": _listify(row.get("candidate_sources")),
                "provenance_tags": _listify(row.get("provenance_tags")),
                "why_now": str(row.get("why_now") or "").strip(),
                "blocked_by": [
                    "report_only_non_governing",
                    f"default_ingest_status={str(row.get('default_ingest_status') or '').strip()}",
                ],
                "evidence_artifacts": ["artifacts/status/scrape_readiness_registry_preview.json"],
            }
        )
    rows.sort(key=lambda row: (int(row.get("rank") or 0), row["action_id"].casefold()))
    return rows


def _targeted_page_rows(
    targeted_page_scrape_execution: dict[str, Any],
    targeted_page_scrape_registry: dict[str, Any],
) -> list[dict[str, Any]]:
    registry_lookup: dict[str, dict[str, Any]] = {}
    for row in targeted_page_scrape_registry.get("rows") or []:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if accession:
            registry_lookup[accession] = row

    rows: list[dict[str, Any]] = []
    for row in targeted_page_scrape_execution.get("rows") or []:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        registry_row = registry_lookup.get(accession, {})
        rows.append(
            {
                "action_id": f"targeted_page_scrape:{accession}",
                "title": f"Targeted page scrape for {accession}",
                "wave_stage": "report_only_scrape_prep",
                "kind": "targeted_page_scrape_candidate",
                "accession": accession,
                "target_family": str(row.get("target_family") or "").strip(),
                "priority_rank": int(row.get("priority_rank") or 0),
                "priority_anchor_target": str(row.get("priority_anchor_target") or "").strip(),
                "default_ingest_status": str(row.get("default_ingest_status") or "").strip(),
                "execution_status": str(row.get("execution_status") or "").strip(),
                "page_scraping_started": bool(row.get("page_scraping_started")),
                "why_now": (
                    "Current targeted page scrape surface already marks this accession as "
                    "candidate-only non-governing."
                ),
                "blocked_by": [
                    "candidate_only_non_governing",
                    "page_scraping_started=false",
                ],
                "candidate_pages": _listify(registry_row.get("candidate_pages")),
                "evidence_artifacts": [
                    "artifacts/status/targeted_page_scrape_execution_preview.json",
                    "artifacts/status/targeted_page_scrape_registry_preview.json",
                ],
            }
        )
    rows.sort(key=lambda row: (row["priority_rank"], row["accession"].casefold()))
    return rows


def _backlog_rows(
    backlog: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    active_rows = [
        row
        for row in backlog.get("rows") or []
        if isinstance(row, dict) and row.get("source_kind") == "observed_active"
    ]
    pending_rows = [
        row
        for row in backlog.get("rows") or []
        if isinstance(row, dict) and row.get("source_kind") == "supervisor_pending"
    ]
    catalog_rows = [
        row
        for row in backlog.get("rows") or []
        if isinstance(row, dict) and row.get("source_kind") == "catalog"
    ]
    return active_rows, pending_rows, catalog_rows


def build_overnight_scrape_wave_analysis(
    scrape_gap_matrix: dict[str, Any],
    overnight_backlog: dict[str, Any],
    scrape_readiness_registry: dict[str, Any],
    targeted_page_scrape_execution: dict[str, Any],
    targeted_page_scrape_registry: dict[str, Any],
) -> dict[str, Any]:
    active_rows, pending_rows, catalog_rows = _backlog_rows(overnight_backlog)

    active_items = []
    for row in active_rows:
        active_items.append(
            {
                "action_id": str(row.get("job_id") or "").strip(),
                "title": str(row.get("title") or "").strip(),
                "wave_stage": "active_now",
                "kind": str(row.get("type") or "download").strip() or "download",
                "queue_window": str(row.get("queue_window") or "").strip(),
                "source_kind": str(row.get("source_kind") or "").strip(),
                "source_keys": _listify(row.get("source_keys")),
                "pid_count": int(row.get("pid_count") or 0),
                "why_now": str(row.get("why_now") or "").strip(),
                "blocked_by": ["already_running", "do_not_duplicate_launch"],
                "evidence_artifacts": [
                    "artifacts/status/overnight_queue_backlog_preview.json",
                    "artifacts/runtime/procurement_supervisor_state.json",
                ],
            }
        )

    pending_items = []
    for row in pending_rows:
        pending_items.append(
            {
                "action_id": str(row.get("job_id") or "").strip(),
                "title": str(row.get("title") or "").strip(),
                "wave_stage": "queued_next",
                "kind": str(row.get("type") or "").strip() or "download",
                "queue_window": str(row.get("queue_window") or "").strip(),
                "source_kind": str(row.get("source_kind") or "").strip(),
                "priority": int(row.get("priority") or 0),
                "command": _listify(row.get("command")),
                "why_now": str(row.get("why_now") or "").strip(),
                "blocked_by": ["already_queued", "do_not_duplicate_launch"],
                "evidence_artifacts": [
                    "artifacts/status/overnight_queue_backlog_preview.json",
                    "artifacts/runtime/procurement_supervisor_state.json",
                ],
            }
        )

    catalog_focus = []
    for row in catalog_rows[:3]:
        catalog_focus.append(
            {
                "action_id": str(row.get("job_id") or "").strip(),
                "title": str(row.get("title") or "").strip(),
                "wave_stage": "deferred_catalog_tail",
                "kind": str(row.get("type") or "").strip(),
                "queue_window": str(row.get("queue_window") or "").strip(),
                "source_kind": str(row.get("source_kind") or "").strip(),
                "priority": str(row.get("priority") or "").strip(),
                "phase": int(row.get("phase") or 0),
                "dependencies": _listify(row.get("dependencies")),
                "files": _listify(row.get("files")),
                "why_now": str(row.get("why_now") or "").strip(),
                "blocked_by": ["active_now_and_queued_wave_not_drainable_yet"],
                "evidence_artifacts": ["artifacts/status/overnight_queue_backlog_preview.json"],
            }
        )

    report_only_prep = _scrape_prep_rows(scrape_readiness_registry)
    targeted_page_prep = _targeted_page_rows(
        targeted_page_scrape_execution,
        targeted_page_scrape_registry,
    )

    ranked_actions: list[dict[str, Any]] = []
    for section_rows in (
        active_items,
        pending_items,
        report_only_prep,
        targeted_page_prep,
        catalog_focus,
    ):
        ranked_actions.extend(section_rows)
    for rank, row in enumerate(ranked_actions, start=1):
        row["rank"] = rank

    gap_rows = scrape_gap_matrix.get("rows") or []
    gap_counts = _count_by(gap_rows, "lane_state")
    lane_ids_by_state: dict[str, list[str]] = {}
    for row in gap_rows:
        if not isinstance(row, dict):
            continue
        lane_state = str(row.get("lane_state") or "").strip()
        lane_id = str(row.get("lane_id") or "").strip()
        if lane_state and lane_id:
            lane_ids_by_state.setdefault(lane_state, []).append(lane_id)

    summary = {
        "active_job_count": len(active_items),
        "queued_job_count": len(pending_items),
        "catalog_tail_count": len(catalog_rows),
        "report_only_scrape_prep_count": len(report_only_prep) + len(targeted_page_prep),
        "gap_lane_state_counts": gap_counts,
        "implemented_lane_ids": lane_ids_by_state.get("implemented", []),
        "partial_lane_ids": lane_ids_by_state.get("partial", []),
        "missing_lane_ids": lane_ids_by_state.get("missing", []),
        "live_queue_source_keys": [item["action_id"] for item in active_items],
        "queued_next_job_ids": [item["action_id"] for item in pending_items],
        "report_only_scrape_targets": [item["action_id"] for item in report_only_prep],
        "targeted_page_scrape_accessions": [
            item["accession"] for item in targeted_page_prep if item.get("accession")
        ],
        "deferred_catalog_focus_ids": [item["action_id"] for item in catalog_focus],
        "blocked_manual_sources": ["elm", "sabio_rk"],
    }

    return {
        "artifact_id": "overnight_scrape_wave_analysis",
        "schema_id": "proteosphere-overnight-scrape-wave-analysis-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summary,
        "ranked_actions": ranked_actions,
        "source_artifacts": {
            "scrape_gap_matrix": "artifacts/status/scrape_gap_matrix_preview.json",
            "overnight_backlog": "artifacts/status/overnight_queue_backlog_preview.json",
            "scrape_readiness_registry": "artifacts/status/scrape_readiness_registry_preview.json",
            "targeted_page_scrape_execution": (
                "artifacts/status/targeted_page_scrape_execution_preview.json"
            ),
            "targeted_page_scrape_registry": (
                "artifacts/status/targeted_page_scrape_registry_preview.json"
            ),
        },
        "truth_boundary": {
            "summary": (
                "This analysis is report-only and non-governing. It ranks the next "
                "scrape/backlog wave, but it does not launch jobs or override current "
                "active downloads."
            ),
            "report_only": True,
            "non_governing": True,
            "no_duplicate_launches": True,
            "targeted_page_scraping_stays_candidate_only": True,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze the overnight scrape backlog into a report-only next-wave plan."
    )
    parser.add_argument("--scrape-gap-matrix", type=Path, default=DEFAULT_SCRAPE_GAP_MATRIX)
    parser.add_argument("--overnight-backlog", type=Path, default=DEFAULT_OVERNIGHT_BACKLOG)
    parser.add_argument(
        "--scrape-readiness-registry",
        type=Path,
        default=DEFAULT_SCRAPE_READINESS_REGISTRY,
    )
    parser.add_argument(
        "--targeted-page-scrape-execution",
        type=Path,
        default=DEFAULT_TARGETED_PAGE_SCRAPE_EXECUTION,
    )
    parser.add_argument(
        "--targeted-page-scrape-registry",
        type=Path,
        default=DEFAULT_TARGETED_PAGE_SCRAPE_REGISTRY,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_overnight_scrape_wave_analysis(
        _load_json(args.scrape_gap_matrix),
        _load_json(args.overnight_backlog),
        _load_json(args.scrape_readiness_registry),
        _load_json(args.targeted_page_scrape_execution),
        _load_json(args.targeted_page_scrape_registry),
    )
    write_json(args.output_json, payload)
    print(args.output_json)


if __name__ == "__main__":
    main()
