from __future__ import annotations

from scripts.export_overnight_execution_contract_preview import (
    build_overnight_execution_contract_preview,
)
from scripts.export_overnight_queue_backlog_preview import (
    build_overnight_queue_backlog_preview,
)
from scripts.export_scrape_gap_matrix_preview import build_scrape_gap_matrix_preview
from scripts.external_dataset_assessment_support import (
    build_external_dataset_audits,
    build_external_dataset_intake_contract_preview,
)
from scripts.training_set_builder_preview_support import (
    build_balance_diagnostics_preview,
    build_cohort_compiler_preview,
    build_package_readiness_preview,
    build_training_set_builder_session_preview,
    build_training_set_readiness_preview,
)


def test_training_set_builder_previews_stay_report_only() -> None:
    eligibility = {
        "rows": [
            {
                "accession": "P00387",
                "ligand_readiness_ladder": "grounded preview-safe",
                "task_eligibility": {
                    "full_packet_current_latest": {"status": "blocked_pending_acquisition"},
                    "grounded_ligand_similarity_preview": {"status": "eligible_for_task"},
                },
            },
            {
                "accession": "Q9NZD4",
                "ligand_readiness_ladder": "candidate-only non-governing",
                "task_eligibility": {
                    "full_packet_current_latest": {"status": "audit_only"},
                    "grounded_ligand_similarity_preview": {
                        "status": "candidate_only_non_governing"
                    },
                },
            },
        ],
        "summary": {"accession_count": 2},
    }
    missing_policy = {"truth_boundary": {"candidate_only_rows_non_governing": True}}
    balanced_plan = {
        "requested_modalities": ["sequence", "structure", "ligand", "ppi"],
        "packet_materialization_mode": "report_only_preview",
        "selected_rows": [
            {
                "accession": "P00387",
                "split": "train",
                "bucket": "moderate_coverage",
                "present_modalities": ["sequence", "structure"],
                "missing_modalities": ["ligand", "ppi"],
                "source_lanes": ["UniProt"],
                "packet_expectation": {"status": "partial"},
                "thin_coverage": False,
                "mixed_evidence": False,
            }
        ],
        "summary": {
            "selected_split_counts": {"train": 1},
            "selected_modality_coverage": {"sequence": 1, "structure": 1},
            "leakage_safe": True,
        },
    }
    external_audit = {
        "audit_results": {
            "overall": {"status": "attention_needed", "decision": "usable_with_caveats"}
        }
    }
    packet_deficit = {
        "summary": {
            "packet_count": 2,
            "judgment_counts": {"useful": 1, "weak": 1},
            "completeness_counts": {"partial": 1, "complete": 1},
        },
        "modality_deficits": [
            {
                "packet_accessions": ["Q9NZD4"],
                "top_source_fix_refs": ["ligand:Q9NZD4"],
            }
        ],
    }
    split_engine_input = {
        "execution_readiness": {
            "assignment_ready": True,
            "fold_export_ready": False,
        },
        "truth_boundary": {"final_split_committed": False},
    }
    split_dry_run = {"status": "aligned"}
    split_gate = {"unlock_readiness": {"cv_fold_export_unlocked": False}}
    split_post_stage = {"gate_check": {"gate_status": "blocked"}}

    cohort = build_cohort_compiler_preview(
        eligibility,
        missing_policy,
        balanced_plan,
        external_audit,
        packet_deficit,
    )
    balance = build_balance_diagnostics_preview(
        eligibility,
        missing_policy,
        balanced_plan,
        external_audit,
        packet_deficit,
    )
    package = build_package_readiness_preview(
        eligibility,
        missing_policy,
        balanced_plan,
        external_audit,
        packet_deficit,
        split_engine_input,
        split_dry_run,
        split_gate,
        split_post_stage,
    )
    readiness = build_training_set_readiness_preview(
        eligibility,
        missing_policy,
        balanced_plan,
        external_audit,
        packet_deficit,
        split_engine_input,
        split_gate,
        package,
    )
    session = build_training_set_builder_session_preview(readiness, cohort, package)

    assert cohort["status"] == "report_only"
    assert cohort["summary"]["selected_count"] == 1
    assert balance["summary"]["thin_coverage_count"] == 0
    assert package["summary"]["ready_for_package"] is False
    assert readiness["status"] == "report_only"
    assert readiness["five_questions"]["package_ready_now"]["status"] == "blocked"
    assert session["summary"]["session_state"] == "ready_for_operator_review"


def test_external_dataset_assessment_and_overnight_previews_are_fail_closed() -> None:
    intake = build_external_dataset_intake_contract_preview()
    audits = build_external_dataset_audits(
        {
            "split_policy": "accession-level only",
            "leakage_ready": {
                "accession_level_only": True,
                "cross_split_duplicates": [],
            },
            "labels": [
                {"accession": "P00387", "split": "train"},
                {"accession": "Q9NZD4", "split": "test"},
            ],
        },
        {"artifact_id": "library_contract", "status": "report_only"},
        {
            "audit_results": {
                "leakage": {"notes": []},
                "modality_readiness": {"modality_counts": {"ligand": {"support-only": 1}}},
            }
        },
        {
            "rows": [
                {
                    "accession": "P00387",
                    "task_eligibility": {
                        "full_packet_current_latest": {"status": "blocked_pending_acquisition"},
                        "grounded_ligand_similarity_preview": {"status": "eligible_for_task"},
                    },
                },
                {
                    "accession": "Q9NZD4",
                    "task_eligibility": {
                        "full_packet_current_latest": {"status": "audit_only"},
                        "grounded_ligand_similarity_preview": {
                            "status": "candidate_only_non_governing"
                        },
                    },
                },
            ]
        },
        {
            "summary": {
                "measurement_type_counts": {"Kd": 3},
                "complex_type_counts": {"protein_ligand": 3},
                "source_counts": {"bindingdb": 2},
            }
        },
        {"rows": [{"accession": "P00387"}]},
        {"rows": [{"accession": "P00387", "structure_unit_count": 1}]},
        {
            "summary": {
                "direct_grounding_candidate_count": 0,
                "off_target_adjacent_context_only_count": 2,
            }
        },
        {"summary": {"unique_mapped_target_accession_count": 1}},
        {"summary": {"source_count": 2}},
    )
    scrape_gap = build_scrape_gap_matrix_preview(
        {"summary": {"status_counts": {"available": 1}}},
        {"summary": {"top_scrape_targets": ["bindingdb"]}},
        {"status": "blocked_pending_zero_gap", "summary": {"remaining_gap_file_count": 2}},
    )
    backlog = build_overnight_queue_backlog_preview(
        {
            "observed_active": [],
            "pending": [],
            "status": "ok",
        }
    )
    execution = build_overnight_execution_contract_preview(
        scrape_gap,
        backlog,
        {"status": "ok"},
        {"status": "aligned"},
        {"status": "blocked_pending_zero_gap"},
    )

    assert intake["status"] == "report_only"
    assert intake["accepted_shapes"][0]["shape_id"] == "json_manifest"
    assert audits["top_level"]["summary"]["overall_verdict"] in {
        "usable_with_caveats",
        "audit_only",
        "blocked_pending_mapping",
        "blocked_pending_cleanup",
    }
    assert audits["top_level"]["truth_boundary"]["non_mutating"] is True
    assert audits["binding"]["verdict"] in {"usable_with_caveats", "audit_only"}
    assert scrape_gap["summary"]["remaining_gap_file_count"] == 2
    assert backlog["summary"]["selected_top_count"] >= 0
    assert execution["summary"]["estimated_cycles"] == 720
