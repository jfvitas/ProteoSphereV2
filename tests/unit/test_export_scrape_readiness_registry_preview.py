from __future__ import annotations

from scripts.export_scrape_readiness_registry_preview import (
    build_scrape_readiness_registry_preview,
)


def test_build_scrape_readiness_registry_preview_stays_report_only() -> None:
    payload = build_scrape_readiness_registry_preview(
        {
            "scrape_and_enrichment_priorities": {
                "top_next_acquisitions": [
                    {"target": "BioGRID guarded procurement first wave"},
                    {"target": "STRING guarded procurement first wave"},
                    {"target": "IntAct authoritative mirror refresh or intake"},
                ]
            }
        },
        {"summary": {"bundle_included_families": ["motif_domain_compact_preview_family"]}},
    )

    assert payload["status"] == "report_only"
    assert payload["row_count"] == 3
    assert payload["summary"]["top_scrape_targets"][0] == "motif_active_site_enrichment"
    assert (
        payload["summary"]["default_ingest_statuses"]["interaction_context_enrichment"]
        == "candidate_only_non_governing"
    )
    assert (
        payload["rows"][1]["status"]
        == "decision_complete_ready_for_non_governing_materialization"
    )
    assert payload["truth_boundary"]["scraping_started"] is True
