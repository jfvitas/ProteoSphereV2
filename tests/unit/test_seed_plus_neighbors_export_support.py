from __future__ import annotations

from scripts.seed_plus_neighbors_export_support import (
    build_post_tail_unlock_dry_run_preview,
    build_seed_plus_neighbors_baseline_sidecar_preview,
    build_seed_plus_neighbors_entity_resolution_preview,
    build_seed_plus_neighbors_multimodal_sidecar_preview,
    build_seed_plus_neighbors_structured_corpus_preview,
)


def test_structured_corpus_preview_captures_seed_plus_neighbors_rows() -> None:
    payload = build_seed_plus_neighbors_structured_corpus_preview()

    summary = payload["summary"]
    assert payload["status"] == "report_only"
    assert summary["seed_accession_count"] == 12
    assert summary["row_count"] > 1000
    assert summary["row_family_counts"]["protein"] >= 12
    assert summary["row_family_counts"]["interaction"] >= 1
    assert summary["row_family_counts"]["page_support"] >= 1


def test_entity_resolution_preview_tracks_unresolved_rows() -> None:
    payload = build_seed_plus_neighbors_entity_resolution_preview()

    summary = payload["summary"]
    assert payload["status"] == "report_only"
    assert summary["row_count"] > 0
    assert summary["unresolved_count"] > 0
    assert "rows" in payload
    assert all("canonical_id" in row for row in payload["rows"])


def test_training_sidecars_and_unlock_dry_run_are_report_only() -> None:
    baseline = build_seed_plus_neighbors_baseline_sidecar_preview()
    multimodal = build_seed_plus_neighbors_multimodal_sidecar_preview()
    unlock = build_post_tail_unlock_dry_run_preview()

    assert baseline["summary"]["example_count"] == 12
    assert baseline["summary"]["governing_ready_example_count"] == 2
    assert baseline["summary"]["all_visible_training_candidates_view_count"] == 12

    assert multimodal["summary"]["strict_governing_training_view_count"] == 2
    assert multimodal["summary"]["all_visible_training_candidates_view_count"] == 12
    assert multimodal["truth_boundary"]["report_only"] is True
    assert multimodal["truth_boundary"]["non_mutating"] is True

    assert unlock["summary"]["live_downloads_complete"] is True
    assert unlock["summary"]["blocked_step_count"] == 0
    assert unlock["summary"]["ready_step_count"] == 8
    assert unlock["truth_boundary"]["dry_run"] is True
