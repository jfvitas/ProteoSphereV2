from __future__ import annotations

from scripts.export_overnight_execution_contract_preview import (
    build_overnight_execution_contract_preview,
)
from scripts.export_overnight_queue_backlog_preview import (
    build_overnight_queue_backlog_preview,
)
from scripts.export_scrape_gap_matrix_preview import build_scrape_gap_matrix_preview
from scripts.overnight_planning_common import (
    load_live_bundle_validation,
    load_procurement_status_board,
    load_runtime_state,
    load_scrape_readiness_registry,
    load_source_coverage_matrix,
)


def test_scrape_gap_matrix_preview_classifies_focused_lanes() -> None:
    payload = build_scrape_gap_matrix_preview(
        load_source_coverage_matrix(),
        load_scrape_readiness_registry(),
        load_procurement_status_board(),
    )
    assert payload["row_count"] == 16
    assert payload["summary"]["implemented_lane_count"] == 14
    assert payload["summary"]["partial_lane_count"] == 0
    assert payload["summary"]["missing_lane_count"] == 2
    assert payload["summary"]["source_coverage_status_counts"]["missing"] == 3
    assert payload["summary"]["source_coverage_status_counts"]["partial"] == 2
    assert "string_interaction_backbone" in payload["summary"]["focused_lane_states"]["implemented"]
    assert payload["summary"]["focused_lane_states"]["partial"] == []
    assert (
        "pdbbind_measurement_backbone"
        in payload["summary"]["focused_lane_states"]["implemented"]
    )
    assert "elm_motif_backbone" in payload["summary"]["focused_lane_states"]["implemented"]
    assert "sabio_rk_kinetics_backbone" in payload["summary"]["focused_lane_states"]["implemented"]
    assert payload["summary"]["focused_lane_states"]["missing"] == [
        "mega_motif_base_backbone",
        "motivated_proteins_backbone",
    ]


def test_overnight_queue_backlog_preview_has_twenty_six_jobs() -> None:
    payload = build_overnight_queue_backlog_preview(load_runtime_state())
    assert payload["job_count"] == 22
    assert payload["active_job_count"] == 0
    assert payload["supervisor_pending_job_count"] == 0
    assert payload["catalog_job_count"] == 22
    assert payload["rows"][0]["source_kind"] == "catalog"
    assert payload["rows"][0]["job_id"] == "P2-I016"
    assert payload["summary"]["queue_state_counts"] == {
        "active_now": 0,
        "supervisor_pending": 0,
        "overnight_catalog": 22,
    }


def test_overnight_execution_contract_preview_uses_runtime_checkpoints() -> None:
    gap_matrix = build_scrape_gap_matrix_preview(
        load_source_coverage_matrix(),
        load_scrape_readiness_registry(),
        load_procurement_status_board(),
    )
    backlog = build_overnight_queue_backlog_preview(load_runtime_state())
    payload = build_overnight_execution_contract_preview(
        gap_matrix,
        backlog,
        load_runtime_state(),
        load_live_bundle_validation(),
        load_procurement_status_board(),
    )
    assert payload["execution_window_hours"] == 12
    assert payload["queue_contract"]["active_job_count"] == 0
    assert payload["queue_contract"]["supervisor_pending_job_count"] == 0
    assert payload["queue_contract"]["catalog_job_count"] == 22
    assert payload["queue_contract"]["checkpoint_file_count"] == 5
    assert len(payload["health_checkpoints"]) == 4
    assert payload["truth_boundary"]["no_duplicate_launches"] is True
    assert (
        payload["summary"]["bundle_validation_status"]
        == "aligned_current_preview_with_verified_assets"
    )
    assert payload["summary"]["missing_lane_count"] == 2
