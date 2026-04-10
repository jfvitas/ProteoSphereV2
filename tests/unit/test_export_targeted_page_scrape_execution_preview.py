from __future__ import annotations

from scripts.export_targeted_page_scrape_execution_preview import (
    build_targeted_page_scrape_execution_preview,
)


def test_build_targeted_page_scrape_execution_preview_orders_by_policy_anchor() -> None:
    payload = build_targeted_page_scrape_execution_preview(
        {
            "rows": [
                {
                    "accession": "P04637",
                    "target_family": "elm_motif_context",
                    "candidate_pages": ["https://elm.example/P04637"],
                    "default_ingest_status": "candidate_only_non_governing",
                    "page_scraping_started": False,
                },
                {
                    "accession": "Q9UCM0",
                    "target_family": "string_interaction_context",
                    "candidate_pages": ["https://string.example/Q9UCM0"],
                    "default_ingest_status": "candidate_only_non_governing",
                    "page_scraping_started": False,
                },
            ]
        },
        {
            "allowed_policy_labels": [
                "report_only_non_governing",
                "preview_bundle_safe_non_governing",
            ]
        },
        {
            "scrape_and_enrichment_priorities": {
                "top_next_acquisitions": [
                    {
                        "rank": 2,
                        "target": "STRING guarded procurement first wave",
                        "why": "interaction breadth first",
                    },
                    {
                        "rank": 5,
                        "target": "ELM acquisition refresh",
                        "why": "motif depth later",
                    },
                ]
            }
        },
    )

    assert payload["row_count"] == 2
    assert payload["rows"][0]["accession"] == "Q9UCM0"
    assert payload["rows"][0]["priority_rank"] == 1
    assert payload["rows"][0]["priority_anchor_target"] == "STRING guarded procurement first wave"
    assert payload["rows"][1]["accession"] == "P04637"
    assert payload["summary"]["ordered_accessions"] == ["Q9UCM0", "P04637"]


def test_build_targeted_page_scrape_execution_preview_stays_candidate_only_non_governing() -> None:
    payload = build_targeted_page_scrape_execution_preview(
        {
            "rows": [
                {
                    "accession": "P04637",
                    "target_family": "elm_motif_context",
                    "candidate_pages": [
                        "https://elm.eu.org/",
                        "https://rest.uniprot.org/uniprotkb/P04637.json",
                    ],
                    "default_ingest_status": "candidate_only_non_governing",
                    "page_scraping_started": False,
                }
            ]
        },
        {
            "allowed_policy_labels": [
                "report_only_non_governing",
                "preview_bundle_safe_non_governing",
                "grounded_and_governing",
            ]
        },
        {
            "scrape_and_enrichment_priorities": {
                "top_next_acquisitions": [
                    {
                        "rank": 5,
                        "target": "ELM acquisition refresh",
                        "why": "motif enrichment",
                    }
                ]
            }
        },
    )

    assert payload["status"] == "report_only"
    assert payload["rows"][0]["default_ingest_status"] == "candidate_only_non_governing"
    assert payload["rows"][0]["policy_label"] == "report_only_non_governing"
    assert payload["rows"][0]["execution_status"] == "ready_for_candidate_only_capture"
    assert payload["rows"][0]["governing_for_split_or_leakage"] is False
    assert payload["truth_boundary"]["candidate_only_non_governing"] is True
    assert payload["truth_boundary"]["bundle_included"] is False
    assert payload["summary"]["page_scraping_started"] is False
