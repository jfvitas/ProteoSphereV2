from __future__ import annotations

from scripts.audit_external_cohort import (
    build_external_cohort_audit,
    render_external_cohort_audit_markdown,
)


def test_build_external_cohort_audit_flags_stratified_bucket_layout() -> None:
    split_labels = {
        "manifest_id": "manifest:test",
        "split_policy": "accession-level only",
        "counts": {"total": 4, "train": 2, "val": 1, "test": 1, "resolved": 4, "unresolved": 0},
        "labels": [
            {"accession": "P1", "split": "train", "bucket": "rich", "status": "resolved"},
            {"accession": "P2", "split": "train", "bucket": "moderate", "status": "resolved"},
            {"accession": "P3", "split": "val", "bucket": "sparse", "status": "resolved"},
            {"accession": "P4", "split": "test", "bucket": "sparse", "status": "resolved"},
        ],
        "leakage_ready": {
            "accession_level_only": True,
            "duplicate_accessions": [],
            "cross_split_duplicates": [],
        },
    }
    library_contract = {"artifact_id": "p50_training_set_creator_library_contract"}
    packet_deficit = {
        "packets": [
            {"accession": "P4", "missing_modalities": ["ligand", "ppi"]},
        ]
    }
    eligibility_matrix = {
        "rows": [
            {
                "accession": "P1",
                "task_eligibility": {
                    "grounded_ligand_similarity_preview": {"status": "eligible_for_task"}
                },
                "ligand_readiness_ladder": "grounded preview-safe",
                "modality_readiness": {
                    "ligand": "grounded preview-safe",
                    "structure": "absent",
                },
            },
            {
                "accession": "P2",
                "task_eligibility": {
                    "grounded_ligand_similarity_preview": {
                        "status": "candidate_only_non_governing"
                    }
                },
                "ligand_readiness_ladder": "candidate-only non-governing",
                "modality_readiness": {
                    "ligand": "candidate-only non-governing",
                    "structure": "absent",
                },
            },
            {
                "accession": "P3",
                "task_eligibility": {
                    "grounded_ligand_similarity_preview": {"status": "library_only"}
                },
                "ligand_readiness_ladder": "support-only",
                "modality_readiness": {"ligand": "support-only", "structure": "support-only"},
            },
            {
                "accession": "P4",
                "task_eligibility": {
                    "grounded_ligand_similarity_preview": {
                        "status": "blocked_pending_acquisition"
                    }
                },
                "ligand_readiness_ladder": "absent",
                "modality_readiness": {"ligand": "absent", "structure": "absent"},
            },
        ]
    }

    payload = build_external_cohort_audit(
        split_labels,
        library_contract,
        packet_deficit_payload=packet_deficit,
        eligibility_matrix_payload=eligibility_matrix,
    )

    assert payload["audit_results"]["imbalance"]["status"] == "attention_needed"
    assert payload["audit_results"]["leakage"]["status"] == "ok"
    assert payload["audit_results"]["ligand_follow_through"]["status"] == "attention_needed"
    assert payload["audit_results"]["ligand_follow_through"]["decision"] == (
        "keep_ligand_split_non_governing"
    )
    assert payload["audit_results"]["ligand_follow_through"]["grounded_accessions"] == ["P1"]
    assert payload["audit_results"]["ligand_follow_through"]["candidate_only_accessions"] == [
        "P2"
    ]
    assert payload["audit_results"]["ligand_follow_through"]["readiness_ladder"]["counts"] == {
        "absent": 1,
        "support-only": 1,
        "candidate-only non-governing": 1,
        "grounded preview-safe": 1,
    }
    assert payload["audit_results"]["modality_readiness"]["status"] == "attention_needed"
    assert payload["audit_results"]["modality_readiness"]["modality_counts"]["ligand"] == {
        "absent": 1,
        "candidate-only non-governing": 1,
        "grounded preview-safe": 1,
        "support-only": 1,
    }
    assert payload["audit_results"]["coverage_gaps"]["missing_modalities_by_accession"] == {
        "P4": ["ligand", "ppi"]
    }
    assert payload["audit_results"]["overall"]["decision"] == "usable_with_notes"


def test_render_external_cohort_audit_markdown_has_core_sections() -> None:
    payload = {
        "audited_split": {
            "manifest_id": "manifest:test",
            "split_policy": "accession-level only",
            "split_counts": {"total": 4},
            "bucket_counts": {"rich": 2, "sparse": 2},
        },
        "audit_results": {
            "imbalance": {"status": "attention_needed"},
            "leakage": {"status": "ok"},
            "coverage_gaps": {"status": "attention_needed"},
            "modality_readiness": {
                "status": "attention_needed",
                "modality_counts": {"ligand": {"grounded preview-safe": 1}},
            },
            "ligand_follow_through": {
                "status": "attention_needed",
                "decision": "keep_ligand_split_non_governing",
                "grounded_accessions": ["P1"],
                "candidate_only_accessions": ["P2"],
                "blocked_accessions": ["P4"],
                "library_only_accessions": ["P3"],
                "readiness_ladder": {
                    "counts": {
                        "absent": 1,
                        "support-only": 1,
                        "candidate-only non-governing": 1,
                        "grounded preview-safe": 1,
                    },
                    "grounded_preview_safe_accessions": ["P1"],
                    "grounded_governing_accessions": [],
                    "candidate_only_non_governing_accessions": ["P2"],
                    "support_only_accessions": ["P3"],
                    "absent_accessions": ["P4"],
                },
            },
            "overall": {"status": "attention_needed", "decision": "usable_with_notes"},
        },
        "recommended_operator_actions": ["Do not reshuffle the frozen split silently."],
    }

    markdown = render_external_cohort_audit_markdown(payload)

    assert "# External Cohort Audit" in markdown
    assert "What Was Audited" in markdown
    assert "Audit Result" in markdown
    assert "Ligand Follow-Through" in markdown
    assert "Modality readiness" in markdown
    assert "Ligand readiness ladder counts" in markdown
    assert "keep_ligand_split_non_governing" in markdown
    assert "Recommended Next Action" in markdown
