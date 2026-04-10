from __future__ import annotations

from scripts.export_compact_enrichment_policy_preview import (
    build_compact_enrichment_policy_preview,
)


def test_build_compact_enrichment_policy_preview_assigns_expected_labels() -> None:
    payload = build_compact_enrichment_policy_preview(
        {
            "status": "complete",
            "row_count": 2,
            "truth_boundary": {
                "ready_for_bundle_preview": False,
                "interaction_family_materialized": False,
            },
        },
        {
            "status": "complete",
            "row_count": 5,
            "truth_boundary": {
                "ready_for_bundle_preview": True,
                "governing_for_split_or_leakage": False,
            },
        },
        {
            "status": "complete",
            "row_count": 3,
            "truth_boundary": {
                "ready_for_bundle_preview": True,
            },
        },
        {
            "record_counts": {
                "interaction_similarity_signatures": 0,
                "motif_domain_compact_preview_family": 5,
                "kinetics_support_preview": 3,
            }
        },
    )

    assert payload["row_count"] == 3
    rows = {row["family_name"]: row for row in payload["rows"]}
    assert rows["interaction_similarity_preview"]["policy_label"] == "report_only_non_governing"
    assert rows["interaction_similarity_preview"]["bundle_included"] is False
    assert rows["motif_domain_compact_preview_family"]["policy_label"] == (
        "preview_bundle_safe_non_governing"
    )
    assert rows["kinetics_support_preview"]["bundle_included"] is True
