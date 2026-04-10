from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _powershell_executable() -> str:
    for candidate in ("powershell.exe", "pwsh.exe"):
        path = shutil.which(candidate)
        if path:
            return path
    raise RuntimeError("PowerShell is required for the operator visibility integration test")


def _run_interface(
    repo_root: Path,
    mode: str,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    command = [
        _powershell_executable(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(repo_root / "scripts" / "powershell_interface.ps1"),
        "-Mode",
        mode,
        *extra_args,
    ]
    return subprocess.run(
        command,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_operator_visibility_tracks_dashboard_export_truthfully() -> None:
    operator = json.loads(_run_interface(REPO_ROOT, "state", "-AsJson").stdout)
    subprocess.run(
        ["python", "scripts/export_operator_dashboard.py"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    results_dir = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"
    dashboard = json.loads((results_dir / "operator_dashboard.json").read_text(encoding="utf-8"))
    run_summary = json.loads((results_dir / "run_summary.json").read_text(encoding="utf-8"))
    summary = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))

    assert operator["benchmark"]["exists"] is True
    assert operator["benchmark"]["benchmark_summary"]["status"] == summary["status"]
    assert (
        operator["benchmark"]["benchmark_summary"]["status"]
        == dashboard["benchmark_summary"]["status"]
    )
    assert operator["benchmark"]["completion_status"] == summary["status"]
    assert operator["benchmark"]["completion_status"] == dashboard["release_grade_status"]

    assert operator["benchmark"]["release_grade_status"] == "blocked"
    assert operator["benchmark"]["release_grade_blockers"] == run_summary["remaining_gaps"]
    assert "blocked_on_release_grade_bar" not in operator["benchmark"][
        "release_grade_blockers"
    ]
    assert operator["benchmark"]["release_ready"] is False

    assert dashboard["assessment"]["coverage_not_validation"] is True
    assert dashboard["assessment"]["identity_safe_resume"] is True
    assert dashboard["assessment"]["release_grade_blocked"] is True
    assert dashboard["assessment"]["release_grade_corpus_validation"] is False
    assert dashboard["dashboard_status"] == "blocked_on_release_grade_bar"
    assert dashboard["release_grade_status"] == "blocked_on_release_grade_bar"
    assert dashboard["benchmark_summary"]["status"] == "blocked_on_release_grade_bar"
    assert dashboard["procurement_status"]["canonical_latest"]["status"] == "ready"
    assert (
        dashboard["procurement_status"]["canonical_latest"]["unresolved_counts"][
            "assay_unresolved_cases"
        ]
        == 0
    )
    assert dashboard["procurement_status"]["summary_library_inventory"]["record_count"] == 11
    assert dashboard["procurement_status"]["summary_library_inventory"]["record_type_counts"] == {
        "protein": 11,
        "protein_variant": 0,
        "structure_unit": 0,
        "protein_protein": 0,
        "protein_ligand": 0,
    }
    assert (
        dashboard["procurement_status"]["protein_variant_library_inventory"]["record_count"]
        > 0
    )
    assert dashboard["procurement_status"]["protein_variant_library_inventory"][
        "record_type_counts"
    ] == {
        "protein": 0,
        "protein_variant": dashboard["procurement_status"]["protein_variant_library_inventory"][
            "record_count"
        ],
        "structure_unit": 0,
        "protein_protein": 0,
        "protein_ligand": 0,
    }
    assert (
        dashboard["procurement_status"]["structure_unit_library_inventory"]["record_count"]
        == 4
    )
    assert (
        dashboard["procurement_status"]["protein_similarity_signature_preview"]["row_count"]
        == 11
    )
    assert dashboard["procurement_status"]["protein_similarity_signature_preview"][
        "ready_for_bundle_preview"
    ] is True
    assert dashboard["procurement_status"]["dictionary_preview"]["row_count"] > 0
    assert dashboard["procurement_status"]["dictionary_preview"]["namespace_count"] > 0
    assert "InterPro" in dashboard["procurement_status"]["dictionary_preview"]["namespaces"]
    assert dashboard["procurement_status"]["dictionary_preview"][
        "ready_for_bundle_preview"
    ] is True
    assert dashboard["procurement_status"]["dictionary_preview"][
        "biological_content_family"
    ] is False
    assert dashboard["procurement_status"]["motif_domain_compact_preview_family"][
        "row_count"
    ] > 0
    assert dashboard["procurement_status"]["motif_domain_compact_preview_family"][
        "included_namespaces"
    ] == ["InterPro", "PROSITE", "Pfam"]
    assert dashboard["procurement_status"]["motif_domain_compact_preview_family"][
        "ready_for_bundle_preview"
    ] is True
    assert dashboard["procurement_status"]["motif_domain_compact_preview_family"][
        "governing_for_split_or_leakage"
    ] is False
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "status"
    ] == "complete"
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "row_count"
    ] == 2
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "accession_count"
    ] == 2
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "source_overlap_accessions"
    ] == ["P69905", "P09105"]
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "candidate_only_row_count"
    ] == 2
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "ready_for_bundle_preview"
    ] is False
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "interaction_family_materialized"
    ] is False
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "direct_interaction_family_claimed"
    ] is False
    assert dashboard["procurement_status"][
        "interaction_similarity_signature_validation"
    ]["status"] == "aligned"
    assert dashboard["procurement_status"][
        "interaction_similarity_signature_validation"
    ]["row_count"] == 2
    assert dashboard["procurement_status"][
        "interaction_similarity_signature_validation"
    ]["candidate_only_accessions"] == ["P69905", "P09105"]
    assert dashboard["procurement_status"][
        "interaction_similarity_signature_validation"
    ]["bundle_safe_immediately"] is False
    assert dashboard["procurement_status"]["sabio_rk_support_preview"]["status"] == "complete"
    assert dashboard["procurement_status"]["sabio_rk_support_preview"][
        "supported_accession_count"
    ] == 3
    assert dashboard["procurement_status"]["sabio_rk_support_preview"][
        "supported_accessions"
    ] == ["P00387", "P04637", "P31749"]
    assert dashboard["procurement_status"]["sabio_rk_support_preview"][
        "live_kinetic_ids_verified"
    ] is False
    assert dashboard["procurement_status"]["sabio_rk_support_preview"][
        "dashboard_blocked"
    ] is True
    assert dashboard["procurement_status"]["procurement_tail_freeze_gate_preview"][
        "gate_status"
    ] == "blocked_pending_zero_gap"
    assert dashboard["procurement_status"]["procurement_tail_freeze_gate_preview"][
        "remaining_gap_file_count"
    ] == 2
    assert dashboard["procurement_status"]["procurement_tail_freeze_gate_preview"][
        "not_yet_started_file_count"
    ] == 0
    assert dashboard["procurement_status"][
        "string_interaction_materialization_plan_preview"
    ]["supported_accession_count"] >= 1
    assert "string_interaction_compact_preview" in dashboard["procurement_status"][
        "string_interaction_materialization_plan_preview"
    ]["planned_family_ids"]
    assert dashboard["procurement_status"][
        "uniref_cluster_materialization_plan_preview"
    ]["planned_family_id"] == "uniref_cluster_context_preview"
    assert dashboard["procurement_status"]["pdb_enrichment_scrape_registry_preview"][
        "seed_structure_ids"
    ] == ["1Y01", "4HHB"]
    assert dashboard["procurement_status"]["structure_entry_context_preview"][
        "harvested_structure_count"
    ] == 2
    assert dashboard["procurement_status"]["pdb_enrichment_validation_preview"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["protein_origin_context_preview"][
        "harvested_accession_count"
    ] == 12
    assert dashboard["procurement_status"]["catalytic_site_context_preview"][
        "accession_count"
    ] == 3
    assert dashboard["procurement_status"]["targeted_page_scrape_registry_preview"][
        "target_accessions"
    ] == ["P04637", "P31749"]
    assert dashboard["procurement_status"]["binding_measurement_registry_preview"][
        "row_count"
    ] >= 23000
    assert dashboard["procurement_status"]["binding_measurement_validation_preview"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["accession_binding_support_preview"][
        "accessions_with_measurements"
    ] >= 2
    assert dashboard["procurement_status"]["interaction_context_preview"][
        "accessions_with_intact_rows"
    ] >= 10
    assert dashboard["procurement_status"]["structure_chain_origin_preview"][
        "chain_count"
    ] == 6
    assert dashboard["procurement_status"]["protein_function_context_preview"][
        "accessions_with_function_comment"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_dump_inventory_preview"][
        "has_mysql_dump"
    ] is True
    assert dashboard["procurement_status"]["bindingdb_target_polymer_context_preview"][
        "accessions_with_bindingdb_polymer_bridge"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_structure_bridge_preview"][
        "structures_with_bindingdb_bridge"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_measurement_subset_preview"][
        "accessions_with_bindingdb_measurements"
    ] >= 1
    assert dashboard["procurement_status"][
        "bindingdb_structure_measurement_projection_preview"
    ]["structures_with_bindingdb_measurements"] >= 1
    assert dashboard["procurement_status"]["bindingdb_partner_monomer_context_preview"][
        "monomer_count"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_structure_assay_summary_preview"][
        "structures_with_assay_summary"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_accession_assay_profile_preview"][
        "accessions_with_assay_profile"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_assay_condition_profile_preview"][
        "accessions_with_condition_profile"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_structure_partner_profile_preview"][
        "structures_with_partner_profile"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_partner_descriptor_reconciliation_preview"][
        "partner_monomer_count"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_accession_partner_identity_profile_preview"][
        "accessions_with_partner_identity_profile"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_structure_grounding_candidate_preview"][
        "accessions_with_future_structure_candidates"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_future_structure_registry_preview"][
        "registered_future_structure_count"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_future_structure_context_preview"][
        "harvested_future_structure_count"
    ] >= 1
    assert dashboard["procurement_status"]["bindingdb_future_structure_alignment_preview"][
        "mismatched_structure_count"
    ] >= 0
    assert dashboard["procurement_status"]["bindingdb_future_structure_triage_preview"][
        "off_target_adjacent_context_only_count"
    ] >= 0
    assert dashboard["procurement_status"][
        "bindingdb_off_target_adjacent_context_profile_preview"
    ]["source_accession_count"] >= 0
    assert dashboard["procurement_status"]["bindingdb_off_target_target_profile_preview"][
        "mapped_target_accession_count"
    ] >= 0
    assert dashboard["procurement_status"]["motif_domain_site_context_preview"][
        "accessions_with_interpro"
    ] >= 1
    assert dashboard["procurement_status"]["uniref_cluster_context_preview"]["row_count"] == 12
    assert dashboard["procurement_status"]["uniref_cluster_context_preview"][
        "gate_status"
    ] == "blocked_pending_zero_gap"
    assert dashboard["procurement_status"]["sequence_redundancy_guard_preview"][
        "row_count"
    ] == 12
    assert dashboard["procurement_status"]["binding_coverage"][
        "complex_type_counts"
    ]["protein_ligand"] >= 19000
    assert dashboard["procurement_status"]["binding_coverage"][
        "bindingdb_future_structure_candidate_accession_count"
    ] >= 1
    assert dashboard["procurement_status"]["binding_coverage"][
        "bindingdb_future_structure_harvested_count"
    ] >= 1
    assert dashboard["procurement_status"]["binding_coverage"][
        "bindingdb_future_structure_mismatched_count"
    ] >= 0
    assert dashboard["procurement_status"]["binding_coverage"][
        "bindingdb_future_structure_off_target_count"
    ] >= 0
    assert dashboard["procurement_status"]["binding_coverage"][
        "bindingdb_off_target_source_accession_count"
    ] >= 0
    assert dashboard["procurement_status"]["binding_coverage"][
        "bindingdb_off_target_mapped_target_count"
    ] >= 0
    assert dashboard["procurement_status"]["post_tail_library_forecast"][
        "seed_structure_ids"
    ] == ["1Y01", "4HHB"]
    assert dashboard["procurement_status"]["ligand_support_readiness_preview"][
        "row_count"
    ] == 4
    assert dashboard["procurement_status"]["ligand_support_readiness_preview"][
        "support_accessions"
    ] == ["P00387", "P09105", "Q2TAC2", "Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_support_readiness_preview"][
        "deferred_accessions"
    ] == ["Q9UCM0"]
    assert dashboard["procurement_status"]["ligand_support_readiness_preview"][
        "bundle_ligands_included"
    ] is False
    assert dashboard["procurement_status"]["ligand_support_readiness_preview"][
        "ligand_rows_materialized"
    ] is False
    assert dashboard["procurement_status"]["next_real_ligand_row_gate_preview"][
        "selected_accession"
    ] == "P09105"
    assert dashboard["procurement_status"]["next_real_ligand_row_gate_preview"][
        "selected_accession_gate_status"
    ] == "blocked_pending_acquisition"
    assert dashboard["procurement_status"]["next_real_ligand_row_gate_preview"][
        "fallback_accession"
    ] == "Q2TAC2"
    assert dashboard["procurement_status"]["next_real_ligand_row_gate_preview"][
        "fallback_accession_gate_status"
    ] == "blocked_pending_acquisition"
    assert dashboard["procurement_status"]["next_real_ligand_row_gate_preview"][
        "can_materialize_new_grounded_accession_now"
    ] is False
    assert dashboard["procurement_status"]["next_real_ligand_row_decision_preview"][
        "selected_accession"
    ] == "P09105"
    assert dashboard["procurement_status"]["next_real_ligand_row_decision_preview"][
        "selected_accession_gate_status"
    ] == "blocked_pending_acquisition"
    assert dashboard["procurement_status"]["next_real_ligand_row_decision_preview"][
        "fallback_accession"
    ] == "Q2TAC2"
    assert dashboard["procurement_status"]["next_real_ligand_row_decision_preview"][
        "fallback_accession_gate_status"
    ] == "blocked_pending_acquisition"
    assert dashboard["procurement_status"]["next_real_ligand_row_decision_preview"][
        "minimum_grounded_promotion_evidence_count"
    ] == 3
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "row_count"
    ] == 4
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "first_accession"
    ] == "P00387"
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "second_accession"
    ] == "Q9NZD4"
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "ordered_accessions"
    ] == ["P00387", "Q9NZD4", "P09105", "Q2TAC2"]
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "grounded_accession_count"
    ] == 2
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "grounded_accessions"
    ] == ["P00387", "Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "first_accession_evidence_kind"
    ] == "local_chembl_bulk_assay_summary"
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "row_complete_operator_summary"
    ] is True
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "deferred_accession"
    ] == "Q9UCM0"
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "ligand_rows_materialized"
    ] is False
    assert dashboard["procurement_status"]["ligand_stage1_operator_queue_preview"][
        "row_count"
    ] == 4
    assert dashboard["procurement_status"]["ligand_stage1_operator_queue_preview"][
        "ordered_accessions"
    ] == ["P00387", "Q9NZD4", "P09105", "Q2TAC2"]
    assert dashboard["procurement_status"]["ligand_stage1_operator_queue_preview"][
        "deferred_accession"
    ] == "Q9UCM0"
    assert dashboard["procurement_status"]["ligand_stage1_operator_queue_preview"][
        "report_only"
    ] is True
    assert dashboard["procurement_status"]["ligand_stage1_operator_queue_preview"][
        "ligand_rows_materialized"
    ] is False
    assert dashboard["procurement_status"]["p00387_ligand_extraction_validation_preview"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["p00387_ligand_extraction_validation_preview"][
        "accession"
    ] == "P00387"
    assert dashboard["procurement_status"]["p00387_ligand_extraction_validation_preview"][
        "target_chembl_id"
    ] == "CHEMBL2146"
    assert dashboard["procurement_status"]["p00387_ligand_extraction_validation_preview"][
        "rows_emitted"
    ] == 25
    assert dashboard["procurement_status"]["p00387_ligand_extraction_validation_preview"][
        "ready_for_operator_preview"
    ] is True
    assert dashboard["procurement_status"]["p00387_ligand_extraction_validation_preview"][
        "canonical_ligand_materialization_claimed"
    ] is False
    assert dashboard["procurement_status"]["q9nzd4_bridge_validation_preview"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["q9nzd4_bridge_validation_preview"][
        "accession"
    ] == "Q9NZD4"
    assert dashboard["procurement_status"]["q9nzd4_bridge_validation_preview"][
        "best_pdb_id"
    ] == "1Y01"
    assert dashboard["procurement_status"]["q9nzd4_bridge_validation_preview"][
        "component_id"
    ] == "CHK"
    assert dashboard["procurement_status"]["q9nzd4_bridge_validation_preview"][
        "ready_for_operator_preview"
    ] is True
    assert dashboard["procurement_status"]["q9nzd4_bridge_validation_preview"][
        "candidate_only"
    ] is True
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "row_count"
    ] == 2
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "validated_accessions"
    ] == ["P00387", "Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "aligned_row_count"
    ] == 2
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "candidate_only_accessions"
    ] == ["Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "ready_for_operator_preview"
    ] is True
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "ligand_rows_materialized"
    ] is False
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "bundle_ligands_included"
    ] is False
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "row_count"
    ] == 4
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "ordered_accessions"
    ] == ["P00387", "Q9NZD4", "P09105", "Q2TAC2"]
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "grounded_accessions"
    ] == ["P00387", "Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "held_support_only_accessions"
    ] == ["P09105", "Q2TAC2"]
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "candidate_only_accessions"
    ] == ["Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "ready_for_operator_preview"
    ] is True
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "ligand_rows_materialized"
    ] is False
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "bundle_ligands_included"
    ] is False
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "row_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "materialized_accessions"
    ] == ["P00387", "Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "grounded_accessions"
    ] == ["P00387"]
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "candidate_only_accessions"
    ] == ["Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "grounded_row_count"
    ] == 23
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "candidate_only_row_count"
    ] == 1
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "ligand_rows_materialized"
    ] is True
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "bundle_ligands_included"
    ] is True
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "canonical_ligand_materialization_claimed"
    ] is False
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "row_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "accession_count"
    ] == 2
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "exact_identity_group_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "chemical_series_group_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "candidate_only_count"
    ] == 1
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "ready_for_bundle_preview"
    ] is True
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "ligand_rows_materialized"
    ] is True
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "canonical_ligand_reconciliation_claimed"
    ] is False
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "gate_status"
    ] == "ready_for_signature_preview"
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "identity_core_preview_row_count"
    ] == 4
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "identity_core_grounded_accession_count"
    ] == 2
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "ligands_materialized"
    ] is True
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "ligand_record_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "next_unlocked_stage"
    ] == "ligand_similarity_signature_preview"
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "ligand_similarity_signatures_materialized"
    ] is False
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "row_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "grounded_accessions"
    ] == ["P00387"]
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "candidate_only_accessions"
    ] == ["Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "policy_mode"
    ] == "mixed_grounded_and_candidate_only_preview"
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "candidate_only_rows_non_governing"
    ] is True
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "split_claims_changed"
    ] is False
    assert (
        dashboard["procurement_status"]["structure_similarity_signature_preview"][
            "row_count"
        ]
        == 4
    )
    assert dashboard["procurement_status"]["structure_similarity_signature_preview"][
        "fold_signature_count"
    ] > 0
    assert dashboard["procurement_status"]["structure_similarity_signature_preview"][
        "ready_for_bundle_preview"
    ] is True
    assert dashboard["procurement_status"]["structure_unit_library_inventory"][
        "record_type_counts"
    ] == {
        "protein": 0,
        "protein_variant": 0,
        "structure_unit": 4,
        "protein_protein": 0,
        "protein_ligand": 0,
    }
    assert (
        dashboard["procurement_status"]["structure_variant_bridge_summary"][
            "overlap_protein_count"
        ]
        == 2
    )
    assert dashboard["procurement_status"]["structure_variant_bridge_summary"][
        "overlap_proteins"
    ] == ["protein:P68871", "protein:P69905"]
    assert dashboard["procurement_status"]["structure_variant_bridge_summary"][
        "per_variant_structure_join_materialized"
    ] is False
    assert (
        dashboard["procurement_status"]["structure_variant_candidate_map"][
            "candidate_count"
        ]
        == 2
    )
    assert dashboard["procurement_status"]["structure_variant_candidate_map"][
        "candidate_statuses"
    ] == ["candidate_only_no_variant_anchor"]
    assert dashboard["procurement_status"]["structure_variant_candidate_map"][
        "direct_structure_backed_variant_join_materialized"
    ] is False
    assert (
        dashboard["procurement_status"]["structure_followup_anchor_candidates"][
            "row_count"
        ]
        == 2
    )
    assert dashboard["procurement_status"]["structure_followup_anchor_candidates"][
        "candidate_accessions"
    ] == ["P04637", "P31749"]
    assert dashboard["procurement_status"]["structure_followup_anchor_candidates"][
        "direct_structure_backed_join_materialized"
    ] is False
    assert (
        dashboard["procurement_status"]["structure_followup_anchor_validation"]["status"]
        == "aligned"
    )
    assert (
        dashboard["procurement_status"]["structure_followup_anchor_validation"][
            "validated_row_count"
        ]
        == 2
    )
    assert dashboard["procurement_status"]["structure_followup_anchor_validation"][
        "issues"
    ] == []
    assert dashboard["procurement_status"]["structure_followup_anchor_validation"][
        "direct_structure_backed_join_certified"
    ] is False
    assert dashboard["procurement_status"]["structure_followup_payload_preview"][
        "target_accession"
    ] == "P31749"
    assert dashboard["procurement_status"]["structure_followup_payload_preview"][
        "payload_accessions"
    ] == ["P31749", "P04637"]
    assert dashboard["procurement_status"]["structure_followup_payload_preview"][
        "payload_row_count"
    ] == 2
    assert dashboard["procurement_status"]["structure_followup_payload_preview"][
        "candidate_only_no_variant_anchor"
    ] is True
    assert dashboard["procurement_status"]["structure_followup_payload_preview"][
        "direct_structure_backed_join_certified"
    ] is False
    assert dashboard["procurement_status"]["structure_followup_payload_preview"][
        "candidate_variant_anchor_count_total"
    ] == 10
    assert dashboard["procurement_status"]["structure_followup_single_accession_preview"][
        "selected_accession"
    ] == "P31749"
    assert dashboard["procurement_status"]["structure_followup_single_accession_preview"][
        "deferred_accession"
    ] == "P04637"
    assert dashboard["procurement_status"]["structure_followup_single_accession_preview"][
        "payload_row_count"
    ] == 1
    assert dashboard["procurement_status"]["structure_followup_single_accession_preview"][
        "single_accession_scope"
    ] is True
    assert dashboard["procurement_status"]["structure_followup_single_accession_preview"][
        "direct_structure_backed_join_certified"
    ] is False
    assert dashboard["procurement_status"][
        "structure_followup_single_accession_validation_preview"
    ]["selected_accession"] == "P31749"
    assert dashboard["procurement_status"][
        "structure_followup_single_accession_validation_preview"
    ]["deferred_accession"] == "P04637"
    assert dashboard["procurement_status"][
        "structure_followup_single_accession_validation_preview"
    ]["anchor_validation_status"] == "aligned"
    assert dashboard["procurement_status"][
        "structure_followup_single_accession_validation_preview"
    ]["direct_structure_backed_join_certified"] is False
    assert dashboard["procurement_status"]["entity_signature_preview"]["row_count"] > 0
    assert dashboard["procurement_status"]["entity_signature_preview"][
        "entity_family_counts"
    ]["protein"] == 11
    assert dashboard["procurement_status"]["entity_signature_preview"][
        "entity_family_counts"
    ]["protein_variant"] > 0
    assert dashboard["procurement_status"]["entity_signature_preview"][
        "entity_family_counts"
    ]["structure_unit"] == 4
    assert dashboard["procurement_status"]["entity_signature_preview"][
        "ligand_groups_materialized"
    ] is False
    assert dashboard["procurement_status"]["entity_split_candidate_preview"][
        "row_count"
    ] > 0
    assert dashboard["procurement_status"]["entity_split_candidate_preview"][
        "default_atomic_unit"
    ] == "entity_signature_row"
    assert dashboard["procurement_status"]["entity_split_candidate_preview"][
        "default_hard_group"
    ] == "protein_spine_group"
    assert dashboard["procurement_status"]["entity_split_candidate_preview"][
        "ready_for_split_engine"
    ] is True
    assert dashboard["procurement_status"]["entity_split_simulation_preview"][
        "candidate_row_count"
    ] > 0
    assert dashboard["procurement_status"]["entity_split_simulation_preview"][
        "assignment_count"
    ] > 0
    assert dashboard["procurement_status"]["entity_split_simulation_preview"][
        "final_split_committed"
    ] is False
    assert dashboard["procurement_status"]["entity_split_recipe_preview"][
        "recipe_id"
    ] == "protein_spine_first_split_recipe_v1"
    assert dashboard["procurement_status"]["entity_split_recipe_preview"][
        "primary_hard_group"
    ] == "protein_spine_group"
    assert dashboard["procurement_status"]["entity_split_recipe_preview"][
        "ready_for_recipe_export"
    ] is True
    assert dashboard["procurement_status"]["entity_split_recipe_preview"][
        "final_split_committed"
    ] is False
    assert dashboard["procurement_status"]["entity_split_assignment_preview"][
        "group_row_count"
    ] == 11
    assert dashboard["procurement_status"]["entity_split_assignment_preview"][
        "assignment_count"
    ] > 0
    assert dashboard["procurement_status"]["entity_split_assignment_preview"][
        "ready_for_fold_export"
    ] is False
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "recipe_id"
    ] == "protein_spine_first_split_recipe_v1"
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "ready_for_split_engine_dry_run"
    ] is True
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "supplemental_non_governing_preview_ready"
    ] is True
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "ligand_governing_split_ready"
    ] is False
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "supplemental_ligand_rows_status"
    ] == "available_non_governing"
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "supplemental_ligand_grounded_accession_count"
    ] == 1
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "supplemental_motif_domain_status"
    ] == "available_non_governing"
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "supplemental_interaction_similarity_status"
    ] == "blocked_candidate_only"
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "cv_folds_materialized"
    ] is False
    assert dashboard["procurement_status"]["split_engine_dry_run_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["split_engine_dry_run_validation"][
        "issue_count"
    ] == 0
    assert dashboard["procurement_status"]["split_engine_dry_run_validation"][
        "final_split_committed"
    ] is False
    assert dashboard["procurement_status"]["split_fold_export_gate_preview"][
        "status"
    ] == "blocked_pending_unlock"
    assert dashboard["procurement_status"]["split_fold_export_gate_preview"][
        "gate_id"
    ] == "cv_fold_export_unlock_gate"
    assert dashboard["procurement_status"]["split_fold_export_gate_preview"][
        "dry_run_validation_status"
    ] == "aligned"
    assert dashboard["procurement_status"]["split_fold_export_gate_preview"][
        "cv_fold_export_unlocked"
    ] is False
    assert dashboard["procurement_status"]["split_fold_export_gate_preview"][
        "ready_for_fold_export"
    ] is False
    assert dashboard["procurement_status"]["split_fold_export_gate_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["split_fold_export_gate_validation"][
        "gate_status"
    ] == "blocked_pending_unlock"
    assert dashboard["procurement_status"]["split_fold_export_gate_validation"][
        "cv_fold_export_unlocked"
    ] is False
    assert dashboard["procurement_status"]["split_fold_export_staging_preview"][
        "status"
    ] == "blocked_report_emitted"
    assert dashboard["procurement_status"]["split_fold_export_staging_preview"][
        "stage_id"
    ] == "run_scoped_fold_export_staging"
    assert dashboard["procurement_status"]["split_fold_export_staging_preview"][
        "run_scoped_only"
    ] is True
    assert dashboard["procurement_status"]["split_fold_export_staging_preview"][
        "cv_fold_export_unlocked"
    ] is False
    assert dashboard["procurement_status"]["split_fold_export_staging_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["split_fold_export_staging_validation"][
        "stage_status"
    ] == "blocked_report_emitted"
    assert dashboard["procurement_status"]["split_fold_export_staging_validation"][
        "run_scoped_only"
    ] is True
    assert dashboard["procurement_status"]["split_post_staging_gate_check_preview"][
        "status"
    ] == "blocked_report_emitted"
    assert dashboard["procurement_status"]["split_post_staging_gate_check_preview"][
        "stage_id"
    ] == "cv_fold_export_unlock_gate_check"
    assert dashboard["procurement_status"]["split_post_staging_gate_check_preview"][
        "run_scoped_only"
    ] is True
    assert dashboard["procurement_status"]["split_post_staging_gate_check_preview"][
        "cv_fold_export_unlocked"
    ] is False
    assert dashboard["procurement_status"]["split_post_staging_gate_check_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["split_post_staging_gate_check_validation"][
        "stage_status"
    ] == "blocked_report_emitted"
    assert dashboard["procurement_status"]["split_post_staging_gate_check_validation"][
        "run_scoped_only"
    ] is True
    assert dashboard["procurement_status"]["split_fold_export_request_preview"][
        "status"
    ] == "blocked_report_emitted"
    assert dashboard["procurement_status"]["split_fold_export_request_preview"][
        "stage_id"
    ] == "run_scoped_fold_export_request"
    assert dashboard["procurement_status"]["split_fold_export_request_preview"][
        "request_only_no_fold_materialization"
    ] is True
    assert dashboard["procurement_status"]["split_fold_export_request_preview"][
        "cv_fold_export_unlocked"
    ] is False
    assert dashboard["procurement_status"]["split_fold_export_request_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["split_fold_export_request_validation"][
        "stage_status"
    ] == "blocked_report_emitted"
    assert dashboard["procurement_status"]["split_fold_export_request_validation"][
        "run_scoped_only"
    ] is True
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "status"
    ] == "complete"
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "execution_status"
    ] == "refresh_required_after_consumed_preview_batch"
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "preview_manifest_status"
    ] == "no_current_valid_batch_requires_refresh"
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "batch_size_limit"
    ] == 1
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "refresh_required"
    ] is True
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "report_only"
    ] is True
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "delete_enabled"
    ] is False
    assert dashboard["procurement_status"][
        "duplicate_cleanup_delete_ready_manifest_preview"
    ]["preview_manifest_status"] == "no_current_valid_batch_requires_refresh"
    assert dashboard["procurement_status"][
        "duplicate_cleanup_delete_ready_manifest_preview"
    ]["action_count"] == 0
    assert dashboard["procurement_status"][
        "duplicate_cleanup_post_delete_verification_contract_preview"
    ]["ready_for_post_delete_checklist"] is False
    assert dashboard["procurement_status"][
        "duplicate_cleanup_first_execution_batch_manifest_preview"
    ]["batch_manifest_status"] == "preview_frozen_not_authorized"
    assert dashboard["procurement_status"][
        "duplicate_cleanup_first_execution_batch_manifest_preview"
    ]["first_action_matches_exemplar"] is True
    assert dashboard["procurement_status"][
        "duplicate_cleanup_first_execution_batch_manifest_preview"
    ]["delete_enabled"] is False
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "row_count"
    ] == 4
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "lanes"
    ] == ["ligand", "structure", "split", "duplicate_cleanup"]
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "first_ligand_accession"
    ] == "P09105"
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "first_ligand_lane_status"
    ] == "blocked_pending_acquisition"
    assert "AlphaFold raw model for P09105" in dashboard["procurement_status"][
        "operator_next_actions_preview"
    ]["first_ligand_best_next_action"]
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "first_ligand_fallback_accession"
    ] == "Q2TAC2"
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "first_ligand_fallback_gate_status"
    ] == "blocked_pending_acquisition"
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "structure_accession"
    ] == "P31749"
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "structure_deferred_accession"
    ] == "P04637"
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "split_run_scoped_only"
    ] is True
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "duplicate_cleanup_batch_size_limit"
    ] == 1
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "duplicate_cleanup_refresh_required"
    ] is True
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "report_only"
    ] is True
    assert dashboard["procurement_status"]["training_set_eligibility_matrix_preview"][
        "row_count"
    ] == 12
    assert dashboard["procurement_status"]["training_set_eligibility_matrix_preview"][
        "grounded_ligand_accessions"
    ] == ["P00387"]
    assert dashboard["procurement_status"]["training_set_eligibility_matrix_preview"][
        "candidate_only_ligand_accessions"
    ] == ["Q9NZD4"]
    assert dashboard["procurement_status"]["training_set_eligibility_matrix_preview"][
        "candidate_only_rows_non_governing"
    ] is True
    assert dashboard["procurement_status"]["missing_data_policy_preview"][
        "policy_category_count"
    ] == 5
    assert dashboard["procurement_status"]["missing_data_policy_preview"][
        "core_rule_count"
    ] == 5
    assert dashboard["procurement_status"]["missing_data_policy_preview"][
        "deletion_default"
    ] is False
    assert "BioGRID guarded procurement first wave" in dashboard["procurement_status"][
        "missing_data_policy_preview"
    ]["top_scrape_targets"]
    assert (
        dashboard["procurement_status"]["operator_accession_coverage_matrix"][
            "protein_accession_count"
        ]
        == 11
    )
    assert dashboard["procurement_status"]["operator_accession_coverage_matrix"][
        "high_priority_accessions"
    ] == ["P04637", "P31749"]
    assert dashboard["procurement_status"]["operator_accession_coverage_matrix"][
        "candidate_only_accessions"
    ] == ["P68871", "P69905"]
    assert dashboard["procurement_status"]["leakage_signature_preview"][
        "candidate_overlap_accessions"
    ] == ["P68871", "P69905"]
    assert dashboard["procurement_status"]["leakage_signature_preview"][
        "structure_followup_accessions"
    ] == ["P04637", "P31749"]
    assert dashboard["procurement_status"]["leakage_group_preview"]["row_count"] == 11
    assert dashboard["procurement_status"]["leakage_group_preview"][
        "candidate_overlap_accessions"
    ] == ["P68871", "P69905"]
    assert dashboard["procurement_status"]["leakage_group_preview"][
        "ready_for_bundle_preview"
    ] is True
    assert dashboard["procurement_status"]["leakage_group_preview"][
        "final_fold_export_committed"
    ] is False
    assert (
        dashboard["procurement_status"]["bundle_manifest_validation"]["status"]
        == "aligned_current_preview_with_verified_assets"
    )
    assert (
        dashboard["procurement_status"]["bundle_manifest_validation"]["contents_doc_exists"]
        is True
    )
    assert (
        dashboard["procurement_status"]["duplicate_cleanup_executor"]["status"]
        == "usable_with_notes"
    )
    assert (
        dashboard["procurement_status"]["duplicate_cleanup_executor"]["action_count"] > 0
    )
