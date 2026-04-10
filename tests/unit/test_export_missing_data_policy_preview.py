from __future__ import annotations

from scripts.export_missing_data_policy_preview import build_missing_data_policy_preview


def test_build_missing_data_policy_preview_includes_rules_and_priorities() -> None:
    eligibility_matrix = {
        "summary": {
            "primary_missing_data_class_counts": {
                "eligible_for_task": 3,
                "blocked_pending_acquisition": 2,
            },
            "task_status_counts": {
                "protein_reference": {"eligible_for_task": 4, "audit_only": 1},
                "full_packet_current_latest": {
                    "eligible_for_task": 3,
                    "blocked_pending_acquisition": 2,
                },
                "grounded_ligand_similarity_preview": {
                    "eligible_for_task": 1,
                    "candidate_only_non_governing": 1,
                    "library_only": 2,
                },
            },
        }
    }
    scope_audit = {
        "scope_judgment": "not yet broad/deep enough",
        "top_next_acquisitions": [
            {"rank": 1, "target": "BioGRID", "why": "PPI breadth"},
            {"rank": 2, "target": "STRING", "why": "network breadth"},
        ],
    }

    payload = build_missing_data_policy_preview(eligibility_matrix, scope_audit)

    assert payload["status"] == "complete"
    assert payload["category_counts"]["eligible_for_task"] == 3
    assert payload["policy_categories"][0]["category"] == "eligible_for_task"
    assert payload["truth_boundary"]["deletion_default"] is False
    assert payload["scrape_and_enrichment_priorities"]["top_next_acquisitions"][0]["target"] == (
        "BioGRID"
    )
