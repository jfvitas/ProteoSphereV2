from __future__ import annotations

from scripts.export_string_interaction_materialization_plan_preview import (
    build_string_interaction_materialization_plan_preview,
)
from scripts.export_uniref_cluster_materialization_plan_preview import (
    build_uniref_cluster_materialization_plan_preview,
)


def test_build_string_interaction_materialization_plan_preview_stays_report_only() -> None:
    payload = build_string_interaction_materialization_plan_preview(
        {"gate_status": "blocked_pending_zero_gap", "remaining_gap_file_count": 3},
        {"percent_complete": 98.1, "status": "partial"},
        {"active_rows": [{"relative_path": "STRING/protein.links.full.v12.0.txt.gz"}]},
        {"rows": [{"accession": "P09105"}]},
        {
            "status": "preview_only",
            "rows": [
                {"accession": "P09105"},
                {"accession": "P69905"},
                {"protein_accession": "P09105"},
            ],
        },
    )

    assert payload["status"] == "report_only"
    assert payload["supported_accession_count"] == 2
    assert payload["planned_families"][0]["family_id"] == "string_interaction_compact_preview"
    assert payload["truth_boundary"]["governing"] is False


def test_build_uniref_cluster_materialization_plan_preview_stays_report_only() -> None:
    payload = build_uniref_cluster_materialization_plan_preview(
        {"gate_status": "blocked_pending_zero_gap"},
        {"rows": [{"accession": "P00387"}, {"accession": "Q9NZD4"}]},
    )

    assert payload["status"] == "report_only"
    assert payload["supported_accession_count"] == 2
    assert payload["summary"]["planned_family_id"] == "uniref_cluster_context_preview"
    assert payload["truth_boundary"]["materialization_started"] is False
