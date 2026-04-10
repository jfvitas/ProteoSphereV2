from __future__ import annotations

from scripts.export_procurement_space_recovery_gap_drift_preview import (
    GIB,
    build_procurement_space_recovery_gap_drift_preview,
)


def test_gap_drift_preview_reports_first_shortfall_observation() -> None:
    payload = build_procurement_space_recovery_gap_drift_preview(
        {"summary": {"reclaim_to_zero_bytes": 5 * GIB}},
        {"batches": {"zero_gap_batch": {"cumulative_reclaim_bytes": 3 * GIB}}},
        {},
    )

    assert payload["summary"]["drift_state"] == "first_shortfall_observation"
    assert payload["summary"]["current_zero_gap_shortfall_bytes"] == 2 * GIB


def test_gap_drift_preview_reports_gap_widening() -> None:
    payload = build_procurement_space_recovery_gap_drift_preview(
        {"summary": {"reclaim_to_zero_bytes": 8 * GIB}},
        {"batches": {"zero_gap_batch": {"cumulative_reclaim_bytes": 5 * GIB}}},
        {"summary": {"current_zero_gap_shortfall_bytes": 2 * GIB}},
    )

    assert payload["summary"]["drift_state"] == "gap_widening"
