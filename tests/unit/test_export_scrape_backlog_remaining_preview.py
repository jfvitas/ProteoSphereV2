from __future__ import annotations

import json
from pathlib import Path


def _sample_payloads() -> tuple[dict, dict, dict, dict, dict]:
    scrape_gap_matrix = {
        "artifact_id": "scrape_gap_matrix_preview",
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "implemented_lane_count": 2,
            "partial_lane_count": 1,
            "missing_lane_count": 1,
        },
        "rows": [
            {"lane_id": "lane_a", "lane_state": "implemented"},
            {"lane_id": "lane_b", "lane_state": "implemented"},
            {"lane_id": "lane_c", "lane_state": "partial"},
            {"lane_id": "lane_d", "lane_state": "missing"},
        ],
    }
    overnight_queue_backlog = {
        "artifact_id": "overnight_queue_backlog_preview",
        "generated_at": "2026-04-03T00:00:00Z",
        "active_job_count": 2,
        "summary": {
            "lane_counts": {
                "active_now": 2,
                "supervisor_pending": 1,
                "overnight_catalog": 3,
            }
        },
    }
    scrape_execution_wave = {
        "artifact_id": "scrape_execution_wave_preview",
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "page_job_count": 2,
            "tail_blocked_job_count": 1,
        },
        "structured_jobs": [
            {
                "rank": 1,
                "job_id": "motif_active_site_enrichment",
                "lane_id": "interpro_motif_backbone",
                "job_category": "structured",
                "lane_state": "implemented",
                "recommended_action": "harvest_now",
            }
        ],
        "page_jobs": [
            {
                "rank": 1,
                "job_id": "page:P04637",
                "lane_id": "elm_motif_context",
                "job_category": "page",
                "accession": "P04637",
                "recommended_action": "stage_now",
                "page_scraping_started": False,
            },
            {
                "rank": 2,
                "job_id": "page:P31749",
                "lane_id": "elm_motif_context",
                "job_category": "page",
                "accession": "P31749",
                "recommended_action": "stage_now",
                "page_scraping_started": False,
            },
        ],
        "tail_blocked_jobs": [
            {
                "rank": 1,
                "job_id": "interaction_context_enrichment",
                "lane_id": "string_interaction_backbone",
                "job_category": "tail_blocked",
                "blocked_by_files": ["protein.links.full.v12.0.txt.gz", "uniref100.xml.gz"],
                "recommended_action": "wait_for_tail_unlock",
            }
        ],
        "wave_order": [
            {
                "rank": 1,
                "job_id": "motif_active_site_enrichment",
                "lane_id": "interpro_motif_backbone",
                "job_category": "structured",
                "lane_state": "implemented",
                "recommended_action": "harvest_now",
            },
            {
                "rank": 2,
                "job_id": "page:P04637",
                "lane_id": "elm_motif_context",
                "job_category": "page",
                "accession": "P04637",
                "recommended_action": "stage_now",
                "page_scraping_started": False,
            },
        ],
    }
    targeted_page_scrape_execution = {
        "artifact_id": "targeted_page_scrape_execution_preview",
        "generated_at": "2026-04-03T00:00:00Z",
        "rows": [
            {"accession": "P04637"},
            {"accession": "P31749"},
        ],
    }
    procurement_tail_freeze_gate = {
        "artifact_id": "procurement_tail_freeze_gate_preview",
        "generated_at": "2026-04-03T00:00:00Z",
        "gate_status": "blocked_pending_zero_gap",
        "remaining_gap_file_count": 2,
        "active_file_count": 2,
        "freeze_conditions": {
            "remaining_gap_files_zero": False,
            "not_yet_started_file_count_zero": True,
            "string_complete": False,
            "uniprot_complete": False,
        },
    }
    return (
        scrape_gap_matrix,
        overnight_queue_backlog,
        scrape_execution_wave,
        targeted_page_scrape_execution,
        procurement_tail_freeze_gate,
    )


def test_build_scrape_backlog_remaining_preview_summarizes_remaining_work() -> None:
    from scripts.export_scrape_backlog_remaining_preview import (
        build_scrape_backlog_remaining_preview,
    )

    payload = build_scrape_backlog_remaining_preview(*_sample_payloads())

    assert payload["artifact_id"] == "scrape_backlog_remaining_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["implemented_and_harvestable_now_count"] == 2
    assert payload["summary"]["preview_or_report_only_count"] == 2
    assert payload["summary"]["still_missing_count"] == 1
    assert payload["summary"]["tail_blocked_family_count"] == 1
    assert payload["summary"]["page_scrape_ready_count"] == 2
    assert payload["summary"]["structured_first_policy"] == (
        "structured_first_then_page_then_tail_blocked"
    )
    assert payload["summary"]["remaining_gap_file_count"] == 2
    assert payload["summary"]["tail_gate_status"] == "blocked_pending_zero_gap"
    assert payload["summary"]["tail_gate_blocked"] is True

    next_jobs = payload["next_priority_jobs"]
    assert len(next_jobs) == 2
    assert next_jobs[0]["job_id"] == "motif_active_site_enrichment"
    assert next_jobs[1]["job_id"] == "page:P04637"
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["non_mutating"] is True


def test_main_writes_json_and_fails_closed_on_missing_inputs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_scrape_backlog_remaining_preview as exporter

    output_json = tmp_path / "scrape_backlog_remaining_preview.json"
    patch_paths = {
        "DEFAULT_SCRAPE_GAP_MATRIX": tmp_path / "missing_scrape_gap_matrix_preview.json",
        "DEFAULT_OVERNIGHT_QUEUE_BACKLOG": (
            tmp_path / "missing_overnight_queue_backlog_preview.json"
        ),
        "DEFAULT_SCRAPE_EXECUTION_WAVE": tmp_path / "missing_scrape_execution_wave_preview.json",
        "DEFAULT_TARGETED_PAGE_SCRAPE_EXECUTION": (
            tmp_path / "missing_targeted_page_scrape_execution_preview.json"
        ),
        "DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE": (
            tmp_path / "missing_procurement_tail_freeze_gate_preview.json"
        ),
        "DEFAULT_OUTPUT_JSON": output_json,
    }
    for name, path in patch_paths.items():
        monkeypatch.setattr(exporter, name, path)

    exit_code = exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["artifact_id"] == "scrape_backlog_remaining_preview"
    assert payload["summary"]["implemented_and_harvestable_now_count"] == 0
    assert payload["summary"]["preview_or_report_only_count"] == 0
    assert payload["summary"]["still_missing_count"] == 0
    assert payload["summary"]["tail_blocked_family_count"] == 0
    assert payload["summary"]["page_scrape_ready_count"] == 0
    assert payload["next_priority_jobs"] == []
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["truth_boundary"]["report_only"] is True
    assert saved["truth_boundary"]["non_mutating"] is True
