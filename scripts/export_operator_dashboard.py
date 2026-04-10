from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"
DEFAULT_OUTPUT = DEFAULT_RESULTS_DIR / "operator_dashboard.json"
DEFAULT_COVERAGE = DEFAULT_RESULTS_DIR / "source_coverage.json"
DEFAULT_METRICS = DEFAULT_RESULTS_DIR / "metrics_summary.json"
DEFAULT_SUMMARY = DEFAULT_RESULTS_DIR / "summary.json"
DEFAULT_PACKET_DEFICIT = REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
DEFAULT_TIER1_DIRECT = REPO_ROOT / "artifacts" / "status" / "post_tier1_direct_pipeline.json"
DEFAULT_CANONICAL_LATEST = REPO_ROOT / "data" / "canonical" / "LATEST.json"
DEFAULT_SUMMARY_LIBRARY_INVENTORY = (
    REPO_ROOT / "artifacts" / "status" / "summary_library_inventory.json"
)
DEFAULT_PROTEIN_VARIANT_LIBRARY_INVENTORY = (
    REPO_ROOT / "artifacts" / "status" / "protein_variant_summary_library_inventory.json"
)
DEFAULT_STRUCTURE_UNIT_LIBRARY_INVENTORY = (
    REPO_ROOT / "artifacts" / "status" / "structure_unit_summary_library_inventory.json"
)
DEFAULT_PROTEIN_SIMILARITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "protein_similarity_signature_preview.json"
)
DEFAULT_DICTIONARY_PREVIEW = REPO_ROOT / "artifacts" / "status" / "dictionary_preview.json"
DEFAULT_MOTIF_DOMAIN_COMPACT_PREVIEW_FAMILY = (
    REPO_ROOT / "artifacts" / "status" / "motif_domain_compact_preview_family.json"
)
DEFAULT_INTERACTION_SIMILARITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "interaction_similarity_signature_preview.json"
)
DEFAULT_INTERACTION_SIMILARITY_SIGNATURE_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "interaction_similarity_signature_validation.json"
)
DEFAULT_SABIO_RK_SUPPORT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "sabio_rk_support_preview.json"
)
DEFAULT_KINETICS_SUPPORT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "kinetics_enzyme_support_preview.json"
)
DEFAULT_COMPACT_ENRICHMENT_POLICY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "compact_enrichment_policy_preview.json"
)
DEFAULT_SCRAPE_READINESS_REGISTRY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "scrape_readiness_registry_preview.json"
)
DEFAULT_PROCUREMENT_SOURCE_COMPLETION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_source_completion_preview.json"
)
DEFAULT_STRING_INTERACTION_MATERIALIZATION_PLAN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "string_interaction_materialization_plan_preview.json"
)
DEFAULT_STRING_INTERACTION_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "string_interaction_materialization_preview.json"
)
DEFAULT_UNIREF_CLUSTER_MATERIALIZATION_PLAN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "uniref_cluster_materialization_plan_preview.json"
)
DEFAULT_PDB_ENRICHMENT_SCRAPE_REGISTRY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdb_enrichment_scrape_registry_preview.json"
)
DEFAULT_STRUCTURE_ENTRY_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_entry_context_preview.json"
)
DEFAULT_PDB_ENRICHMENT_HARVEST_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdb_enrichment_harvest_preview.json"
)
DEFAULT_PDB_ENRICHMENT_VALIDATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdb_enrichment_validation_preview.json"
)
DEFAULT_LIGAND_CONTEXT_SCRAPE_REGISTRY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_context_scrape_registry_preview.json"
)
DEFAULT_PROTEIN_ORIGIN_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "protein_origin_context_preview.json"
)
DEFAULT_CATALYTIC_SITE_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "catalytic_site_context_preview.json"
)
DEFAULT_TARGETED_PAGE_SCRAPE_REGISTRY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_registry_preview.json"
)
DEFAULT_SEED_PLUS_NEIGHBORS_STRUCTURED_CORPUS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "seed_plus_neighbors_structured_corpus_preview.json"
)
DEFAULT_PDBBIND_EXPANDED_STRUCTURED_CORPUS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdbbind_expanded_structured_corpus_preview.json"
)
DEFAULT_PDBBIND_PROTEIN_COHORT_GRAPH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdbbind_protein_cohort_graph_preview.json"
)
DEFAULT_PAPER_PDB_SPLIT_ASSESSMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "paper_pdb_split_assessment.json"
)
DEFAULT_PDB_PAPER_SPLIT_LEAKAGE_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_leakage_matrix_preview.json"
)
DEFAULT_PDB_PAPER_SPLIT_ACCEPTANCE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_acceptance_gate_preview.json"
)
DEFAULT_PDB_PAPER_SPLIT_SEQUENCE_SIGNATURE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_sequence_signature_audit_preview.json"
)
DEFAULT_PDB_PAPER_SPLIT_MUTATION_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_mutation_audit_preview.json"
)
DEFAULT_PDB_PAPER_SPLIT_STRUCTURE_STATE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_structure_state_audit_preview.json"
)
DEFAULT_PDB_PAPER_DATASET_QUALITY_VERDICT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_dataset_quality_verdict_preview.json"
)
DEFAULT_PDB_PAPER_SPLIT_REMEDIATION_PLAN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_remediation_plan_preview.json"
)
DEFAULT_TRAINING_SET_BASELINE_SIDECAR_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_baseline_sidecar_preview.json"
)
DEFAULT_TRAINING_SET_MULTIMODAL_SIDECAR_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_multimodal_sidecar_preview.json"
)
DEFAULT_TRAINING_PACKET_SUMMARY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_packet_summary_preview.json"
)
DEFAULT_BINDING_MEASUREMENT_REGISTRY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "binding_measurement_registry_preview.json"
)
DEFAULT_BINDING_MEASUREMENT_VALIDATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "binding_measurement_validation_preview.json"
)
DEFAULT_STRUCTURE_BINDING_AFFINITY_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_binding_affinity_context_preview.json"
)
DEFAULT_ACCESSION_BINDING_SUPPORT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "accession_binding_support_preview.json"
)
DEFAULT_STRUCTURE_CHAIN_ORIGIN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_chain_origin_preview.json"
)
DEFAULT_STRUCTURE_LIGAND_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_ligand_context_preview.json"
)
DEFAULT_STRUCTURE_ASSEMBLY_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_assembly_context_preview.json"
)
DEFAULT_STRUCTURE_VALIDATION_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_validation_context_preview.json"
)
DEFAULT_STRUCTURE_PUBLICATION_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_publication_context_preview.json"
)
DEFAULT_STRUCTURE_ORIGIN_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_origin_context_preview.json"
)
DEFAULT_BOUND_LIGAND_CHARACTER_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bound_ligand_character_context_preview.json"
)
DEFAULT_LIGAND_ENVIRONMENT_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_environment_context_preview.json"
)
DEFAULT_INTERACTION_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "interaction_context_preview.json"
)
DEFAULT_INTERACTION_ORIGIN_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "interaction_origin_context_preview.json"
)
DEFAULT_INTERACTION_PARTNER_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "interaction_partner_context_preview.json"
)
DEFAULT_PROTEIN_FUNCTION_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "protein_function_context_preview.json"
)
DEFAULT_PROTEIN_FEATURE_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "protein_feature_context_preview.json"
)
DEFAULT_PROTEIN_REFERENCE_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "protein_reference_context_preview.json"
)
DEFAULT_ENZYME_BEHAVIOR_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "enzyme_behavior_context_preview.json"
)
DEFAULT_PDB_CHAIN_PROJECTION_CONTRACT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "pdb_chain_projection_contract_preview.json"
)
DEFAULT_BINDINGDB_DUMP_INVENTORY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_dump_inventory_preview.json"
)
DEFAULT_BINDINGDB_TARGET_POLYMER_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_target_polymer_context_preview.json"
)
DEFAULT_BINDINGDB_STRUCTURE_BRIDGE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_structure_bridge_preview.json"
)
DEFAULT_BINDINGDB_MEASUREMENT_SUBSET_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_measurement_subset_preview.json"
)
DEFAULT_BINDINGDB_STRUCTURE_MEASUREMENT_PROJECTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_structure_measurement_projection_preview.json"
)
DEFAULT_BINDINGDB_PARTNER_MONOMER_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_partner_monomer_context_preview.json"
)
DEFAULT_BINDINGDB_STRUCTURE_ASSAY_SUMMARY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_structure_assay_summary_preview.json"
)
DEFAULT_BINDINGDB_ACCESSION_ASSAY_PROFILE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_accession_assay_profile_preview.json"
)
DEFAULT_BINDINGDB_ASSAY_CONDITION_PROFILE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_assay_condition_profile_preview.json"
)
DEFAULT_BINDINGDB_STRUCTURE_PARTNER_PROFILE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_structure_partner_profile_preview.json"
)
DEFAULT_BINDINGDB_PARTNER_DESCRIPTOR_RECONCILIATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_partner_descriptor_reconciliation_preview.json"
)
DEFAULT_BINDINGDB_ACCESSION_PARTNER_IDENTITY_PROFILE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_accession_partner_identity_profile_preview.json"
)
DEFAULT_BINDINGDB_STRUCTURE_GROUNDING_CANDIDATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_structure_grounding_candidate_preview.json"
)
DEFAULT_BINDINGDB_FUTURE_STRUCTURE_REGISTRY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_registry_preview.json"
)
DEFAULT_BINDINGDB_FUTURE_STRUCTURE_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_context_preview.json"
)
DEFAULT_BINDINGDB_FUTURE_STRUCTURE_ALIGNMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_alignment_preview.json"
)
DEFAULT_BINDINGDB_FUTURE_STRUCTURE_TRIAGE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_triage_preview.json"
)
DEFAULT_BINDINGDB_OFF_TARGET_ADJACENT_CONTEXT_PROFILE_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "bindingdb_off_target_adjacent_context_profile_preview.json"
)
DEFAULT_BINDINGDB_OFF_TARGET_TARGET_PROFILE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_off_target_target_profile_preview.json"
)
DEFAULT_MOTIF_DOMAIN_SITE_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "motif_domain_site_context_preview.json"
)
DEFAULT_UNIREF_CLUSTER_CONTEXT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "uniref_cluster_context_preview.json"
)
DEFAULT_SEQUENCE_REDUNDANCY_GUARD_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "sequence_redundancy_guard_preview.json"
)
DEFAULT_ARCHIVE_CLEANUP_KEEPER_RULES_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "archive_cleanup_keeper_rules_preview.json"
)
DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_freeze_gate_preview.json"
)
DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_support_readiness_preview.json"
)
DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_identity_pilot_preview.json"
)
DEFAULT_LIGAND_STAGE1_OPERATOR_QUEUE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_stage1_operator_queue_preview.json"
)
DEFAULT_P00387_LIGAND_EXTRACTION_VALIDATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "p00387_ligand_extraction_validation_preview.json"
)
DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "q9nzd4_bridge_validation_preview.json"
)
DEFAULT_LIGAND_STAGE1_VALIDATION_PANEL_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_stage1_validation_panel_preview.json"
)
DEFAULT_LIGAND_IDENTITY_CORE_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_identity_core_materialization_preview.json"
)
DEFAULT_NEXT_REAL_LIGAND_ROW_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "next_real_ligand_row_gate_preview.json"
)
DEFAULT_NEXT_REAL_LIGAND_ROW_DECISION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "next_real_ligand_row_decision_preview.json"
)
DEFAULT_LIGAND_ROW_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
)
DEFAULT_LIGAND_SIMILARITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_similarity_signature_preview.json"
)
DEFAULT_LIGAND_SIMILARITY_SIGNATURE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_similarity_signature_gate_preview.json"
)
DEFAULT_LIGAND_SIMILARITY_SIGNATURE_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "ligand_similarity_signature_validation.json"
)
DEFAULT_STRUCTURE_SIMILARITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_similarity_signature_preview.json"
)
DEFAULT_STRUCTURE_VARIANT_BRIDGE_SUMMARY = (
    REPO_ROOT / "artifacts" / "status" / "structure_variant_bridge_summary.json"
)
DEFAULT_STRUCTURE_VARIANT_CANDIDATE_MAP = (
    REPO_ROOT / "artifacts" / "status" / "structure_variant_candidate_map.json"
)
DEFAULT_STRUCTURE_FOLLOWUP_ANCHOR_CANDIDATES = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_anchor_candidates.json"
)
DEFAULT_STRUCTURE_FOLLOWUP_ANCHOR_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_anchor_validation.json"
)
DEFAULT_STRUCTURE_FOLLOWUP_PAYLOAD_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_payload_preview.json"
)
DEFAULT_STRUCTURE_FOLLOWUP_SINGLE_ACCESSION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_single_accession_preview.json"
)
DEFAULT_STRUCTURE_FOLLOWUP_SINGLE_ACCESSION_VALIDATION_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "structure_followup_single_accession_validation_preview.json"
)
DEFAULT_ENTITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_signature_preview.json"
)
DEFAULT_ENTITY_SPLIT_CANDIDATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_candidate_preview.json"
)
DEFAULT_ENTITY_SPLIT_SIMULATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_simulation_preview.json"
)
DEFAULT_ENTITY_SPLIT_RECIPE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_recipe_preview.json"
)
DEFAULT_ENTITY_SPLIT_ASSIGNMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_assignment_preview.json"
)
DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_input_preview.json"
)
DEFAULT_SPLIT_ENGINE_DRY_RUN_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_dry_run_validation.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_gate_preview.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_GATE_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_gate_validation.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_STAGING_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_staging_preview.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_STAGING_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_staging_validation.json"
)
DEFAULT_SPLIT_POST_STAGING_GATE_CHECK_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_post_staging_gate_check_preview.json"
)
DEFAULT_SPLIT_POST_STAGING_GATE_CHECK_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_post_staging_gate_check_validation.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_REQUEST_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_request_preview.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_REQUEST_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_request_validation.json"
)
DEFAULT_OPERATOR_ACCESSION_COVERAGE_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "summary_library_operator_accession_matrix.json"
)
DEFAULT_LEAKAGE_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "leakage_signature_preview.json"
)
DEFAULT_LEAKAGE_GROUP_PREVIEW = REPO_ROOT / "artifacts" / "status" / "leakage_group_preview.json"
DEFAULT_BUNDLE_MANIFEST_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "live_bundle_manifest_validation.json"
)
DEFAULT_DUPLICATE_EXECUTOR_STATUS = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_executor_status.json"
)
DEFAULT_DUPLICATE_FIRST_EXECUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_first_execution_preview.json"
)
DEFAULT_DUPLICATE_DELETE_READY_MANIFEST_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_delete_ready_manifest_preview.json"
)
DEFAULT_DUPLICATE_POST_DELETE_VERIFICATION_CONTRACT_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "duplicate_cleanup_post_delete_verification_contract_preview.json"
)
DEFAULT_DUPLICATE_FIRST_EXECUTION_BATCH_MANIFEST_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "p86_duplicate_cleanup_first_execution_batch_manifest_preview.json"
)
DEFAULT_OPERATOR_NEXT_ACTIONS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "operator_next_actions_preview.json"
)
DEFAULT_TRAINING_SET_ELIGIBILITY_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_MISSING_DATA_POLICY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "missing_data_policy_preview.json"
)
DEFAULT_TRAINING_SET_READINESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_readiness_preview.json"
)
DEFAULT_FINAL_STRUCTURED_DATASET_BUNDLE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "final_structured_dataset_bundle_preview.json"
)
DEFAULT_RELEASE_GRADE_READINESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_grade_readiness_preview.json"
)
DEFAULT_RELEASE_GRADE_CLOSURE_QUEUE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_grade_closure_queue_preview.json"
)
DEFAULT_RELEASE_RUNTIME_MATURITY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_runtime_maturity_preview.json"
)
DEFAULT_RELEASE_SOURCE_COVERAGE_DEPTH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_source_coverage_depth_preview.json"
)
DEFAULT_RELEASE_PROVENANCE_DEPTH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_provenance_depth_preview.json"
)
DEFAULT_RELEASE_GRADE_RUNBOOK_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_grade_runbook_preview.json"
)
DEFAULT_RELEASE_ACCESSION_CLOSURE_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_accession_closure_matrix_preview.json"
)
DEFAULT_RELEASE_ACCESSION_ACTION_QUEUE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_accession_action_queue_preview.json"
)
DEFAULT_RELEASE_PROMOTION_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_promotion_gate_preview.json"
)
DEFAULT_RELEASE_SOURCE_FIX_FOLLOWUP_BATCH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_source_fix_followup_batch_preview.json"
)
DEFAULT_RELEASE_CANDIDATE_PROMOTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_candidate_promotion_preview.json"
)
DEFAULT_RELEASE_RUNTIME_QUALIFICATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_runtime_qualification_preview.json"
)
DEFAULT_RELEASE_GOVERNING_SUFFICIENCY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_governing_sufficiency_preview.json"
)
DEFAULT_RELEASE_ACCESSION_EVIDENCE_PACK_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_accession_evidence_pack_preview.json"
)
DEFAULT_RELEASE_REPORTING_COMPLETENESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_reporting_completeness_preview.json"
)
DEFAULT_RELEASE_BLOCKER_RESOLUTION_BOARD_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "release_blocker_resolution_board_preview.json"
)
DEFAULT_PROCUREMENT_EXTERNAL_DRIVE_MOUNT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_external_drive_mount_preview.json"
)
DEFAULT_PROCUREMENT_EXPANSION_WAVE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_expansion_wave_preview.json"
)
DEFAULT_PROCUREMENT_EXPANSION_STORAGE_BUDGET_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_expansion_storage_budget_preview.json"
)
DEFAULT_MISSING_SCRAPE_FAMILY_CONTRACTS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "missing_scrape_family_contracts_preview.json"
)
DEFAULT_COHORT_COMPILER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "cohort_compiler_preview.json"
)
DEFAULT_BALANCE_DIAGNOSTICS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "balance_diagnostics_preview.json"
)
DEFAULT_PACKAGE_READINESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
)
DEFAULT_TRAINING_SET_BUILDER_SESSION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_builder_session_preview.json"
)
DEFAULT_TRAINING_SET_BUILDER_RUNBOOK_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_builder_runbook_preview.json"
)
DEFAULT_EXTERNAL_DATASET_INTAKE_CONTRACT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_intake_contract_preview.json"
)
DEFAULT_EXTERNAL_DATASET_ASSESSMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_assessment_preview.json"
)
DEFAULT_SAMPLE_EXTERNAL_DATASET_ASSESSMENT_BUNDLE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "sample_external_dataset_assessment_bundle_preview.json"
)
DEFAULT_EXTERNAL_DATASET_LEAKAGE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_leakage_audit_preview.json"
)
DEFAULT_EXTERNAL_DATASET_MODALITY_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_modality_audit_preview.json"
)
DEFAULT_EXTERNAL_DATASET_BINDING_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_binding_audit_preview.json"
)
DEFAULT_EXTERNAL_DATASET_STRUCTURE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_structure_audit_preview.json"
)
DEFAULT_EXTERNAL_DATASET_PROVENANCE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_provenance_audit_preview.json"
)
DEFAULT_SCRAPE_GAP_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "scrape_gap_matrix_preview.json"
)
DEFAULT_OVERNIGHT_QUEUE_BACKLOG_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "overnight_queue_backlog_preview.json"
)
DEFAULT_OVERNIGHT_EXECUTION_CONTRACT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "overnight_execution_contract_preview.json"
)
DEFAULT_OVERNIGHT_QUEUE_REPAIR_STATUS = (
    REPO_ROOT / "artifacts" / "status" / "overnight_queue_repair_status.json"
)
DEFAULT_OVERNIGHT_IDLE_STATUS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "overnight_idle_status_preview.json"
)
DEFAULT_OVERNIGHT_WAVE_ADVANCE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "overnight_wave_advance_preview.json"
)
DEFAULT_OVERNIGHT_PENDING_RECONCILIATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "overnight_pending_reconciliation_preview.json"
)
DEFAULT_OVERNIGHT_WORKER_LAUNCH_GAP_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "overnight_worker_launch_gap_preview.json"
)
DEFAULT_BINDING_MEASUREMENT_SUSPECT_ROWS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "binding_measurement_suspect_rows_preview.json"
)
DEFAULT_CROSS_SOURCE_DUPLICATE_MEASUREMENT_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "cross_source_duplicate_measurement_audit_preview.json"
)
DEFAULT_TRAINING_SET_CANDIDATE_PACKAGE_MANIFEST_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_candidate_package_manifest_preview.json"
)
DEFAULT_INTERACTION_STRING_MERGE_IMPACT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "interaction_string_merge_impact_preview.json"
)
DEFAULT_PROCUREMENT_PROCESS_DIAGNOSTICS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_process_diagnostics_preview.json"
)
DEFAULT_PROCUREMENT_SUPERVISOR_FRESHNESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_supervisor_freshness_preview.json"
)
DEFAULT_PROCUREMENT_TAIL_SIGNAL_RECONCILIATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_signal_reconciliation_preview.json"
)
DEFAULT_PROCUREMENT_TAIL_GROWTH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_growth_preview.json"
)
DEFAULT_PROCUREMENT_HEADROOM_GUARD_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_headroom_guard_preview.json"
)
DEFAULT_PROCUREMENT_TAIL_SPACE_DRIFT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_space_drift_preview.json"
)
DEFAULT_PROCUREMENT_TAIL_SOURCE_PRESSURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_source_pressure_preview.json"
)
DEFAULT_PROCUREMENT_TAIL_LOG_PROGRESS_REGISTRY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_log_progress_registry_preview.json"
)
DEFAULT_PROCUREMENT_TAIL_COMPLETION_MARGIN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_completion_margin_preview.json"
)
DEFAULT_PROCUREMENT_SPACE_RECOVERY_TARGET_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_target_preview.json"
)
DEFAULT_PROCUREMENT_SPACE_RECOVERY_CANDIDATES_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_candidates_preview.json"
)
DEFAULT_PROCUREMENT_SPACE_RECOVERY_EXECUTION_BATCH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_execution_batch_preview.json"
)
DEFAULT_PROCUREMENT_SPACE_RECOVERY_SAFETY_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_safety_register_preview.json"
)
DEFAULT_PROCUREMENT_TAIL_FILL_RISK_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_fill_risk_preview.json"
)
DEFAULT_PROCUREMENT_SPACE_RECOVERY_TRIGGER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_trigger_preview.json"
)
DEFAULT_PROCUREMENT_SPACE_RECOVERY_GAP_DRIFT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_gap_drift_preview.json"
)
DEFAULT_PROCUREMENT_SPACE_RECOVERY_COVERAGE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_coverage_preview.json"
)
DEFAULT_PROCUREMENT_RECOVERY_INTERVENTION_PRIORITY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_recovery_intervention_priority_preview.json"
)
DEFAULT_PROCUREMENT_RECOVERY_ESCALATION_LANE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_recovery_escalation_lane_preview.json"
)
DEFAULT_PROCUREMENT_SPACE_RECOVERY_CONCENTRATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_concentration_preview.json"
)
DEFAULT_PROCUREMENT_RECOVERY_SHORTFALL_BRIDGE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_recovery_shortfall_bridge_preview.json"
)
DEFAULT_PROCUREMENT_RECOVERY_LANE_FRAGILITY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_recovery_lane_fragility_preview.json"
)
DEFAULT_PROCUREMENT_BROADER_SEARCH_TRIGGER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_broader_search_trigger_preview.json"
)
DEFAULT_SPLIT_SIMULATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_simulation_preview.json"
)
DEFAULT_TRAINING_SET_REMEDIATION_PLAN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_remediation_plan_preview.json"
)
DEFAULT_COHORT_INCLUSION_RATIONALE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "cohort_inclusion_rationale_preview.json"
)
DEFAULT_TRAINING_SET_UNBLOCK_PLAN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unblock_plan_preview.json"
)
DEFAULT_TRAINING_SET_GATING_EVIDENCE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_gating_evidence_preview.json"
)
DEFAULT_TRAINING_SET_ACTION_QUEUE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_action_queue_preview.json"
)
DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_blocker_burndown_preview.json"
)
DEFAULT_TRAINING_SET_MODALITY_GAP_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_modality_gap_register_preview.json"
)
DEFAULT_TRAINING_SET_PACKAGE_BLOCKER_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_package_blocker_matrix_preview.json"
)
DEFAULT_TRAINING_SET_GATE_LADDER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_gate_ladder_preview.json"
)
DEFAULT_TRAINING_SET_UNLOCK_ROUTE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unlock_route_preview.json"
)
DEFAULT_TRAINING_SET_TRANSITION_CONTRACT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_transition_contract_preview.json"
)
DEFAULT_TRAINING_SET_SOURCE_FIX_BATCH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_source_fix_batch_preview.json"
)
DEFAULT_TRAINING_SET_PACKAGE_TRANSITION_BATCH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_package_transition_batch_preview.json"
)
DEFAULT_TRAINING_SET_PACKAGE_EXECUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_package_execution_preview.json"
)
DEFAULT_TRAINING_SET_PREVIEW_HOLD_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_preview_hold_register_preview.json"
)
DEFAULT_TRAINING_SET_PREVIEW_HOLD_EXIT_CRITERIA_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_preview_hold_exit_criteria_preview.json"
)
DEFAULT_TRAINING_SET_PREVIEW_HOLD_CLEARANCE_BATCH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_set_preview_hold_clearance_batch_preview.json"
)
DEFAULT_EXTERNAL_DATASET_FLAW_TAXONOMY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_flaw_taxonomy_preview.json"
)
DEFAULT_EXTERNAL_DATASET_RISK_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_risk_register_preview.json"
)
DEFAULT_EXTERNAL_DATASET_CONFLICT_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_conflict_register_preview.json"
)
DEFAULT_EXTERNAL_DATASET_ISSUE_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_issue_matrix_preview.json"
)
DEFAULT_EXTERNAL_DATASET_MANIFEST_LINT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_manifest_lint_preview.json"
)
DEFAULT_EXTERNAL_DATASET_ACCEPTANCE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json"
)
DEFAULT_EXTERNAL_DATASET_ADMISSION_DECISION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_admission_decision_preview.json"
)
DEFAULT_EXTERNAL_DATASET_CLEARANCE_DELTA_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_clearance_delta_preview.json"
)
DEFAULT_EXTERNAL_DATASET_ACCEPTANCE_PATH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_path_preview.json"
)
DEFAULT_EXTERNAL_DATASET_REMEDIATION_READINESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_remediation_readiness_preview.json"
)
DEFAULT_EXTERNAL_DATASET_CAVEAT_EXECUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_caveat_execution_preview.json"
)
DEFAULT_EXTERNAL_DATASET_BLOCKED_ACQUISITION_BATCH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_blocked_acquisition_batch_preview.json"
)
DEFAULT_EXTERNAL_DATASET_ACQUISITION_UNBLOCK_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acquisition_unblock_preview.json"
)
DEFAULT_EXTERNAL_DATASET_ADVISORY_FOLLOWUP_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_advisory_followup_register_preview.json"
)
DEFAULT_EXTERNAL_DATASET_CAVEAT_EXIT_CRITERIA_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_caveat_exit_criteria_preview.json"
)
DEFAULT_EXTERNAL_DATASET_CAVEAT_REVIEW_BATCH_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_caveat_review_batch_preview.json"
)
DEFAULT_EXTERNAL_DATASET_RESOLUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)
DEFAULT_EXTERNAL_DATASET_RESOLUTION_DIFF_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_diff_preview.json"
)
DEFAULT_EXTERNAL_DATASET_REMEDIATION_TEMPLATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_remediation_template_preview.json"
)
DEFAULT_EXTERNAL_DATASET_FIXTURE_CATALOG_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_fixture_catalog_preview.json"
)
DEFAULT_EXTERNAL_DATASET_REMEDIATION_QUEUE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_remediation_queue_preview.json"
)
DEFAULT_DOWNLOAD_LOCATION_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "download_location_audit_preview.json"
)
DEFAULT_PROCUREMENT_STALE_PART_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_stale_part_audit_preview.json"
)
DEFAULT_TRAINING_PACKET_COMPLETENESS_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_packet_completeness_matrix_preview.json"
)
DEFAULT_TRAINING_SPLIT_ALIGNMENT_RECHECK_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_split_alignment_recheck_preview.json"
)
DEFAULT_TRAINING_PACKET_MATERIALIZATION_QUEUE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "training_packet_materialization_queue_preview.json"
)
DEFAULT_POST_TAIL_UNLOCK_DRY_RUN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "post_tail_unlock_dry_run_preview.json"
)
DEFAULT_SCRAPE_EXECUTION_WAVE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "scrape_execution_wave_preview.json"
)
DEFAULT_SCRAPE_BACKLOG_REMAINING_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "scrape_backlog_remaining_preview.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _ensure_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"missing {label}: {path}")


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return _read_json(path)
    except json.JSONDecodeError:
        return None


def _ensure_script_export(
    path: Path,
    script_name: str,
    refresh: bool = False,
) -> dict[str, Any] | None:
    if path.exists() and not refresh:
        return _read_json_if_exists(path)

    script_path = REPO_ROOT / "scripts" / script_name
    if not script_path.exists():
        return None

    try:
        subprocess.run(
            [sys.executable, str(script_path)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError:
        return _read_json_if_exists(path)
    if not path.exists():
        return None
    return _read_json_if_exists(path)


def _ensure_ligand_support_readiness_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_ligand_support_readiness_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_ligand_support_readiness_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = module.build_ligand_support_readiness_preview(
        module._read_json(module.DEFAULT_SUPPORT_SUBSLICE),
        module._read_json(module.DEFAULT_PACKET_DEFICIT_DASHBOARD),
        module._read_json(module.DEFAULT_LOCAL_LIGAND_SOURCE_MAP),
        module._read_json(module.DEFAULT_LOCAL_LIGAND_GAP_PROBE),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_procurement_tail_freeze_gate_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_procurement_tail_freeze_gate_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_procurement_tail_freeze_gate_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = module.build_procurement_tail_freeze_gate_preview(
        module._read_json(module.DEFAULT_BROAD_MIRROR_PROGRESS),
        module._read_json(module.DEFAULT_REMAINING_GAPS),
        module._read_json(module.DEFAULT_REMAINING_TRANSFER_STATUS),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_next_real_ligand_row_decision_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_next_real_ligand_row_decision_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_next_real_ligand_row_decision_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = module.build_next_real_ligand_row_decision_preview(
        module._read_json(module.DEFAULT_GATE_PREVIEW),
        module._read_json(module.DEFAULT_LOCAL_SOURCE_MAP),
        module._read_json(module.DEFAULT_LOCAL_GAP_PROBE),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_ligand_identity_pilot_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_ligand_identity_pilot_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_ligand_identity_pilot_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = module.build_ligand_identity_pilot_preview(
        module._read_json(module.DEFAULT_PILOT_ORDER),
        module._read_json(module.DEFAULT_LIGAND_SUPPORT),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_ligand_stage1_operator_queue_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_ligand_stage1_operator_queue_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_ligand_stage1_operator_queue_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ligand_identity = _ensure_ligand_identity_pilot_preview(DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW)
    ligand_support = _ensure_ligand_support_readiness_preview(
        DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW
    )
    if ligand_identity is None or ligand_support is None:
        return None

    payload = module.build_ligand_stage1_operator_queue_preview(
        ligand_identity,
        ligand_support,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_p00387_ligand_extraction_validation_preview(
    path: Path,
) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_p00387_ligand_extraction_validation_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_p00387_ligand_extraction_validation_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = module.build_p00387_ligand_extraction_validation_preview(
        module._read_json(module.DEFAULT_CONTRACT),
        module._read_json(module.DEFAULT_PAYLOAD),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_q9nzd4_bridge_validation_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_q9nzd4_bridge_validation_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_q9nzd4_bridge_validation_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = module.build_q9nzd4_bridge_validation_preview(
        module._read_json(module.DEFAULT_BRIDGE_PAYLOAD),
        module._read_json(module.DEFAULT_EXECUTION_SLICE),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_ligand_stage1_validation_panel_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_ligand_stage1_validation_panel_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_ligand_stage1_validation_panel_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = module.build_ligand_stage1_validation_panel_preview(
        _ensure_p00387_ligand_extraction_validation_preview(
            DEFAULT_P00387_LIGAND_EXTRACTION_VALIDATION_PREVIEW
        ),
        _ensure_q9nzd4_bridge_validation_preview(DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_ligand_identity_core_materialization_preview(
    path: Path,
) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_ligand_identity_core_materialization_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_ligand_identity_core_materialization_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ligand_identity_pilot = _ensure_ligand_identity_pilot_preview(
        DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW
    )
    ligand_support = _ensure_ligand_support_readiness_preview(
        DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW
    )
    p00387_validation = _ensure_p00387_ligand_extraction_validation_preview(
        DEFAULT_P00387_LIGAND_EXTRACTION_VALIDATION_PREVIEW
    )
    q9nzd4_validation = _ensure_q9nzd4_bridge_validation_preview(
        DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW
    )
    if (
        ligand_identity_pilot is None
        or ligand_support is None
        or p00387_validation is None
        or q9nzd4_validation is None
    ):
        return None

    payload = module.build_ligand_identity_core_materialization_preview(
        ligand_identity_pilot,
        ligand_support,
        p00387_validation,
        q9nzd4_validation,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_ligand_row_materialization_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_ligand_row_materialization_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_ligand_row_materialization_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = module.build_ligand_row_materialization_preview(
        module._read_json(module.DEFAULT_P00387_PAYLOAD),
        module._read_json(module.DEFAULT_P00387_VALIDATION),
        module._read_json(module.DEFAULT_Q9NZD4_VALIDATION),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_ligand_similarity_signature_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_ligand_similarity_signature_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_ligand_similarity_signature_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = module.build_ligand_similarity_signature_preview(
        module._read_json(module.DEFAULT_LIGAND_ROW_PREVIEW)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_ligand_similarity_signature_gate_preview(
    path: Path,
) -> dict[str, Any] | None:
    module_path = REPO_ROOT / "scripts" / "export_ligand_similarity_signature_gate_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_ligand_similarity_signature_gate_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    bundle_manifest = _read_json_if_exists(
        REPO_ROOT / "artifacts" / "status" / "lightweight_bundle_manifest.json"
    )
    ligand_identity_core_preview = _ensure_ligand_identity_core_materialization_preview(
        DEFAULT_LIGAND_IDENTITY_CORE_MATERIALIZATION_PREVIEW
    )
    ligand_row_preview = _ensure_ligand_row_materialization_preview(
        DEFAULT_LIGAND_ROW_MATERIALIZATION_PREVIEW
    )
    if (
        bundle_manifest is None
        or ligand_identity_core_preview is None
        or ligand_row_preview is None
    ):
        return None

    payload = module.build_ligand_similarity_signature_gate_preview(
        bundle_manifest,
        ligand_identity_core_preview,
        ligand_row_preview,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_ligand_similarity_signature_validation(
    path: Path,
) -> dict[str, Any] | None:
    module_path = REPO_ROOT / "scripts" / "validate_ligand_similarity_signature_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_validate_ligand_similarity_signature_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    preview = _ensure_ligand_similarity_signature_preview(
        module.DEFAULT_LIGAND_SIMILARITY_SIGNATURE_PREVIEW
    )
    gate = _ensure_ligand_similarity_signature_gate_preview(
        module.DEFAULT_LIGAND_SIMILARITY_SIGNATURE_GATE_PREVIEW
    )
    if preview is None or gate is None:
        return None

    payload = module.build_ligand_similarity_signature_validation(preview, gate)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_structure_followup_single_accession_preview(
    path: Path,
) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_structure_followup_single_accession_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_structure_followup_single_accession_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = module.build_structure_followup_single_accession_preview(
        module._read_json(module.DEFAULT_PROMOTION_PLAN),
        module._read_json(module.DEFAULT_PAYLOAD_PREVIEW),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_structure_followup_single_accession_validation_preview(
    path: Path,
) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = (
        REPO_ROOT / "scripts" / "export_structure_followup_single_accession_validation_preview.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_export_structure_followup_single_accession_validation_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    single_accession_preview = _ensure_structure_followup_single_accession_preview(
        DEFAULT_STRUCTURE_FOLLOWUP_SINGLE_ACCESSION_PREVIEW
    )
    anchor_validation = _read_json_if_exists(DEFAULT_STRUCTURE_FOLLOWUP_ANCHOR_VALIDATION)
    if single_accession_preview is None or anchor_validation is None:
        return None

    payload = module.build_structure_followup_single_accession_validation_preview(
        single_accession_preview,
        anchor_validation,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_duplicate_cleanup_first_execution_preview(
    path: Path,
) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_duplicate_cleanup_first_execution_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_duplicate_cleanup_first_execution_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = module.build_duplicate_cleanup_first_execution_preview(
        module._read_json(module.DEFAULT_DELETE_READY_MANIFEST),
        module._read_json(module.DEFAULT_EXECUTOR_STATUS),
        legacy_checklist=module._read_json(module.DEFAULT_CHECKLIST),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_operator_next_actions_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        payload = _read_json(path)
        prioritized_actions = payload.get("prioritized_actions", [])
        ligand_detail = (
            prioritized_actions[0].get("detail", {})
            if prioritized_actions and isinstance(prioritized_actions[0], dict)
            else {}
        )
        if (
            prioritized_actions
            and all(isinstance(row, dict) and "detail" in row for row in prioritized_actions)
            and "selected_accession_gate_status" in ligand_detail
        ):
            return payload

    module_path = REPO_ROOT / "scripts" / "export_operator_next_actions_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_operator_next_actions_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ligand_decision = _ensure_next_real_ligand_row_decision_preview(
        DEFAULT_NEXT_REAL_LIGAND_ROW_DECISION_PREVIEW
    )
    structure_validation = _ensure_structure_followup_single_accession_validation_preview(
        DEFAULT_STRUCTURE_FOLLOWUP_SINGLE_ACCESSION_VALIDATION_PREVIEW
    )
    split_request = _read_json_if_exists(DEFAULT_SPLIT_FOLD_EXPORT_REQUEST_PREVIEW)
    duplicate_preview = _ensure_duplicate_cleanup_first_execution_preview(
        DEFAULT_DUPLICATE_FIRST_EXECUTION_PREVIEW
    )
    duplicate_delete_ready_manifest = _read_json_if_exists(
        REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_delete_ready_manifest_preview.json"
    )
    if (
        ligand_decision is None
        or structure_validation is None
        or split_request is None
        or duplicate_preview is None
        or duplicate_delete_ready_manifest is None
    ):
        return None

    payload = module.build_operator_next_actions_preview(
        ligand_decision,
        structure_validation,
        split_request,
        duplicate_preview,
        duplicate_delete_ready_manifest,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_scrape_readiness_registry_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_scrape_readiness_registry_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_scrape_readiness_registry_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.build_scrape_readiness_registry_preview(
        module._read_json(module.DEFAULT_MISSING_DATA_POLICY),
        module._read_json(module.DEFAULT_COMPACT_ENRICHMENT_POLICY),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_archive_cleanup_keeper_rules_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_archive_cleanup_keeper_rules_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_archive_cleanup_keeper_rules_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.build_archive_cleanup_keeper_rules_preview(
        module._read_json(module.DEFAULT_DUPLICATE_CLEANUP_STATUS)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_training_set_eligibility_matrix_preview(
    path: Path,
) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_training_set_eligibility_matrix_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_training_set_eligibility_matrix_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.build_training_set_eligibility_matrix_preview(
        module._read_json(module.DEFAULT_PACKET_DEFICIT),
        module._read_json(module.DEFAULT_ACCESSION_MATRIX),
        module._read_json(module.DEFAULT_LIGAND_ROW_PREVIEW),
        module._read_json(module.DEFAULT_LIGAND_SUPPORT_READINESS),
        module._read_json(module.DEFAULT_MOTIF_DOMAIN_PREVIEW),
        module._read_json(module.DEFAULT_INTERACTION_SIMILARITY_PREVIEW),
        module._read_json(module.DEFAULT_KINETICS_SUPPORT_PREVIEW),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_compact_enrichment_policy_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_compact_enrichment_policy_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_compact_enrichment_policy_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.build_compact_enrichment_policy_preview(
        module._read_json(module.DEFAULT_INTERACTION_SIMILARITY_PREVIEW),
        module._read_json(module.DEFAULT_MOTIF_DOMAIN_PREVIEW),
        module._read_json(module.DEFAULT_KINETICS_SUPPORT_PREVIEW),
        module._read_json(module.DEFAULT_BUNDLE_MANIFEST),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _ensure_missing_data_policy_preview(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)

    module_path = REPO_ROOT / "scripts" / "export_missing_data_policy_preview.py"
    spec = importlib.util.spec_from_file_location(
        "_export_missing_data_policy_preview",
        module_path,
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.build_missing_data_policy_preview(
        module._read_json(module.DEFAULT_ELIGIBILITY_MATRIX),
        module._read_json(module.DEFAULT_SCOPE_AUDIT),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    module.DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    module.DEFAULT_OUTPUT_MD.write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        values.append(item)
    return values


def _compact_benchmark_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": summary["task_id"],
        "status": summary["status"],
        "executed": summary["executed"],
        "execution_scope": summary["execution_scope"],
        "runtime": summary["runtime"],
        "blocker_categories": summary["blocker_categories"],
        "ready_for_next_wave": summary["ready_for_next_wave"],
        "artifacts": summary["artifacts"],
    }


def _compact_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": metrics["task_id"],
        "status": metrics["status"],
        "benchmark_task": metrics["benchmark_task"],
        "run": metrics["run"],
        "runtime": metrics["runtime"],
        "loss_summary": metrics["loss_summary"],
        "checkpoint_summary": metrics["checkpoint_summary"],
        "log_summary": metrics["log_summary"],
        "truth_boundary": metrics["truth_boundary"],
    }


def _compact_coverage(coverage: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": coverage["task_id"],
        "status": coverage["status"],
        "manifest_id": coverage["frozen_cohort"]["manifest_id"],
        "frozen_cohort": coverage["frozen_cohort"],
        "summary": coverage["summary"],
        "semantics": coverage["semantics"],
        "run_context": coverage["run_context"],
        "lane_index": coverage["lane_index"],
        "blockers": coverage["blockers"],
    }


def _compact_packet_latest(packet_deficit: dict[str, Any]) -> dict[str, Any]:
    summary = packet_deficit["summary"]
    return {
        "status": packet_deficit["status"],
        "generated_at": packet_deficit["generated_at"],
        "packet_count": summary["packet_count"],
        "packet_status_counts": summary["packet_status_counts"],
        "packet_deficit_count": summary["packet_deficit_count"],
        "total_missing_modality_count": summary["total_missing_modality_count"],
        "modality_deficit_counts": summary["modality_deficit_counts"],
        "highest_leverage_source_fix_refs": [
            candidate["source_ref"]
            for candidate in summary.get("highest_leverage_source_fixes", [])
        ],
        "latest_summary_path": packet_deficit["inputs"].get("latest_summary_path"),
    }


def _compact_tier1_direct_pipeline(tier1_pipeline: dict[str, Any]) -> dict[str, Any]:
    scope_root = REPO_ROOT / Path(tier1_pipeline["scope_root"])
    scoped_materialization_path = scope_root / "selected_cohort_materialization.json"
    scoped_materialization = _read_json_if_exists(scoped_materialization_path)
    regression_gate = tier1_pipeline.get("packet_regression_gate")

    scoped_regression: dict[str, Any] | None = None
    if scoped_materialization is not None:
        scoped_summary = scoped_materialization["summary"]
        scoped_materialization_state = scoped_materialization["materialization"]
        scoped_regression = {
            "path": str(scoped_materialization_path).replace("\\", "/"),
            "status": scoped_materialization["status"],
            "packet_count": scoped_summary["packet_count"],
            "packet_status_counts": scoped_summary["packet_status_counts"],
            "missing_modality_counts": scoped_summary["missing_modality_counts"],
            "status_mismatch_count": scoped_summary["status_mismatch_count"],
            "latest_promotion_state": scoped_materialization_state["latest_promotion_state"],
            "release_grade_ready": scoped_materialization_state["release_grade_ready"],
        }

    return {
        "status": tier1_pipeline["status"],
        "generated_at": tier1_pipeline["generated_at"],
        "promotion_status": tier1_pipeline["promotion_status"],
        "promotion_id": tier1_pipeline["promotion_id"],
        "promotion_path": tier1_pipeline["promotion_path"],
        "run_id": tier1_pipeline["run_id"],
        "scope_root": tier1_pipeline["scope_root"],
        "step_count": tier1_pipeline["step_count"],
        "direct_promotion_succeeded": (
            tier1_pipeline["status"] == "passed"
            and tier1_pipeline["promotion_status"] == "promoted"
        ),
        "packet_regression_gate": (
            {
                "status": regression_gate["status"],
                "baseline_path": regression_gate["baseline_path"],
                "candidate_path": regression_gate["candidate_path"],
                "baseline_metrics": regression_gate["baseline_metrics"],
                "candidate_metrics": regression_gate["candidate_metrics"],
                "regressions": regression_gate["regressions"],
                "improvements": regression_gate["improvements"],
                "notes": regression_gate["notes"],
            }
            if regression_gate is not None
            else None
        ),
        "scoped_post_tier1_regression": scoped_regression,
        "race_condition_caveat": (
            "older scoped Tier 1 run artifacts, especially under "
            "runs/tier1_direct_validation/20260323T175411Z, may still reflect the "
            "pre-bridge-fallback 3 complete / 9 partial state; operator and "
            "procurement reporting should follow the current scope_root and packet "
            "regression gate instead"
        ),
    }


def _compact_canonical_latest(canonical_latest: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": canonical_latest["status"],
        "reason": canonical_latest["reason"],
        "run_id": canonical_latest["run_id"],
        "created_at": canonical_latest["created_at"],
        "record_counts": canonical_latest["record_counts"],
        "unresolved_counts": canonical_latest["unresolved_counts"],
    }


def _compact_summary_library_inventory(summary_library_inventory: dict[str, Any]) -> dict[str, Any]:
    return {
        "library_id": summary_library_inventory["library_id"],
        "schema_version": summary_library_inventory["schema_version"],
        "source_manifest_id": summary_library_inventory["source_manifest_id"],
        "record_count": summary_library_inventory["record_count"],
        "record_type_counts": summary_library_inventory["record_type_counts"],
        "join_status_counts": summary_library_inventory["join_status_counts"],
        "storage_tier_counts": summary_library_inventory["storage_tier_counts"],
    }


def _compact_bundle_manifest_validation(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload["overall_assessment"]["status"],
        "operator_implication": payload["overall_assessment"]["operator_implication"],
        "needs_attention": payload["validation_gates"]["needs_attention"],
        "contents_doc_exists": payload["docs"]["contents_doc_exists"],
        "schema_doc_exists": payload["docs"]["schema_doc_exists"],
    }


def _compact_structure_variant_bridge_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload["status"],
        "variant_record_count": payload["variant_record_count"],
        "structure_unit_record_count": payload["structure_unit_record_count"],
        "overlap_protein_count": payload["overlap_protein_count"],
        "overlap_proteins": [row["protein_ref"] for row in payload.get("overlap_rows", [])],
        "per_variant_structure_join_materialized": payload["truth_boundary"][
            "per_variant_structure_join_materialized"
        ],
    }


def _compact_structure_variant_candidate_map(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload["status"],
        "candidate_count": payload["candidate_count"],
        "candidate_statuses": sorted(
            {row["candidate_status"] for row in payload.get("candidate_rows", [])}
        ),
        "candidate_proteins": [row["protein_ref"] for row in payload.get("candidate_rows", [])],
        "direct_structure_backed_variant_join_materialized": payload["truth_boundary"][
            "direct_structure_backed_variant_join_materialized"
        ],
    }


def _compact_operator_accession_coverage_matrix(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "protein_accession_count": summary["protein_accession_count"],
        "variant_bearing_accession_count": summary["variant_bearing_accession_count"],
        "structure_bearing_accession_count": summary["structure_bearing_accession_count"],
        "high_priority_accessions": summary["high_priority_accessions"],
        "candidate_only_accessions": summary["candidate_only_accessions"],
    }


def _compact_structure_followup_anchor_candidates(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "candidate_accessions": summary["candidate_accessions"],
        "missing_evidence_accessions": summary["missing_evidence_accessions"],
        "candidate_variant_anchor_count": summary["candidate_variant_anchor_count"],
        "direct_structure_backed_join_materialized": payload["truth_boundary"][
            "direct_structure_backed_join_materialized"
        ],
    }


def _compact_structure_followup_anchor_validation(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload["validation"]
    return {
        "status": payload["status"],
        "validated_row_count": validation["validated_row_count"],
        "candidate_variant_anchor_count": validation["candidate_variant_anchor_count"],
        "issues": validation["issues"],
        "warnings": validation["warnings"],
        "direct_structure_backed_join_certified": payload["truth_boundary"][
            "direct_structure_backed_join_certified"
        ],
    }


def _compact_structure_followup_payload_preview(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload["validation_context"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "target_accession": payload["target_accession"],
        "payload_accessions": payload["payload_accessions"],
        "payload_row_count": payload["payload_row_count"],
        "first_variant_ref": payload["payload_rows"][0]["variant_ref"],
        "first_structure_ref": (
            f"{payload['payload_rows'][0]['structure_id']}:{payload['payload_rows'][0]['chain_id']}"
        ),
        "first_coverage": payload["payload_rows"][0]["coverage"],
        "anchor_validation_status": validation["anchor_validation_status"],
        "candidate_variant_anchor_count_total": validation["candidate_variant_anchor_count_total"],
        "candidate_only_no_variant_anchor": truth["candidate_only_no_variant_anchor"],
        "direct_structure_backed_join_certified": truth["direct_structure_backed_join_certified"],
        "ready_for_preview_validation": truth["ready_for_preview_validation"],
    }


def _compact_structure_followup_single_accession_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    row = payload["payload_row"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "selected_accession": payload["selected_accession"],
        "deferred_accession": payload["deferred_accession"],
        "payload_row_count": payload["payload_row_count"],
        "variant_ref": row["variant_ref"],
        "structure_ref": f"{row['structure_id']}:{row['chain_id']}",
        "coverage": row["coverage"],
        "single_accession_scope": truth["single_accession_scope"],
        "candidate_only_no_variant_anchor": truth["candidate_only_no_variant_anchor"],
        "direct_structure_backed_join_certified": truth["direct_structure_backed_join_certified"],
        "ready_for_operator_preview": truth["ready_for_operator_preview"],
    }


def _compact_structure_followup_single_accession_validation_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": payload["status"],
        "selected_accession": payload["selected_accession"],
        "deferred_accession": payload["deferred_accession"],
        "payload_row_count": payload["payload_row_count"],
        "anchor_validation_status": payload["anchor_validation_status"],
        "validated_row_count": payload["validated_row_count"],
        "candidate_variant_anchor_count_total": payload["candidate_variant_anchor_count_total"],
        "candidate_variant_anchor_count": payload["candidate_variant_anchor_count"],
        "recommended_anchor_present_in_best_targets": payload[
            "recommended_anchor_present_in_best_targets"
        ],
        "variant_positions_within_recommended_span": payload[
            "variant_positions_within_recommended_span"
        ],
        "candidate_only_no_variant_anchor": payload["candidate_only_no_variant_anchor"],
        "direct_structure_backed_join_certified": payload["direct_structure_backed_join_certified"],
        "ready_for_operator_preview": payload["ready_for_operator_preview"],
    }


def _compact_structure_similarity_signature_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "protein_count": summary["protein_count"],
        "fold_signature_count": summary["fold_signature_count"],
        "candidate_only_count": summary["candidate_only_count"],
        "ready_for_bundle_preview": payload["truth_boundary"]["ready_for_bundle_preview"],
        "direct_structure_backed_variant_join_materialized": payload["truth_boundary"][
            "direct_structure_backed_variant_join_materialized"
        ],
    }


def _compact_protein_similarity_signature_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "protein_count": summary["protein_count"],
        "unique_similarity_group_count": summary["unique_similarity_group_count"],
        "ready_for_bundle_preview": payload["truth_boundary"]["ready_for_bundle_preview"],
        "ligand_similarity_materialized": payload["truth_boundary"][
            "ligand_similarity_materialized"
        ],
    }


def _compact_dictionary_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "namespace_count": summary["namespace_count"],
        "namespaces": [row["namespace"] for row in summary["namespaces"]],
        "reference_kind_counts": summary["reference_kind_counts"],
        "ready_for_bundle_preview": payload["truth_boundary"]["ready_for_bundle_preview"],
        "biological_content_family": payload["truth_boundary"]["biological_content_family"],
    }


def _compact_motif_domain_compact_preview_family(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload["summary"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "namespace_count": summary["namespace_count"],
        "included_namespaces": [row["namespace"] for row in summary["included_namespaces"]],
        "reference_kind_counts": summary["reference_kind_counts"],
        "supporting_record_count": summary["supporting_record_count"],
        "ready_for_bundle_preview": truth["ready_for_bundle_preview"],
        "biological_content_family": truth["biological_content_family"],
        "governing_for_split_or_leakage": truth["governing_for_split_or_leakage"],
    }


def _compact_interaction_similarity_signature_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload["summary"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "accession_count": summary["accession_count"],
        "unique_interaction_similarity_group_count": summary[
            "unique_interaction_similarity_group_count"
        ],
        "candidate_only_row_count": summary["candidate_only_row_count"],
        "source_overlap_accessions": summary["source_overlap_accessions"],
        "biogrid_matched_row_total": summary["biogrid_matched_row_total"],
        "intact_present_count": summary["intact_present_count"],
        "string_top_level_file_partial_count": summary["string_top_level_file_partial_count"],
        "ready_for_bundle_preview": truth["ready_for_bundle_preview"],
        "interaction_family_materialized": truth["interaction_family_materialized"],
        "direct_interaction_family_claimed": truth["direct_interaction_family_claimed"],
        "candidate_only_rows": truth["candidate_only_rows"],
    }


def _compact_interaction_similarity_signature_validation(
    payload: dict[str, Any],
) -> dict[str, Any]:
    validation = payload["validation"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": validation["row_count"],
        "accession_count": validation["accession_count"],
        "candidate_only_accessions": validation["candidate_only_accessions"],
        "issue_count": validation["issue_count"],
        "bundle_safe_immediately": truth["bundle_safe_immediately"],
        "bundle_interaction_similarity_signatures_included": truth[
            "bundle_interaction_similarity_signatures_included"
        ],
        "interaction_family_materialized": truth["interaction_family_materialized"],
        "direct_interaction_family_claimed": truth["direct_interaction_family_claimed"],
    }


def _compact_sabio_rk_support_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "supported_accession_count": summary["supported_accession_count"],
        "supported_accessions": summary["supported_accessions"],
        "supported_high_priority_accession_count": summary[
            "supported_high_priority_accession_count"
        ],
        "live_kinetic_law_verified_count": summary["live_kinetic_law_verified_count"],
        "ready_for_next_wave": summary["ready_for_next_wave"],
        "seed_only": truth["seed_only"],
        "live_kinetic_ids_verified": truth["live_kinetic_ids_verified"],
        "live_sbml_exports_verified": truth["live_sbml_exports_verified"],
        "dashboard_blocked": truth["dashboard_blocked"],
    }


def _compact_kinetics_support_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "supported_accession_count": summary["supported_accession_count"],
        "supported_accessions": summary["supported_accessions"],
        "support_status_counts": summary["support_status_counts"],
        "ready_for_next_wave": summary["ready_for_next_wave"],
        "live_kinetic_ids_verified": truth["live_kinetic_ids_verified"],
        "live_enzyme_activity_verified": truth["live_enzyme_activity_verified"],
        "ready_for_bundle_preview": True,
        "governing_for_split_or_leakage": False,
        "policy_label": payload.get("policy_label"),
    }


def _compact_ligand_support_readiness_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload["summary"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "support_accessions": summary["support_accessions"],
        "deferred_accessions": summary["deferred_accessions"],
        "lane_status_counts": summary["lane_status_counts"],
        "bundle_ligands_included": summary["bundle_ligands_included"],
        "ligand_rows_materialized": truth["ligand_rows_materialized"],
        "q9ucm0_deferred": truth["q9ucm0_deferred"],
        "ready_for_operator_preview": truth["ready_for_operator_preview"],
    }


def _compact_ligand_identity_pilot_preview(payload: dict[str, Any]) -> dict[str, Any]:
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "first_accession": payload["rows"][0]["accession"],
        "second_accession": payload["rows"][1]["accession"],
        "ordered_accessions": [row["accession"] for row in payload.get("rows", [])],
        "grounded_accession_count": payload.get("grounded_accession_count", 0),
        "grounded_accessions": payload.get("grounded_accessions", []),
        "first_accession_evidence_kind": payload["rows"][0].get("grounded_evidence_kind"),
        "row_complete_operator_summary": True,
        "deferred_accession": payload["deferred_accession"],
        "report_only": truth["report_only"],
        "ligand_rows_materialized": truth["ligand_rows_materialized"],
        "bundle_ligands_included": truth["bundle_ligands_included"],
        "ready_for_operator_preview": truth["ready_for_operator_preview"],
    }


def _compact_ligand_stage1_operator_queue_preview(payload: dict[str, Any]) -> dict[str, Any]:
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "ordered_accessions": [row["accession"] for row in payload.get("ordered_rows", [])],
        "first_accession": payload["ordered_rows"][0]["accession"],
        "second_accession": payload["ordered_rows"][1]["accession"],
        "deferred_accession": payload["deferred_row"]["accession"],
        "operator_labels": [row["operator_label"] for row in payload.get("ordered_rows", [])],
        "report_only": truth["report_only"],
        "ligand_rows_materialized": truth["ligand_rows_materialized"],
        "bundle_ligands_included": truth["bundle_ligands_included"],
        "q9ucm0_deferred": truth["q9ucm0_deferred"],
        "ready_for_operator_preview": truth["ready_for_operator_preview"],
    }


def _compact_p00387_ligand_extraction_validation_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    truth = payload["truth_boundary"]
    validation = payload["validation_summary"]
    return {
        "status": payload["status"],
        "accession": payload["accession"],
        "target_chembl_id": payload["target_chembl_id"],
        "rows_emitted": payload["rows_emitted"],
        "activity_count_total": payload["activity_count_total"],
        "distinct_ligand_count_in_payload": payload["distinct_ligand_count_in_payload"],
        "ready_for_operator_preview": validation["ready_for_operator_preview"],
        "canonical_ligand_materialization_claimed": truth[
            "canonical_ligand_materialization_claimed"
        ],
    }


def _compact_q9nzd4_bridge_validation_preview(payload: dict[str, Any]) -> dict[str, Any]:
    truth = payload["truth_boundary"]
    validation = payload["validation_summary"]
    return {
        "status": payload["status"],
        "accession": payload["accession"],
        "best_pdb_id": payload["best_pdb_id"],
        "component_id": payload["component_id"],
        "component_role": payload["component_role"],
        "matched_pdb_id_count": payload["matched_pdb_id_count"],
        "ready_for_operator_preview": validation["ready_for_operator_preview"],
        "candidate_only": truth["candidate_only"],
        "canonical_ligand_materialization_claimed": truth[
            "canonical_ligand_materialization_claimed"
        ],
    }


def _compact_ligand_stage1_validation_panel_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "validated_accessions": summary["validated_accessions"],
        "aligned_row_count": summary["aligned_row_count"],
        "candidate_only_accessions": summary["candidate_only_accessions"],
        "ready_for_operator_preview": summary["operator_ready"],
        "ligand_rows_materialized": truth["ligand_rows_materialized"],
        "bundle_ligands_included": truth["bundle_ligands_included"],
    }


def _compact_ligand_identity_core_materialization_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload["summary"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "ordered_accessions": summary["ordered_accessions"],
        "grounded_accessions": summary["grounded_accessions"],
        "grounded_accession_count": summary["grounded_accession_count"],
        "held_support_only_accessions": summary["held_support_only_accessions"],
        "candidate_only_accessions": summary["candidate_only_accessions"],
        "ready_for_operator_preview": summary["ready_for_bundle_preview"],
        "ligand_rows_materialized": truth["ligand_rows_materialized"],
        "bundle_ligands_included": truth["bundle_ligands_included"],
    }


def _compact_next_real_ligand_row_gate_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "selected_accession": payload["selected_accession"],
        "selected_accession_gate_status": payload["selected_accession_gate_status"],
        "fallback_accession": payload["fallback_accession"],
        "fallback_accession_gate_status": payload["fallback_accession_gate_status"],
        "current_grounded_accession_count": payload["current_grounded_accession_count"],
        "current_grounded_accessions": payload["current_grounded_accessions"],
        "can_materialize_new_grounded_accession_now": payload[
            "can_materialize_new_grounded_accession_now"
        ],
        "next_unlocked_stage": payload["next_unlocked_stage"],
        "candidate_only_rows_non_governing": truth["candidate_only_rows_non_governing"],
    }


def _compact_next_real_ligand_row_decision_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    selected_criteria = payload["selected_accession_probe_criteria"]
    fallback_criteria = payload["fallback_probe_criteria"]
    return {
        "status": payload["status"],
        "selected_accession": payload["selected_accession"],
        "selected_accession_gate_status": payload["selected_accession_gate_status"],
        "selected_source_classification": selected_criteria.get("source_classification"),
        "selected_gap_probe_classification": selected_criteria.get("gap_probe_classification"),
        "selected_best_next_action": selected_criteria.get("best_next_action"),
        "fallback_accession": payload["fallback_accession"],
        "fallback_accession_gate_status": payload["fallback_accession_gate_status"],
        "fallback_source_classification": fallback_criteria.get("source_classification"),
        "fallback_gap_probe_classification": fallback_criteria.get("gap_probe_classification"),
        "fallback_best_next_action": fallback_criteria.get("best_next_action"),
        "minimum_grounded_promotion_evidence_count": len(
            payload.get("minimum_grounded_promotion_evidence") or []
        ),
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_ligand_row_materialization_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload["summary"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "materialized_accessions": summary["materialized_accessions"],
        "grounded_accessions": summary["grounded_accessions"],
        "candidate_only_accessions": summary["candidate_only_accessions"],
        "grounded_row_count": summary["grounded_row_count"],
        "candidate_only_row_count": summary["candidate_only_row_count"],
        "ligand_namespace_counts": summary["ligand_namespace_counts"],
        "first_ligand_ref": payload["rows"][0]["ligand_ref"] if payload["rows"] else None,
        "ready_for_operator_preview": summary["ready_for_bundle_preview"],
        "ligand_rows_materialized": truth["ligand_rows_materialized"],
        "bundle_ligands_included": truth["bundle_ligands_included"],
        "canonical_ligand_materialization_claimed": truth[
            "canonical_ligand_materialization_claimed"
        ],
    }


def _compact_ligand_similarity_signature_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload["summary"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "accession_count": summary["accession_count"],
        "exact_identity_group_count": summary["exact_identity_group_count"],
        "chemical_series_group_count": summary["chemical_series_group_count"],
        "candidate_only_count": summary["candidate_only_count"],
        "ligand_namespace_counts": summary["ligand_namespace_counts"],
        "ready_for_bundle_preview": truth["ready_for_bundle_preview"],
        "ligand_rows_materialized": truth["ligand_rows_materialized"],
        "canonical_ligand_reconciliation_claimed": truth["canonical_ligand_reconciliation_claimed"],
    }


def _compact_ligand_similarity_signature_gate_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "stage_id": payload["stage_id"],
        "gate_status": payload["gate_status"],
        "identity_core_preview_row_count": payload["identity_core_preview_row_count"],
        "identity_core_grounded_accession_count": payload["identity_core_grounded_accession_count"],
        "ligands_materialized": payload["ligands_materialized"],
        "ligand_record_count": payload["ligand_record_count"],
        "next_unlocked_stage": payload["next_unlocked_stage"],
        "ligand_similarity_signatures_materialized": truth[
            "ligand_similarity_signatures_materialized"
        ],
    }


def _compact_ligand_similarity_signature_validation(
    payload: dict[str, Any],
) -> dict[str, Any]:
    validation = payload["validation"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "row_count": validation["row_count"],
        "grounded_accessions": validation["grounded_accessions"],
        "candidate_only_accessions": validation["candidate_only_accessions"],
        "candidate_only_namespaces": validation["candidate_only_namespaces"],
        "policy_mode": validation["policy_mode"],
        "issue_count": validation["issue_count"],
        "candidate_only_rows_non_governing": truth["candidate_only_rows_non_governing"],
        "canonical_ligand_reconciliation_claimed": truth["canonical_ligand_reconciliation_claimed"],
        "split_claims_changed": truth["split_claims_changed"],
    }


def _compact_entity_signature_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "entity_family_counts": summary["entity_family_counts"],
        "protein_spine_count": summary["protein_spine_count"],
        "variant_delta_group_count": summary["variant_delta_group_count"],
        "structure_chain_group_count": summary["structure_chain_group_count"],
        "ligand_groups_materialized": payload["truth_boundary"]["ligand_groups_materialized"],
        "direct_structure_backed_variant_join_materialized": payload["truth_boundary"][
            "direct_structure_backed_variant_join_materialized"
        ],
    }


def _compact_entity_split_candidate_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "entity_family_counts": summary["entity_family_counts"],
        "linked_group_count": summary["linked_group_count"],
        "default_atomic_unit": summary["default_atomic_unit"],
        "default_hard_group": summary["default_hard_group"],
        "ready_for_split_engine": payload["truth_boundary"]["ready_for_split_engine"],
        "ligand_rows_materialized": payload["truth_boundary"]["ligand_rows_materialized"],
    }


def _compact_entity_split_simulation_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "candidate_row_count": summary["candidate_row_count"],
        "assignment_count": summary["assignment_count"],
        "rejected_count": summary["rejected_count"],
        "split_counts": summary["split_counts"],
        "target_counts": summary["target_counts"],
        "ready_for_split_engine": True,
        "final_split_committed": payload["truth_boundary"]["final_split_committed"],
    }


def _compact_entity_split_recipe_preview(payload: dict[str, Any]) -> dict[str, Any]:
    recipe = payload["recipe"]
    grounding = payload["grounding"]
    return {
        "status": payload["status"],
        "recipe_id": recipe["recipe_id"],
        "input_artifact": recipe["input_artifact"],
        "atomic_unit": recipe["atomic_unit"],
        "primary_hard_group": recipe["hard_grouping"]["primary_group"],
        "candidate_row_count": grounding["candidate_row_count"],
        "linked_group_count": grounding["linked_group_count"],
        "simulation_assignment_count": grounding["simulation_assignment_count"],
        "ready_for_recipe_export": payload["truth_boundary"]["ready_for_recipe_export"],
        "final_split_committed": payload["truth_boundary"]["final_split_committed"],
    }


def _compact_entity_split_assignment_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "group_row_count": payload["group_row_count"],
        "candidate_row_count": summary["candidate_row_count"],
        "assignment_count": summary["assignment_count"],
        "split_group_counts": summary["split_group_counts"],
        "ready_for_fold_export": payload["truth_boundary"]["ready_for_fold_export"],
        "final_split_committed": payload["truth_boundary"]["final_split_committed"],
    }


def _compact_split_engine_input_preview(payload: dict[str, Any]) -> dict[str, Any]:
    recipe_binding = payload["recipe_binding"]
    assignment_binding = payload["assignment_binding"]
    execution_readiness = payload["execution_readiness"]
    supplemental = payload.get("supplemental_non_governing_signals") or {}
    ligand_rows = supplemental.get("ligand_rows") or {}
    motif_domain_compact = supplemental.get("motif_domain_compact") or {}
    interaction_similarity_preview = supplemental.get("interaction_similarity_preview") or {}
    return {
        "status": payload["status"],
        "recipe_id": recipe_binding["recipe_id"],
        "input_artifact": recipe_binding["input_artifact"],
        "group_row_count": assignment_binding["group_row_count"],
        "candidate_row_count": assignment_binding["candidate_row_count"],
        "assignment_count": assignment_binding["assignment_count"],
        "next_unlocked_stage": execution_readiness["next_unlocked_stage"],
        "supplemental_non_governing_preview_ready": execution_readiness[
            "supplemental_non_governing_preview_ready"
        ],
        "ligand_governing_split_ready": execution_readiness["ligand_governing_split_ready"],
        "supplemental_ligand_rows_status": ligand_rows.get("status"),
        "supplemental_ligand_grounded_accession_count": ligand_rows.get("grounded_accession_count"),
        "supplemental_motif_domain_status": motif_domain_compact.get("status"),
        "supplemental_interaction_similarity_status": (
            interaction_similarity_preview.get("status")
        ),
        "ready_for_split_engine_dry_run": payload["truth_boundary"][
            "ready_for_split_engine_dry_run"
        ],
        "cv_folds_materialized": payload["truth_boundary"]["cv_folds_materialized"],
    }


def _compact_split_engine_dry_run_validation(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload["validation"]
    return {
        "status": payload["status"],
        "recipe_id": validation["recipe_id"],
        "candidate_row_count": validation["candidate_row_count"],
        "assignment_count": validation["assignment_count"],
        "split_group_counts": validation["split_group_counts"],
        "match_count": len(validation["matches"]),
        "issue_count": len(validation["issues"]),
        "final_split_committed": payload["truth_boundary"]["final_split_committed"],
        "fold_export_ready": payload["truth_boundary"]["fold_export_ready"],
    }


def _compact_split_fold_export_gate_preview(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload["validation_snapshot"]
    execution = payload["execution_snapshot"]
    readiness = payload["unlock_readiness"]
    return {
        "status": payload["status"],
        "gate_id": payload["gate"]["gate_id"],
        "required_condition_count": payload["gate"]["required_condition_count"],
        "dry_run_validation_status": validation["dry_run_validation_status"],
        "dry_run_issue_count": validation["dry_run_issue_count"],
        "candidate_row_count": validation["candidate_row_count"],
        "assignment_count": validation["assignment_count"],
        "cv_fold_export_unlocked": readiness["cv_fold_export_unlocked"],
        "blocked_reasons": readiness["blocked_reasons"],
        "ready_for_fold_export": readiness["ready_for_fold_export"],
        "cv_folds_materialized": execution["cv_folds_materialized"],
        "final_split_committed": execution["final_split_committed"],
    }


def _compact_split_fold_export_gate_validation(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload["validation"]
    return {
        "status": payload["status"],
        "gate_status": validation["gate_status"],
        "required_condition_count": validation["required_condition_count"],
        "candidate_row_count": validation["candidate_row_count"],
        "assignment_count": validation["assignment_count"],
        "dry_run_issue_count": validation["dry_run_issue_count"],
        "blocked_reasons": validation["blocked_reasons"],
        "cv_fold_export_unlocked": payload["truth_boundary"]["cv_fold_export_unlocked"],
        "cv_folds_materialized": payload["truth_boundary"]["cv_folds_materialized"],
        "final_split_committed": payload["truth_boundary"]["final_split_committed"],
    }


def _compact_split_fold_export_staging_preview(payload: dict[str, Any]) -> dict[str, Any]:
    gate = payload["gate_binding"]
    staging_manifest = payload["staging_manifest"]
    blocked = payload["blocked_report"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "stage_id": payload["stage"]["stage_id"],
        "surface_id": payload["stage"]["surface_id"],
        "gate_status": gate["gate_status"],
        "candidate_row_count": staging_manifest["candidate_row_count"],
        "assignment_count": staging_manifest["assignment_count"],
        "blocked_reasons": blocked["blocked_reasons"],
        "dry_run_validation_status": blocked["dry_run_validation_status"],
        "validation_status": blocked["validation_status"],
        "run_scoped_only": truth["run_scoped_only"],
        "cv_fold_export_unlocked": truth["cv_fold_export_unlocked"],
        "cv_folds_materialized": truth["cv_folds_materialized"],
        "final_split_committed": truth["final_split_committed"],
    }


def _compact_split_fold_export_staging_validation(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload["validation"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "stage_status": validation["stage_status"],
        "gate_status": validation["gate_status"],
        "candidate_row_count": validation["candidate_row_count"],
        "assignment_count": validation["assignment_count"],
        "dry_run_issue_count": validation["dry_run_issue_count"],
        "blocked_reasons": validation["blocked_reasons"],
        "run_scoped_only": truth["run_scoped_only"],
        "cv_fold_export_unlocked": truth["cv_fold_export_unlocked"],
        "cv_folds_materialized": truth["cv_folds_materialized"],
        "final_split_committed": truth["final_split_committed"],
    }


def _compact_split_post_staging_gate_check_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    stage = payload["stage"]
    gate = payload["gate_check"]
    parity = payload["staging_parity"]
    blocked = payload["blocked_report"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "stage_id": stage["stage_id"],
        "stage_shape": stage["stage_shape"],
        "gate_status": gate["gate_status"],
        "candidate_row_count": parity["candidate_row_count"],
        "assignment_count": parity["assignment_count"],
        "blocked_reasons": blocked["blocked_reasons"],
        "run_scoped_only": truth["run_scoped_only"],
        "cv_fold_export_unlocked": truth["cv_fold_export_unlocked"],
        "cv_folds_materialized": truth["cv_folds_materialized"],
        "final_split_committed": truth["final_split_committed"],
    }


def _compact_split_post_staging_gate_check_validation(
    payload: dict[str, Any],
) -> dict[str, Any]:
    validation = payload["validation"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "stage_status": validation["stage_status"],
        "gate_status": validation["gate_status"],
        "candidate_row_count": validation["candidate_row_count"],
        "assignment_count": validation["assignment_count"],
        "blocked_reasons": validation["blocked_reasons"],
        "run_scoped_only": truth["run_scoped_only"],
        "cv_fold_export_unlocked": truth["cv_fold_export_unlocked"],
        "cv_folds_materialized": truth["cv_folds_materialized"],
        "final_split_committed": truth["final_split_committed"],
    }


def _compact_split_fold_export_request_preview(payload: dict[str, Any]) -> dict[str, Any]:
    stage = payload["stage"]
    binding = payload["request_binding"]
    blocked = payload["blocked_report"]
    return {
        "status": payload["status"],
        "stage_id": stage["stage_id"],
        "stage_shape": stage["stage_shape"],
        "today_status": stage["today_status"],
        "candidate_row_count": binding["candidate_row_count"],
        "assignment_count": binding["assignment_count"],
        "linked_group_count": binding["linked_group_count"],
        "post_staging_validation_status": blocked["post_staging_validation_status"],
        "cv_fold_export_unlocked": blocked["cv_fold_export_unlocked"],
        "cv_folds_materialized": blocked["cv_folds_materialized"],
        "final_split_committed": blocked["final_split_committed"],
        "request_only_no_fold_materialization": payload["truth_boundary"][
            "request_only_no_fold_materialization"
        ],
    }


def _compact_split_fold_export_request_validation(
    payload: dict[str, Any],
) -> dict[str, Any]:
    validation = payload["validation"]
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "stage_status": validation["stage_status"],
        "gate_status": validation["gate_status"],
        "candidate_row_count": validation["candidate_row_count"],
        "assignment_count": validation["assignment_count"],
        "issue_count": len(validation["issues"]),
        "match_count": len(validation["matches"]),
        "blocked_reasons": validation["blocked_reasons"],
        "run_scoped_only": truth["run_scoped_only"],
        "cv_fold_export_unlocked": truth["cv_fold_export_unlocked"],
        "cv_folds_materialized": truth["cv_folds_materialized"],
    }


def _compact_leakage_signature_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "candidate_overlap_accessions": summary["candidate_overlap_accessions"],
        "structure_followup_accessions": summary["structure_followup_accessions"],
        "protein_only_accessions": summary["protein_only_accessions"],
    }


def _compact_leakage_group_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "split_group_counts": summary["split_group_counts"],
        "risk_class_counts": summary["risk_class_counts"],
        "candidate_overlap_accessions": summary["candidate_overlap_accessions"],
        "ready_for_bundle_preview": payload["truth_boundary"]["ready_for_bundle_preview"],
        "final_fold_export_committed": payload["truth_boundary"]["final_fold_export_committed"],
    }


def _compact_duplicate_executor_status(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload["status"],
        "validation_status": payload["validation"]["status"],
        "action_count": payload["plan_summary"]["action_count"],
        "planned_reclaimable_bytes": payload["plan_summary"]["planned_reclaimable_bytes"],
        "allowed_cohorts": payload["plan_summary"]["allowed_cohorts"],
        "warnings": payload["validation"]["warnings"],
        "errors": payload["validation"]["errors"],
    }


def _compact_duplicate_cleanup_first_execution_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    truth = payload["truth_boundary"]
    return {
        "status": payload["status"],
        "execution_status": payload["execution_status"],
        "preview_manifest_status": payload.get("preview_manifest_status"),
        "batch_size_limit": payload["batch_size_limit"],
        "batch_shape": payload["batch_shape"],
        "duplicate_class": payload["duplicate_class"],
        "reclaimable_bytes": payload["reclaimable_bytes"],
        "delete_ready_action_count": payload.get("delete_ready_action_count"),
        "refresh_required": payload.get("refresh_required"),
        "executor_validation_status": payload["executor_validation_status"],
        "report_only": truth["report_only"],
        "delete_enabled": truth["delete_enabled"],
        "latest_surfaces_mutated": truth["latest_surfaces_mutated"],
        "ready_for_operator_preview": truth["ready_for_operator_preview"],
    }


def _compact_duplicate_cleanup_delete_ready_manifest_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    truth = payload.get("truth_boundary") or {}
    constraints = payload.get("constraint_checks") or {}
    return {
        "status": payload.get("status"),
        "preview_manifest_status": payload.get("preview_manifest_status"),
        "execution_blocked": payload.get("execution_blocked"),
        "action_count": payload.get("action_count"),
        "duplicate_class": (payload.get("delete_batch") or {}).get("duplicate_class"),
        "reclaimable_bytes": (payload.get("delete_batch") or {}).get("reclaimable_bytes"),
        "all_constraints_satisfied_preview": constraints.get("all_constraints_satisfied_preview"),
        "keeper_path_exists": constraints.get("keeper_path_exists"),
        "checksum_present": constraints.get("checksum_present"),
        "report_only": truth.get("report_only"),
        "delete_enabled": truth.get("delete_enabled"),
        "requires_plan_refresh_when_consumed": truth.get("requires_plan_refresh_when_consumed"),
    }


def _compact_duplicate_cleanup_post_delete_verification_contract_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    truth = payload.get("truth_boundary") or {}
    return {
        "status": payload.get("status"),
        "delete_ready_action_count": payload.get("delete_ready_action_count"),
        "frozen_manifest_ref": payload.get("frozen_manifest_ref"),
        "ready_for_post_delete_checklist": truth.get("ready_for_post_delete_checklist"),
        "report_only": truth.get("report_only"),
        "delete_enabled": truth.get("delete_enabled"),
    }


def _compact_duplicate_cleanup_first_execution_batch_manifest_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    truth = payload["truth_boundary"]
    validation = payload["validation"]
    return {
        "status": payload["status"],
        "execution_status": payload["execution_status"],
        "batch_manifest_status": payload["batch_manifest_status"],
        "batch_size_limit": payload["batch_identity"]["batch_size_limit"],
        "cohort_name": payload["batch_identity"]["cohort_name"],
        "duplicate_class": payload["frozen_action"]["duplicate_class"],
        "reclaimable_bytes": payload["frozen_action"]["reclaimable_bytes"],
        "first_action_matches_exemplar": payload["plan_alignment"]["first_action_matches_exemplar"],
        "validation_status": validation["status"],
        "report_only": truth["report_only"],
        "delete_enabled": truth["delete_enabled"],
        "mutation_allowed": truth["mutation_allowed"],
        "ready_for_operator_preview": truth["ready_for_operator_preview"],
    }


def _compact_operator_next_actions_preview(payload: dict[str, Any]) -> dict[str, Any]:
    prioritized_actions = payload.get("prioritized_actions", [])
    ligand_row = prioritized_actions[0] if len(prioritized_actions) > 0 else {}
    structure_row = prioritized_actions[1] if len(prioritized_actions) > 1 else {}
    split_row = prioritized_actions[2] if len(prioritized_actions) > 2 else {}
    duplicate_row = prioritized_actions[3] if len(prioritized_actions) > 3 else {}
    ligand_detail = ligand_row.get("detail", {})
    structure_detail = structure_row.get("detail", {})
    split_detail = split_row.get("detail", {})
    duplicate_detail = duplicate_row.get("detail", {})
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "lanes": [row["lane"] for row in prioritized_actions],
        "first_ligand_accession": ligand_row.get("accession"),
        "first_ligand_lane_status": ligand_detail.get("selected_accession_gate_status"),
        "first_ligand_best_next_action": ligand_detail.get("best_next_action"),
        "first_ligand_fallback_accession": ligand_detail.get("fallback_accession"),
        "first_ligand_fallback_gate_status": ligand_detail.get("fallback_accession_gate_status"),
        "first_ligand_grounded_accessions": ligand_detail.get("current_grounded_accessions"),
        "structure_accession": structure_row.get("accession"),
        "structure_deferred_accession": structure_detail.get("deferred_accession"),
        "split_status": split_row.get("status"),
        "split_run_scoped_only": split_detail.get("request_scope"),
        "duplicate_cleanup_status": duplicate_row.get("status"),
        "duplicate_cleanup_batch_size_limit": duplicate_detail.get("batch_size_limit"),
        "duplicate_cleanup_action_count": duplicate_detail.get("delete_ready_action_count"),
        "duplicate_cleanup_refresh_required": duplicate_detail.get("refresh_required"),
        "report_only": payload["truth_boundary"]["report_only"],
        "ready_for_operator_preview": payload["truth_boundary"]["ready_for_operator_preview"],
    }


def _compact_training_set_eligibility_matrix_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "accession_count": summary["accession_count"],
        "packet_visible_accession_count": summary["packet_visible_accession_count"],
        "protein_summary_accession_count": summary["protein_summary_accession_count"],
        "grounded_ligand_accessions": summary["grounded_ligand_accessions"],
        "candidate_only_ligand_accessions": summary["candidate_only_ligand_accessions"],
        "ligand_readiness_ladder_counts": summary.get("ligand_readiness_ladder_counts", {}),
        "modality_readiness_counts": summary.get("modality_readiness_counts", {}),
        "primary_missing_data_class_counts": summary["primary_missing_data_class_counts"],
        "task_status_counts": summary["task_status_counts"],
        "candidate_only_rows_non_governing": payload["truth_boundary"][
            "candidate_only_rows_non_governing"
        ],
        "missing_values_imputed": payload["truth_boundary"]["missing_values_imputed"],
    }


def _compact_missing_data_policy_preview(payload: dict[str, Any]) -> dict[str, Any]:
    priorities = payload["scrape_and_enrichment_priorities"]["top_next_acquisitions"]
    return {
        "status": payload["status"],
        "category_counts": payload["category_counts"],
        "task_status_counts": payload["task_status_counts"],
        "modality_readiness_counts": payload.get("modality_readiness_counts", {}),
        "modality_readiness_ladder": payload.get("modality_readiness_ladder", []),
        "policy_category_count": len(payload["policy_categories"]),
        "core_rule_count": len(payload["policy_rules"]),
        "scope_judgment": payload["scrape_and_enrichment_priorities"]["scope_judgment"],
        "top_scrape_targets": [row["target"] for row in priorities],
        "report_only": payload["truth_boundary"]["report_only"],
        "missing_values_imputed": payload["truth_boundary"]["missing_values_imputed"],
        "candidate_only_rows_non_governing": payload["truth_boundary"][
            "candidate_only_rows_non_governing"
        ],
        "deletion_default": payload["truth_boundary"]["deletion_default"],
    }


def _compact_training_set_readiness_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "readiness_state": payload.get("readiness_state"),
        "accession_count": summary.get("accession_count"),
        "selected_count": summary.get("selected_count"),
        "blocked_reason_count": len(summary.get("blocked_reasons") or []),
        "assignment_ready": summary.get("assignment_ready"),
        "fold_export_ready": summary.get("fold_export_ready"),
        "package_ready": summary.get("package_ready"),
        "external_audit_decision": summary.get("external_audit_decision"),
        "release_ready": summary.get("release_ready"),
        "report_only": (payload.get("truth_boundary") or {}).get("report_only"),
    }


def _compact_final_structured_dataset_bundle_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "run_id": summary.get("run_id"),
        "corpus_row_count": summary.get("corpus_row_count"),
        "strict_governing_training_view_count": summary.get(
            "strict_governing_training_view_count"
        ),
        "all_visible_training_candidates_view_count": summary.get(
            "all_visible_training_candidates_view_count"
        ),
        "packet_count": summary.get("packet_count"),
        "package_readiness_state": summary.get("package_readiness_state"),
    }


def _compact_pdbbind_expanded_structured_corpus_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "dataset_generation_mode": summary.get("dataset_generation_mode"),
        "row_count": summary.get("row_count"),
        "protein_count": summary.get("protein_count"),
        "protein_cohort_count": summary.get("protein_cohort_count"),
        "structure_count": summary.get("structure_count"),
        "interaction_count": summary.get("interaction_count"),
        "measurement_count": summary.get("measurement_count"),
    }


def _compact_pdbbind_protein_cohort_graph_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "protein_count": summary.get("protein_count"),
        "direct_ppi_edge_count": summary.get("direct_ppi_edge_count"),
        "proteins_with_direct_ppi_partners": summary.get("proteins_with_direct_ppi_partners"),
        "proteins_with_cohort_neighbors": summary.get("proteins_with_cohort_neighbors"),
        "uniref90_multi_member_group_count": summary.get("uniref90_multi_member_group_count"),
        "uniref50_multi_member_group_count": summary.get("uniref50_multi_member_group_count"),
        "max_total_neighbor_count": summary.get("max_total_neighbor_count"),
    }


def _compact_paper_pdb_split_assessment(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "verdict": summary.get("verdict"),
        "total_structure_count": summary.get("total_structure_count"),
        "covered_structure_count": summary.get("covered_structure_count"),
        "missing_structure_count": summary.get("missing_structure_count"),
        "direct_protein_overlap_count": summary.get("direct_protein_overlap_count"),
        "uniref90_cluster_overlap_count": summary.get("uniref90_cluster_overlap_count"),
        "shared_partner_overlap_count": summary.get("shared_partner_overlap_count"),
        "flagged_structure_pair_count": summary.get("flagged_structure_pair_count"),
    }


def _compact_pdb_paper_split_leakage_matrix(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "verdict": summary.get("verdict"),
        "blocked_category_count": summary.get("blocked_category_count"),
        "review_category_count": summary.get("review_category_count"),
        "blocked_categories": summary.get("blocked_categories"),
        "review_categories": summary.get("review_categories"),
        "flagged_structure_pair_count": summary.get("flagged_structure_pair_count"),
    }


def _compact_pdb_paper_split_acceptance_gate(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "decision": summary.get("decision"),
        "blocked_gate_count": summary.get("blocked_gate_count"),
        "attention_gate_count": summary.get("attention_gate_count"),
        "blocked_gates": summary.get("blocked_gates"),
        "attention_gates": summary.get("attention_gates"),
    }


def _compact_pdb_paper_split_sequence_signature_audit(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "sequence_decision": summary.get("sequence_decision"),
        "requested_accession_count": summary.get("requested_accession_count"),
        "sequence_present_count": summary.get("sequence_present_count"),
        "exact_sequence_overlap_count": summary.get("exact_sequence_overlap_count"),
        "near_sequence_flagged_count": summary.get("near_sequence_flagged_count"),
    }


def _compact_pdb_paper_split_mutation_audit(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "decision": summary.get("decision"),
        "candidate_pair_count": summary.get("candidate_pair_count"),
        "mutation_like_pair_count": summary.get("mutation_like_pair_count"),
        "relation_counts": summary.get("relation_counts"),
    }


def _compact_pdb_paper_split_structure_state_audit(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "decision": summary.get("decision"),
        "flagged_pair_count": summary.get("flagged_pair_count"),
        "relation_counts": summary.get("relation_counts"),
        "risk_level_counts": summary.get("risk_level_counts"),
    }


def _compact_pdb_paper_dataset_quality_verdict(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "overall_decision": summary.get("overall_decision"),
        "readiness": summary.get("readiness"),
        "blocked_reason_count": summary.get("blocked_reason_count"),
        "review_reason_count": summary.get("review_reason_count"),
        "blocked_reasons": summary.get("blocked_reasons"),
        "review_reasons": summary.get("review_reasons"),
        "coverage_fraction": summary.get("coverage_fraction"),
        "top_recommendation": summary.get("top_recommendation"),
    }


def _compact_pdb_paper_split_remediation_plan(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "preferred_plan": summary.get("preferred_plan"),
        "blocking_edge_count": summary.get("blocking_edge_count"),
        "hybrid_holdout_count": summary.get("hybrid_holdout_count"),
        "test_only_holdout_count": summary.get("test_only_holdout_count"),
        "train_only_holdout_count": summary.get("train_only_holdout_count"),
        "missing_source_fix_count": summary.get("missing_source_fix_count"),
    }


def _compact_release_grade_readiness_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    blocker_rows = payload.get("blocker_rows") or []
    return {
        "status": payload.get("status"),
        "release_grade_status": summary.get("release_grade_status"),
        "blocker_count": summary.get("blocker_count"),
        "blocker_categories": summary.get("blocker_categories"),
        "dataset_creation_complete_for_current_scope": summary.get(
            "dataset_creation_complete_for_current_scope"
        ),
        "final_dataset_bundle_present": summary.get("final_dataset_bundle_present"),
        "corpus_row_count": summary.get("corpus_row_count"),
        "strict_governing_training_view_count": summary.get(
            "strict_governing_training_view_count"
        ),
        "release_ledger_blocked_count": summary.get("release_ledger_blocked_count"),
        "release_card_count": summary.get("release_card_count"),
        "top_blocker": blocker_rows[0].get("blocker") if blocker_rows else None,
    }


def _compact_release_grade_closure_queue_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    queue_rows = payload.get("queue_rows") or []
    return {
        "status": payload.get("status"),
        "release_grade_status": summary.get("release_grade_status"),
        "queue_length": summary.get("queue_length"),
        "ready_to_execute_count": summary.get("ready_to_execute_count"),
        "package_readiness_state": summary.get("package_readiness_state"),
        "strict_governing_training_view_count": summary.get(
            "strict_governing_training_view_count"
        ),
        "top_action": queue_rows[0].get("next_action") if queue_rows else None,
        "next_phase_backlog_path": summary.get("next_phase_backlog_path"),
    }


def _compact_release_runtime_maturity_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "runtime_surface": summary.get("runtime_surface"),
        "cohort_size": summary.get("cohort_size"),
        "resumed_run_processed_examples": summary.get("resumed_run_processed_examples"),
        "completion_ratio": summary.get("completion_ratio"),
        "checkpoint_resumes": summary.get("checkpoint_resumes"),
        "identity_safe_resume": summary.get("identity_safe_resume"),
        "runtime_maturity_state": summary.get("runtime_maturity_state"),
    }


def _compact_release_source_coverage_depth_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "total_accessions": summary.get("total_accessions"),
        "thin_coverage_count": summary.get("thin_coverage_count"),
        "thin_coverage_fraction": summary.get("thin_coverage_fraction"),
        "direct_live_smoke_count": summary.get("direct_live_smoke_count"),
        "probe_backed_count": summary.get("probe_backed_count"),
        "snapshot_backed_count": summary.get("snapshot_backed_count"),
        "coverage_depth_state": summary.get("coverage_depth_state"),
    }


def _compact_release_provenance_depth_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "ledger_entry_count": summary.get("ledger_entry_count"),
        "ledger_blocked_count": summary.get("ledger_blocked_count"),
        "ledger_blocked_fraction": summary.get("ledger_blocked_fraction"),
        "provenance_row_count": summary.get("provenance_row_count"),
        "release_card_count": summary.get("release_card_count"),
        "provenance_depth_state": summary.get("provenance_depth_state"),
    }


def _compact_release_grade_runbook_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    steps = payload.get("steps") or []
    return {
        "status": payload.get("status"),
        "release_grade_status": summary.get("release_grade_status"),
        "command_count": summary.get("command_count"),
        "queue_length": summary.get("queue_length"),
        "runtime_maturity_state": summary.get("runtime_maturity_state"),
        "coverage_depth_state": summary.get("coverage_depth_state"),
        "provenance_depth_state": summary.get("provenance_depth_state"),
        "step_ids": [row.get("step_id") for row in steps],
    }


def _compact_release_accession_closure_matrix_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    rows = payload.get("rows") or []
    return {
        "status": payload.get("status"),
        "accession_count": summary.get("accession_count"),
        "closest_to_release_count": summary.get("closest_to_release_count"),
        "preview_only_non_governing_count": summary.get("preview_only_non_governing_count"),
        "blocked_pending_acquisition_count": summary.get("blocked_pending_acquisition_count"),
        "top_accessions": [row.get("accession") for row in rows[:3]],
    }


def _compact_release_accession_action_queue_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    rows = payload.get("rows") or []
    return {
        "status": payload.get("status"),
        "action_row_count": summary.get("action_row_count"),
        "promotion_review_count": summary.get("promotion_review_count"),
        "support_only_hold_count": summary.get("support_only_hold_count"),
        "source_fix_followup_count": summary.get("source_fix_followup_count"),
        "top_priority_accessions": [row.get("accession") for row in rows[:3]],
    }


def _compact_release_promotion_gate_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "candidate_count": summary.get("candidate_count"),
        "promotion_gate_state": summary.get("promotion_gate_state"),
        "promotion_ready_now": summary.get("promotion_ready_now"),
        "top_candidate_accessions": summary.get("top_candidate_accessions"),
    }


def _compact_release_source_fix_followup_batch_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "batch_row_count": summary.get("batch_row_count"),
        "blocked_accession_count": summary.get("blocked_accession_count"),
        "shared_source_fix_ref_count": summary.get("shared_source_fix_ref_count"),
        "next_batch_state": summary.get("next_batch_state"),
    }


def _compact_release_candidate_promotion_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "candidate_count": summary.get("candidate_count"),
        "promotion_blocked": summary.get("promotion_blocked"),
        "top_candidate_accessions": summary.get("top_candidate_accessions"),
    }


def _compact_release_runtime_qualification_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    checks = payload.get("deterministic_checks") or {}
    return {
        "status": payload.get("status"),
        "dataset_generation_mode": summary.get("dataset_generation_mode"),
        "runtime_qualification_state": summary.get("runtime_qualification_state"),
        "qualification_complete": summary.get("qualification_complete"),
        "certification_scope": summary.get("certification_scope"),
        "cohort_size": summary.get("cohort_size"),
        "all_deterministic_checks_passed": all(bool(value) for value in checks.values())
        if checks
        else None,
    }


def _compact_release_governing_sufficiency_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "dataset_generation_mode": summary.get("dataset_generation_mode"),
        "governing_sufficiency_state": summary.get("governing_sufficiency_state"),
        "governing_sufficiency_complete": summary.get("governing_sufficiency_complete"),
        "strict_governing_allowed_count": summary.get("strict_governing_allowed_count"),
        "non_governing_by_design_count": summary.get("non_governing_by_design_count"),
        "deferred_to_v2_source_fix_count": summary.get("deferred_to_v2_source_fix_count"),
    }


def _compact_release_accession_evidence_pack_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    rows = payload.get("rows") or []
    return {
        "status": payload.get("status"),
        "dataset_generation_mode": summary.get("dataset_generation_mode"),
        "row_complete_count": summary.get("row_complete_count"),
        "strict_governing_row_count": summary.get("strict_governing_row_count"),
        "deferred_to_v2_count": summary.get("deferred_to_v2_count"),
        "top_accessions": [row.get("accession") for row in rows[:3]],
    }


def _compact_release_reporting_completeness_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "dataset_generation_mode": summary.get("dataset_generation_mode"),
        "reporting_completeness_state": summary.get("reporting_completeness_state"),
        "reporting_completeness_complete": summary.get("reporting_completeness_complete"),
        "row_complete_count": summary.get("row_complete_count"),
        "release_card_count": summary.get("release_card_count"),
    }


def _compact_release_blocker_resolution_board_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "dataset_generation_mode": summary.get("dataset_generation_mode"),
        "release_v1_bar_state": summary.get("release_v1_bar_state"),
        "resolved_release_blocker_count": summary.get("resolved_release_blocker_count"),
        "open_v1_blocker_count": summary.get("open_v1_blocker_count"),
        "deferred_to_v2_count": summary.get("deferred_to_v2_count"),
    }


def _compact_procurement_external_drive_mount_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "mount_state": summary.get("mount_state"),
        "authority_ready": summary.get("authority_ready"),
        "expected_external_root": summary.get("expected_external_root"),
        "free_bytes": summary.get("free_bytes"),
    }


def _compact_procurement_expansion_wave_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    rows = payload.get("rows") or []
    return {
        "status": payload.get("status"),
        "dataset_generation_mode": summary.get("dataset_generation_mode"),
        "external_drive_mount_state": summary.get("external_drive_mount_state"),
        "queue_length": summary.get("queue_length"),
        "ready_to_execute_count": summary.get("ready_to_execute_count"),
        "top_dataset_ids": [row.get("dataset_id") for row in rows[:3]],
    }


def _compact_procurement_expansion_storage_budget_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "external_drive_mount_state": summary.get("external_drive_mount_state"),
        "baseline_raw_bytes": summary.get("baseline_raw_bytes"),
        "known_additional_bytes": summary.get("known_additional_bytes"),
        "projected_v2_raw_bytes": summary.get("projected_v2_raw_bytes"),
        "projected_v2_plus_optional_qfo_bytes": summary.get(
            "projected_v2_plus_optional_qfo_bytes"
        ),
    }


def _compact_missing_scrape_family_contracts_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "dataset_generation_mode": summary.get("dataset_generation_mode"),
        "missing_lane_count": summary.get("missing_lane_count"),
        "contract_ready_count": summary.get("contract_ready_count"),
        "deferred_until_external_drive_count": summary.get(
            "deferred_until_external_drive_count"
        ),
        "lane_ids": summary.get("lane_ids"),
    }


def _compact_cohort_compiler_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "row_count": payload.get("row_count"),
        "candidate_universe_count": summary.get("candidate_universe_count"),
        "selected_count": summary.get("selected_count"),
        "blocked_full_packet_accession_count": len(
            summary.get("blocked_full_packet_accessions") or []
        ),
        "candidate_only_ligand_accession_count": len(
            summary.get("candidate_only_ligand_accessions") or []
        ),
        "split_assignment_ready": summary.get("split_assignment_ready"),
    }


def _compact_balance_diagnostics_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "selected_count": summary.get("selected_count"),
        "split_counts": summary.get("split_counts"),
        "bucket_counts": summary.get("bucket_counts"),
        "thin_coverage_count": summary.get("thin_coverage_count"),
        "mixed_evidence_count": summary.get("mixed_evidence_count"),
        "requested_modalities": summary.get("requested_modalities"),
    }


def _compact_package_readiness_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "readiness_state": payload.get("readiness_state"),
        "packet_count": summary.get("packet_count"),
        "judgment_counts": summary.get("judgment_counts"),
        "completeness_counts": summary.get("completeness_counts"),
        "fold_export_ready": summary.get("fold_export_ready"),
        "cv_fold_export_unlocked": summary.get("cv_fold_export_unlocked"),
        "final_split_committed": summary.get("final_split_committed"),
        "ready_for_package": summary.get("ready_for_package"),
        "blocked_reasons": summary.get("blocked_reasons"),
    }


def _compact_training_set_builder_session_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "session_state": summary.get("session_state"),
        "selected_count": summary.get("selected_count"),
        "package_ready": summary.get("package_ready"),
        "blocked_reasons": summary.get("blocked_reasons"),
        "recommended_cli_commands": payload.get("recommended_cli_commands"),
    }


def _compact_training_set_builder_runbook_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "selected_count": summary.get("selected_count"),
        "package_ready": summary.get("package_ready"),
        "blocked_reasons": summary.get("blocked_reasons"),
        "command_count": summary.get("command_count"),
        "session_state": summary.get("session_state"),
        "step_ids": [row.get("step_id") for row in payload.get("steps") or []],
    }


def _compact_external_dataset_intake_contract_preview(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "accepted_shape_ids": [row.get("shape_id") for row in payload.get("accepted_shapes") or []],
        "secondary_shape_ids": [
            row.get("shape_id") for row in payload.get("secondary_shapes") or []
        ],
        "verdict_vocabulary": payload.get("verdict_vocabulary") or [],
    }


def _compact_external_dataset_assessment_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "overall_verdict": summary.get("overall_verdict"),
        "missing_mapping_accession_count": summary.get("missing_mapping_accession_count"),
        "candidate_only_accession_count": summary.get("candidate_only_accession_count"),
        "measured_accession_count": summary.get("measured_accession_count"),
        "seed_structure_overlap_accession_count": summary.get(
            "seed_structure_overlap_accession_count"
        ),
        "sub_audits": payload.get("sub_audits"),
    }


def _compact_sample_external_dataset_assessment_bundle_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "sample_manifest_count": summary.get("sample_manifest_count"),
        "sample_manifest_row_count": summary.get("sample_manifest_row_count"),
        "assessment_overall_verdict": summary.get("assessment_overall_verdict"),
        "sub_audit_verdicts": summary.get("sub_audit_verdicts"),
    }


def _compact_binding_measurement_suspect_rows_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "suspect_row_count": summary.get("suspect_row_count"),
        "suspect_accession_count": summary.get("suspect_accession_count"),
        "measurement_origin_counts": summary.get("measurement_origin_counts"),
        "top_suspect_accessions": summary.get("top_suspect_accessions"),
    }


def _compact_cross_source_duplicate_measurement_audit_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "registry_row_count": summary.get("registry_row_count"),
        "cross_source_duplicate_group_count": summary.get("cross_source_duplicate_group_count"),
        "top_source_pair_counts": summary.get("top_source_pair_counts"),
        "top_source_presence_counts": summary.get("top_source_presence_counts"),
    }


def _compact_training_set_candidate_package_manifest_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "manifest_status": payload.get("manifest_status"),
        "selected_count": summary.get("selected_count"),
        "package_ready": summary.get("package_ready"),
        "package_role_counts": summary.get("package_role_counts"),
        "blocked_reasons": summary.get("blocked_reasons"),
    }


def _compact_procurement_process_diagnostics_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    comparison = payload.get("comparison") or {}
    return {
        "status": payload.get("status"),
        "authoritative_tail_file_count": summary.get("authoritative_tail_file_count"),
        "authoritative_source_counts": summary.get("authoritative_source_counts"),
        "raw_process_table_active_count": summary.get("raw_process_table_active_count"),
        "raw_process_table_duplicate_count": summary.get("raw_process_table_duplicate_count"),
        "raw_process_excess": comparison.get("raw_process_excess"),
    }


def _compact_procurement_supervisor_freshness_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "freshness_state": summary.get("freshness_state"),
        "board_active_observed_download_count": summary.get("board_active_observed_download_count"),
        "supervisor_state_status": summary.get("supervisor_state_status"),
        "supervisor_state_pending_count": summary.get("supervisor_state_pending_count"),
        "supervisor_heartbeat_fresh": summary.get("supervisor_heartbeat_fresh"),
        "stale_state_superseded_by_board": summary.get("stale_state_superseded_by_board"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_tail_signal_reconciliation_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "reconciliation_state": summary.get("reconciliation_state"),
        "authoritative_tail_file_count": summary.get("authoritative_tail_file_count"),
        "board_active_observed_download_count": summary.get("board_active_observed_download_count"),
        "remaining_transfer_active_file_count": summary.get("remaining_transfer_active_file_count"),
        "diagnostics_authoritative_tail_file_count": summary.get(
            "diagnostics_authoritative_tail_file_count"
        ),
        "raw_process_table_active_count": summary.get("raw_process_table_active_count"),
        "stale_supervisor_status": summary.get("stale_supervisor_status"),
        "stale_supervisor_pending_count": summary.get("stale_supervisor_pending_count"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_tail_growth_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "growth_state": summary.get("growth_state"),
        "active_tail_file_count": summary.get("active_tail_file_count"),
        "sampled_tail_file_count": summary.get("sampled_tail_file_count"),
        "positive_growth_file_count": summary.get("positive_growth_file_count"),
        "stalled_file_count": summary.get("stalled_file_count"),
        "sample_window_seconds": summary.get("sample_window_seconds"),
        "total_delta_bytes": summary.get("total_delta_bytes"),
        "aggregate_bytes_per_second": summary.get("aggregate_bytes_per_second"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_headroom_guard_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "guard_state": summary.get("guard_state"),
        "free_bytes": summary.get("free_bytes"),
        "free_gib": summary.get("free_gib"),
        "active_tail_file_count": summary.get("active_tail_file_count"),
        "active_tail_bytes": summary.get("active_tail_bytes"),
        "recent_growth_bytes_per_second": summary.get("recent_growth_bytes_per_second"),
        "estimated_hours_to_zero_free_at_recent_rate": summary.get(
            "estimated_hours_to_zero_free_at_recent_rate"
        ),
        "free_to_active_tail_ratio": summary.get("free_to_active_tail_ratio"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_tail_space_drift_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "drift_state": summary.get("drift_state"),
        "sampled_tail_file_count": summary.get("sampled_tail_file_count"),
        "free_delta_bytes": summary.get("free_delta_bytes"),
        "total_tail_delta_bytes": summary.get("total_tail_delta_bytes"),
        "net_space_gap_bytes": summary.get("net_space_gap_bytes"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_tail_source_pressure_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "pressure_state": summary.get("pressure_state"),
        "source_count": summary.get("source_count"),
        "dominant_source_id": summary.get("dominant_source_id"),
        "dominant_source_name": summary.get("dominant_source_name"),
        "dominant_source_byte_share": summary.get("dominant_source_byte_share"),
        "dominant_source_growth_share": summary.get("dominant_source_growth_share"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_tail_log_progress_registry_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "registry_state": summary.get("registry_state"),
        "tail_row_count": summary.get("tail_row_count"),
        "parsed_row_count": summary.get("parsed_row_count"),
        "exact_total_count": summary.get("exact_total_count"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_tail_completion_margin_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "completion_state": summary.get("completion_state"),
        "parsed_total_count": summary.get("parsed_total_count"),
        "free_gib": summary.get("free_gib"),
        "total_remaining_gib": summary.get("total_remaining_gib"),
        "projected_free_after_completion_gib": summary.get("projected_free_after_completion_gib"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_space_recovery_target_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "target_state": summary.get("target_state"),
        "reclaim_to_zero_gib": summary.get("reclaim_to_zero_gib"),
        "reclaim_to_10_gib_buffer_gib": summary.get("reclaim_to_10_gib_buffer_gib"),
        "reclaim_to_20_gib_buffer_gib": summary.get("reclaim_to_20_gib_buffer_gib"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_space_recovery_candidates_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "recovery_state": summary.get("recovery_state"),
        "ranked_candidate_count": summary.get("ranked_candidate_count"),
        "duplicate_first_candidate_count": summary.get("duplicate_first_candidate_count"),
        "total_ranked_reclaim_gib": summary.get("total_ranked_reclaim_gib"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_space_recovery_execution_batch_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "execution_state": summary.get("execution_state"),
        "zero_gap_batch_meets_target": summary.get("zero_gap_batch_meets_target"),
        "buffer_10_gib_batch_meets_target": summary.get("buffer_10_gib_batch_meets_target"),
        "buffer_20_gib_batch_meets_target": summary.get("buffer_20_gib_batch_meets_target"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_space_recovery_safety_register_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "safety_state": summary.get("safety_state"),
        "duplicate_first_category_count": summary.get("duplicate_first_category_count"),
        "review_required_category_count": summary.get("review_required_category_count"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_tail_fill_risk_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "risk_state": summary.get("risk_state"),
        "estimated_hours_to_zero_free": summary.get("estimated_hours_to_zero_free"),
        "slowest_completion_hours": summary.get("slowest_completion_hours"),
        "cushion_hours": summary.get("cushion_hours"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_space_recovery_trigger_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "trigger_state": summary.get("trigger_state"),
        "risk_state": summary.get("risk_state"),
        "execution_state": summary.get("execution_state"),
        "zero_gap_batch_meets_target": summary.get("zero_gap_batch_meets_target"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_space_recovery_gap_drift_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "drift_state": summary.get("drift_state"),
        "current_zero_gap_shortfall_gib": summary.get("current_zero_gap_shortfall_gib"),
        "gap_delta_gib": summary.get("gap_delta_gib"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_recovery_intervention_priority_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "priority_state": summary.get("priority_state"),
        "risk_state": summary.get("risk_state"),
        "trigger_state": summary.get("trigger_state"),
        "safety_state": summary.get("safety_state"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_space_recovery_coverage_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "coverage_state": summary.get("coverage_state"),
        "zero_gap_coverage_fraction": summary.get("zero_gap_coverage_fraction"),
        "zero_gap_shortfall_gib": summary.get("zero_gap_shortfall_gib"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_recovery_escalation_lane_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "escalation_state": summary.get("escalation_state"),
        "zero_gap_shortfall_gib": summary.get("zero_gap_shortfall_gib"),
        "additional_ranked_reclaim_gib": summary.get("additional_ranked_reclaim_gib"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_space_recovery_concentration_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "concentration_state": summary.get("concentration_state"),
        "top1_reclaim_fraction": summary.get("top1_reclaim_fraction"),
        "top3_reclaim_fraction": summary.get("top3_reclaim_fraction"),
        "lead_candidate_filename": summary.get("lead_candidate_filename"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_recovery_shortfall_bridge_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "bridge_state": summary.get("bridge_state"),
        "zero_gap_shortfall_gib": summary.get("zero_gap_shortfall_gib"),
        "review_required_category_count": summary.get("review_required_category_count"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_recovery_lane_fragility_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "fragility_state": summary.get("fragility_state"),
        "lead_candidate_filename": summary.get("lead_candidate_filename"),
        "lead_candidate_reclaim_gib": summary.get("lead_candidate_reclaim_gib"),
        "residual_vs_shortfall_fraction": summary.get("residual_vs_shortfall_fraction"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_procurement_broader_search_trigger_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "trigger_state": summary.get("trigger_state"),
        "risk_state": summary.get("risk_state"),
        "bridge_state": summary.get("bridge_state"),
        "cushion_hours": summary.get("cushion_hours"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_split_simulation_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    truth_boundary = payload.get("truth_boundary") or {}
    return {
        "status": payload.get("status"),
        "label_count": summary.get("label_count"),
        "split_counts": summary.get("split_counts"),
        "dry_run_validation_status": summary.get("dry_run_validation_status"),
        "fold_export_gate_status": summary.get("fold_export_gate_status"),
        "post_staging_gate_status": summary.get("post_staging_gate_status"),
        "package_ready": summary.get("package_ready"),
        "package_blocking_factors": summary.get("package_blocking_factors"),
        "final_split_committed": truth_boundary.get("final_split_committed"),
    }


def _compact_training_set_remediation_plan_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    issue_bucket_counts = summary.get("issue_bucket_counts") or {}
    top_issue_bucket = summary.get("top_issue_bucket")
    if top_issue_bucket is None and issue_bucket_counts:
        top_issue_bucket = max(
            issue_bucket_counts.items(),
            key=lambda item: (item[1], item[0]),
        )[0]
    return {
        "status": payload.get("status"),
        "row_count": payload.get("row_count") or summary.get("selected_count"),
        "blocked_accession_count": summary.get("blocked_accession_count")
        or summary.get("blocked_count"),
        "candidate_only_accession_count": summary.get("candidate_only_accession_count")
        or summary.get("candidate_only_count"),
        "top_issue_bucket": top_issue_bucket,
        "top_source_fix_refs": summary.get("top_source_fix_refs"),
    }


def _compact_cohort_inclusion_rationale_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    rows = payload.get("rows") or []
    return {
        "status": payload.get("status", "report_only"),
        "row_count": payload.get("row_count") or len(rows),
        "gated_count": summary.get("gated_count"),
        "preview_only_count": summary.get("preview_only_count"),
        "governing_ready_count": summary.get("governing_ready_count"),
        "top_inclusion_reason": summary.get("top_inclusion_reason"),
    }


def _compact_training_set_unblock_plan_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "impacted_accession_count": summary.get("impacted_accession_count"),
        "blocked_reason_count": summary.get("blocked_reason_count"),
        "top_blocked_reasons": summary.get("top_blocked_reasons"),
        "top_source_fix_refs": summary.get("top_source_fix_refs"),
    }


def _compact_training_set_gating_evidence_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "row_count": summary.get("selected_count"),
        "gated_count": summary.get("gated_count"),
        "preview_only_count": summary.get("preview_only_count"),
        "package_ready": summary.get("package_ready"),
        "top_package_blockers": summary.get("top_package_blockers"),
        "top_next_action_refs": summary.get("top_next_action_refs"),
    }


def _compact_training_set_action_queue_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_accession_count"),
        "queue_length": summary.get("queue_length"),
        "impacted_accession_count": summary.get("impacted_accession_count"),
        "package_ready": summary.get("package_ready"),
        "priority_bucket_counts": summary.get("priority_bucket_counts"),
        "top_action_refs": summary.get("top_action_refs"),
    }


def _compact_training_set_blocker_burndown_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_accession_count"),
        "blocked_accession_count": summary.get("blocked_accession_count"),
        "critical_action_count": summary.get("critical_action_count"),
        "package_ready": summary.get("package_ready"),
        "assignment_ready": summary.get("assignment_ready"),
        "top_blocker_categories": summary.get("top_blocker_categories"),
        "remediation_progression_summary": summary.get("remediation_progression_summary"),
    }


def _compact_training_set_modality_gap_register_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_accession_count"),
        "blocked_modality_count": summary.get("blocked_modality_count"),
        "package_ready": summary.get("package_ready"),
        "gap_category_counts": summary.get("gap_category_counts"),
        "top_gap_modalities": summary.get("top_gap_modalities"),
        "top_gap_accessions": summary.get("top_gap_accessions"),
    }


def _compact_training_set_package_blocker_matrix_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_accession_count"),
        "blocked_accession_count": summary.get("blocked_accession_count"),
        "fold_export_blocked_count": summary.get("fold_export_blocked_count"),
        "modality_blocked_count": summary.get("modality_blocked_count"),
        "package_ready": summary.get("package_ready"),
        "blocked_reason_counts": summary.get("blocked_reason_counts"),
        "top_blocking_reasons": summary.get("top_blocking_reasons"),
        "top_blocked_accessions": summary.get("top_blocked_accessions"),
    }


def _compact_training_set_gate_ladder_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_count"),
        "assignment_ready": summary.get("assignment_ready"),
        "fold_export_ready": summary.get("fold_export_ready"),
        "cv_fold_export_unlocked": summary.get("cv_fold_export_unlocked"),
        "package_ready": summary.get("package_ready"),
        "gate_ladder_status": summary.get("gate_ladder_status"),
        "top_blocking_reasons": summary.get("top_blocking_reasons"),
        "consistency_alert_count": len(summary.get("consistency_alerts") or []),
    }


def _compact_training_set_unlock_route_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_count"),
        "current_route_state": summary.get("current_route_state")
        or summary.get("current_unlock_state"),
        "current_stage": summary.get("current_stage") or summary.get("next_unlock_stage"),
        "blocked_route_count": summary.get("blocked_route_count")
        or summary.get("blocking_gate_count"),
        "source_fix_route_count": summary.get("source_fix_route_count"),
        "next_transition": summary.get("next_transition") or summary.get("next_unlock_stage"),
        "route_step_count": summary.get("route_step_count")
        or summary.get("unlock_route_stage_count"),
    }


def _compact_training_set_transition_contract_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_count"),
        "current_transition_state": summary.get("current_transition_state"),
        "next_transition_contract": summary.get("next_transition_contract"),
        "transition_step_count": summary.get("transition_step_count"),
        "source_fix_transition_pending_count": summary.get("source_fix_transition_pending_count"),
        "package_transition_blocked_count": summary.get("package_transition_blocked_count"),
        "package_transition_ready_count": summary.get("package_transition_ready_count"),
    }


def _compact_training_set_source_fix_batch_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_count"),
        "source_fix_batch_row_count": summary.get("source_fix_batch_row_count"),
        "current_batch_state": summary.get("current_batch_state"),
        "next_source_fix_batch": summary.get("next_source_fix_batch"),
        "shared_source_fix_ref_count": summary.get("shared_source_fix_ref_count"),
        "blocked_pending_acquisition_count": summary.get("blocked_pending_acquisition_count"),
    }


def _compact_training_set_package_transition_batch_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_count"),
        "package_transition_batch_row_count": summary.get("package_transition_batch_row_count"),
        "current_batch_state": summary.get("current_batch_state"),
        "next_package_batch": summary.get("next_package_batch"),
        "preview_visible_package_count": summary.get("preview_visible_package_count"),
        "governing_ready_package_count": summary.get("governing_ready_package_count"),
        "fold_export_blocked_count": summary.get("fold_export_blocked_count"),
    }


def _compact_training_set_package_execution_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_count"),
        "package_execution_row_count": summary.get("package_execution_row_count"),
        "current_execution_state": summary.get("current_execution_state"),
        "next_execution_lane": summary.get("next_execution_lane"),
        "preview_hold_count": summary.get("preview_hold_count"),
        "unlock_follow_up_count": summary.get("unlock_follow_up_count"),
    }


def _compact_training_set_preview_hold_register_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_count"),
        "preview_hold_row_count": summary.get("preview_hold_row_count"),
        "current_hold_state": summary.get("current_hold_state"),
        "next_hold_lane": summary.get("next_hold_lane"),
        "support_only_hold_count": summary.get("support_only_hold_count"),
        "non_governing_hold_count": summary.get("non_governing_hold_count"),
    }


def _compact_training_set_preview_hold_exit_criteria_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_count"),
        "exit_criteria_row_count": summary.get("exit_criteria_row_count"),
        "current_exit_state": summary.get("current_exit_state"),
        "package_gate_blocked_count": summary.get("package_gate_blocked_count"),
        "packet_and_modality_blocked_count": summary.get("packet_and_modality_blocked_count"),
    }


def _compact_training_set_preview_hold_clearance_batch_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "selected_accession_count": summary.get("selected_count"),
        "clearance_batch_row_count": summary.get("clearance_batch_row_count"),
        "current_batch_state": summary.get("current_batch_state"),
        "package_gate_recheck_count": summary.get("package_gate_recheck_count"),
        "packet_modality_recheck_count": summary.get("packet_modality_recheck_count"),
    }


def _compact_external_dataset_flaw_taxonomy_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "overall_verdict": summary.get("overall_verdict"),
        "blocked_accession_count": summary.get("blocked_accession_count"),
        "lint_failures_present": summary.get("lint_failures_present"),
        "top_blocking_categories": summary.get("top_blocking_categories"),
        "category_counts": summary.get("category_counts"),
    }


def _compact_external_dataset_risk_register_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "overall_verdict": summary.get("overall_verdict"),
        "blocked_gate_count": summary.get("blocked_gate_count"),
        "patent_or_provenance_risk_present": summary.get("patent_or_provenance_risk_present"),
        "mapping_risk_present": summary.get("mapping_risk_present"),
        "highest_risk_categories": summary.get("highest_risk_categories"),
        "top_risk_row_count": summary.get("top_risk_row_count"),
    }


def _compact_external_dataset_conflict_register_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "overall_verdict": summary.get("overall_verdict"),
        "conflict_category_counts": summary.get("conflict_category_counts"),
        "top_conflict_categories": summary.get("top_conflict_categories"),
        "mapping_conflict_present": summary.get("mapping_conflict_present"),
        "provenance_conflict_present": summary.get("provenance_conflict_present"),
        "top_conflict_row_count": summary.get("top_conflict_row_count"),
    }


def _compact_external_dataset_admission_decision_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "overall_decision": summary.get("overall_decision"),
        "overall_verdict": summary.get("overall_verdict"),
        "blocking_gate_count": summary.get("blocking_gate_count"),
        "decision_reasons": summary.get("decision_reasons"),
        "top_required_remediations": summary.get("top_required_remediations"),
        "advisory_only": summary.get("advisory_only"),
    }


def _compact_external_dataset_clearance_delta_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "current_clearance_state": summary.get("current_clearance_state"),
        "current_clearance_verdict": summary.get("current_clearance_verdict"),
        "blocking_gate_count": summary.get("blocking_gate_count"),
        "required_change_count": summary.get("required_change_count"),
        "required_changes": summary.get("required_changes"),
        "advisory_only": summary.get("advisory_only"),
    }


def _compact_external_dataset_acceptance_path_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "current_path_state": summary.get("current_path_state"),
        "current_path_verdict": summary.get("current_path_verdict")
        or summary.get("overall_verdict"),
        "current_stage": summary.get("current_stage") or summary.get("next_acceptance_stage"),
        "blocking_transition_count": summary.get("blocking_transition_count")
        or summary.get("blocking_gate_count"),
        "blocked_accession_count": summary.get("blocked_accession_count"),
        "next_transition": summary.get("next_transition") or summary.get("next_acceptance_stage"),
    }


def _compact_external_dataset_remediation_readiness_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "current_readiness_state": summary.get("current_readiness_state"),
        "next_ready_batch": summary.get("next_ready_batch"),
        "readiness_step_count": summary.get("readiness_step_count"),
        "blocked_pending_acquisition_count": summary.get("blocked_pending_acquisition_count"),
        "advisory_follow_up_count": summary.get("advisory_follow_up_count"),
        "executable_now_count": summary.get("executable_now_count"),
    }


def _compact_external_dataset_caveat_execution_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "caveat_execution_row_count": summary.get("caveat_execution_row_count"),
        "current_execution_state": summary.get("current_execution_state"),
        "next_execution_batch": summary.get("next_execution_batch"),
        "structure_sensitive_follow_up_count": summary.get("structure_sensitive_follow_up_count"),
        "binding_follow_up_count": summary.get("binding_follow_up_count"),
        "provenance_follow_up_count": summary.get("provenance_follow_up_count"),
    }


def _compact_external_dataset_blocked_acquisition_batch_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "blocked_acquisition_row_count": summary.get("blocked_acquisition_row_count"),
        "current_batch_state": summary.get("current_batch_state"),
        "next_blocked_batch": summary.get("next_blocked_batch"),
        "p0_blocker_count": summary.get("p0_blocker_count"),
        "blocked_gate_count": summary.get("blocked_gate_count"),
    }


def _compact_external_dataset_acquisition_unblock_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "acquisition_unblock_row_count": summary.get("acquisition_unblock_row_count"),
        "current_unblock_state": summary.get("current_unblock_state"),
        "next_unblock_batch": summary.get("next_unblock_batch"),
        "acquisition_follow_up_count": summary.get("acquisition_follow_up_count"),
        "mapping_follow_up_count": summary.get("mapping_follow_up_count"),
    }


def _compact_external_dataset_advisory_followup_register_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "advisory_followup_row_count": summary.get("advisory_followup_row_count"),
        "current_followup_state": summary.get("current_followup_state"),
        "next_followup_lane": summary.get("next_followup_lane"),
        "structure_alignment_followup_count": summary.get("structure_alignment_followup_count"),
        "binding_provenance_followup_count": summary.get("binding_provenance_followup_count"),
    }


def _compact_external_dataset_caveat_exit_criteria_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "caveat_exit_row_count": summary.get("caveat_exit_row_count"),
        "current_exit_state": summary.get("current_exit_state"),
        "structure_alignment_exit_count": summary.get("structure_alignment_exit_count"),
        "binding_provenance_exit_count": summary.get("binding_provenance_exit_count"),
    }


def _compact_external_dataset_caveat_review_batch_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "review_batch_row_count": summary.get("review_batch_row_count"),
        "current_batch_state": summary.get("current_batch_state"),
        "structure_alignment_review_count": summary.get("structure_alignment_review_count"),
        "binding_provenance_review_count": summary.get("binding_provenance_review_count"),
    }


def _compact_sub_audit_preview(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "verdict": payload.get("verdict"),
        "summary": payload.get("summary"),
    }


def _compact_scrape_gap_matrix_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "row_count": payload.get("row_count"),
        "status_counts": summary.get("status_counts"),
        "gate_status": summary.get("gate_status"),
        "remaining_gap_file_count": summary.get("remaining_gap_file_count"),
        "tail_blocked_lanes": summary.get("tail_blocked_lanes"),
    }


def _compact_overnight_queue_backlog_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "pending_task_count": summary.get("pending_task_count"),
        "selected_top_count": summary.get("selected_top_count"),
        "lane_counts": summary.get("lane_counts"),
        "top_task_ids": [row.get("task_id") for row in (payload.get("rows") or [])[:10]],
    }


def _compact_overnight_execution_contract_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "top_level_driver": summary.get("top_level_driver"),
        "poll_seconds": summary.get("poll_seconds"),
        "full_sweep_every": summary.get("full_sweep_every"),
        "target_hours": summary.get("target_hours"),
        "estimated_cycles": summary.get("estimated_cycles"),
        "active_worker_count_snapshot": summary.get("active_worker_count_snapshot"),
        "procurement_handoff_required": summary.get("procurement_handoff_required"),
        "pause_conditions": payload.get("pause_conditions"),
    }


def _compact_overnight_queue_repair_status(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "recovery_state": payload.get("recovery_state"),
        "repaired_stale_dispatch_count": summary.get("repaired_stale_dispatch_count"),
        "recovered_and_redispatched_count": summary.get("recovered_and_redispatched_count"),
        "recovered_and_idle_count": summary.get("recovered_and_idle_count"),
        "current_stale_dispatch_count": summary.get("current_stale_dispatch_count"),
        "missing_dispatch_manifest_count": summary.get("missing_dispatch_manifest_count"),
    }


def _compact_overnight_idle_status_preview(payload: dict[str, Any]) -> dict[str, Any]:
    queue_summary = payload.get("queue_summary") or {}
    tail_awareness = payload.get("procurement_tail_awareness") or {}
    return {
        "status": payload.get("status"),
        "idle_state": payload.get("idle_state"),
        "ready_count": queue_summary.get("ready_count"),
        "pending_count": queue_summary.get("pending_count"),
        "blocked_count": queue_summary.get("blocked_count"),
        "active_worker_count": queue_summary.get("active_worker_count"),
        "queue_is_drained": queue_summary.get("queue_is_drained"),
        "active_download_count": tail_awareness.get("active_download_count"),
        "tail_state": tail_awareness.get("tail_state"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_overnight_wave_advance_preview(payload: dict[str, Any]) -> dict[str, Any]:
    monitor_summary = payload.get("monitor_summary") or {}
    return {
        "status": payload.get("status"),
        "added_task_count": payload.get("added_task_count"),
        "dispatched_count": payload.get("dispatched_count"),
        "active_worker_count": payload.get("active_worker_count"),
        "catalog_exhausted": payload.get("catalog_exhausted"),
        "pre_queue_total": payload.get("pre_queue_total"),
        "post_queue_total": payload.get("post_queue_total"),
        "execution_order": payload.get("execution_order"),
        "monitor_alert_count": len(monitor_summary.get("alerts") or []),
    }


def _compact_overnight_pending_reconciliation_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "reconciliation_state": summary.get("reconciliation_state"),
        "queue_file_pending_count": summary.get("queue_file_pending_count"),
        "monitor_pending_count": summary.get("monitor_pending_count"),
        "idle_preview_pending_count": summary.get("idle_preview_pending_count"),
        "stale_preview_detected": summary.get("stale_preview_detected"),
        "queue_monitor_pending_drift": summary.get("queue_monitor_pending_drift"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_overnight_worker_launch_gap_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "launch_gap_state": summary.get("launch_gap_state"),
        "launch_gap_detected": summary.get("launch_gap_detected"),
        "launchable_backlog_count": summary.get("launchable_backlog_count"),
        "launch_gap_count": summary.get("launch_gap_count"),
        "queue_file_pending_count": summary.get("queue_file_pending_count"),
        "active_worker_count": summary.get("active_worker_count"),
        "supervisor_heartbeat_fresh": summary.get("supervisor_heartbeat_fresh"),
        "stale_runtime_signal_present": summary.get("stale_runtime_signal_present"),
        "next_suggested_action": payload.get("next_suggested_action"),
    }


def _compact_scrape_execution_wave_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "structured_job_count": summary.get("structured_job_count"),
        "page_job_count": summary.get("page_job_count"),
        "captured_page_job_count": summary.get("captured_page_job_count"),
        "tail_blocked_job_count": summary.get("tail_blocked_job_count"),
        "executed_structured_job_count": summary.get("executed_structured_job_count"),
        "failed_structured_job_count": summary.get("failed_structured_job_count"),
        "top_structured_job_ids": summary.get("top_structured_job_ids"),
        "top_page_accessions": summary.get("top_page_accessions"),
        "tail_blocked_job_ids": summary.get("tail_blocked_job_ids"),
        "active_download_count": summary.get("active_download_count"),
        "page_scraping_started": summary.get("page_scraping_started"),
        "payload_capture_started": summary.get("payload_capture_started"),
    }


def _compact_download_location_audit_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "wanted_file_count": summary.get("wanted_file_count"),
        "downloaded_count": summary.get("downloaded_count"),
        "in_process_count": summary.get("in_process_count"),
        "missing_count": summary.get("missing_count"),
        "all_wanted_files_accounted_for": summary.get("all_wanted_files_accounted_for"),
    }


def _compact_procurement_stale_part_audit_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "in_process_row_count": summary.get("in_process_row_count"),
        "live_transfer_count": summary.get("live_transfer_count"),
        "stale_residue_count": summary.get("stale_residue_count"),
        "review_count": summary.get("review_count"),
    }


def _compact_training_packet_completeness_matrix_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "selected_accession_count": summary.get("selected_accession_count"),
        "packet_lane_counts": summary.get("packet_lane_counts"),
        "missing_modality_counts": summary.get("missing_modality_counts"),
    }


def _compact_training_split_alignment_recheck_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "selected_accession_count": summary.get("selected_accession_count"),
        "matched_accession_count": summary.get("matched_accession_count"),
        "mismatch_count": summary.get("mismatch_count"),
        "expected_8_2_2_layout": summary.get("expected_8_2_2_layout"),
        "package_ready": summary.get("package_ready"),
    }


def _compact_training_packet_materialization_queue_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "selected_accession_count": summary.get("selected_accession_count"),
        "packet_lane_counts": summary.get("packet_lane_counts"),
        "stub_root": summary.get("stub_root"),
    }


def _compact_external_dataset_remediation_template_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "overall_verdict": summary.get("overall_verdict"),
        "template_row_count": summary.get("template_row_count"),
    }


def _compact_external_dataset_resolution_diff_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "claimed_accession_count": summary.get("claimed_accession_count"),
        "resolved_accession_count": summary.get("resolved_accession_count"),
        "unresolved_or_blocked_count": summary.get("unresolved_or_blocked_count"),
        "conflicted_accession_count": summary.get("conflicted_accession_count"),
    }


def _compact_external_dataset_fixture_catalog_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "fixture_count": summary.get("fixture_count"),
        "fixture_types": summary.get("fixture_types"),
    }


def _compact_post_tail_unlock_dry_run_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "live_downloads_complete": summary.get("live_downloads_complete"),
        "ready_step_count": summary.get("ready_step_count"),
        "blocked_step_count": summary.get("blocked_step_count"),
    }


def _compact_scrape_backlog_remaining_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "implemented_and_harvestable_now_count": summary.get(
            "implemented_and_harvestable_now_count"
        ),
        "preview_or_report_only_count": summary.get("preview_or_report_only_count"),
        "still_missing_count": summary.get("still_missing_count"),
        "tail_blocked_family_count": summary.get("tail_blocked_family_count"),
        "page_scrape_ready_count": summary.get("page_scrape_ready_count"),
        "next_priority_job_count": summary.get("next_priority_job_count"),
        "structured_first_policy": summary.get("structured_first_policy"),
    }


def _compact_external_dataset_issue_matrix_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "row_count": payload.get("row_count") or summary.get("issue_row_count"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "top_issue_category": summary.get("top_issue_category")
        or max(
            (summary.get("issue_category_counts") or {"unknown": 0}).items(),
            key=lambda item: (item[1], item[0]),
        )[0],
        "top_verdict": summary.get("top_verdict") or summary.get("overall_verdict"),
        "issue_category_counts": summary.get("issue_category_counts"),
    }


def _compact_external_dataset_manifest_lint_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "accepted_shape_count": summary.get("accepted_shape_count"),
        "linted_shape_count": summary.get("linted_shape_count"),
        "overall_verdict": summary.get("overall_verdict"),
        "missing_required_field_count": summary.get("missing_required_field_count"),
    }


def _compact_external_dataset_acceptance_gate_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "overall_verdict": summary.get("overall_verdict"),
        "blocked_gate_count": summary.get("blocked_gate_count"),
        "usable_with_caveats_gate_count": summary.get("usable_with_caveats_gate_count"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
    }


def _compact_external_dataset_resolution_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "accession_row_count": summary.get("accession_row_count"),
        "overall_resolution_verdict": summary.get("overall_resolution_verdict"),
        "blocked_accession_count": summary.get("blocked_accession_count"),
        "caveated_accession_count": summary.get("caveated_accession_count"),
        "mapping_incomplete_accession_count": summary.get("mapping_incomplete_accession_count"),
        "top_blocking_gates": summary.get("top_blocking_gates"),
    }


def _compact_external_dataset_remediation_queue_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status", "report_only"),
        "dataset_accession_count": summary.get("dataset_accession_count"),
        "queue_length": summary.get("remediation_queue_row_count"),
        "blocked_accession_count": summary.get("blocked_accession_count"),
        "overall_queue_verdict": summary.get("overall_queue_verdict"),
        "priority_bucket_counts": summary.get("priority_bucket_counts"),
        "top_blocking_gates": summary.get("top_blocking_gates"),
    }


def _compact_interaction_string_merge_impact_preview(payload: dict[str, Any]) -> dict[str, Any]:
    current_state = payload.get("current_state") or {}
    merge_impact = payload.get("merge_impact") or {}
    return {
        "status": payload.get("status"),
        "preview_row_count": current_state.get("preview_row_count"),
        "candidate_only_row_count": current_state.get("candidate_only_row_count"),
        "string_surface_state": current_state.get("string_surface_state"),
        "procurement_gate_status": current_state.get("procurement_gate_status"),
        "remaining_gap_file_count": current_state.get("remaining_gap_file_count"),
        "merge_changes_split_or_leakage": merge_impact.get("merge_changes_split_or_leakage"),
        "bundle_safe_immediately": merge_impact.get("bundle_safe_immediately"),
        "procurement_tail_completion_required": merge_impact.get(
            "procurement_tail_completion_required"
        ),
    }


def _compact_compact_enrichment_policy_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "policy_counts": summary["policy_counts"],
        "bundle_included_families": summary["bundle_included_families"],
        "report_only_families": summary["report_only_families"],
        "allowed_policy_labels": payload.get("allowed_policy_labels", []),
    }


def _compact_scrape_readiness_registry_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "top_scrape_targets": summary.get("top_scrape_targets", []),
        "default_ingest_statuses": summary.get("default_ingest_statuses", {}),
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_procurement_source_completion_preview(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "string_completion_status": payload.get("string_completion_status"),
        "uniprot_completion_status": payload.get("uniprot_completion_status"),
        "source_completion_count": len(payload.get("source_completion") or []),
        "report_only": (payload.get("truth_boundary") or {}).get("report_only"),
    }


def _compact_seed_plus_neighbors_structured_corpus_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "row_count": summary.get("row_count"),
        "seed_accession_count": summary.get("seed_accession_count"),
        "one_hop_neighbor_accession_count": summary.get("one_hop_neighbor_accession_count"),
        "row_family_counts": summary.get("row_family_counts", {}),
        "governing_status_counts": summary.get("governing_status_counts", {}),
        "report_only": (payload.get("truth_boundary") or {}).get("report_only"),
    }


def _compact_training_set_baseline_sidecar_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "example_count": summary.get("example_count"),
        "governing_ready_example_count": summary.get("governing_ready_example_count"),
        "blocked_pending_acquisition_example_count": summary.get(
            "blocked_pending_acquisition_example_count"
        ),
        "report_only": (payload.get("truth_boundary") or {}).get("report_only"),
    }


def _compact_training_set_multimodal_sidecar_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "example_count": summary.get("example_count"),
        "issue_count": summary.get("issue_count"),
        "canonical_record_count": summary.get("canonical_record_count"),
        "corpus_row_count": summary.get("corpus_row_count"),
        "strict_governing_training_view_count": summary.get(
            "strict_governing_training_view_count"
        ),
        "all_visible_training_candidates_view_count": summary.get(
            "all_visible_training_candidates_view_count"
        ),
        "report_only": (payload.get("truth_boundary") or {}).get("report_only"),
    }


def _compact_training_packet_summary_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "packet_count": summary.get("packet_count"),
        "packet_lane_counts": summary.get("packet_lane_counts", {}),
        "report_only": (payload.get("truth_boundary") or {}).get("report_only"),
    }


def _compact_string_interaction_materialization_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload.get("status"),
        "materialization_state": summary.get("materialization_state"),
        "seed_accession_count": summary.get("seed_accession_count"),
        "normalized_row_count": summary.get("normalized_row_count"),
        "support_only_row_count": summary.get("support_only_row_count"),
        "candidate_only_row_count": summary.get("candidate_only_row_count"),
        "report_only": (payload.get("truth_boundary") or {}).get("report_only"),
    }


def _compact_string_interaction_materialization_plan_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": payload["status"],
        "mirror_completion_status": payload.get("mirror_completion_status"),
        "remaining_gap_file_count": payload.get("remaining_gap_file_count"),
        "supported_accession_count": payload.get("supported_accession_count"),
        "planned_family_ids": [
            row.get("family_id") for row in (payload.get("planned_families") or [])
        ],
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_uniref_cluster_materialization_plan_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload["status"],
        "mirror_completion_status": payload.get("mirror_completion_status"),
        "supported_accession_count": payload.get("supported_accession_count"),
        "planned_family_id": summary.get("planned_family_id"),
        "planned_guard_family_id": summary.get("planned_guard_family_id"),
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_pdb_enrichment_scrape_registry_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "seed_structure_ids": summary.get("seed_structure_ids", []),
        "structured_source_ids": summary.get("structured_source_ids", []),
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_structure_entry_context_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "structure_ids": summary.get("structure_ids", []),
        "harvested_structure_count": summary.get("harvested_structure_count"),
        "mapped_uniprot_accession_count": summary.get("mapped_uniprot_accession_count"),
        "bound_component_count": summary.get("bound_component_count"),
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_pdb_enrichment_harvest_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "harvested_structure_count": summary.get("harvested_structure_count"),
        "successful_source_call_count": summary.get("successful_source_call_count"),
        "expected_source_call_count": summary.get("expected_source_call_count"),
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_pdb_enrichment_validation_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": payload["status"],
        "validated_row_count": payload.get("validated_row_count"),
        "validated_structure_ids": payload.get("validated_structure_ids", []),
        "issues": payload.get("issues", []),
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_ligand_context_scrape_registry_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "accessions_with_ligand_refs": summary.get("accessions_with_ligand_refs", []),
        "candidate_only_accession_count": summary.get("candidate_only_accession_count"),
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_protein_origin_context_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "harvested_accession_count": summary.get("harvested_accession_count"),
        "error_count": summary.get("error_count"),
        "reviewed_accession_count": summary.get("reviewed_accession_count"),
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_catalytic_site_context_preview(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "accession_count": summary.get("accession_count"),
        "with_catalytic_comment_count": summary.get("with_catalytic_comment_count"),
        "with_cofactor_comment_count": summary.get("with_cofactor_comment_count"),
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_targeted_page_scrape_registry_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "target_accessions": [row.get("accession") for row in (payload.get("rows") or [])],
        "page_scraping_started": payload["truth_boundary"]["page_scraping_started"],
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_generic_preview(
    payload: dict[str, Any], *, extra_summary_keys: Iterable[str] = ()
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    compact = {
        "status": payload.get("status"),
        "row_count": payload.get("row_count"),
        "report_only": (payload.get("truth_boundary") or {}).get("report_only"),
    }
    for key in extra_summary_keys:
        compact[key] = summary.get(key)
    return compact


def _compact_archive_cleanup_keeper_rules_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    return {
        "status": payload["status"],
        "row_count": payload["row_count"],
        "families": summary.get("families", []),
        "delete_ready_now_count": summary.get("delete_ready_now_count"),
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _compact_procurement_tail_freeze_gate_preview(
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": payload["status"],
        "gate_status": payload["gate_status"],
        "remaining_gap_file_count": payload["remaining_gap_file_count"],
        "active_file_count": payload["active_file_count"],
        "not_yet_started_file_count": payload["not_yet_started_file_count"],
        "source_statuses": payload["source_statuses"],
        "freeze_conditions": payload["freeze_conditions"],
        "tracked_gap_file_count": len(payload.get("tracked_gap_files") or []),
        "report_only": payload["truth_boundary"]["report_only"],
    }


def _split_subset(split_counts: dict[str, Any]) -> dict[str, Any]:
    return {key: split_counts[key] for key in ("train", "val", "test")}


def _build_blockers(
    *,
    coverage: dict[str, Any],
    metrics: dict[str, Any],
    summary: dict[str, Any],
) -> list[str]:
    run = metrics["run"]
    blockers = [
        *coverage.get("blockers", []),
        *run.get("remaining_gaps", []),
        *run.get("limitations", []),
        *summary.get("blocker_categories", []),
    ]
    semantics = coverage.get("semantics", {})
    if semantics.get("coverage_not_validation"):
        blockers.append("source coverage is a conservative inventory, not validation.")
    if not semantics.get("release_grade_corpus_validation", True):
        blockers.append("release-grade corpus validation remains false.")
    if summary["status"] == "blocked_on_release_grade_bar":
        blockers.append("release-grade go/no-go remains blocked.")
    if metrics["status"] != "completed_on_prototype_runtime":
        blockers.append("metrics pack is not rooted in the prototype runtime output.")
    return _dedupe(blockers)


def build_operator_dashboard(
    *,
    coverage_path: Path = DEFAULT_COVERAGE,
    metrics_path: Path = DEFAULT_METRICS,
    summary_path: Path = DEFAULT_SUMMARY,
    packet_deficit_path: Path = DEFAULT_PACKET_DEFICIT,
    tier1_direct_pipeline_path: Path = DEFAULT_TIER1_DIRECT,
    canonical_latest_path: Path = DEFAULT_CANONICAL_LATEST,
    summary_library_inventory_path: Path = DEFAULT_SUMMARY_LIBRARY_INVENTORY,
    protein_variant_library_inventory_path: Path = DEFAULT_PROTEIN_VARIANT_LIBRARY_INVENTORY,
    structure_unit_library_inventory_path: Path = DEFAULT_STRUCTURE_UNIT_LIBRARY_INVENTORY,
    protein_similarity_signature_preview_path: Path = (
        DEFAULT_PROTEIN_SIMILARITY_SIGNATURE_PREVIEW
    ),
    dictionary_preview_path: Path = DEFAULT_DICTIONARY_PREVIEW,
    motif_domain_compact_preview_family_path: Path = (DEFAULT_MOTIF_DOMAIN_COMPACT_PREVIEW_FAMILY),
    interaction_similarity_signature_preview_path: Path = (
        DEFAULT_INTERACTION_SIMILARITY_SIGNATURE_PREVIEW
    ),
    interaction_similarity_signature_validation_path: Path = (
        DEFAULT_INTERACTION_SIMILARITY_SIGNATURE_VALIDATION
    ),
    sabio_rk_support_preview_path: Path = DEFAULT_SABIO_RK_SUPPORT_PREVIEW,
    kinetics_support_preview_path: Path = DEFAULT_KINETICS_SUPPORT_PREVIEW,
    compact_enrichment_policy_preview_path: Path = DEFAULT_COMPACT_ENRICHMENT_POLICY_PREVIEW,
    scrape_readiness_registry_preview_path: Path = DEFAULT_SCRAPE_READINESS_REGISTRY_PREVIEW,
    procurement_source_completion_preview_path: Path = (
        DEFAULT_PROCUREMENT_SOURCE_COMPLETION_PREVIEW
    ),
    string_interaction_materialization_preview_path: Path = (
        DEFAULT_STRING_INTERACTION_MATERIALIZATION_PREVIEW
    ),
    string_interaction_materialization_plan_preview_path: Path = (
        DEFAULT_STRING_INTERACTION_MATERIALIZATION_PLAN_PREVIEW
    ),
    uniref_cluster_materialization_plan_preview_path: Path = (
        DEFAULT_UNIREF_CLUSTER_MATERIALIZATION_PLAN_PREVIEW
    ),
    pdb_enrichment_scrape_registry_preview_path: Path = (
        DEFAULT_PDB_ENRICHMENT_SCRAPE_REGISTRY_PREVIEW
    ),
    structure_entry_context_preview_path: Path = DEFAULT_STRUCTURE_ENTRY_CONTEXT_PREVIEW,
    pdb_enrichment_harvest_preview_path: Path = DEFAULT_PDB_ENRICHMENT_HARVEST_PREVIEW,
    pdb_enrichment_validation_preview_path: Path = (DEFAULT_PDB_ENRICHMENT_VALIDATION_PREVIEW),
    ligand_context_scrape_registry_preview_path: Path = (
        DEFAULT_LIGAND_CONTEXT_SCRAPE_REGISTRY_PREVIEW
    ),
    protein_origin_context_preview_path: Path = DEFAULT_PROTEIN_ORIGIN_CONTEXT_PREVIEW,
    catalytic_site_context_preview_path: Path = DEFAULT_CATALYTIC_SITE_CONTEXT_PREVIEW,
    targeted_page_scrape_registry_preview_path: Path = (
        DEFAULT_TARGETED_PAGE_SCRAPE_REGISTRY_PREVIEW
    ),
    seed_plus_neighbors_structured_corpus_preview_path: Path = (
        DEFAULT_SEED_PLUS_NEIGHBORS_STRUCTURED_CORPUS_PREVIEW
    ),
    training_set_baseline_sidecar_preview_path: Path = (
        DEFAULT_TRAINING_SET_BASELINE_SIDECAR_PREVIEW
    ),
    training_set_multimodal_sidecar_preview_path: Path = (
        DEFAULT_TRAINING_SET_MULTIMODAL_SIDECAR_PREVIEW
    ),
    training_packet_summary_preview_path: Path = DEFAULT_TRAINING_PACKET_SUMMARY_PREVIEW,
    bindingdb_dump_inventory_preview_path: Path = DEFAULT_BINDINGDB_DUMP_INVENTORY_PREVIEW,
    bindingdb_target_polymer_context_preview_path: Path = (
        DEFAULT_BINDINGDB_TARGET_POLYMER_CONTEXT_PREVIEW
    ),
    bindingdb_structure_bridge_preview_path: Path = (DEFAULT_BINDINGDB_STRUCTURE_BRIDGE_PREVIEW),
    archive_cleanup_keeper_rules_preview_path: Path = (
        DEFAULT_ARCHIVE_CLEANUP_KEEPER_RULES_PREVIEW
    ),
    procurement_tail_freeze_gate_preview_path: Path = (
        DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE_PREVIEW
    ),
    ligand_support_readiness_preview_path: Path = (DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW),
    ligand_identity_pilot_preview_path: Path = DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW,
    ligand_stage1_operator_queue_preview_path: Path = (
        DEFAULT_LIGAND_STAGE1_OPERATOR_QUEUE_PREVIEW
    ),
    p00387_ligand_extraction_validation_preview_path: Path = (
        DEFAULT_P00387_LIGAND_EXTRACTION_VALIDATION_PREVIEW
    ),
    q9nzd4_bridge_validation_preview_path: Path = (DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW),
    ligand_stage1_validation_panel_preview_path: Path = (
        DEFAULT_LIGAND_STAGE1_VALIDATION_PANEL_PREVIEW
    ),
    ligand_identity_core_materialization_preview_path: Path = (
        DEFAULT_LIGAND_IDENTITY_CORE_MATERIALIZATION_PREVIEW
    ),
    next_real_ligand_row_gate_preview_path: Path = (DEFAULT_NEXT_REAL_LIGAND_ROW_GATE_PREVIEW),
    next_real_ligand_row_decision_preview_path: Path = (
        DEFAULT_NEXT_REAL_LIGAND_ROW_DECISION_PREVIEW
    ),
    ligand_row_materialization_preview_path: Path = (DEFAULT_LIGAND_ROW_MATERIALIZATION_PREVIEW),
    ligand_similarity_signature_preview_path: Path = (DEFAULT_LIGAND_SIMILARITY_SIGNATURE_PREVIEW),
    ligand_similarity_signature_gate_preview_path: Path = (
        DEFAULT_LIGAND_SIMILARITY_SIGNATURE_GATE_PREVIEW
    ),
    structure_similarity_signature_preview_path: Path = (
        DEFAULT_STRUCTURE_SIMILARITY_SIGNATURE_PREVIEW
    ),
    structure_variant_bridge_summary_path: Path = DEFAULT_STRUCTURE_VARIANT_BRIDGE_SUMMARY,
    structure_variant_candidate_map_path: Path = DEFAULT_STRUCTURE_VARIANT_CANDIDATE_MAP,
    structure_followup_anchor_candidates_path: Path = DEFAULT_STRUCTURE_FOLLOWUP_ANCHOR_CANDIDATES,
    structure_followup_anchor_validation_path: Path = DEFAULT_STRUCTURE_FOLLOWUP_ANCHOR_VALIDATION,
    structure_followup_payload_preview_path: Path = DEFAULT_STRUCTURE_FOLLOWUP_PAYLOAD_PREVIEW,
    structure_followup_single_accession_preview_path: Path = (
        DEFAULT_STRUCTURE_FOLLOWUP_SINGLE_ACCESSION_PREVIEW
    ),
    structure_followup_single_accession_validation_preview_path: Path = (
        DEFAULT_STRUCTURE_FOLLOWUP_SINGLE_ACCESSION_VALIDATION_PREVIEW
    ),
    entity_signature_preview_path: Path = DEFAULT_ENTITY_SIGNATURE_PREVIEW,
    entity_split_candidate_preview_path: Path = DEFAULT_ENTITY_SPLIT_CANDIDATE_PREVIEW,
    entity_split_simulation_preview_path: Path = DEFAULT_ENTITY_SPLIT_SIMULATION_PREVIEW,
    entity_split_recipe_preview_path: Path = DEFAULT_ENTITY_SPLIT_RECIPE_PREVIEW,
    entity_split_assignment_preview_path: Path = DEFAULT_ENTITY_SPLIT_ASSIGNMENT_PREVIEW,
    split_engine_input_preview_path: Path = DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW,
    split_engine_dry_run_validation_path: Path = DEFAULT_SPLIT_ENGINE_DRY_RUN_VALIDATION,
    split_fold_export_gate_preview_path: Path = DEFAULT_SPLIT_FOLD_EXPORT_GATE_PREVIEW,
    split_fold_export_gate_validation_path: Path = DEFAULT_SPLIT_FOLD_EXPORT_GATE_VALIDATION,
    split_fold_export_staging_preview_path: Path = DEFAULT_SPLIT_FOLD_EXPORT_STAGING_PREVIEW,
    split_fold_export_staging_validation_path: Path = DEFAULT_SPLIT_FOLD_EXPORT_STAGING_VALIDATION,
    split_post_staging_gate_check_preview_path: Path = (
        DEFAULT_SPLIT_POST_STAGING_GATE_CHECK_PREVIEW
    ),
    split_post_staging_gate_check_validation_path: Path = (
        DEFAULT_SPLIT_POST_STAGING_GATE_CHECK_VALIDATION
    ),
    split_fold_export_request_preview_path: Path = (DEFAULT_SPLIT_FOLD_EXPORT_REQUEST_PREVIEW),
    split_fold_export_request_validation_path: Path = (
        DEFAULT_SPLIT_FOLD_EXPORT_REQUEST_VALIDATION
    ),
    operator_accession_coverage_matrix_path: Path = DEFAULT_OPERATOR_ACCESSION_COVERAGE_MATRIX,
    leakage_signature_preview_path: Path = DEFAULT_LEAKAGE_SIGNATURE_PREVIEW,
    leakage_group_preview_path: Path = DEFAULT_LEAKAGE_GROUP_PREVIEW,
    bundle_manifest_validation_path: Path = DEFAULT_BUNDLE_MANIFEST_VALIDATION,
    duplicate_executor_status_path: Path = DEFAULT_DUPLICATE_EXECUTOR_STATUS,
    duplicate_first_execution_preview_path: Path = (DEFAULT_DUPLICATE_FIRST_EXECUTION_PREVIEW),
    duplicate_delete_ready_manifest_preview_path: Path = (
        DEFAULT_DUPLICATE_DELETE_READY_MANIFEST_PREVIEW
    ),
    duplicate_post_delete_verification_contract_preview_path: Path = (
        DEFAULT_DUPLICATE_POST_DELETE_VERIFICATION_CONTRACT_PREVIEW
    ),
    duplicate_first_execution_batch_manifest_preview_path: Path = (
        DEFAULT_DUPLICATE_FIRST_EXECUTION_BATCH_MANIFEST_PREVIEW
    ),
    operator_next_actions_preview_path: Path = DEFAULT_OPERATOR_NEXT_ACTIONS_PREVIEW,
    training_set_eligibility_matrix_preview_path: Path = (
        DEFAULT_TRAINING_SET_ELIGIBILITY_MATRIX_PREVIEW
    ),
    missing_data_policy_preview_path: Path = DEFAULT_MISSING_DATA_POLICY_PREVIEW,
    final_structured_dataset_bundle_preview_path: Path = (
        DEFAULT_FINAL_STRUCTURED_DATASET_BUNDLE_PREVIEW
    ),
    release_grade_readiness_preview_path: Path = DEFAULT_RELEASE_GRADE_READINESS_PREVIEW,
    release_grade_closure_queue_preview_path: Path = (
        DEFAULT_RELEASE_GRADE_CLOSURE_QUEUE_PREVIEW
    ),
    release_runtime_maturity_preview_path: Path = DEFAULT_RELEASE_RUNTIME_MATURITY_PREVIEW,
    release_source_coverage_depth_preview_path: Path = (
        DEFAULT_RELEASE_SOURCE_COVERAGE_DEPTH_PREVIEW
    ),
    release_provenance_depth_preview_path: Path = (
        DEFAULT_RELEASE_PROVENANCE_DEPTH_PREVIEW
    ),
    release_grade_runbook_preview_path: Path = DEFAULT_RELEASE_GRADE_RUNBOOK_PREVIEW,
    release_accession_closure_matrix_preview_path: Path = (
        DEFAULT_RELEASE_ACCESSION_CLOSURE_MATRIX_PREVIEW
    ),
    release_accession_action_queue_preview_path: Path = (
        DEFAULT_RELEASE_ACCESSION_ACTION_QUEUE_PREVIEW
    ),
    release_promotion_gate_preview_path: Path = DEFAULT_RELEASE_PROMOTION_GATE_PREVIEW,
    release_source_fix_followup_batch_preview_path: Path = (
        DEFAULT_RELEASE_SOURCE_FIX_FOLLOWUP_BATCH_PREVIEW
    ),
    release_candidate_promotion_preview_path: Path = (
        DEFAULT_RELEASE_CANDIDATE_PROMOTION_PREVIEW
    ),
    release_runtime_qualification_preview_path: Path = (
        DEFAULT_RELEASE_RUNTIME_QUALIFICATION_PREVIEW
    ),
    release_governing_sufficiency_preview_path: Path = (
        DEFAULT_RELEASE_GOVERNING_SUFFICIENCY_PREVIEW
    ),
    release_accession_evidence_pack_preview_path: Path = (
        DEFAULT_RELEASE_ACCESSION_EVIDENCE_PACK_PREVIEW
    ),
    release_reporting_completeness_preview_path: Path = (
        DEFAULT_RELEASE_REPORTING_COMPLETENESS_PREVIEW
    ),
    release_blocker_resolution_board_preview_path: Path = (
        DEFAULT_RELEASE_BLOCKER_RESOLUTION_BOARD_PREVIEW
    ),
    procurement_external_drive_mount_preview_path: Path = (
        DEFAULT_PROCUREMENT_EXTERNAL_DRIVE_MOUNT_PREVIEW
    ),
    procurement_expansion_wave_preview_path: Path = (
        DEFAULT_PROCUREMENT_EXPANSION_WAVE_PREVIEW
    ),
    procurement_expansion_storage_budget_preview_path: Path = (
        DEFAULT_PROCUREMENT_EXPANSION_STORAGE_BUDGET_PREVIEW
    ),
    missing_scrape_family_contracts_preview_path: Path = (
        DEFAULT_MISSING_SCRAPE_FAMILY_CONTRACTS_PREVIEW
    ),
) -> dict[str, Any]:
    for path, label in (
        (coverage_path, "source coverage"),
        (metrics_path, "metrics summary"),
        (summary_path, "benchmark summary"),
    ):
        _ensure_exists(path, label)

    coverage = _read_json(coverage_path)
    metrics = _read_json(metrics_path)
    summary = _read_json(summary_path)

    coverage_total = coverage["summary"]["total_accessions"]
    if coverage_total != metrics["cohort"]["target_size"]:
        raise ValueError("coverage and metrics cohort sizes diverge")
    if coverage_total != summary["execution_scope"]["cohort_size"]:
        raise ValueError("coverage and summary cohort sizes diverge")
    if (
        _split_subset(metrics["cohort"]["split_counts"])
        != coverage["frozen_cohort"]["split_counts"]
    ):
        raise ValueError("coverage and metrics split counts diverge")
    if (
        _split_subset(summary["execution_scope"]["split_counts"])
        != coverage["frozen_cohort"]["split_counts"]
    ):
        raise ValueError("coverage and summary split counts diverge")
    if metrics["run"]["selected_accession_count"] != coverage_total:
        raise ValueError("selected accession count does not match coverage total")
    if (
        summary["runtime"]["first_run_processed_examples"]
        != metrics["runtime"]["first_run_processed_examples"]
    ):
        raise ValueError("summary and metrics first-run counts diverge")
    if (
        summary["runtime"]["resumed_run_processed_examples"]
        != metrics["runtime"]["resumed_run_processed_examples"]
    ):
        raise ValueError("summary and metrics resumed counts diverge")

    benchmark_summary = _compact_benchmark_summary(summary)
    metrics_summary = _compact_metrics(metrics)
    coverage_summary = _compact_coverage(coverage)
    packet_latest = _read_json_if_exists(packet_deficit_path)
    tier1_direct_pipeline = _read_json_if_exists(tier1_direct_pipeline_path)
    canonical_latest = _read_json_if_exists(canonical_latest_path)
    summary_library_inventory = _read_json_if_exists(summary_library_inventory_path)
    protein_variant_library_inventory = _read_json_if_exists(protein_variant_library_inventory_path)
    structure_unit_library_inventory = _read_json_if_exists(structure_unit_library_inventory_path)
    protein_similarity_signature_preview = _read_json_if_exists(
        protein_similarity_signature_preview_path
    )
    dictionary_preview = _read_json_if_exists(dictionary_preview_path)
    motif_domain_compact_preview_family = _read_json_if_exists(
        motif_domain_compact_preview_family_path
    )
    interaction_similarity_signature_preview = _read_json_if_exists(
        interaction_similarity_signature_preview_path
    )
    interaction_similarity_signature_validation = _read_json_if_exists(
        interaction_similarity_signature_validation_path
    )
    sabio_rk_support_preview = _read_json_if_exists(sabio_rk_support_preview_path)
    kinetics_support_preview = _read_json_if_exists(kinetics_support_preview_path)
    compact_enrichment_policy_preview = _ensure_compact_enrichment_policy_preview(
        compact_enrichment_policy_preview_path
    )
    scrape_readiness_registry_preview = _ensure_scrape_readiness_registry_preview(
        scrape_readiness_registry_preview_path
    )
    procurement_source_completion_preview = _read_json_if_exists(
        procurement_source_completion_preview_path
    )
    string_interaction_materialization_preview = _ensure_script_export(
        string_interaction_materialization_preview_path,
        "export_string_interaction_materialization_preview.py",
        refresh=True,
    )
    string_interaction_materialization_plan_preview = _read_json_if_exists(
        string_interaction_materialization_plan_preview_path
    )
    uniref_cluster_materialization_plan_preview = _read_json_if_exists(
        uniref_cluster_materialization_plan_preview_path
    )
    pdb_enrichment_scrape_registry_preview = _read_json_if_exists(
        pdb_enrichment_scrape_registry_preview_path
    )
    structure_entry_context_preview = _read_json_if_exists(structure_entry_context_preview_path)
    pdb_enrichment_harvest_preview = _read_json_if_exists(pdb_enrichment_harvest_preview_path)
    pdb_enrichment_validation_preview = _read_json_if_exists(pdb_enrichment_validation_preview_path)
    ligand_context_scrape_registry_preview = _read_json_if_exists(
        ligand_context_scrape_registry_preview_path
    )
    protein_origin_context_preview = _read_json_if_exists(protein_origin_context_preview_path)
    catalytic_site_context_preview = _read_json_if_exists(catalytic_site_context_preview_path)
    targeted_page_scrape_registry_preview = _read_json_if_exists(
        targeted_page_scrape_registry_preview_path
    )
    seed_plus_neighbors_structured_corpus_preview = _read_json_if_exists(
        seed_plus_neighbors_structured_corpus_preview_path
    )
    training_set_baseline_sidecar_preview = _read_json_if_exists(
        training_set_baseline_sidecar_preview_path
    )
    training_set_multimodal_sidecar_preview = _read_json_if_exists(
        training_set_multimodal_sidecar_preview_path
    )
    training_packet_summary_preview = _read_json_if_exists(training_packet_summary_preview_path)
    binding_measurement_registry_preview = _read_json_if_exists(
        DEFAULT_BINDING_MEASUREMENT_REGISTRY_PREVIEW
    )
    binding_measurement_validation_preview = _read_json_if_exists(
        DEFAULT_BINDING_MEASUREMENT_VALIDATION_PREVIEW
    )
    structure_binding_affinity_context_preview = _read_json_if_exists(
        DEFAULT_STRUCTURE_BINDING_AFFINITY_CONTEXT_PREVIEW
    )
    accession_binding_support_preview = _read_json_if_exists(
        DEFAULT_ACCESSION_BINDING_SUPPORT_PREVIEW
    )
    structure_chain_origin_preview = _read_json_if_exists(DEFAULT_STRUCTURE_CHAIN_ORIGIN_PREVIEW)
    structure_ligand_context_preview = _read_json_if_exists(
        DEFAULT_STRUCTURE_LIGAND_CONTEXT_PREVIEW
    )
    structure_assembly_context_preview = _read_json_if_exists(
        DEFAULT_STRUCTURE_ASSEMBLY_CONTEXT_PREVIEW
    )
    structure_validation_context_preview = _read_json_if_exists(
        DEFAULT_STRUCTURE_VALIDATION_CONTEXT_PREVIEW
    )
    structure_publication_context_preview = _read_json_if_exists(
        DEFAULT_STRUCTURE_PUBLICATION_CONTEXT_PREVIEW
    )
    structure_origin_context_preview = _read_json_if_exists(
        DEFAULT_STRUCTURE_ORIGIN_CONTEXT_PREVIEW
    )
    bound_ligand_character_context_preview = _read_json_if_exists(
        DEFAULT_BOUND_LIGAND_CHARACTER_CONTEXT_PREVIEW
    )
    ligand_environment_context_preview = _read_json_if_exists(
        DEFAULT_LIGAND_ENVIRONMENT_CONTEXT_PREVIEW
    )
    interaction_context_preview = _read_json_if_exists(DEFAULT_INTERACTION_CONTEXT_PREVIEW)
    interaction_origin_context_preview = _read_json_if_exists(
        DEFAULT_INTERACTION_ORIGIN_CONTEXT_PREVIEW
    )
    interaction_partner_context_preview = _read_json_if_exists(
        DEFAULT_INTERACTION_PARTNER_CONTEXT_PREVIEW
    )
    protein_function_context_preview = _read_json_if_exists(
        DEFAULT_PROTEIN_FUNCTION_CONTEXT_PREVIEW
    )
    protein_feature_context_preview = _read_json_if_exists(DEFAULT_PROTEIN_FEATURE_CONTEXT_PREVIEW)
    protein_reference_context_preview = _read_json_if_exists(
        DEFAULT_PROTEIN_REFERENCE_CONTEXT_PREVIEW
    )
    enzyme_behavior_context_preview = _read_json_if_exists(DEFAULT_ENZYME_BEHAVIOR_CONTEXT_PREVIEW)
    pdb_chain_projection_contract_preview = _read_json_if_exists(
        DEFAULT_PDB_CHAIN_PROJECTION_CONTRACT_PREVIEW
    )
    bindingdb_dump_inventory_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_DUMP_INVENTORY_PREVIEW
    )
    bindingdb_target_polymer_context_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_TARGET_POLYMER_CONTEXT_PREVIEW
    )
    bindingdb_structure_bridge_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_STRUCTURE_BRIDGE_PREVIEW
    )
    bindingdb_measurement_subset_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_MEASUREMENT_SUBSET_PREVIEW
    )
    bindingdb_structure_measurement_projection_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_STRUCTURE_MEASUREMENT_PROJECTION_PREVIEW
    )
    bindingdb_partner_monomer_context_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_PARTNER_MONOMER_CONTEXT_PREVIEW
    )
    bindingdb_structure_assay_summary_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_STRUCTURE_ASSAY_SUMMARY_PREVIEW
    )
    bindingdb_accession_assay_profile_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_ACCESSION_ASSAY_PROFILE_PREVIEW
    )
    bindingdb_assay_condition_profile_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_ASSAY_CONDITION_PROFILE_PREVIEW
    )
    bindingdb_structure_partner_profile_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_STRUCTURE_PARTNER_PROFILE_PREVIEW
    )
    bindingdb_partner_descriptor_reconciliation_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_PARTNER_DESCRIPTOR_RECONCILIATION_PREVIEW
    )
    bindingdb_accession_partner_identity_profile_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_ACCESSION_PARTNER_IDENTITY_PROFILE_PREVIEW
    )
    bindingdb_structure_grounding_candidate_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_STRUCTURE_GROUNDING_CANDIDATE_PREVIEW
    )
    bindingdb_future_structure_registry_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_FUTURE_STRUCTURE_REGISTRY_PREVIEW
    )
    bindingdb_future_structure_context_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_FUTURE_STRUCTURE_CONTEXT_PREVIEW
    )
    bindingdb_future_structure_alignment_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_FUTURE_STRUCTURE_ALIGNMENT_PREVIEW
    )
    bindingdb_future_structure_triage_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_FUTURE_STRUCTURE_TRIAGE_PREVIEW
    )
    bindingdb_off_target_adjacent_context_profile_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_OFF_TARGET_ADJACENT_CONTEXT_PROFILE_PREVIEW
    )
    bindingdb_off_target_target_profile_preview = _read_json_if_exists(
        DEFAULT_BINDINGDB_OFF_TARGET_TARGET_PROFILE_PREVIEW
    )
    motif_domain_site_context_preview = _read_json_if_exists(
        DEFAULT_MOTIF_DOMAIN_SITE_CONTEXT_PREVIEW
    )
    uniref_cluster_context_preview = _read_json_if_exists(DEFAULT_UNIREF_CLUSTER_CONTEXT_PREVIEW)
    sequence_redundancy_guard_preview = _read_json_if_exists(
        DEFAULT_SEQUENCE_REDUNDANCY_GUARD_PREVIEW
    )
    archive_cleanup_keeper_rules_preview = _ensure_archive_cleanup_keeper_rules_preview(
        archive_cleanup_keeper_rules_preview_path
    )
    procurement_tail_freeze_gate_preview = _ensure_procurement_tail_freeze_gate_preview(
        procurement_tail_freeze_gate_preview_path
    )
    ligand_support_readiness_preview = _ensure_ligand_support_readiness_preview(
        ligand_support_readiness_preview_path
    )
    ligand_identity_pilot_preview = _ensure_ligand_identity_pilot_preview(
        ligand_identity_pilot_preview_path
    )
    ligand_stage1_operator_queue_preview = _ensure_ligand_stage1_operator_queue_preview(
        ligand_stage1_operator_queue_preview_path
    )
    p00387_ligand_extraction_validation_preview = (
        _ensure_p00387_ligand_extraction_validation_preview(
            p00387_ligand_extraction_validation_preview_path
        )
    )
    q9nzd4_bridge_validation_preview = _ensure_q9nzd4_bridge_validation_preview(
        q9nzd4_bridge_validation_preview_path
    )
    ligand_stage1_validation_panel_preview = _ensure_ligand_stage1_validation_panel_preview(
        ligand_stage1_validation_panel_preview_path
    )
    ligand_identity_core_materialization_preview = (
        _ensure_ligand_identity_core_materialization_preview(
            ligand_identity_core_materialization_preview_path
        )
    )
    next_real_ligand_row_gate_preview = _read_json_if_exists(next_real_ligand_row_gate_preview_path)
    next_real_ligand_row_decision_preview = _ensure_next_real_ligand_row_decision_preview(
        next_real_ligand_row_decision_preview_path
    )
    ligand_row_materialization_preview = _ensure_ligand_row_materialization_preview(
        ligand_row_materialization_preview_path
    )
    ligand_similarity_signature_preview = _ensure_ligand_similarity_signature_preview(
        ligand_similarity_signature_preview_path
    )
    ligand_similarity_signature_gate_preview = _ensure_ligand_similarity_signature_gate_preview(
        ligand_similarity_signature_gate_preview_path
    )
    ligand_similarity_signature_validation = _ensure_ligand_similarity_signature_validation(
        DEFAULT_LIGAND_SIMILARITY_SIGNATURE_VALIDATION
    )
    structure_similarity_signature_preview = _read_json_if_exists(
        structure_similarity_signature_preview_path
    )
    structure_variant_bridge_summary = _read_json_if_exists(structure_variant_bridge_summary_path)
    structure_variant_candidate_map = _read_json_if_exists(structure_variant_candidate_map_path)
    structure_followup_anchor_candidates = _read_json_if_exists(
        structure_followup_anchor_candidates_path
    )
    structure_followup_anchor_validation = _read_json_if_exists(
        structure_followup_anchor_validation_path
    )
    structure_followup_payload_preview = _read_json_if_exists(
        structure_followup_payload_preview_path
    )
    structure_followup_single_accession_preview = (
        _ensure_structure_followup_single_accession_preview(
            structure_followup_single_accession_preview_path
        )
    )
    structure_followup_single_accession_validation_preview = (
        _ensure_structure_followup_single_accession_validation_preview(
            structure_followup_single_accession_validation_preview_path
        )
    )
    entity_signature_preview = _read_json_if_exists(entity_signature_preview_path)
    entity_split_candidate_preview = _read_json_if_exists(entity_split_candidate_preview_path)
    entity_split_simulation_preview = _read_json_if_exists(entity_split_simulation_preview_path)
    entity_split_recipe_preview = _read_json_if_exists(entity_split_recipe_preview_path)
    entity_split_assignment_preview = _read_json_if_exists(entity_split_assignment_preview_path)
    split_engine_input_preview = _read_json_if_exists(split_engine_input_preview_path)
    split_engine_dry_run_validation = _read_json_if_exists(split_engine_dry_run_validation_path)
    split_fold_export_gate_preview = _read_json_if_exists(split_fold_export_gate_preview_path)
    split_fold_export_gate_validation = _read_json_if_exists(split_fold_export_gate_validation_path)
    split_fold_export_staging_preview = _read_json_if_exists(split_fold_export_staging_preview_path)
    split_fold_export_staging_validation = _read_json_if_exists(
        split_fold_export_staging_validation_path
    )
    split_post_staging_gate_check_preview = _read_json_if_exists(
        split_post_staging_gate_check_preview_path
    )
    split_post_staging_gate_check_validation = _read_json_if_exists(
        split_post_staging_gate_check_validation_path
    )
    split_fold_export_request_preview = _read_json_if_exists(split_fold_export_request_preview_path)
    split_fold_export_request_validation = _read_json_if_exists(
        split_fold_export_request_validation_path
    )
    operator_accession_coverage_matrix = _read_json_if_exists(
        operator_accession_coverage_matrix_path
    )
    leakage_signature_preview = _read_json_if_exists(leakage_signature_preview_path)
    leakage_group_preview = _read_json_if_exists(leakage_group_preview_path)
    bundle_manifest_validation = _read_json_if_exists(bundle_manifest_validation_path)
    duplicate_executor_status = _read_json_if_exists(duplicate_executor_status_path)
    duplicate_first_execution_preview = _ensure_duplicate_cleanup_first_execution_preview(
        duplicate_first_execution_preview_path
    )
    duplicate_delete_ready_manifest_preview = _read_json_if_exists(
        duplicate_delete_ready_manifest_preview_path
    )
    duplicate_post_delete_verification_contract_preview = _read_json_if_exists(
        duplicate_post_delete_verification_contract_preview_path
    )
    duplicate_first_execution_batch_manifest_preview = _read_json_if_exists(
        duplicate_first_execution_batch_manifest_preview_path
    )
    operator_next_actions_preview = _ensure_operator_next_actions_preview(
        operator_next_actions_preview_path
    )
    training_set_eligibility_matrix_preview = _ensure_training_set_eligibility_matrix_preview(
        training_set_eligibility_matrix_preview_path
    )
    missing_data_policy_preview = _ensure_missing_data_policy_preview(
        missing_data_policy_preview_path
    )
    training_set_readiness_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_READINESS_PREVIEW,
        "export_training_set_readiness_preview.py",
        refresh=True,
    )
    final_structured_dataset_bundle_preview = _ensure_script_export(
        DEFAULT_FINAL_STRUCTURED_DATASET_BUNDLE_PREVIEW,
        "export_final_structured_dataset_bundle.py",
        refresh=True,
    )
    release_grade_readiness_preview = _ensure_script_export(
        DEFAULT_RELEASE_GRADE_READINESS_PREVIEW,
        "export_release_grade_readiness_preview.py",
        refresh=True,
    )
    release_grade_closure_queue_preview = _ensure_script_export(
        DEFAULT_RELEASE_GRADE_CLOSURE_QUEUE_PREVIEW,
        "export_release_grade_closure_queue_preview.py",
        refresh=True,
    )
    release_runtime_maturity_preview = _ensure_script_export(
        DEFAULT_RELEASE_RUNTIME_MATURITY_PREVIEW,
        "export_release_runtime_maturity_preview.py",
        refresh=True,
    )
    release_source_coverage_depth_preview = _ensure_script_export(
        DEFAULT_RELEASE_SOURCE_COVERAGE_DEPTH_PREVIEW,
        "export_release_source_coverage_depth_preview.py",
        refresh=True,
    )
    release_provenance_depth_preview = _ensure_script_export(
        DEFAULT_RELEASE_PROVENANCE_DEPTH_PREVIEW,
        "export_release_provenance_depth_preview.py",
        refresh=True,
    )
    release_grade_runbook_preview = _ensure_script_export(
        DEFAULT_RELEASE_GRADE_RUNBOOK_PREVIEW,
        "export_release_grade_runbook_preview.py",
        refresh=True,
    )
    release_accession_closure_matrix_preview = _ensure_script_export(
        DEFAULT_RELEASE_ACCESSION_CLOSURE_MATRIX_PREVIEW,
        "export_release_accession_closure_matrix_preview.py",
        refresh=True,
    )
    release_accession_action_queue_preview = _ensure_script_export(
        DEFAULT_RELEASE_ACCESSION_ACTION_QUEUE_PREVIEW,
        "export_release_accession_action_queue_preview.py",
        refresh=True,
    )
    release_promotion_gate_preview = _ensure_script_export(
        DEFAULT_RELEASE_PROMOTION_GATE_PREVIEW,
        "export_release_promotion_gate_preview.py",
        refresh=True,
    )
    release_source_fix_followup_batch_preview = _ensure_script_export(
        DEFAULT_RELEASE_SOURCE_FIX_FOLLOWUP_BATCH_PREVIEW,
        "export_release_source_fix_followup_batch_preview.py",
        refresh=True,
    )
    release_candidate_promotion_preview = _ensure_script_export(
        DEFAULT_RELEASE_CANDIDATE_PROMOTION_PREVIEW,
        "export_release_candidate_promotion_preview.py",
        refresh=True,
    )
    release_runtime_qualification_preview = _ensure_script_export(
        DEFAULT_RELEASE_RUNTIME_QUALIFICATION_PREVIEW,
        "export_release_runtime_qualification_preview.py",
        refresh=True,
    )
    release_governing_sufficiency_preview = _ensure_script_export(
        DEFAULT_RELEASE_GOVERNING_SUFFICIENCY_PREVIEW,
        "export_release_governing_sufficiency_preview.py",
        refresh=True,
    )
    release_accession_evidence_pack_preview = _ensure_script_export(
        DEFAULT_RELEASE_ACCESSION_EVIDENCE_PACK_PREVIEW,
        "export_release_accession_evidence_pack_preview.py",
        refresh=True,
    )
    release_reporting_completeness_preview = _ensure_script_export(
        DEFAULT_RELEASE_REPORTING_COMPLETENESS_PREVIEW,
        "export_release_reporting_completeness_preview.py",
        refresh=True,
    )
    release_blocker_resolution_board_preview = _ensure_script_export(
        DEFAULT_RELEASE_BLOCKER_RESOLUTION_BOARD_PREVIEW,
        "export_release_blocker_resolution_board_preview.py",
        refresh=True,
    )
    procurement_external_drive_mount_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_EXTERNAL_DRIVE_MOUNT_PREVIEW,
        "export_procurement_external_drive_mount_preview.py",
        refresh=True,
    )
    procurement_expansion_wave_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_EXPANSION_WAVE_PREVIEW,
        "export_procurement_expansion_wave_preview.py",
        refresh=True,
    )
    procurement_expansion_storage_budget_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_EXPANSION_STORAGE_BUDGET_PREVIEW,
        "export_procurement_expansion_storage_budget_preview.py",
        refresh=True,
    )
    missing_scrape_family_contracts_preview = _ensure_script_export(
        DEFAULT_MISSING_SCRAPE_FAMILY_CONTRACTS_PREVIEW,
        "export_missing_scrape_family_contracts_preview.py",
        refresh=True,
    )
    cohort_compiler_preview = _ensure_script_export(
        DEFAULT_COHORT_COMPILER_PREVIEW,
        "export_cohort_compiler_preview.py",
        refresh=True,
    )
    balance_diagnostics_preview = _ensure_script_export(
        DEFAULT_BALANCE_DIAGNOSTICS_PREVIEW,
        "export_balance_diagnostics_preview.py",
        refresh=True,
    )
    package_readiness_preview = _ensure_script_export(
        DEFAULT_PACKAGE_READINESS_PREVIEW,
        "export_package_readiness_preview.py",
        refresh=True,
    )
    training_set_builder_session_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_BUILDER_SESSION_PREVIEW,
        "export_training_set_builder_session_preview.py",
        refresh=True,
    )
    training_set_builder_runbook_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_BUILDER_RUNBOOK_PREVIEW,
        "export_training_set_builder_runbook_preview.py",
        refresh=True,
    )
    external_dataset_intake_contract_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_INTAKE_CONTRACT_PREVIEW,
        "export_external_dataset_intake_contract_preview.py",
        refresh=True,
    )
    external_dataset_assessment_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_ASSESSMENT_PREVIEW,
        "export_external_dataset_assessment_preview.py",
        refresh=True,
    )
    external_dataset_leakage_audit_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_LEAKAGE_AUDIT_PREVIEW,
        "export_external_dataset_leakage_audit_preview.py",
        refresh=True,
    )
    external_dataset_modality_audit_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_MODALITY_AUDIT_PREVIEW,
        "export_external_dataset_modality_audit_preview.py",
        refresh=True,
    )
    external_dataset_binding_audit_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_BINDING_AUDIT_PREVIEW,
        "export_external_dataset_binding_audit_preview.py",
        refresh=True,
    )
    external_dataset_structure_audit_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_STRUCTURE_AUDIT_PREVIEW,
        "export_external_dataset_structure_audit_preview.py",
        refresh=True,
    )
    external_dataset_provenance_audit_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_PROVENANCE_AUDIT_PREVIEW,
        "export_external_dataset_provenance_audit_preview.py",
        refresh=True,
    )
    sample_external_dataset_assessment_bundle_preview = _ensure_script_export(
        DEFAULT_SAMPLE_EXTERNAL_DATASET_ASSESSMENT_BUNDLE_PREVIEW,
        "export_sample_external_dataset_assessment_bundle.py",
        refresh=True,
    )
    scrape_gap_matrix_preview = _ensure_script_export(
        DEFAULT_SCRAPE_GAP_MATRIX_PREVIEW,
        "export_scrape_gap_matrix_preview.py",
        refresh=True,
    )
    overnight_queue_backlog_preview = _ensure_script_export(
        DEFAULT_OVERNIGHT_QUEUE_BACKLOG_PREVIEW,
        "export_overnight_queue_backlog_preview.py",
        refresh=True,
    )
    overnight_execution_contract_preview = _ensure_script_export(
        DEFAULT_OVERNIGHT_EXECUTION_CONTRACT_PREVIEW,
        "export_overnight_execution_contract_preview.py",
        refresh=True,
    )
    overnight_queue_repair_status = _ensure_script_export(
        DEFAULT_OVERNIGHT_QUEUE_REPAIR_STATUS,
        "export_overnight_queue_repair_status.py",
        refresh=True,
    )
    overnight_idle_status_preview = _ensure_script_export(
        DEFAULT_OVERNIGHT_IDLE_STATUS_PREVIEW,
        "export_overnight_idle_status_preview.py",
        refresh=True,
    )
    overnight_pending_reconciliation_preview = _ensure_script_export(
        DEFAULT_OVERNIGHT_PENDING_RECONCILIATION_PREVIEW,
        "export_overnight_pending_reconciliation_preview.py",
        refresh=True,
    )
    overnight_worker_launch_gap_preview = _ensure_script_export(
        DEFAULT_OVERNIGHT_WORKER_LAUNCH_GAP_PREVIEW,
        "export_overnight_worker_launch_gap_preview.py",
        refresh=True,
    )
    overnight_wave_advance_preview = _read_json_if_exists(DEFAULT_OVERNIGHT_WAVE_ADVANCE_PREVIEW)
    binding_measurement_suspect_rows_preview = _ensure_script_export(
        DEFAULT_BINDING_MEASUREMENT_SUSPECT_ROWS_PREVIEW,
        "export_binding_measurement_suspect_rows_preview.py",
        refresh=True,
    )
    cross_source_duplicate_measurement_audit_preview = _ensure_script_export(
        DEFAULT_CROSS_SOURCE_DUPLICATE_MEASUREMENT_AUDIT_PREVIEW,
        "export_cross_source_duplicate_measurement_audit_preview.py",
        refresh=True,
    )
    training_set_candidate_package_manifest_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_CANDIDATE_PACKAGE_MANIFEST_PREVIEW,
        "export_training_set_candidate_package_manifest_preview.py",
        refresh=True,
    )
    procurement_process_diagnostics_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_PROCESS_DIAGNOSTICS_PREVIEW,
        "export_procurement_process_diagnostics.py",
        refresh=True,
    )
    procurement_supervisor_freshness_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_SUPERVISOR_FRESHNESS_PREVIEW,
        "export_procurement_supervisor_freshness_preview.py",
        refresh=True,
    )
    procurement_tail_signal_reconciliation_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_TAIL_SIGNAL_RECONCILIATION_PREVIEW,
        "export_procurement_tail_signal_reconciliation_preview.py",
        refresh=True,
    )
    procurement_tail_growth_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_TAIL_GROWTH_PREVIEW,
        "export_procurement_tail_growth_preview.py",
        refresh=True,
    )
    procurement_headroom_guard_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_HEADROOM_GUARD_PREVIEW,
        "export_procurement_headroom_guard_preview.py",
        refresh=True,
    )
    procurement_tail_space_drift_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_TAIL_SPACE_DRIFT_PREVIEW,
        "export_procurement_tail_space_drift_preview.py",
        refresh=True,
    )
    procurement_tail_source_pressure_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_TAIL_SOURCE_PRESSURE_PREVIEW,
        "export_procurement_tail_source_pressure_preview.py",
        refresh=True,
    )
    procurement_tail_log_progress_registry_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_TAIL_LOG_PROGRESS_REGISTRY_PREVIEW,
        "export_procurement_tail_log_progress_registry_preview.py",
        refresh=True,
    )
    procurement_tail_completion_margin_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_TAIL_COMPLETION_MARGIN_PREVIEW,
        "export_procurement_tail_completion_margin_preview.py",
        refresh=True,
    )
    procurement_space_recovery_target_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_SPACE_RECOVERY_TARGET_PREVIEW,
        "export_procurement_space_recovery_target_preview.py",
        refresh=True,
    )
    procurement_space_recovery_candidates_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_SPACE_RECOVERY_CANDIDATES_PREVIEW,
        "export_procurement_space_recovery_candidates_preview.py",
        refresh=True,
    )
    procurement_space_recovery_execution_batch_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_SPACE_RECOVERY_EXECUTION_BATCH_PREVIEW,
        "export_procurement_space_recovery_execution_batch_preview.py",
        refresh=True,
    )
    procurement_space_recovery_safety_register_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_SPACE_RECOVERY_SAFETY_REGISTER_PREVIEW,
        "export_procurement_space_recovery_safety_register_preview.py",
        refresh=True,
    )
    procurement_tail_fill_risk_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_TAIL_FILL_RISK_PREVIEW,
        "export_procurement_tail_fill_risk_preview.py",
        refresh=True,
    )
    procurement_space_recovery_trigger_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_SPACE_RECOVERY_TRIGGER_PREVIEW,
        "export_procurement_space_recovery_trigger_preview.py",
        refresh=True,
    )
    procurement_space_recovery_gap_drift_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_SPACE_RECOVERY_GAP_DRIFT_PREVIEW,
        "export_procurement_space_recovery_gap_drift_preview.py",
        refresh=True,
    )
    procurement_space_recovery_coverage_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_SPACE_RECOVERY_COVERAGE_PREVIEW,
        "export_procurement_space_recovery_coverage_preview.py",
        refresh=True,
    )
    procurement_recovery_intervention_priority_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_RECOVERY_INTERVENTION_PRIORITY_PREVIEW,
        "export_procurement_recovery_intervention_priority_preview.py",
        refresh=True,
    )
    procurement_recovery_escalation_lane_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_RECOVERY_ESCALATION_LANE_PREVIEW,
        "export_procurement_recovery_escalation_lane_preview.py",
        refresh=True,
    )
    procurement_space_recovery_concentration_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_SPACE_RECOVERY_CONCENTRATION_PREVIEW,
        "export_procurement_space_recovery_concentration_preview.py",
        refresh=True,
    )
    procurement_recovery_shortfall_bridge_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_RECOVERY_SHORTFALL_BRIDGE_PREVIEW,
        "export_procurement_recovery_shortfall_bridge_preview.py",
        refresh=True,
    )
    procurement_recovery_lane_fragility_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_RECOVERY_LANE_FRAGILITY_PREVIEW,
        "export_procurement_recovery_lane_fragility_preview.py",
        refresh=True,
    )
    procurement_broader_search_trigger_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_BROADER_SEARCH_TRIGGER_PREVIEW,
        "export_procurement_broader_search_trigger_preview.py",
        refresh=True,
    )
    procurement_source_completion_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_SOURCE_COMPLETION_PREVIEW,
        "export_procurement_source_completion_preview.py",
        refresh=True,
    )
    string_interaction_materialization_plan_preview = _read_json_if_exists(
        DEFAULT_STRING_INTERACTION_MATERIALIZATION_PLAN_PREVIEW
    )
    seed_plus_neighbors_structured_corpus_preview = _ensure_script_export(
        DEFAULT_SEED_PLUS_NEIGHBORS_STRUCTURED_CORPUS_PREVIEW,
        "export_seed_plus_neighbors_structured_corpus_preview.py",
        refresh=True,
    )
    pdbbind_expanded_structured_corpus_preview = _ensure_script_export(
        DEFAULT_PDBBIND_EXPANDED_STRUCTURED_CORPUS_PREVIEW,
        "export_pdbbind_expanded_structured_corpus_preview.py",
        refresh=True,
    )
    pdbbind_protein_cohort_graph_preview = _ensure_script_export(
        DEFAULT_PDBBIND_PROTEIN_COHORT_GRAPH_PREVIEW,
        "export_pdbbind_protein_cohort_graph_preview.py",
        refresh=True,
    )
    paper_pdb_split_assessment_preview = _read_json_if_exists(
        DEFAULT_PAPER_PDB_SPLIT_ASSESSMENT_PREVIEW
    )
    pdb_paper_split_leakage_matrix_preview = _read_json_if_exists(
        DEFAULT_PDB_PAPER_SPLIT_LEAKAGE_MATRIX_PREVIEW
    )
    pdb_paper_split_acceptance_gate_preview = _read_json_if_exists(
        DEFAULT_PDB_PAPER_SPLIT_ACCEPTANCE_GATE_PREVIEW
    )
    pdb_paper_split_sequence_signature_audit_preview = _read_json_if_exists(
        DEFAULT_PDB_PAPER_SPLIT_SEQUENCE_SIGNATURE_AUDIT_PREVIEW
    )
    pdb_paper_split_mutation_audit_preview = _read_json_if_exists(
        DEFAULT_PDB_PAPER_SPLIT_MUTATION_AUDIT_PREVIEW
    )
    pdb_paper_split_structure_state_audit_preview = _read_json_if_exists(
        DEFAULT_PDB_PAPER_SPLIT_STRUCTURE_STATE_AUDIT_PREVIEW
    )
    pdb_paper_dataset_quality_verdict_preview = _read_json_if_exists(
        DEFAULT_PDB_PAPER_DATASET_QUALITY_VERDICT_PREVIEW
    )
    pdb_paper_split_remediation_plan_preview = _read_json_if_exists(
        DEFAULT_PDB_PAPER_SPLIT_REMEDIATION_PLAN_PREVIEW
    )
    training_set_baseline_sidecar_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_BASELINE_SIDECAR_PREVIEW,
        "export_seed_plus_neighbors_baseline_sidecar_preview.py",
        refresh=True,
    )
    training_set_multimodal_sidecar_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_MULTIMODAL_SIDECAR_PREVIEW,
        "export_seed_plus_neighbors_multimodal_sidecar_preview.py",
        refresh=True,
    )
    training_packet_summary_preview = _ensure_script_export(
        DEFAULT_TRAINING_PACKET_SUMMARY_PREVIEW,
        "export_training_packet_summary_preview.py",
        refresh=True,
    )
    split_simulation_preview = _ensure_script_export(
        DEFAULT_SPLIT_SIMULATION_PREVIEW,
        "export_split_simulation_preview.py",
        refresh=True,
    )
    training_set_remediation_plan_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_REMEDIATION_PLAN_PREVIEW,
        "export_training_set_remediation_plan_preview.py",
        refresh=True,
    )
    cohort_inclusion_rationale_preview = _ensure_script_export(
        DEFAULT_COHORT_INCLUSION_RATIONALE_PREVIEW,
        "export_cohort_inclusion_rationale_preview.py",
        refresh=True,
    )
    training_set_unblock_plan_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_UNBLOCK_PLAN_PREVIEW,
        "export_training_set_unblock_plan_preview.py",
        refresh=True,
    )
    training_set_gating_evidence_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_GATING_EVIDENCE_PREVIEW,
        "export_training_set_gating_evidence_preview.py",
        refresh=True,
    )
    training_set_action_queue_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_ACTION_QUEUE_PREVIEW,
        "export_training_set_action_queue_preview.py",
        refresh=True,
    )
    training_set_blocker_burndown_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN_PREVIEW,
        "export_training_set_blocker_burndown_preview.py",
        refresh=True,
    )
    training_set_modality_gap_register_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_MODALITY_GAP_REGISTER_PREVIEW,
        "export_training_set_modality_gap_register_preview.py",
        refresh=True,
    )
    training_set_package_blocker_matrix_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_PACKAGE_BLOCKER_MATRIX_PREVIEW,
        "export_training_set_package_blocker_matrix_preview.py",
        refresh=True,
    )
    training_set_gate_ladder_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_GATE_LADDER_PREVIEW,
        "export_training_set_gate_ladder_preview.py",
        refresh=True,
    )
    training_set_unlock_route_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_UNLOCK_ROUTE_PREVIEW,
        "export_training_set_unlock_route_preview.py",
        refresh=True,
    )
    training_set_transition_contract_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_TRANSITION_CONTRACT_PREVIEW,
        "export_training_set_transition_contract_preview.py",
        refresh=True,
    )
    training_set_source_fix_batch_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_SOURCE_FIX_BATCH_PREVIEW,
        "export_training_set_source_fix_batch_preview.py",
        refresh=True,
    )
    training_set_package_transition_batch_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_PACKAGE_TRANSITION_BATCH_PREVIEW,
        "export_training_set_package_transition_batch_preview.py",
        refresh=True,
    )
    training_set_package_execution_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_PACKAGE_EXECUTION_PREVIEW,
        "export_training_set_package_execution_preview.py",
        refresh=True,
    )
    training_packet_completeness_matrix_preview = _ensure_script_export(
        DEFAULT_TRAINING_PACKET_COMPLETENESS_MATRIX_PREVIEW,
        "export_training_packet_completeness_matrix_preview.py",
        refresh=True,
    )
    training_split_alignment_recheck_preview = _ensure_script_export(
        DEFAULT_TRAINING_SPLIT_ALIGNMENT_RECHECK_PREVIEW,
        "export_training_split_alignment_recheck_preview.py",
        refresh=True,
    )
    training_packet_materialization_queue_preview = _ensure_script_export(
        DEFAULT_TRAINING_PACKET_MATERIALIZATION_QUEUE_PREVIEW,
        "export_training_packet_materialization_queue_preview.py",
        refresh=True,
    )
    training_set_preview_hold_register_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_PREVIEW_HOLD_REGISTER_PREVIEW,
        "export_training_set_preview_hold_register_preview.py",
        refresh=True,
    )
    training_set_preview_hold_exit_criteria_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_PREVIEW_HOLD_EXIT_CRITERIA_PREVIEW,
        "export_training_set_preview_hold_exit_criteria_preview.py",
        refresh=True,
    )
    training_set_preview_hold_clearance_batch_preview = _ensure_script_export(
        DEFAULT_TRAINING_SET_PREVIEW_HOLD_CLEARANCE_BATCH_PREVIEW,
        "export_training_set_preview_hold_clearance_batch_preview.py",
        refresh=True,
    )
    external_dataset_flaw_taxonomy_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_FLAW_TAXONOMY_PREVIEW,
        "export_external_dataset_flaw_taxonomy_preview.py",
        refresh=True,
    )
    external_dataset_risk_register_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_RISK_REGISTER_PREVIEW,
        "export_external_dataset_risk_register_preview.py",
        refresh=True,
    )
    external_dataset_conflict_register_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_CONFLICT_REGISTER_PREVIEW,
        "export_external_dataset_conflict_register_preview.py",
        refresh=True,
    )
    external_dataset_issue_matrix_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_ISSUE_MATRIX_PREVIEW,
        "export_external_dataset_issue_matrix_preview.py",
        refresh=True,
    )
    external_dataset_manifest_lint_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_MANIFEST_LINT_PREVIEW,
        "export_external_dataset_manifest_lint_preview.py",
        refresh=True,
    )
    external_dataset_acceptance_gate_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_ACCEPTANCE_GATE_PREVIEW,
        "export_external_dataset_acceptance_gate_preview.py",
        refresh=True,
    )
    external_dataset_admission_decision_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_ADMISSION_DECISION_PREVIEW,
        "export_external_dataset_admission_decision_preview.py",
        refresh=True,
    )
    external_dataset_clearance_delta_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_CLEARANCE_DELTA_PREVIEW,
        "export_external_dataset_clearance_delta_preview.py",
        refresh=True,
    )
    external_dataset_acceptance_path_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_ACCEPTANCE_PATH_PREVIEW,
        "export_external_dataset_acceptance_path_preview.py",
        refresh=True,
    )
    external_dataset_remediation_readiness_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_REMEDIATION_READINESS_PREVIEW,
        "export_external_dataset_remediation_readiness_preview.py",
        refresh=True,
    )
    external_dataset_caveat_execution_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_CAVEAT_EXECUTION_PREVIEW,
        "export_external_dataset_caveat_execution_preview.py",
        refresh=True,
    )
    external_dataset_blocked_acquisition_batch_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_BLOCKED_ACQUISITION_BATCH_PREVIEW,
        "export_external_dataset_blocked_acquisition_batch_preview.py",
        refresh=True,
    )
    external_dataset_acquisition_unblock_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_ACQUISITION_UNBLOCK_PREVIEW,
        "export_external_dataset_acquisition_unblock_preview.py",
        refresh=True,
    )
    external_dataset_advisory_followup_register_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_ADVISORY_FOLLOWUP_REGISTER_PREVIEW,
        "export_external_dataset_advisory_followup_register_preview.py",
        refresh=True,
    )
    external_dataset_caveat_exit_criteria_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_CAVEAT_EXIT_CRITERIA_PREVIEW,
        "export_external_dataset_caveat_exit_criteria_preview.py",
        refresh=True,
    )
    external_dataset_caveat_review_batch_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_CAVEAT_REVIEW_BATCH_PREVIEW,
        "export_external_dataset_caveat_review_batch_preview.py",
        refresh=True,
    )
    external_dataset_resolution_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_RESOLUTION_PREVIEW,
        "export_external_dataset_resolution_preview.py",
        refresh=True,
    )
    external_dataset_resolution_diff_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_RESOLUTION_DIFF_PREVIEW,
        "export_external_dataset_resolution_diff_preview.py",
        refresh=True,
    )
    external_dataset_remediation_template_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_REMEDIATION_TEMPLATE_PREVIEW,
        "export_external_dataset_remediation_template_preview.py",
        refresh=True,
    )
    external_dataset_fixture_catalog_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_FIXTURE_CATALOG_PREVIEW,
        "export_external_dataset_fixture_catalog_preview.py",
        refresh=True,
    )
    external_dataset_remediation_queue_preview = _ensure_script_export(
        DEFAULT_EXTERNAL_DATASET_REMEDIATION_QUEUE_PREVIEW,
        "export_external_dataset_remediation_queue_preview.py",
        refresh=True,
    )
    download_location_audit_preview = _ensure_script_export(
        DEFAULT_DOWNLOAD_LOCATION_AUDIT_PREVIEW,
        "export_download_location_audit_preview.py",
        refresh=True,
    )
    procurement_stale_part_audit_preview = _ensure_script_export(
        DEFAULT_PROCUREMENT_STALE_PART_AUDIT_PREVIEW,
        "export_procurement_stale_part_audit_preview.py",
        refresh=True,
    )
    post_tail_unlock_dry_run_preview = _ensure_script_export(
        DEFAULT_POST_TAIL_UNLOCK_DRY_RUN_PREVIEW,
        "run_post_tail_unlock.py",
        refresh=True,
    )
    scrape_execution_wave_preview = _ensure_script_export(
        DEFAULT_SCRAPE_EXECUTION_WAVE_PREVIEW,
        "export_scrape_execution_wave_preview.py",
        refresh=True,
    )
    scrape_backlog_remaining_preview = _ensure_script_export(
        DEFAULT_SCRAPE_BACKLOG_REMAINING_PREVIEW,
        "export_scrape_backlog_remaining_preview.py",
        refresh=True,
    )
    interaction_string_merge_impact_preview = _ensure_script_export(
        DEFAULT_INTERACTION_STRING_MERGE_IMPACT_PREVIEW,
        "export_interaction_string_merge_impact_preview.py",
        refresh=True,
    )
    split_leakage = coverage["frozen_cohort"]["split_leakage_metadata"]
    coverage_semantics = coverage["semantics"]

    release_target = summary.get("release_target") or {}
    release_bar_closed = bool(release_target.get("benchmark_release_bar_closed"))
    operator_release_ready = bool(release_target.get("operator_release_ready"))
    release_grade_status = summary["status"]
    dashboard_status = release_grade_status

    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "task_id": "P6-T029",
        "dashboard_status": dashboard_status,
        "release_grade_status": release_grade_status,
        "operator_go_no_go": "go" if operator_release_ready else "no-go",
        "truth_boundary": metrics["truth_boundary"],
        "coverage_semantics": coverage_semantics,
        "benchmark_summary": benchmark_summary,
        "metrics_summary": metrics_summary,
        "coverage_summary": coverage_summary,
        "procurement_status": {
            "strong_packet_latest": (
                _compact_packet_latest(packet_latest) if packet_latest is not None else None
            ),
            "canonical_latest": (
                _compact_canonical_latest(canonical_latest)
                if canonical_latest is not None
                else None
            ),
            "tier1_direct_pipeline": (
                _compact_tier1_direct_pipeline(tier1_direct_pipeline)
                if tier1_direct_pipeline is not None
                else None
            ),
            "summary_library_inventory": (
                _compact_summary_library_inventory(summary_library_inventory)
                if summary_library_inventory is not None
                else None
            ),
            "protein_variant_library_inventory": (
                _compact_summary_library_inventory(protein_variant_library_inventory)
                if protein_variant_library_inventory is not None
                else None
            ),
            "structure_unit_library_inventory": (
                _compact_summary_library_inventory(structure_unit_library_inventory)
                if structure_unit_library_inventory is not None
                else None
            ),
            "protein_similarity_signature_preview": (
                _compact_protein_similarity_signature_preview(protein_similarity_signature_preview)
                if protein_similarity_signature_preview is not None
                else None
            ),
            "dictionary_preview": (
                _compact_dictionary_preview(dictionary_preview)
                if dictionary_preview is not None
                else None
            ),
            "motif_domain_compact_preview_family": (
                _compact_motif_domain_compact_preview_family(motif_domain_compact_preview_family)
                if motif_domain_compact_preview_family is not None
                else None
            ),
            "interaction_similarity_signature_preview": (
                _compact_interaction_similarity_signature_preview(
                    interaction_similarity_signature_preview
                )
                if interaction_similarity_signature_preview is not None
                else None
            ),
            "interaction_similarity_signature_validation": (
                _compact_interaction_similarity_signature_validation(
                    interaction_similarity_signature_validation
                )
                if interaction_similarity_signature_validation is not None
                else None
            ),
            "sabio_rk_support_preview": (
                _compact_sabio_rk_support_preview(sabio_rk_support_preview)
                if sabio_rk_support_preview is not None
                else None
            ),
            "kinetics_support_preview": (
                _compact_kinetics_support_preview(kinetics_support_preview)
                if kinetics_support_preview is not None
                else None
            ),
            "compact_enrichment_policy_preview": (
                _compact_compact_enrichment_policy_preview(compact_enrichment_policy_preview)
                if compact_enrichment_policy_preview is not None
                else None
            ),
            "scrape_readiness_registry_preview": (
                _compact_scrape_readiness_registry_preview(scrape_readiness_registry_preview)
                if scrape_readiness_registry_preview is not None
                else None
            ),
            "procurement_source_completion_preview": (
                _compact_procurement_source_completion_preview(
                    procurement_source_completion_preview
                )
                if procurement_source_completion_preview is not None
                else None
            ),
            "string_interaction_materialization_plan_preview": (
                _compact_string_interaction_materialization_plan_preview(
                    string_interaction_materialization_plan_preview
                )
                if string_interaction_materialization_plan_preview is not None
                else None
            ),
            "uniref_cluster_materialization_plan_preview": (
                _compact_uniref_cluster_materialization_plan_preview(
                    uniref_cluster_materialization_plan_preview
                )
                if uniref_cluster_materialization_plan_preview is not None
                else None
            ),
            "pdb_enrichment_scrape_registry_preview": (
                _compact_pdb_enrichment_scrape_registry_preview(
                    pdb_enrichment_scrape_registry_preview
                )
                if pdb_enrichment_scrape_registry_preview is not None
                else None
            ),
            "structure_entry_context_preview": (
                _compact_structure_entry_context_preview(structure_entry_context_preview)
                if structure_entry_context_preview is not None
                else None
            ),
            "pdb_enrichment_harvest_preview": (
                _compact_pdb_enrichment_harvest_preview(pdb_enrichment_harvest_preview)
                if pdb_enrichment_harvest_preview is not None
                else None
            ),
            "pdb_enrichment_validation_preview": (
                _compact_pdb_enrichment_validation_preview(pdb_enrichment_validation_preview)
                if pdb_enrichment_validation_preview is not None
                else None
            ),
            "ligand_context_scrape_registry_preview": (
                _compact_ligand_context_scrape_registry_preview(
                    ligand_context_scrape_registry_preview
                )
                if ligand_context_scrape_registry_preview is not None
                else None
            ),
            "protein_origin_context_preview": (
                _compact_protein_origin_context_preview(protein_origin_context_preview)
                if protein_origin_context_preview is not None
                else None
            ),
            "catalytic_site_context_preview": (
                _compact_catalytic_site_context_preview(catalytic_site_context_preview)
                if catalytic_site_context_preview is not None
                else None
            ),
            "targeted_page_scrape_registry_preview": (
                _compact_targeted_page_scrape_registry_preview(
                    targeted_page_scrape_registry_preview
                )
                if targeted_page_scrape_registry_preview is not None
                else None
            ),
            "binding_measurement_registry_preview": (
                _compact_generic_preview(
                    binding_measurement_registry_preview,
                    extra_summary_keys=(
                        "source_counts",
                        "complex_type_counts",
                        "measurement_type_counts",
                    ),
                )
                if binding_measurement_registry_preview is not None
                else None
            ),
            "binding_measurement_validation_preview": (
                {
                    "status": binding_measurement_validation_preview.get("status"),
                    "validated_row_count": binding_measurement_validation_preview.get(
                        "validated_row_count"
                    ),
                    "issues": binding_measurement_validation_preview.get("issues", []),
                    "report_only": (
                        binding_measurement_validation_preview.get("truth_boundary") or {}
                    ).get("report_only"),
                }
                if binding_measurement_validation_preview is not None
                else None
            ),
            "structure_binding_affinity_context_preview": (
                _compact_generic_preview(
                    structure_binding_affinity_context_preview,
                    extra_summary_keys=("structure_count", "complex_type_counts"),
                )
                if structure_binding_affinity_context_preview is not None
                else None
            ),
            "accession_binding_support_preview": (
                _compact_generic_preview(
                    accession_binding_support_preview,
                    extra_summary_keys=("accessions_with_measurements", "support_status_counts"),
                )
                if accession_binding_support_preview is not None
                else None
            ),
            "structure_chain_origin_preview": (
                _compact_generic_preview(
                    structure_chain_origin_preview,
                    extra_summary_keys=("structure_count", "chain_count"),
                )
                if structure_chain_origin_preview is not None
                else None
            ),
            "structure_ligand_context_preview": (
                _compact_generic_preview(
                    structure_ligand_context_preview,
                    extra_summary_keys=("structure_count", "ligand_count", "ccd_ids"),
                )
                if structure_ligand_context_preview is not None
                else None
            ),
            "structure_assembly_context_preview": (
                _compact_generic_preview(
                    structure_assembly_context_preview,
                    extra_summary_keys=("structure_count",),
                )
                if structure_assembly_context_preview is not None
                else None
            ),
            "structure_validation_context_preview": (
                _compact_generic_preview(
                    structure_validation_context_preview,
                    extra_summary_keys=("structure_count",),
                )
                if structure_validation_context_preview is not None
                else None
            ),
            "structure_publication_context_preview": (
                _compact_generic_preview(
                    structure_publication_context_preview,
                    extra_summary_keys=("structure_count", "pubmed_backed_count"),
                )
                if structure_publication_context_preview is not None
                else None
            ),
            "structure_origin_context_preview": (
                _compact_generic_preview(
                    structure_origin_context_preview,
                    extra_summary_keys=("structure_count",),
                )
                if structure_origin_context_preview is not None
                else None
            ),
            "bound_ligand_character_context_preview": (
                _compact_generic_preview(
                    bound_ligand_character_context_preview,
                    extra_summary_keys=("ligand_count",),
                )
                if bound_ligand_character_context_preview is not None
                else None
            ),
            "ligand_environment_context_preview": (
                _compact_generic_preview(
                    ligand_environment_context_preview,
                    extra_summary_keys=("structure_count",),
                )
                if ligand_environment_context_preview is not None
                else None
            ),
            "interaction_context_preview": (
                _compact_generic_preview(
                    interaction_context_preview,
                    extra_summary_keys=(
                        "accessions_with_intact_rows",
                        "accessions_with_biogrid_rows",
                    ),
                )
                if interaction_context_preview is not None
                else None
            ),
            "interaction_origin_context_preview": (
                _compact_generic_preview(
                    interaction_origin_context_preview,
                    extra_summary_keys=("accessions_with_evidence",),
                )
                if interaction_origin_context_preview is not None
                else None
            ),
            "interaction_partner_context_preview": (
                _compact_generic_preview(
                    interaction_partner_context_preview,
                    extra_summary_keys=("accessions_with_partners",),
                )
                if interaction_partner_context_preview is not None
                else None
            ),
            "protein_function_context_preview": (
                _compact_generic_preview(
                    protein_function_context_preview,
                    extra_summary_keys=("accessions_with_function_comment",),
                )
                if protein_function_context_preview is not None
                else None
            ),
            "protein_feature_context_preview": (
                _compact_generic_preview(
                    protein_feature_context_preview,
                    extra_summary_keys=("accessions_with_features",),
                )
                if protein_feature_context_preview is not None
                else None
            ),
            "protein_reference_context_preview": (
                _compact_generic_preview(
                    protein_reference_context_preview,
                    extra_summary_keys=(
                        "accessions_with_references",
                        "accessions_with_disease_comment",
                    ),
                )
                if protein_reference_context_preview is not None
                else None
            ),
            "enzyme_behavior_context_preview": (
                _compact_generic_preview(
                    enzyme_behavior_context_preview,
                    extra_summary_keys=("supported_now_count",),
                )
                if enzyme_behavior_context_preview is not None
                else None
            ),
            "pdb_chain_projection_contract_preview": (
                {
                    "status": pdb_chain_projection_contract_preview.get("status"),
                    "join_keys": pdb_chain_projection_contract_preview.get("join_keys", []),
                    "projection_targets": pdb_chain_projection_contract_preview.get(
                        "projection_targets", []
                    ),
                    "report_only": (
                        pdb_chain_projection_contract_preview.get("truth_boundary") or {}
                    ).get("report_only"),
                }
                if pdb_chain_projection_contract_preview is not None
                else None
            ),
            "bindingdb_dump_inventory_preview": (
                {
                    "status": bindingdb_dump_inventory_preview.get("status"),
                    "has_mysql_dump": bindingdb_dump_inventory_preview.get("has_mysql_dump"),
                    "sampled_table_count": (
                        (bindingdb_dump_inventory_preview.get("summary") or {}).get(
                            "sampled_table_count"
                        )
                    ),
                    "dump_entry_name": (
                        (bindingdb_dump_inventory_preview.get("summary") or {}).get(
                            "dump_entry_name"
                        )
                    ),
                    "report_only": (
                        bindingdb_dump_inventory_preview.get("truth_boundary") or {}
                    ).get("report_only"),
                }
                if bindingdb_dump_inventory_preview is not None
                else None
            ),
            "bindingdb_target_polymer_context_preview": (
                _compact_generic_preview(
                    bindingdb_target_polymer_context_preview,
                    extra_summary_keys=(
                        "accessions_with_bindingdb_polymer_bridge",
                        "accessions_without_bindingdb_polymer_bridge",
                    ),
                )
                if bindingdb_target_polymer_context_preview is not None
                else None
            ),
            "bindingdb_structure_bridge_preview": (
                _compact_generic_preview(
                    bindingdb_structure_bridge_preview,
                    extra_summary_keys=(
                        "structures_with_bindingdb_bridge",
                        "structures_without_bindingdb_bridge",
                    ),
                )
                if bindingdb_structure_bridge_preview is not None
                else None
            ),
            "bindingdb_measurement_subset_preview": (
                _compact_generic_preview(
                    bindingdb_measurement_subset_preview,
                    extra_summary_keys=(
                        "accessions_with_bindingdb_measurements",
                        "measurement_type_counts",
                    ),
                )
                if bindingdb_measurement_subset_preview is not None
                else None
            ),
            "bindingdb_structure_measurement_projection_preview": (
                _compact_generic_preview(
                    bindingdb_structure_measurement_projection_preview,
                    extra_summary_keys=(
                        "structures_with_bindingdb_measurements",
                        "structures_without_bindingdb_measurements",
                    ),
                )
                if bindingdb_structure_measurement_projection_preview is not None
                else None
            ),
            "bindingdb_partner_monomer_context_preview": (
                _compact_generic_preview(
                    bindingdb_partner_monomer_context_preview,
                    extra_summary_keys=(
                        "monomer_count",
                        "monomers_with_chembl_id",
                        "monomers_with_smiles",
                    ),
                )
                if bindingdb_partner_monomer_context_preview is not None
                else None
            ),
            "bindingdb_structure_assay_summary_preview": (
                _compact_generic_preview(
                    bindingdb_structure_assay_summary_preview,
                    extra_summary_keys=(
                        "structures_with_assay_summary",
                        "structures_with_measurement_technique",
                    ),
                )
                if bindingdb_structure_assay_summary_preview is not None
                else None
            ),
            "bindingdb_accession_assay_profile_preview": (
                _compact_generic_preview(
                    bindingdb_accession_assay_profile_preview,
                    extra_summary_keys=(
                        "accessions_with_assay_profile",
                        "accessions_with_projected_structure_support",
                        "accessions_with_direct_thermodynamics",
                    ),
                )
                if bindingdb_accession_assay_profile_preview is not None
                else None
            ),
            "bindingdb_assay_condition_profile_preview": (
                _compact_generic_preview(
                    bindingdb_assay_condition_profile_preview,
                    extra_summary_keys=(
                        "accessions_with_condition_profile",
                        "accessions_with_reported_pH",
                        "accessions_with_reported_temperature",
                        "accessions_with_concentration_ranges",
                    ),
                )
                if bindingdb_assay_condition_profile_preview is not None
                else None
            ),
            "bindingdb_structure_partner_profile_preview": (
                _compact_generic_preview(
                    bindingdb_structure_partner_profile_preview,
                    extra_summary_keys=(
                        "structures_with_partner_profile",
                        "structures_with_smiles_backed_partners",
                    ),
                )
                if bindingdb_structure_partner_profile_preview is not None
                else None
            ),
            "bindingdb_partner_descriptor_reconciliation_preview": (
                _compact_generic_preview(
                    bindingdb_partner_descriptor_reconciliation_preview,
                    extra_summary_keys=(
                        "partner_monomer_count",
                        "partners_with_seed_structure_overlap",
                        "partners_with_chemistry_descriptors",
                        "reconciliation_status_counts",
                    ),
                )
                if bindingdb_partner_descriptor_reconciliation_preview is not None
                else None
            ),
            "bindingdb_accession_partner_identity_profile_preview": (
                _compact_generic_preview(
                    bindingdb_accession_partner_identity_profile_preview,
                    extra_summary_keys=(
                        "accessions_with_partner_identity_profile",
                        "accessions_with_seed_bridgeable_partners",
                        "accessions_with_descriptor_rich_partners",
                    ),
                )
                if bindingdb_accession_partner_identity_profile_preview is not None
                else None
            ),
            "bindingdb_structure_grounding_candidate_preview": (
                _compact_generic_preview(
                    bindingdb_structure_grounding_candidate_preview,
                    extra_summary_keys=(
                        "accessions_with_seed_structure_support",
                        "accessions_with_future_structure_candidates",
                        "accessions_with_het_code_candidates",
                        "global_future_structure_candidate_count",
                    ),
                )
                if bindingdb_structure_grounding_candidate_preview is not None
                else None
            ),
            "bindingdb_future_structure_registry_preview": (
                _compact_generic_preview(
                    bindingdb_future_structure_registry_preview,
                    extra_summary_keys=(
                        "registered_future_structure_count",
                        "source_accession_count",
                        "structures_with_supporting_het_codes",
                    ),
                )
                if bindingdb_future_structure_registry_preview is not None
                else None
            ),
            "bindingdb_future_structure_context_preview": (
                _compact_generic_preview(
                    bindingdb_future_structure_context_preview,
                    extra_summary_keys=(
                        "harvested_future_structure_count",
                        "structures_with_resolution",
                        "structures_with_bound_components",
                    ),
                )
                if bindingdb_future_structure_context_preview is not None
                else None
            ),
            "bindingdb_future_structure_alignment_preview": (
                _compact_generic_preview(
                    bindingdb_future_structure_alignment_preview,
                    extra_summary_keys=(
                        "aligned_structure_count",
                        "mismatched_structure_count",
                        "unmapped_structure_count",
                        "alignment_status_counts",
                    ),
                )
                if bindingdb_future_structure_alignment_preview is not None
                else None
            ),
            "bindingdb_future_structure_triage_preview": (
                _compact_generic_preview(
                    bindingdb_future_structure_triage_preview,
                    extra_summary_keys=(
                        "direct_grounding_candidate_count",
                        "off_target_adjacent_context_only_count",
                        "followup_needed_count",
                        "triage_status_counts",
                    ),
                )
                if bindingdb_future_structure_triage_preview is not None
                else None
            ),
            "bindingdb_off_target_adjacent_context_profile_preview": (
                _compact_generic_preview(
                    bindingdb_off_target_adjacent_context_profile_preview,
                    extra_summary_keys=(
                        "source_accession_count",
                        "off_target_structure_count",
                        "unique_mapped_target_accession_count",
                    ),
                )
                if bindingdb_off_target_adjacent_context_profile_preview is not None
                else None
            ),
            "bindingdb_off_target_target_profile_preview": (
                _compact_generic_preview(
                    bindingdb_off_target_target_profile_preview,
                    extra_summary_keys=(
                        "mapped_target_accession_count",
                        "off_target_structure_count",
                        "source_accession_count",
                    ),
                )
                if bindingdb_off_target_target_profile_preview is not None
                else None
            ),
            "motif_domain_site_context_preview": (
                _compact_generic_preview(
                    motif_domain_site_context_preview,
                    extra_summary_keys=(
                        "accessions_with_interpro",
                        "accessions_with_site_features",
                        "accessions_with_pfam",
                    ),
                )
                if motif_domain_site_context_preview is not None
                else None
            ),
            "uniref_cluster_context_preview": (
                _compact_generic_preview(
                    uniref_cluster_context_preview,
                    extra_summary_keys=(
                        "accessions_with_uniref100_crossref",
                        "accessions_with_all_identity_levels",
                        "gate_status",
                    ),
                )
                if uniref_cluster_context_preview is not None
                else None
            ),
            "sequence_redundancy_guard_preview": (
                _compact_generic_preview(
                    sequence_redundancy_guard_preview,
                    extra_summary_keys=(
                        "accessions_with_cluster_ids",
                        "shared_cluster_accession_count",
                        "shared_cluster_group_count",
                    ),
                )
                if sequence_redundancy_guard_preview is not None
                else None
            ),
            "post_tail_library_forecast": {
                "string_predicted_family_ids": (
                    [
                        row.get("family_id")
                        for row in (
                            string_interaction_materialization_plan_preview.get("planned_families")
                            or []
                        )
                    ]
                    if string_interaction_materialization_plan_preview is not None
                    else []
                ),
                "string_supported_accession_count": (
                    string_interaction_materialization_plan_preview.get("supported_accession_count")
                    if string_interaction_materialization_plan_preview is not None
                    else None
                ),
                "uniref_supported_accession_count": (
                    uniref_cluster_materialization_plan_preview.get("supported_accession_count")
                    if uniref_cluster_materialization_plan_preview is not None
                    else None
                ),
                "seed_structure_ids": (
                    (pdb_enrichment_scrape_registry_preview.get("summary") or {}).get(
                        "seed_structure_ids", []
                    )
                    if pdb_enrichment_scrape_registry_preview is not None
                    else []
                ),
                "report_only": True,
                "governing": False,
            },
            "binding_coverage": {
                "complex_type_counts": (
                    (binding_measurement_registry_preview.get("summary") or {}).get(
                        "complex_type_counts", {}
                    )
                    if binding_measurement_registry_preview is not None
                    else {}
                ),
                "measurement_type_counts": (
                    (binding_measurement_registry_preview.get("summary") or {}).get(
                        "measurement_type_counts", {}
                    )
                    if binding_measurement_registry_preview is not None
                    else {}
                ),
                "accessions_with_measurements": (
                    (accession_binding_support_preview.get("summary") or {}).get(
                        "accessions_with_measurements"
                    )
                    if accession_binding_support_preview is not None
                    else None
                ),
                "bindingdb_profiled_accession_count": (
                    (bindingdb_accession_assay_profile_preview.get("summary") or {}).get(
                        "accessions_with_assay_profile"
                    )
                    if bindingdb_accession_assay_profile_preview is not None
                    else None
                ),
                "bindingdb_condition_profiled_accession_count": (
                    (bindingdb_assay_condition_profile_preview.get("summary") or {}).get(
                        "accessions_with_condition_profile"
                    )
                    if bindingdb_assay_condition_profile_preview is not None
                    else None
                ),
                "bindingdb_partner_profile_structure_count": (
                    (bindingdb_structure_partner_profile_preview.get("summary") or {}).get(
                        "structures_with_partner_profile"
                    )
                    if bindingdb_structure_partner_profile_preview is not None
                    else None
                ),
                "bindingdb_partner_reconciled_count": (
                    (bindingdb_partner_descriptor_reconciliation_preview.get("summary") or {}).get(
                        "partner_monomer_count"
                    )
                    if bindingdb_partner_descriptor_reconciliation_preview is not None
                    else None
                ),
                "bindingdb_accession_partner_identity_count": (
                    (bindingdb_accession_partner_identity_profile_preview.get("summary") or {}).get(
                        "accessions_with_partner_identity_profile"
                    )
                    if bindingdb_accession_partner_identity_profile_preview is not None
                    else None
                ),
                "bindingdb_future_structure_candidate_accession_count": (
                    (bindingdb_structure_grounding_candidate_preview.get("summary") or {}).get(
                        "accessions_with_future_structure_candidates"
                    )
                    if bindingdb_structure_grounding_candidate_preview is not None
                    else None
                ),
                "bindingdb_seed_structure_supported_accession_count": (
                    (bindingdb_structure_grounding_candidate_preview.get("summary") or {}).get(
                        "accessions_with_seed_structure_support"
                    )
                    if bindingdb_structure_grounding_candidate_preview is not None
                    else None
                ),
                "bindingdb_future_structure_registry_count": (
                    (bindingdb_future_structure_registry_preview.get("summary") or {}).get(
                        "registered_future_structure_count"
                    )
                    if bindingdb_future_structure_registry_preview is not None
                    else None
                ),
                "bindingdb_future_structure_harvested_count": (
                    (bindingdb_future_structure_context_preview.get("summary") or {}).get(
                        "harvested_future_structure_count"
                    )
                    if bindingdb_future_structure_context_preview is not None
                    else None
                ),
                "bindingdb_future_structure_mismatched_count": (
                    (bindingdb_future_structure_alignment_preview.get("summary") or {}).get(
                        "mismatched_structure_count"
                    )
                    if bindingdb_future_structure_alignment_preview is not None
                    else None
                ),
                "bindingdb_future_structure_off_target_count": (
                    (bindingdb_future_structure_triage_preview.get("summary") or {}).get(
                        "off_target_adjacent_context_only_count"
                    )
                    if bindingdb_future_structure_triage_preview is not None
                    else None
                ),
                "bindingdb_off_target_source_accession_count": (
                    (
                        bindingdb_off_target_adjacent_context_profile_preview.get("summary") or {}
                    ).get("source_accession_count")
                    if bindingdb_off_target_adjacent_context_profile_preview is not None
                    else None
                ),
                "bindingdb_off_target_mapped_target_count": (
                    (bindingdb_off_target_target_profile_preview.get("summary") or {}).get(
                        "mapped_target_accession_count"
                    )
                    if bindingdb_off_target_target_profile_preview is not None
                    else None
                ),
                "report_only": True,
                "governing": False,
            },
            "archive_cleanup_keeper_rules_preview": (
                _compact_archive_cleanup_keeper_rules_preview(archive_cleanup_keeper_rules_preview)
                if archive_cleanup_keeper_rules_preview is not None
                else None
            ),
            "procurement_tail_freeze_gate_preview": (
                _compact_procurement_tail_freeze_gate_preview(procurement_tail_freeze_gate_preview)
                if procurement_tail_freeze_gate_preview is not None
                else None
            ),
            "ligand_support_readiness_preview": (
                _compact_ligand_support_readiness_preview(ligand_support_readiness_preview)
                if ligand_support_readiness_preview is not None
                else None
            ),
            "ligand_identity_pilot_preview": (
                _compact_ligand_identity_pilot_preview(ligand_identity_pilot_preview)
                if ligand_identity_pilot_preview is not None
                else None
            ),
            "ligand_stage1_operator_queue_preview": (
                _compact_ligand_stage1_operator_queue_preview(ligand_stage1_operator_queue_preview)
                if ligand_stage1_operator_queue_preview is not None
                else None
            ),
            "p00387_ligand_extraction_validation_preview": (
                _compact_p00387_ligand_extraction_validation_preview(
                    p00387_ligand_extraction_validation_preview
                )
                if p00387_ligand_extraction_validation_preview is not None
                else None
            ),
            "q9nzd4_bridge_validation_preview": (
                _compact_q9nzd4_bridge_validation_preview(q9nzd4_bridge_validation_preview)
                if q9nzd4_bridge_validation_preview is not None
                else None
            ),
            "ligand_stage1_validation_panel_preview": (
                _compact_ligand_stage1_validation_panel_preview(
                    ligand_stage1_validation_panel_preview
                )
                if ligand_stage1_validation_panel_preview is not None
                else None
            ),
            "ligand_identity_core_materialization_preview": (
                _compact_ligand_identity_core_materialization_preview(
                    ligand_identity_core_materialization_preview
                )
                if ligand_identity_core_materialization_preview is not None
                else None
            ),
            "next_real_ligand_row_gate_preview": (
                _compact_next_real_ligand_row_gate_preview(next_real_ligand_row_gate_preview)
                if next_real_ligand_row_gate_preview is not None
                else None
            ),
            "next_real_ligand_row_decision_preview": (
                _compact_next_real_ligand_row_decision_preview(
                    next_real_ligand_row_decision_preview
                )
                if next_real_ligand_row_decision_preview is not None
                else None
            ),
            "ligand_row_materialization_preview": (
                _compact_ligand_row_materialization_preview(ligand_row_materialization_preview)
                if ligand_row_materialization_preview is not None
                else None
            ),
            "ligand_similarity_signature_preview": (
                _compact_ligand_similarity_signature_preview(ligand_similarity_signature_preview)
                if ligand_similarity_signature_preview is not None
                else None
            ),
            "ligand_similarity_signature_gate_preview": (
                _compact_ligand_similarity_signature_gate_preview(
                    ligand_similarity_signature_gate_preview
                )
                if ligand_similarity_signature_gate_preview is not None
                else None
            ),
            "ligand_similarity_signature_validation": (
                _compact_ligand_similarity_signature_validation(
                    ligand_similarity_signature_validation
                )
                if ligand_similarity_signature_validation is not None
                else None
            ),
            "structure_similarity_signature_preview": (
                _compact_structure_similarity_signature_preview(
                    structure_similarity_signature_preview
                )
                if structure_similarity_signature_preview is not None
                else None
            ),
            "structure_variant_bridge_summary": (
                _compact_structure_variant_bridge_summary(structure_variant_bridge_summary)
                if structure_variant_bridge_summary is not None
                else None
            ),
            "structure_variant_candidate_map": (
                _compact_structure_variant_candidate_map(structure_variant_candidate_map)
                if structure_variant_candidate_map is not None
                else None
            ),
            "structure_followup_anchor_candidates": (
                _compact_structure_followup_anchor_candidates(structure_followup_anchor_candidates)
                if structure_followup_anchor_candidates is not None
                else None
            ),
            "structure_followup_anchor_validation": (
                _compact_structure_followup_anchor_validation(structure_followup_anchor_validation)
                if structure_followup_anchor_validation is not None
                else None
            ),
            "structure_followup_payload_preview": (
                _compact_structure_followup_payload_preview(structure_followup_payload_preview)
                if structure_followup_payload_preview is not None
                else None
            ),
            "structure_followup_single_accession_preview": (
                _compact_structure_followup_single_accession_preview(
                    structure_followup_single_accession_preview
                )
                if structure_followup_single_accession_preview is not None
                else None
            ),
            "structure_followup_single_accession_validation_preview": (
                _compact_structure_followup_single_accession_validation_preview(
                    structure_followup_single_accession_validation_preview
                )
                if structure_followup_single_accession_validation_preview is not None
                else None
            ),
            "entity_signature_preview": (
                _compact_entity_signature_preview(entity_signature_preview)
                if entity_signature_preview is not None
                else None
            ),
            "entity_split_candidate_preview": (
                _compact_entity_split_candidate_preview(entity_split_candidate_preview)
                if entity_split_candidate_preview is not None
                else None
            ),
            "entity_split_simulation_preview": (
                _compact_entity_split_simulation_preview(entity_split_simulation_preview)
                if entity_split_simulation_preview is not None
                else None
            ),
            "entity_split_recipe_preview": (
                _compact_entity_split_recipe_preview(entity_split_recipe_preview)
                if entity_split_recipe_preview is not None
                else None
            ),
            "entity_split_assignment_preview": (
                _compact_entity_split_assignment_preview(entity_split_assignment_preview)
                if entity_split_assignment_preview is not None
                else None
            ),
            "split_engine_input_preview": (
                _compact_split_engine_input_preview(split_engine_input_preview)
                if split_engine_input_preview is not None
                else None
            ),
            "split_engine_dry_run_validation": (
                _compact_split_engine_dry_run_validation(split_engine_dry_run_validation)
                if split_engine_dry_run_validation is not None
                else None
            ),
            "split_fold_export_gate_preview": (
                _compact_split_fold_export_gate_preview(split_fold_export_gate_preview)
                if split_fold_export_gate_preview is not None
                else None
            ),
            "split_fold_export_gate_validation": (
                _compact_split_fold_export_gate_validation(split_fold_export_gate_validation)
                if split_fold_export_gate_validation is not None
                else None
            ),
            "split_fold_export_staging_preview": (
                _compact_split_fold_export_staging_preview(split_fold_export_staging_preview)
                if split_fold_export_staging_preview is not None
                else None
            ),
            "split_fold_export_staging_validation": (
                _compact_split_fold_export_staging_validation(split_fold_export_staging_validation)
                if split_fold_export_staging_validation is not None
                else None
            ),
            "split_post_staging_gate_check_preview": (
                _compact_split_post_staging_gate_check_preview(
                    split_post_staging_gate_check_preview
                )
                if split_post_staging_gate_check_preview is not None
                else None
            ),
            "split_post_staging_gate_check_validation": (
                _compact_split_post_staging_gate_check_validation(
                    split_post_staging_gate_check_validation
                )
                if split_post_staging_gate_check_validation is not None
                else None
            ),
            "split_fold_export_request_preview": (
                _compact_split_fold_export_request_preview(split_fold_export_request_preview)
                if split_fold_export_request_preview is not None
                else None
            ),
            "split_fold_export_request_validation": (
                _compact_split_fold_export_request_validation(split_fold_export_request_validation)
                if split_fold_export_request_validation is not None
                else None
            ),
            "operator_accession_coverage_matrix": (
                _compact_operator_accession_coverage_matrix(operator_accession_coverage_matrix)
                if operator_accession_coverage_matrix is not None
                else None
            ),
            "leakage_signature_preview": (
                _compact_leakage_signature_preview(leakage_signature_preview)
                if leakage_signature_preview is not None
                else None
            ),
            "leakage_group_preview": (
                _compact_leakage_group_preview(leakage_group_preview)
                if leakage_group_preview is not None
                else None
            ),
            "bundle_manifest_validation": (
                _compact_bundle_manifest_validation(bundle_manifest_validation)
                if bundle_manifest_validation is not None
                else None
            ),
            "duplicate_cleanup_executor": (
                _compact_duplicate_executor_status(duplicate_executor_status)
                if duplicate_executor_status is not None
                else None
            ),
            "duplicate_cleanup_first_execution_preview": (
                _compact_duplicate_cleanup_first_execution_preview(
                    duplicate_first_execution_preview
                )
                if duplicate_first_execution_preview is not None
                else None
            ),
            "duplicate_cleanup_delete_ready_manifest_preview": (
                _compact_duplicate_cleanup_delete_ready_manifest_preview(
                    duplicate_delete_ready_manifest_preview
                )
                if duplicate_delete_ready_manifest_preview is not None
                else None
            ),
            "duplicate_cleanup_post_delete_verification_contract_preview": (
                _compact_duplicate_cleanup_post_delete_verification_contract_preview(
                    duplicate_post_delete_verification_contract_preview
                )
                if duplicate_post_delete_verification_contract_preview is not None
                else None
            ),
            "duplicate_cleanup_first_execution_batch_manifest_preview": (
                _compact_duplicate_cleanup_first_execution_batch_manifest_preview(
                    duplicate_first_execution_batch_manifest_preview
                )
                if duplicate_first_execution_batch_manifest_preview is not None
                else None
            ),
            "operator_next_actions_preview": (
                _compact_operator_next_actions_preview(operator_next_actions_preview)
                if operator_next_actions_preview is not None
                else None
            ),
            "training_set_eligibility_matrix_preview": (
                _compact_training_set_eligibility_matrix_preview(
                    training_set_eligibility_matrix_preview
                )
                if training_set_eligibility_matrix_preview is not None
                else None
            ),
            "missing_data_policy_preview": (
                _compact_missing_data_policy_preview(missing_data_policy_preview)
                if missing_data_policy_preview is not None
                else None
            ),
            "bindingdb_structure_projection_count": (
                (bindingdb_structure_measurement_projection_preview.get("summary") or {}).get(
                    "structures_with_bindingdb_measurements", 0
                )
                if bindingdb_structure_measurement_projection_preview is not None
                else 0
            ),
            "bindingdb_partner_monomer_count": (
                (bindingdb_partner_monomer_context_preview.get("summary") or {}).get(
                    "monomer_count", 0
                )
                if bindingdb_partner_monomer_context_preview is not None
                else 0
            ),
        },
        "training_set_creation_and_assessment": {
            "seed_plus_neighbors_structured_corpus_preview": (
                _compact_seed_plus_neighbors_structured_corpus_preview(
                    seed_plus_neighbors_structured_corpus_preview
                )
                if seed_plus_neighbors_structured_corpus_preview is not None
                else None
            ),
            "training_set_baseline_sidecar_preview": (
                _compact_training_set_baseline_sidecar_preview(
                    training_set_baseline_sidecar_preview
                )
                if training_set_baseline_sidecar_preview is not None
                else None
            ),
            "training_set_multimodal_sidecar_preview": (
                _compact_training_set_multimodal_sidecar_preview(
                    training_set_multimodal_sidecar_preview
                )
                if training_set_multimodal_sidecar_preview is not None
                else None
            ),
            "training_packet_summary_preview": (
                _compact_training_packet_summary_preview(training_packet_summary_preview)
                if training_packet_summary_preview is not None
                else None
            ),
            "training_set_readiness_preview": (
                _compact_training_set_readiness_preview(training_set_readiness_preview)
                if training_set_readiness_preview is not None
                else None
            ),
            "cohort_compiler_preview": (
                _compact_cohort_compiler_preview(cohort_compiler_preview)
                if cohort_compiler_preview is not None
                else None
            ),
            "balance_diagnostics_preview": (
                _compact_balance_diagnostics_preview(balance_diagnostics_preview)
                if balance_diagnostics_preview is not None
                else None
            ),
            "package_readiness_preview": (
                _compact_package_readiness_preview(package_readiness_preview)
                if package_readiness_preview is not None
                else None
            ),
            "training_set_candidate_package_manifest_preview": (
                _compact_training_set_candidate_package_manifest_preview(
                    training_set_candidate_package_manifest_preview
                )
                if training_set_candidate_package_manifest_preview is not None
                else None
            ),
            "training_packet_completeness_matrix_preview": (
                _compact_training_packet_completeness_matrix_preview(
                    training_packet_completeness_matrix_preview
                )
                if training_packet_completeness_matrix_preview is not None
                else None
            ),
            "training_split_alignment_recheck_preview": (
                _compact_training_split_alignment_recheck_preview(
                    training_split_alignment_recheck_preview
                )
                if training_split_alignment_recheck_preview is not None
                else None
            ),
            "training_packet_materialization_queue_preview": (
                _compact_training_packet_materialization_queue_preview(
                    training_packet_materialization_queue_preview
                )
                if training_packet_materialization_queue_preview is not None
                else None
            ),
            "procurement_process_diagnostics_preview": (
                _compact_procurement_process_diagnostics_preview(
                    procurement_process_diagnostics_preview
                )
                if procurement_process_diagnostics_preview is not None
                else None
            ),
            "split_simulation_preview": (
                _compact_split_simulation_preview(split_simulation_preview)
                if split_simulation_preview is not None
                else None
            ),
            "training_set_remediation_plan_preview": (
                _compact_training_set_remediation_plan_preview(
                    training_set_remediation_plan_preview
                )
                if training_set_remediation_plan_preview is not None
                else None
            ),
            "cohort_inclusion_rationale_preview": (
                _compact_cohort_inclusion_rationale_preview(cohort_inclusion_rationale_preview)
                if cohort_inclusion_rationale_preview is not None
                else None
            ),
            "training_set_unblock_plan_preview": (
                _compact_training_set_unblock_plan_preview(training_set_unblock_plan_preview)
                if training_set_unblock_plan_preview is not None
                else None
            ),
            "training_set_gating_evidence_preview": (
                _compact_training_set_gating_evidence_preview(training_set_gating_evidence_preview)
                if training_set_gating_evidence_preview is not None
                else None
            ),
            "training_set_action_queue_preview": (
                _compact_training_set_action_queue_preview(training_set_action_queue_preview)
                if training_set_action_queue_preview is not None
                else None
            ),
            "training_set_blocker_burndown_preview": (
                _compact_training_set_blocker_burndown_preview(
                    training_set_blocker_burndown_preview
                )
                if training_set_blocker_burndown_preview is not None
                else None
            ),
            "training_set_modality_gap_register_preview": (
                _compact_training_set_modality_gap_register_preview(
                    training_set_modality_gap_register_preview
                )
                if training_set_modality_gap_register_preview is not None
                else None
            ),
            "training_set_package_blocker_matrix_preview": (
                _compact_training_set_package_blocker_matrix_preview(
                    training_set_package_blocker_matrix_preview
                )
                if training_set_package_blocker_matrix_preview is not None
                else None
            ),
            "training_set_gate_ladder_preview": (
                _compact_training_set_gate_ladder_preview(training_set_gate_ladder_preview)
                if training_set_gate_ladder_preview is not None
                else None
            ),
            "training_set_unlock_route_preview": (
                _compact_training_set_unlock_route_preview(training_set_unlock_route_preview)
                if training_set_unlock_route_preview is not None
                else None
            ),
            "training_set_transition_contract_preview": (
                _compact_training_set_transition_contract_preview(
                    training_set_transition_contract_preview
                )
                if training_set_transition_contract_preview is not None
                else None
            ),
            "training_set_source_fix_batch_preview": (
                _compact_training_set_source_fix_batch_preview(
                    training_set_source_fix_batch_preview
                )
                if training_set_source_fix_batch_preview is not None
                else None
            ),
            "training_set_package_transition_batch_preview": (
                _compact_training_set_package_transition_batch_preview(
                    training_set_package_transition_batch_preview
                )
                if training_set_package_transition_batch_preview is not None
                else None
            ),
            "training_set_package_execution_preview": (
                _compact_training_set_package_execution_preview(
                    training_set_package_execution_preview
                )
                if training_set_package_execution_preview is not None
                else None
            ),
            "training_set_preview_hold_register_preview": (
                _compact_training_set_preview_hold_register_preview(
                    training_set_preview_hold_register_preview
                )
                if training_set_preview_hold_register_preview is not None
                else None
            ),
            "training_set_preview_hold_exit_criteria_preview": (
                _compact_training_set_preview_hold_exit_criteria_preview(
                    training_set_preview_hold_exit_criteria_preview
                )
                if training_set_preview_hold_exit_criteria_preview is not None
                else None
            ),
            "training_set_preview_hold_clearance_batch_preview": (
                _compact_training_set_preview_hold_clearance_batch_preview(
                    training_set_preview_hold_clearance_batch_preview
                )
                if training_set_preview_hold_clearance_batch_preview is not None
                else None
            ),
            "training_set_builder_session_preview": (
                _compact_training_set_builder_session_preview(training_set_builder_session_preview)
                if training_set_builder_session_preview is not None
                else None
            ),
            "training_set_builder_runbook_preview": (
                _compact_training_set_builder_runbook_preview(training_set_builder_runbook_preview)
                if training_set_builder_runbook_preview is not None
                else None
            ),
            "final_structured_dataset_bundle_preview": (
                _compact_final_structured_dataset_bundle_preview(
                    final_structured_dataset_bundle_preview
                )
                if final_structured_dataset_bundle_preview is not None
                else None
            ),
            "pdbbind_expanded_structured_corpus_preview": (
                _compact_pdbbind_expanded_structured_corpus_preview(
                    pdbbind_expanded_structured_corpus_preview
                )
                if pdbbind_expanded_structured_corpus_preview is not None
                else None
            ),
            "pdbbind_protein_cohort_graph_preview": (
                _compact_pdbbind_protein_cohort_graph_preview(
                    pdbbind_protein_cohort_graph_preview
                )
                if pdbbind_protein_cohort_graph_preview is not None
                else None
            ),
            "paper_pdb_split_assessment_preview": (
                _compact_paper_pdb_split_assessment(paper_pdb_split_assessment_preview)
                if paper_pdb_split_assessment_preview is not None
                else None
            ),
            "pdb_paper_split_leakage_matrix_preview": (
                _compact_pdb_paper_split_leakage_matrix(
                    pdb_paper_split_leakage_matrix_preview
                )
                if pdb_paper_split_leakage_matrix_preview is not None
                else None
            ),
            "pdb_paper_split_acceptance_gate_preview": (
                _compact_pdb_paper_split_acceptance_gate(
                    pdb_paper_split_acceptance_gate_preview
                )
                if pdb_paper_split_acceptance_gate_preview is not None
                else None
            ),
            "pdb_paper_split_sequence_signature_audit_preview": (
                _compact_pdb_paper_split_sequence_signature_audit(
                    pdb_paper_split_sequence_signature_audit_preview
                )
                if pdb_paper_split_sequence_signature_audit_preview is not None
                else None
            ),
            "pdb_paper_split_mutation_audit_preview": (
                _compact_pdb_paper_split_mutation_audit(
                    pdb_paper_split_mutation_audit_preview
                )
                if pdb_paper_split_mutation_audit_preview is not None
                else None
            ),
            "pdb_paper_split_structure_state_audit_preview": (
                _compact_pdb_paper_split_structure_state_audit(
                    pdb_paper_split_structure_state_audit_preview
                )
                if pdb_paper_split_structure_state_audit_preview is not None
                else None
            ),
            "pdb_paper_dataset_quality_verdict_preview": (
                _compact_pdb_paper_dataset_quality_verdict(
                    pdb_paper_dataset_quality_verdict_preview
                )
                if pdb_paper_dataset_quality_verdict_preview is not None
                else None
            ),
            "pdb_paper_split_remediation_plan_preview": (
                _compact_pdb_paper_split_remediation_plan(
                    pdb_paper_split_remediation_plan_preview
                )
                if pdb_paper_split_remediation_plan_preview is not None
                else None
            ),
            "release_grade_readiness_preview": (
                _compact_release_grade_readiness_preview(release_grade_readiness_preview)
                if release_grade_readiness_preview is not None
                else None
            ),
            "release_grade_closure_queue_preview": (
                _compact_release_grade_closure_queue_preview(
                    release_grade_closure_queue_preview
                )
                if release_grade_closure_queue_preview is not None
                else None
            ),
            "release_runtime_maturity_preview": (
                _compact_release_runtime_maturity_preview(release_runtime_maturity_preview)
                if release_runtime_maturity_preview is not None
                else None
            ),
            "release_source_coverage_depth_preview": (
                _compact_release_source_coverage_depth_preview(
                    release_source_coverage_depth_preview
                )
                if release_source_coverage_depth_preview is not None
                else None
            ),
            "release_provenance_depth_preview": (
                _compact_release_provenance_depth_preview(release_provenance_depth_preview)
                if release_provenance_depth_preview is not None
                else None
            ),
            "release_grade_runbook_preview": (
                _compact_release_grade_runbook_preview(release_grade_runbook_preview)
                if release_grade_runbook_preview is not None
                else None
            ),
            "release_accession_closure_matrix_preview": (
                _compact_release_accession_closure_matrix_preview(
                    release_accession_closure_matrix_preview
                )
                if release_accession_closure_matrix_preview is not None
                else None
            ),
            "release_accession_action_queue_preview": (
                _compact_release_accession_action_queue_preview(
                    release_accession_action_queue_preview
                )
                if release_accession_action_queue_preview is not None
                else None
            ),
            "release_promotion_gate_preview": (
                _compact_release_promotion_gate_preview(release_promotion_gate_preview)
                if release_promotion_gate_preview is not None
                else None
            ),
            "release_source_fix_followup_batch_preview": (
                _compact_release_source_fix_followup_batch_preview(
                    release_source_fix_followup_batch_preview
                )
                if release_source_fix_followup_batch_preview is not None
                else None
            ),
            "release_candidate_promotion_preview": (
                _compact_release_candidate_promotion_preview(
                    release_candidate_promotion_preview
                )
                if release_candidate_promotion_preview is not None
                else None
            ),
            "release_runtime_qualification_preview": (
                _compact_release_runtime_qualification_preview(
                    release_runtime_qualification_preview
                )
                if release_runtime_qualification_preview is not None
                else None
            ),
            "release_governing_sufficiency_preview": (
                _compact_release_governing_sufficiency_preview(
                    release_governing_sufficiency_preview
                )
                if release_governing_sufficiency_preview is not None
                else None
            ),
            "release_accession_evidence_pack_preview": (
                _compact_release_accession_evidence_pack_preview(
                    release_accession_evidence_pack_preview
                )
                if release_accession_evidence_pack_preview is not None
                else None
            ),
            "release_reporting_completeness_preview": (
                _compact_release_reporting_completeness_preview(
                    release_reporting_completeness_preview
                )
                if release_reporting_completeness_preview is not None
                else None
            ),
            "release_blocker_resolution_board_preview": (
                _compact_release_blocker_resolution_board_preview(
                    release_blocker_resolution_board_preview
                )
                if release_blocker_resolution_board_preview is not None
                else None
            ),
            "procurement_external_drive_mount_preview": (
                _compact_procurement_external_drive_mount_preview(
                    procurement_external_drive_mount_preview
                )
                if procurement_external_drive_mount_preview is not None
                else None
            ),
            "procurement_expansion_wave_preview": (
                _compact_procurement_expansion_wave_preview(procurement_expansion_wave_preview)
                if procurement_expansion_wave_preview is not None
                else None
            ),
            "procurement_expansion_storage_budget_preview": (
                _compact_procurement_expansion_storage_budget_preview(
                    procurement_expansion_storage_budget_preview
                )
                if procurement_expansion_storage_budget_preview is not None
                else None
            ),
            "missing_scrape_family_contracts_preview": (
                _compact_missing_scrape_family_contracts_preview(
                    missing_scrape_family_contracts_preview
                )
                if missing_scrape_family_contracts_preview is not None
                else None
            ),
            "external_dataset_intake_contract_preview": (
                _compact_external_dataset_intake_contract_preview(
                    external_dataset_intake_contract_preview
                )
                if external_dataset_intake_contract_preview is not None
                else None
            ),
            "external_dataset_assessment_preview": (
                _compact_external_dataset_assessment_preview(external_dataset_assessment_preview)
                if external_dataset_assessment_preview is not None
                else None
            ),
            "external_dataset_flaw_taxonomy_preview": (
                _compact_external_dataset_flaw_taxonomy_preview(
                    external_dataset_flaw_taxonomy_preview
                )
                if external_dataset_flaw_taxonomy_preview is not None
                else None
            ),
            "external_dataset_risk_register_preview": (
                _compact_external_dataset_risk_register_preview(
                    external_dataset_risk_register_preview
                )
                if external_dataset_risk_register_preview is not None
                else None
            ),
            "external_dataset_conflict_register_preview": (
                _compact_external_dataset_conflict_register_preview(
                    external_dataset_conflict_register_preview
                )
                if external_dataset_conflict_register_preview is not None
                else None
            ),
            "external_dataset_issue_matrix_preview": (
                _compact_external_dataset_issue_matrix_preview(
                    external_dataset_issue_matrix_preview
                )
                if external_dataset_issue_matrix_preview is not None
                else None
            ),
            "external_dataset_manifest_lint_preview": (
                _compact_external_dataset_manifest_lint_preview(
                    external_dataset_manifest_lint_preview
                )
                if external_dataset_manifest_lint_preview is not None
                else None
            ),
            "external_dataset_acceptance_gate_preview": (
                _compact_external_dataset_acceptance_gate_preview(
                    external_dataset_acceptance_gate_preview
                )
                if external_dataset_acceptance_gate_preview is not None
                else None
            ),
            "external_dataset_admission_decision_preview": (
                _compact_external_dataset_admission_decision_preview(
                    external_dataset_admission_decision_preview
                )
                if external_dataset_admission_decision_preview is not None
                else None
            ),
            "external_dataset_clearance_delta_preview": (
                _compact_external_dataset_clearance_delta_preview(
                    external_dataset_clearance_delta_preview
                )
                if external_dataset_clearance_delta_preview is not None
                else None
            ),
            "external_dataset_acceptance_path_preview": (
                _compact_external_dataset_acceptance_path_preview(
                    external_dataset_acceptance_path_preview
                )
                if external_dataset_acceptance_path_preview is not None
                else None
            ),
            "external_dataset_remediation_readiness_preview": (
                _compact_external_dataset_remediation_readiness_preview(
                    external_dataset_remediation_readiness_preview
                )
                if external_dataset_remediation_readiness_preview is not None
                else None
            ),
            "external_dataset_caveat_execution_preview": (
                _compact_external_dataset_caveat_execution_preview(
                    external_dataset_caveat_execution_preview
                )
                if external_dataset_caveat_execution_preview is not None
                else None
            ),
            "external_dataset_blocked_acquisition_batch_preview": (
                _compact_external_dataset_blocked_acquisition_batch_preview(
                    external_dataset_blocked_acquisition_batch_preview
                )
                if external_dataset_blocked_acquisition_batch_preview is not None
                else None
            ),
            "external_dataset_acquisition_unblock_preview": (
                _compact_external_dataset_acquisition_unblock_preview(
                    external_dataset_acquisition_unblock_preview
                )
                if external_dataset_acquisition_unblock_preview is not None
                else None
            ),
            "external_dataset_advisory_followup_register_preview": (
                _compact_external_dataset_advisory_followup_register_preview(
                    external_dataset_advisory_followup_register_preview
                )
                if external_dataset_advisory_followup_register_preview is not None
                else None
            ),
            "external_dataset_caveat_exit_criteria_preview": (
                _compact_external_dataset_caveat_exit_criteria_preview(
                    external_dataset_caveat_exit_criteria_preview
                )
                if external_dataset_caveat_exit_criteria_preview is not None
                else None
            ),
            "external_dataset_caveat_review_batch_preview": (
                _compact_external_dataset_caveat_review_batch_preview(
                    external_dataset_caveat_review_batch_preview
                )
                if external_dataset_caveat_review_batch_preview is not None
                else None
            ),
            "external_dataset_resolution_preview": (
                _compact_external_dataset_resolution_preview(external_dataset_resolution_preview)
                if external_dataset_resolution_preview is not None
                else None
            ),
            "external_dataset_resolution_diff_preview": (
                _compact_external_dataset_resolution_diff_preview(
                    external_dataset_resolution_diff_preview
                )
                if external_dataset_resolution_diff_preview is not None
                else None
            ),
            "external_dataset_remediation_template_preview": (
                _compact_external_dataset_remediation_template_preview(
                    external_dataset_remediation_template_preview
                )
                if external_dataset_remediation_template_preview is not None
                else None
            ),
            "external_dataset_fixture_catalog_preview": (
                _compact_external_dataset_fixture_catalog_preview(
                    external_dataset_fixture_catalog_preview
                )
                if external_dataset_fixture_catalog_preview is not None
                else None
            ),
            "external_dataset_remediation_queue_preview": (
                _compact_external_dataset_remediation_queue_preview(
                    external_dataset_remediation_queue_preview
                )
                if external_dataset_remediation_queue_preview is not None
                else None
            ),
            "sample_external_dataset_assessment_bundle_preview": (
                _compact_sample_external_dataset_assessment_bundle_preview(
                    sample_external_dataset_assessment_bundle_preview
                )
                if sample_external_dataset_assessment_bundle_preview is not None
                else None
            ),
            "external_dataset_leakage_audit_preview": (
                _compact_sub_audit_preview(external_dataset_leakage_audit_preview)
                if external_dataset_leakage_audit_preview is not None
                else None
            ),
            "external_dataset_modality_audit_preview": (
                _compact_sub_audit_preview(external_dataset_modality_audit_preview)
                if external_dataset_modality_audit_preview is not None
                else None
            ),
            "external_dataset_binding_audit_preview": (
                _compact_sub_audit_preview(external_dataset_binding_audit_preview)
                if external_dataset_binding_audit_preview is not None
                else None
            ),
            "external_dataset_structure_audit_preview": (
                _compact_sub_audit_preview(external_dataset_structure_audit_preview)
                if external_dataset_structure_audit_preview is not None
                else None
            ),
            "external_dataset_provenance_audit_preview": (
                _compact_sub_audit_preview(external_dataset_provenance_audit_preview)
                if external_dataset_provenance_audit_preview is not None
                else None
            ),
            "binding_measurement_suspect_rows_preview": (
                _compact_binding_measurement_suspect_rows_preview(
                    binding_measurement_suspect_rows_preview
                )
                if binding_measurement_suspect_rows_preview is not None
                else None
            ),
            "cross_source_duplicate_measurement_audit_preview": (
                _compact_cross_source_duplicate_measurement_audit_preview(
                    cross_source_duplicate_measurement_audit_preview
                )
                if cross_source_duplicate_measurement_audit_preview is not None
                else None
            ),
        },
        "overnight_parallel": {
            "procurement_source_completion_preview": (
                _compact_procurement_source_completion_preview(
                    procurement_source_completion_preview
                )
                if procurement_source_completion_preview is not None
                else None
            ),
            "string_interaction_materialization_preview": (
                _compact_string_interaction_materialization_preview(
                    string_interaction_materialization_preview
                )
                if string_interaction_materialization_preview is not None
                else None
            ),
            "scrape_gap_matrix_preview": (
                _compact_scrape_gap_matrix_preview(scrape_gap_matrix_preview)
                if scrape_gap_matrix_preview is not None
                else None
            ),
            "scrape_execution_wave_preview": (
                _compact_scrape_execution_wave_preview(scrape_execution_wave_preview)
                if scrape_execution_wave_preview is not None
                else None
            ),
            "scrape_backlog_remaining_preview": (
                _compact_scrape_backlog_remaining_preview(scrape_backlog_remaining_preview)
                if scrape_backlog_remaining_preview is not None
                else None
            ),
            "overnight_queue_backlog_preview": (
                _compact_overnight_queue_backlog_preview(overnight_queue_backlog_preview)
                if overnight_queue_backlog_preview is not None
                else None
            ),
            "overnight_execution_contract_preview": (
                _compact_overnight_execution_contract_preview(overnight_execution_contract_preview)
                if overnight_execution_contract_preview is not None
                else None
            ),
            "overnight_queue_repair_status": (
                _compact_overnight_queue_repair_status(overnight_queue_repair_status)
                if overnight_queue_repair_status is not None
                else None
            ),
            "overnight_idle_status_preview": (
                _compact_overnight_idle_status_preview(overnight_idle_status_preview)
                if overnight_idle_status_preview is not None
                else None
            ),
            "overnight_pending_reconciliation_preview": (
                _compact_overnight_pending_reconciliation_preview(
                    overnight_pending_reconciliation_preview
                )
                if overnight_pending_reconciliation_preview is not None
                else None
            ),
            "overnight_worker_launch_gap_preview": (
                _compact_overnight_worker_launch_gap_preview(overnight_worker_launch_gap_preview)
                if overnight_worker_launch_gap_preview is not None
                else None
            ),
            "procurement_supervisor_freshness_preview": (
                _compact_procurement_supervisor_freshness_preview(
                    procurement_supervisor_freshness_preview
                )
                if procurement_supervisor_freshness_preview is not None
                else None
            ),
            "download_location_audit_preview": (
                _compact_download_location_audit_preview(download_location_audit_preview)
                if download_location_audit_preview is not None
                else None
            ),
            "procurement_stale_part_audit_preview": (
                _compact_procurement_stale_part_audit_preview(procurement_stale_part_audit_preview)
                if procurement_stale_part_audit_preview is not None
                else None
            ),
            "post_tail_unlock_dry_run_preview": (
                _compact_post_tail_unlock_dry_run_preview(post_tail_unlock_dry_run_preview)
                if post_tail_unlock_dry_run_preview is not None
                else None
            ),
            "procurement_tail_signal_reconciliation_preview": (
                _compact_procurement_tail_signal_reconciliation_preview(
                    procurement_tail_signal_reconciliation_preview
                )
                if procurement_tail_signal_reconciliation_preview is not None
                else None
            ),
            "procurement_tail_growth_preview": (
                _compact_procurement_tail_growth_preview(procurement_tail_growth_preview)
                if procurement_tail_growth_preview is not None
                else None
            ),
            "procurement_headroom_guard_preview": (
                _compact_procurement_headroom_guard_preview(procurement_headroom_guard_preview)
                if procurement_headroom_guard_preview is not None
                else None
            ),
            "procurement_tail_space_drift_preview": (
                _compact_procurement_tail_space_drift_preview(procurement_tail_space_drift_preview)
                if procurement_tail_space_drift_preview is not None
                else None
            ),
            "procurement_tail_source_pressure_preview": (
                _compact_procurement_tail_source_pressure_preview(
                    procurement_tail_source_pressure_preview
                )
                if procurement_tail_source_pressure_preview is not None
                else None
            ),
            "procurement_tail_log_progress_registry_preview": (
                _compact_procurement_tail_log_progress_registry_preview(
                    procurement_tail_log_progress_registry_preview
                )
                if procurement_tail_log_progress_registry_preview is not None
                else None
            ),
            "procurement_tail_completion_margin_preview": (
                _compact_procurement_tail_completion_margin_preview(
                    procurement_tail_completion_margin_preview
                )
                if procurement_tail_completion_margin_preview is not None
                else None
            ),
            "procurement_space_recovery_target_preview": (
                _compact_procurement_space_recovery_target_preview(
                    procurement_space_recovery_target_preview
                )
                if procurement_space_recovery_target_preview is not None
                else None
            ),
            "procurement_space_recovery_candidates_preview": (
                _compact_procurement_space_recovery_candidates_preview(
                    procurement_space_recovery_candidates_preview
                )
                if procurement_space_recovery_candidates_preview is not None
                else None
            ),
            "procurement_space_recovery_execution_batch_preview": (
                _compact_procurement_space_recovery_execution_batch_preview(
                    procurement_space_recovery_execution_batch_preview
                )
                if procurement_space_recovery_execution_batch_preview is not None
                else None
            ),
            "procurement_space_recovery_safety_register_preview": (
                _compact_procurement_space_recovery_safety_register_preview(
                    procurement_space_recovery_safety_register_preview
                )
                if procurement_space_recovery_safety_register_preview is not None
                else None
            ),
            "procurement_tail_fill_risk_preview": (
                _compact_procurement_tail_fill_risk_preview(procurement_tail_fill_risk_preview)
                if procurement_tail_fill_risk_preview is not None
                else None
            ),
            "procurement_space_recovery_trigger_preview": (
                _compact_procurement_space_recovery_trigger_preview(
                    procurement_space_recovery_trigger_preview
                )
                if procurement_space_recovery_trigger_preview is not None
                else None
            ),
            "procurement_space_recovery_gap_drift_preview": (
                _compact_procurement_space_recovery_gap_drift_preview(
                    procurement_space_recovery_gap_drift_preview
                )
                if procurement_space_recovery_gap_drift_preview is not None
                else None
            ),
            "procurement_space_recovery_coverage_preview": (
                _compact_procurement_space_recovery_coverage_preview(
                    procurement_space_recovery_coverage_preview
                )
                if procurement_space_recovery_coverage_preview is not None
                else None
            ),
            "procurement_recovery_intervention_priority_preview": (
                _compact_procurement_recovery_intervention_priority_preview(
                    procurement_recovery_intervention_priority_preview
                )
                if procurement_recovery_intervention_priority_preview is not None
                else None
            ),
            "procurement_recovery_escalation_lane_preview": (
                _compact_procurement_recovery_escalation_lane_preview(
                    procurement_recovery_escalation_lane_preview
                )
                if procurement_recovery_escalation_lane_preview is not None
                else None
            ),
            "procurement_space_recovery_concentration_preview": (
                _compact_procurement_space_recovery_concentration_preview(
                    procurement_space_recovery_concentration_preview
                )
                if procurement_space_recovery_concentration_preview is not None
                else None
            ),
            "procurement_recovery_shortfall_bridge_preview": (
                _compact_procurement_recovery_shortfall_bridge_preview(
                    procurement_recovery_shortfall_bridge_preview
                )
                if procurement_recovery_shortfall_bridge_preview is not None
                else None
            ),
            "procurement_recovery_lane_fragility_preview": (
                _compact_procurement_recovery_lane_fragility_preview(
                    procurement_recovery_lane_fragility_preview
                )
                if procurement_recovery_lane_fragility_preview is not None
                else None
            ),
            "procurement_broader_search_trigger_preview": (
                _compact_procurement_broader_search_trigger_preview(
                    procurement_broader_search_trigger_preview
                )
                if procurement_broader_search_trigger_preview is not None
                else None
            ),
            "overnight_wave_advance_preview": (
                _compact_overnight_wave_advance_preview(overnight_wave_advance_preview)
                if overnight_wave_advance_preview is not None
                else None
            ),
            "interaction_string_merge_impact_preview": (
                _compact_interaction_string_merge_impact_preview(
                    interaction_string_merge_impact_preview
                )
                if interaction_string_merge_impact_preview is not None
                else None
            ),
        },
        "assessment": {
            "ready_for_release": operator_release_ready,
            "benchmark_release_bar_closed": release_bar_closed,
            "prototype_runtime_completed": bool(
                (summary.get("runtime") or {}).get("final_status") == "completed"
            ),
            "release_grade_blocked": not release_bar_closed,
            "coverage_not_validation": coverage_semantics["coverage_not_validation"],
            "release_grade_corpus_validation": coverage_semantics[
                "release_grade_corpus_validation"
            ],
            "mixed_evidence_rows_are_conservative": coverage_semantics[
                "mixed_evidence_rows_are_conservative"
            ],
            "leakage_ready": bool(
                split_leakage["accession_level_only"]
                and not split_leakage["cross_split_duplicates"]
            ),
            "identity_safe_resume": (
                metrics["runtime"]["resume_continuity"]["declared"] == "identity-safe"
            ),
            "strong_enough_for_truthful_rerun": [
                "frozen cohort exists and is leakage-ready",
                "12 accessions are resolved with 8/2/2 split counts",
                "processed-example counts and checkpoint continuity are consistent",
                "coverage and metrics artifacts agree on cohort size",
                "coverage is conservative inventory rather than validation",
            ],
            "expansion_wave_deferred": (
                (procurement_expansion_wave_preview or {}).get("summary", {}).get(
                    "ready_to_execute_count"
                )
                == 0
            ),
            "missing_scrape_family_count": (
                (missing_scrape_family_contracts_preview or {}).get("summary", {}).get(
                    "missing_lane_count"
                )
            ),
        },
        "blockers": _build_blockers(
            coverage=coverage,
            metrics=metrics,
            summary=summary,
        ),
        "source_files": {
            "source_coverage": str(coverage_path).replace("\\", "/"),
            "metrics_summary": str(metrics_path).replace("\\", "/"),
            "benchmark_summary": str(summary_path).replace("\\", "/"),
            "packet_deficit_dashboard": (
                str(packet_deficit_path).replace("\\", "/") if packet_latest is not None else None
            ),
            "canonical_latest": (
                str(canonical_latest_path).replace("\\", "/")
                if canonical_latest is not None
                else None
            ),
            "tier1_direct_pipeline": (
                str(tier1_direct_pipeline_path).replace("\\", "/")
                if tier1_direct_pipeline is not None
                else None
            ),
            "summary_library_inventory": (
                str(summary_library_inventory_path).replace("\\", "/")
                if summary_library_inventory is not None
                else None
            ),
            "structure_unit_library_inventory": (
                str(structure_unit_library_inventory_path).replace("\\", "/")
                if structure_unit_library_inventory is not None
                else None
            ),
            "protein_similarity_signature_preview": (
                str(protein_similarity_signature_preview_path).replace("\\", "/")
                if protein_similarity_signature_preview is not None
                else None
            ),
            "dictionary_preview": (
                str(dictionary_preview_path).replace("\\", "/")
                if dictionary_preview is not None
                else None
            ),
            "motif_domain_compact_preview_family": (
                str(motif_domain_compact_preview_family_path).replace("\\", "/")
                if motif_domain_compact_preview_family is not None
                else None
            ),
            "interaction_similarity_signature_preview": (
                str(interaction_similarity_signature_preview_path).replace("\\", "/")
                if interaction_similarity_signature_preview is not None
                else None
            ),
            "interaction_similarity_signature_validation": (
                str(interaction_similarity_signature_validation_path).replace("\\", "/")
                if interaction_similarity_signature_validation is not None
                else None
            ),
            "sabio_rk_support_preview": (
                str(sabio_rk_support_preview_path).replace("\\", "/")
                if sabio_rk_support_preview is not None
                else None
            ),
            "kinetics_support_preview": (
                str(kinetics_support_preview_path).replace("\\", "/")
                if kinetics_support_preview is not None
                else None
            ),
            "compact_enrichment_policy_preview": (
                str(compact_enrichment_policy_preview_path).replace("\\", "/")
                if compact_enrichment_policy_preview is not None
                else None
            ),
            "scrape_readiness_registry_preview": (
                str(scrape_readiness_registry_preview_path).replace("\\", "/")
                if scrape_readiness_registry_preview is not None
                else None
            ),
            "string_interaction_materialization_preview": (
                str(string_interaction_materialization_preview_path).replace("\\", "/")
                if string_interaction_materialization_preview is not None
                else None
            ),
            "string_interaction_materialization_plan_preview": (
                str(string_interaction_materialization_plan_preview_path).replace("\\", "/")
                if string_interaction_materialization_plan_preview is not None
                else None
            ),
            "uniref_cluster_materialization_plan_preview": (
                str(uniref_cluster_materialization_plan_preview_path).replace("\\", "/")
                if uniref_cluster_materialization_plan_preview is not None
                else None
            ),
            "pdb_enrichment_scrape_registry_preview": (
                str(pdb_enrichment_scrape_registry_preview_path).replace("\\", "/")
                if pdb_enrichment_scrape_registry_preview is not None
                else None
            ),
            "structure_entry_context_preview": (
                str(structure_entry_context_preview_path).replace("\\", "/")
                if structure_entry_context_preview is not None
                else None
            ),
            "pdb_enrichment_harvest_preview": (
                str(pdb_enrichment_harvest_preview_path).replace("\\", "/")
                if pdb_enrichment_harvest_preview is not None
                else None
            ),
            "pdb_enrichment_validation_preview": (
                str(pdb_enrichment_validation_preview_path).replace("\\", "/")
                if pdb_enrichment_validation_preview is not None
                else None
            ),
            "ligand_context_scrape_registry_preview": (
                str(ligand_context_scrape_registry_preview_path).replace("\\", "/")
                if ligand_context_scrape_registry_preview is not None
                else None
            ),
            "protein_origin_context_preview": (
                str(protein_origin_context_preview_path).replace("\\", "/")
                if protein_origin_context_preview is not None
                else None
            ),
            "catalytic_site_context_preview": (
                str(catalytic_site_context_preview_path).replace("\\", "/")
                if catalytic_site_context_preview is not None
                else None
            ),
            "targeted_page_scrape_registry_preview": (
                str(targeted_page_scrape_registry_preview_path).replace("\\", "/")
                if targeted_page_scrape_registry_preview is not None
                else None
            ),
            "bindingdb_structure_measurement_projection_preview": (
                str(DEFAULT_BINDINGDB_STRUCTURE_MEASUREMENT_PROJECTION_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_structure_measurement_projection_preview is not None
                else None
            ),
            "bindingdb_partner_monomer_context_preview": (
                str(DEFAULT_BINDINGDB_PARTNER_MONOMER_CONTEXT_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_partner_monomer_context_preview is not None
                else None
            ),
            "bindingdb_structure_assay_summary_preview": (
                str(DEFAULT_BINDINGDB_STRUCTURE_ASSAY_SUMMARY_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_structure_assay_summary_preview is not None
                else None
            ),
            "bindingdb_accession_assay_profile_preview": (
                str(DEFAULT_BINDINGDB_ACCESSION_ASSAY_PROFILE_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_accession_assay_profile_preview is not None
                else None
            ),
            "bindingdb_assay_condition_profile_preview": (
                str(DEFAULT_BINDINGDB_ASSAY_CONDITION_PROFILE_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_assay_condition_profile_preview is not None
                else None
            ),
            "bindingdb_structure_partner_profile_preview": (
                str(DEFAULT_BINDINGDB_STRUCTURE_PARTNER_PROFILE_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_structure_partner_profile_preview is not None
                else None
            ),
            "bindingdb_partner_descriptor_reconciliation_preview": (
                str(DEFAULT_BINDINGDB_PARTNER_DESCRIPTOR_RECONCILIATION_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_partner_descriptor_reconciliation_preview is not None
                else None
            ),
            "bindingdb_accession_partner_identity_profile_preview": (
                str(DEFAULT_BINDINGDB_ACCESSION_PARTNER_IDENTITY_PROFILE_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_accession_partner_identity_profile_preview is not None
                else None
            ),
            "bindingdb_structure_grounding_candidate_preview": (
                str(DEFAULT_BINDINGDB_STRUCTURE_GROUNDING_CANDIDATE_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_structure_grounding_candidate_preview is not None
                else None
            ),
            "bindingdb_future_structure_registry_preview": (
                str(DEFAULT_BINDINGDB_FUTURE_STRUCTURE_REGISTRY_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_future_structure_registry_preview is not None
                else None
            ),
            "bindingdb_future_structure_context_preview": (
                str(DEFAULT_BINDINGDB_FUTURE_STRUCTURE_CONTEXT_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_future_structure_context_preview is not None
                else None
            ),
            "bindingdb_future_structure_alignment_preview": (
                str(DEFAULT_BINDINGDB_FUTURE_STRUCTURE_ALIGNMENT_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_future_structure_alignment_preview is not None
                else None
            ),
            "bindingdb_future_structure_triage_preview": (
                str(DEFAULT_BINDINGDB_FUTURE_STRUCTURE_TRIAGE_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_future_structure_triage_preview is not None
                else None
            ),
            "bindingdb_off_target_adjacent_context_profile_preview": (
                str(DEFAULT_BINDINGDB_OFF_TARGET_ADJACENT_CONTEXT_PROFILE_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_off_target_adjacent_context_profile_preview is not None
                else None
            ),
            "bindingdb_off_target_target_profile_preview": (
                str(DEFAULT_BINDINGDB_OFF_TARGET_TARGET_PROFILE_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if bindingdb_off_target_target_profile_preview is not None
                else None
            ),
            "archive_cleanup_keeper_rules_preview": (
                str(archive_cleanup_keeper_rules_preview_path).replace("\\", "/")
                if archive_cleanup_keeper_rules_preview is not None
                else None
            ),
            "procurement_tail_freeze_gate_preview": (
                str(procurement_tail_freeze_gate_preview_path).replace("\\", "/")
                if procurement_tail_freeze_gate_preview is not None
                else None
            ),
            "ligand_support_readiness_preview": (
                str(ligand_support_readiness_preview_path).replace("\\", "/")
                if ligand_support_readiness_preview is not None
                else None
            ),
            "ligand_identity_pilot_preview": (
                str(ligand_identity_pilot_preview_path).replace("\\", "/")
                if ligand_identity_pilot_preview is not None
                else None
            ),
            "ligand_stage1_operator_queue_preview": (
                str(ligand_stage1_operator_queue_preview_path).replace("\\", "/")
                if ligand_stage1_operator_queue_preview is not None
                else None
            ),
            "p00387_ligand_extraction_validation_preview": (
                str(p00387_ligand_extraction_validation_preview_path).replace("\\", "/")
                if p00387_ligand_extraction_validation_preview is not None
                else None
            ),
            "q9nzd4_bridge_validation_preview": (
                str(q9nzd4_bridge_validation_preview_path).replace("\\", "/")
                if q9nzd4_bridge_validation_preview is not None
                else None
            ),
            "ligand_stage1_validation_panel_preview": (
                str(ligand_stage1_validation_panel_preview_path).replace("\\", "/")
                if ligand_stage1_validation_panel_preview is not None
                else None
            ),
            "ligand_identity_core_materialization_preview": (
                str(ligand_identity_core_materialization_preview_path).replace("\\", "/")
                if ligand_identity_core_materialization_preview is not None
                else None
            ),
            "next_real_ligand_row_gate_preview": (
                str(next_real_ligand_row_gate_preview_path).replace("\\", "/")
                if next_real_ligand_row_gate_preview is not None
                else None
            ),
            "next_real_ligand_row_decision_preview": (
                str(next_real_ligand_row_decision_preview_path).replace("\\", "/")
                if next_real_ligand_row_decision_preview is not None
                else None
            ),
            "ligand_row_materialization_preview": (
                str(ligand_row_materialization_preview_path).replace("\\", "/")
                if ligand_row_materialization_preview is not None
                else None
            ),
            "ligand_similarity_signature_preview": (
                str(ligand_similarity_signature_preview_path).replace("\\", "/")
                if ligand_similarity_signature_preview is not None
                else None
            ),
            "ligand_similarity_signature_gate_preview": (
                str(ligand_similarity_signature_gate_preview_path).replace("\\", "/")
                if ligand_similarity_signature_gate_preview is not None
                else None
            ),
            "ligand_similarity_signature_validation": (
                str(DEFAULT_LIGAND_SIMILARITY_SIGNATURE_VALIDATION).replace("\\", "/")
                if ligand_similarity_signature_validation is not None
                else None
            ),
            "structure_similarity_signature_preview": (
                str(structure_similarity_signature_preview_path).replace("\\", "/")
                if structure_similarity_signature_preview is not None
                else None
            ),
            "structure_variant_bridge_summary": (
                str(structure_variant_bridge_summary_path).replace("\\", "/")
                if structure_variant_bridge_summary is not None
                else None
            ),
            "structure_variant_candidate_map": (
                str(structure_variant_candidate_map_path).replace("\\", "/")
                if structure_variant_candidate_map is not None
                else None
            ),
            "structure_followup_payload_preview": (
                str(structure_followup_payload_preview_path).replace("\\", "/")
                if structure_followup_payload_preview is not None
                else None
            ),
            "structure_followup_single_accession_preview": (
                str(structure_followup_single_accession_preview_path).replace("\\", "/")
                if structure_followup_single_accession_preview is not None
                else None
            ),
            "structure_followup_single_accession_validation_preview": (
                str(structure_followup_single_accession_validation_preview_path).replace(
                    "\\",
                    "/",
                )
                if structure_followup_single_accession_validation_preview is not None
                else None
            ),
            "operator_accession_coverage_matrix": (
                str(operator_accession_coverage_matrix_path).replace("\\", "/")
                if operator_accession_coverage_matrix is not None
                else None
            ),
            "entity_split_recipe_preview": (
                str(entity_split_recipe_preview_path).replace("\\", "/")
                if entity_split_recipe_preview is not None
                else None
            ),
            "entity_split_assignment_preview": (
                str(entity_split_assignment_preview_path).replace("\\", "/")
                if entity_split_assignment_preview is not None
                else None
            ),
            "split_engine_input_preview": (
                str(split_engine_input_preview_path).replace("\\", "/")
                if split_engine_input_preview is not None
                else None
            ),
            "split_engine_dry_run_validation": (
                str(split_engine_dry_run_validation_path).replace("\\", "/")
                if split_engine_dry_run_validation is not None
                else None
            ),
            "split_fold_export_gate_preview": (
                str(split_fold_export_gate_preview_path).replace("\\", "/")
                if split_fold_export_gate_preview is not None
                else None
            ),
            "split_fold_export_gate_validation": (
                str(split_fold_export_gate_validation_path).replace("\\", "/")
                if split_fold_export_gate_validation is not None
                else None
            ),
            "split_fold_export_staging_preview": (
                str(split_fold_export_staging_preview_path).replace("\\", "/")
                if split_fold_export_staging_preview is not None
                else None
            ),
            "split_fold_export_staging_validation": (
                str(split_fold_export_staging_validation_path).replace("\\", "/")
                if split_fold_export_staging_validation is not None
                else None
            ),
            "split_post_staging_gate_check_preview": (
                str(split_post_staging_gate_check_preview_path).replace("\\", "/")
                if split_post_staging_gate_check_preview is not None
                else None
            ),
            "split_post_staging_gate_check_validation": (
                str(split_post_staging_gate_check_validation_path).replace("\\", "/")
                if split_post_staging_gate_check_validation is not None
                else None
            ),
            "split_fold_export_request_preview": (
                str(split_fold_export_request_preview_path).replace("\\", "/")
                if split_fold_export_request_preview is not None
                else None
            ),
            "split_fold_export_request_validation": (
                str(split_fold_export_request_validation_path).replace("\\", "/")
                if split_fold_export_request_validation is not None
                else None
            ),
            "leakage_signature_preview": (
                str(leakage_signature_preview_path).replace("\\", "/")
                if leakage_signature_preview is not None
                else None
            ),
            "leakage_group_preview": (
                str(leakage_group_preview_path).replace("\\", "/")
                if leakage_group_preview is not None
                else None
            ),
            "duplicate_cleanup_first_execution_preview": (
                str(duplicate_first_execution_preview_path).replace("\\", "/")
                if duplicate_first_execution_preview is not None
                else None
            ),
            "duplicate_cleanup_delete_ready_manifest_preview": (
                str(duplicate_delete_ready_manifest_preview_path).replace("\\", "/")
                if duplicate_delete_ready_manifest_preview is not None
                else None
            ),
            "duplicate_cleanup_post_delete_verification_contract_preview": (
                str(duplicate_post_delete_verification_contract_preview_path).replace(
                    "\\",
                    "/",
                )
                if duplicate_post_delete_verification_contract_preview is not None
                else None
            ),
            "duplicate_cleanup_first_execution_batch_manifest_preview": (
                str(duplicate_first_execution_batch_manifest_preview_path).replace(
                    "\\",
                    "/",
                )
                if duplicate_first_execution_batch_manifest_preview is not None
                else None
            ),
            "operator_next_actions_preview": (
                str(operator_next_actions_preview_path).replace("\\", "/")
                if operator_next_actions_preview is not None
                else None
            ),
            "training_set_eligibility_matrix_preview": (
                str(training_set_eligibility_matrix_preview_path).replace("\\", "/")
                if training_set_eligibility_matrix_preview is not None
                else None
            ),
            "missing_data_policy_preview": (
                str(missing_data_policy_preview_path).replace("\\", "/")
                if missing_data_policy_preview is not None
                else None
            ),
            "training_set_readiness_preview": (
                str(DEFAULT_TRAINING_SET_READINESS_PREVIEW).replace("\\", "/")
                if training_set_readiness_preview is not None
                else None
            ),
            "training_set_builder_runbook_preview": (
                str(DEFAULT_TRAINING_SET_BUILDER_RUNBOOK_PREVIEW).replace("\\", "/")
                if training_set_builder_runbook_preview is not None
                else None
            ),
            "final_structured_dataset_bundle_preview": (
                str(DEFAULT_FINAL_STRUCTURED_DATASET_BUNDLE_PREVIEW).replace("\\", "/")
                if final_structured_dataset_bundle_preview is not None
                else None
            ),
            "pdbbind_expanded_structured_corpus_preview": (
                str(DEFAULT_PDBBIND_EXPANDED_STRUCTURED_CORPUS_PREVIEW).replace("\\", "/")
                if pdbbind_expanded_structured_corpus_preview is not None
                else None
            ),
            "pdbbind_protein_cohort_graph_preview": (
                str(DEFAULT_PDBBIND_PROTEIN_COHORT_GRAPH_PREVIEW).replace("\\", "/")
                if pdbbind_protein_cohort_graph_preview is not None
                else None
            ),
            "paper_pdb_split_assessment_preview": (
                str(DEFAULT_PAPER_PDB_SPLIT_ASSESSMENT_PREVIEW).replace("\\", "/")
                if paper_pdb_split_assessment_preview is not None
                else None
            ),
            "pdb_paper_split_leakage_matrix_preview": (
                str(DEFAULT_PDB_PAPER_SPLIT_LEAKAGE_MATRIX_PREVIEW).replace("\\", "/")
                if pdb_paper_split_leakage_matrix_preview is not None
                else None
            ),
            "pdb_paper_split_acceptance_gate_preview": (
                str(DEFAULT_PDB_PAPER_SPLIT_ACCEPTANCE_GATE_PREVIEW).replace("\\", "/")
                if pdb_paper_split_acceptance_gate_preview is not None
                else None
            ),
            "pdb_paper_split_sequence_signature_audit_preview": (
                str(DEFAULT_PDB_PAPER_SPLIT_SEQUENCE_SIGNATURE_AUDIT_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if pdb_paper_split_sequence_signature_audit_preview is not None
                else None
            ),
            "pdb_paper_split_mutation_audit_preview": (
                str(DEFAULT_PDB_PAPER_SPLIT_MUTATION_AUDIT_PREVIEW).replace("\\", "/")
                if pdb_paper_split_mutation_audit_preview is not None
                else None
            ),
            "pdb_paper_split_structure_state_audit_preview": (
                str(DEFAULT_PDB_PAPER_SPLIT_STRUCTURE_STATE_AUDIT_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if pdb_paper_split_structure_state_audit_preview is not None
                else None
            ),
            "pdb_paper_dataset_quality_verdict_preview": (
                str(DEFAULT_PDB_PAPER_DATASET_QUALITY_VERDICT_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if pdb_paper_dataset_quality_verdict_preview is not None
                else None
            ),
            "pdb_paper_split_remediation_plan_preview": (
                str(DEFAULT_PDB_PAPER_SPLIT_REMEDIATION_PLAN_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if pdb_paper_split_remediation_plan_preview is not None
                else None
            ),
            "release_grade_readiness_preview": (
                str(DEFAULT_RELEASE_GRADE_READINESS_PREVIEW).replace("\\", "/")
                if release_grade_readiness_preview is not None
                else None
            ),
            "release_grade_closure_queue_preview": (
                str(DEFAULT_RELEASE_GRADE_CLOSURE_QUEUE_PREVIEW).replace("\\", "/")
                if release_grade_closure_queue_preview is not None
                else None
            ),
            "release_runtime_maturity_preview": (
                str(DEFAULT_RELEASE_RUNTIME_MATURITY_PREVIEW).replace("\\", "/")
                if release_runtime_maturity_preview is not None
                else None
            ),
            "release_source_coverage_depth_preview": (
                str(DEFAULT_RELEASE_SOURCE_COVERAGE_DEPTH_PREVIEW).replace("\\", "/")
                if release_source_coverage_depth_preview is not None
                else None
            ),
            "release_provenance_depth_preview": (
                str(DEFAULT_RELEASE_PROVENANCE_DEPTH_PREVIEW).replace("\\", "/")
                if release_provenance_depth_preview is not None
                else None
            ),
            "release_grade_runbook_preview": (
                str(DEFAULT_RELEASE_GRADE_RUNBOOK_PREVIEW).replace("\\", "/")
                if release_grade_runbook_preview is not None
                else None
            ),
            "release_accession_closure_matrix_preview": (
                str(DEFAULT_RELEASE_ACCESSION_CLOSURE_MATRIX_PREVIEW).replace("\\", "/")
                if release_accession_closure_matrix_preview is not None
                else None
            ),
            "release_accession_action_queue_preview": (
                str(DEFAULT_RELEASE_ACCESSION_ACTION_QUEUE_PREVIEW).replace("\\", "/")
                if release_accession_action_queue_preview is not None
                else None
            ),
            "release_promotion_gate_preview": (
                str(DEFAULT_RELEASE_PROMOTION_GATE_PREVIEW).replace("\\", "/")
                if release_promotion_gate_preview is not None
                else None
            ),
            "release_source_fix_followup_batch_preview": (
                str(DEFAULT_RELEASE_SOURCE_FIX_FOLLOWUP_BATCH_PREVIEW).replace("\\", "/")
                if release_source_fix_followup_batch_preview is not None
                else None
            ),
            "release_candidate_promotion_preview": (
                str(DEFAULT_RELEASE_CANDIDATE_PROMOTION_PREVIEW).replace("\\", "/")
                if release_candidate_promotion_preview is not None
                else None
            ),
            "release_runtime_qualification_preview": (
                str(DEFAULT_RELEASE_RUNTIME_QUALIFICATION_PREVIEW).replace("\\", "/")
                if release_runtime_qualification_preview is not None
                else None
            ),
            "release_governing_sufficiency_preview": (
                str(DEFAULT_RELEASE_GOVERNING_SUFFICIENCY_PREVIEW).replace("\\", "/")
                if release_governing_sufficiency_preview is not None
                else None
            ),
            "release_accession_evidence_pack_preview": (
                str(DEFAULT_RELEASE_ACCESSION_EVIDENCE_PACK_PREVIEW).replace("\\", "/")
                if release_accession_evidence_pack_preview is not None
                else None
            ),
            "release_reporting_completeness_preview": (
                str(DEFAULT_RELEASE_REPORTING_COMPLETENESS_PREVIEW).replace("\\", "/")
                if release_reporting_completeness_preview is not None
                else None
            ),
            "release_blocker_resolution_board_preview": (
                str(DEFAULT_RELEASE_BLOCKER_RESOLUTION_BOARD_PREVIEW).replace("\\", "/")
                if release_blocker_resolution_board_preview is not None
                else None
            ),
            "procurement_external_drive_mount_preview": (
                str(DEFAULT_PROCUREMENT_EXTERNAL_DRIVE_MOUNT_PREVIEW).replace("\\", "/")
                if procurement_external_drive_mount_preview is not None
                else None
            ),
            "procurement_expansion_wave_preview": (
                str(DEFAULT_PROCUREMENT_EXPANSION_WAVE_PREVIEW).replace("\\", "/")
                if procurement_expansion_wave_preview is not None
                else None
            ),
            "procurement_expansion_storage_budget_preview": (
                str(DEFAULT_PROCUREMENT_EXPANSION_STORAGE_BUDGET_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if procurement_expansion_storage_budget_preview is not None
                else None
            ),
            "missing_scrape_family_contracts_preview": (
                str(DEFAULT_MISSING_SCRAPE_FAMILY_CONTRACTS_PREVIEW).replace("\\", "/")
                if missing_scrape_family_contracts_preview is not None
                else None
            ),
            "training_set_remediation_plan_preview": (
                str(DEFAULT_TRAINING_SET_REMEDIATION_PLAN_PREVIEW).replace("\\", "/")
                if training_set_remediation_plan_preview is not None
                else None
            ),
            "training_set_blocker_burndown_preview": (
                str(DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN_PREVIEW).replace("\\", "/")
                if training_set_blocker_burndown_preview is not None
                else None
            ),
            "training_set_modality_gap_register_preview": (
                str(DEFAULT_TRAINING_SET_MODALITY_GAP_REGISTER_PREVIEW).replace("\\", "/")
                if training_set_modality_gap_register_preview is not None
                else None
            ),
            "training_set_package_blocker_matrix_preview": (
                str(DEFAULT_TRAINING_SET_PACKAGE_BLOCKER_MATRIX_PREVIEW).replace("\\", "/")
                if training_set_package_blocker_matrix_preview is not None
                else None
            ),
            "training_set_gate_ladder_preview": (
                str(DEFAULT_TRAINING_SET_GATE_LADDER_PREVIEW).replace("\\", "/")
                if training_set_gate_ladder_preview is not None
                else None
            ),
            "training_set_unlock_route_preview": (
                str(DEFAULT_TRAINING_SET_UNLOCK_ROUTE_PREVIEW).replace("\\", "/")
                if training_set_unlock_route_preview is not None
                else None
            ),
            "training_set_transition_contract_preview": (
                str(DEFAULT_TRAINING_SET_TRANSITION_CONTRACT_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if training_set_transition_contract_preview is not None
                else None
            ),
            "training_set_source_fix_batch_preview": (
                str(DEFAULT_TRAINING_SET_SOURCE_FIX_BATCH_PREVIEW).replace("\\", "/")
                if training_set_source_fix_batch_preview is not None
                else None
            ),
            "training_set_package_transition_batch_preview": (
                str(DEFAULT_TRAINING_SET_PACKAGE_TRANSITION_BATCH_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if training_set_package_transition_batch_preview is not None
                else None
            ),
            "training_set_package_execution_preview": (
                str(DEFAULT_TRAINING_SET_PACKAGE_EXECUTION_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if training_set_package_execution_preview is not None
                else None
            ),
            "training_set_preview_hold_register_preview": (
                str(DEFAULT_TRAINING_SET_PREVIEW_HOLD_REGISTER_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if training_set_preview_hold_register_preview is not None
                else None
            ),
            "training_set_preview_hold_exit_criteria_preview": (
                str(DEFAULT_TRAINING_SET_PREVIEW_HOLD_EXIT_CRITERIA_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if training_set_preview_hold_exit_criteria_preview is not None
                else None
            ),
            "training_set_preview_hold_clearance_batch_preview": (
                str(DEFAULT_TRAINING_SET_PREVIEW_HOLD_CLEARANCE_BATCH_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if training_set_preview_hold_clearance_batch_preview is not None
                else None
            ),
            "binding_measurement_suspect_rows_preview": (
                str(DEFAULT_BINDING_MEASUREMENT_SUSPECT_ROWS_PREVIEW).replace("\\", "/")
                if binding_measurement_suspect_rows_preview is not None
                else None
            ),
            "cross_source_duplicate_measurement_audit_preview": (
                str(DEFAULT_CROSS_SOURCE_DUPLICATE_MEASUREMENT_AUDIT_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if cross_source_duplicate_measurement_audit_preview is not None
                else None
            ),
            "training_set_candidate_package_manifest_preview": (
                str(DEFAULT_TRAINING_SET_CANDIDATE_PACKAGE_MANIFEST_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if training_set_candidate_package_manifest_preview is not None
                else None
            ),
            "training_packet_completeness_matrix_preview": (
                str(DEFAULT_TRAINING_PACKET_COMPLETENESS_MATRIX_PREVIEW).replace("\\", "/")
                if training_packet_completeness_matrix_preview is not None
                else None
            ),
            "training_split_alignment_recheck_preview": (
                str(DEFAULT_TRAINING_SPLIT_ALIGNMENT_RECHECK_PREVIEW).replace("\\", "/")
                if training_split_alignment_recheck_preview is not None
                else None
            ),
            "training_packet_materialization_queue_preview": (
                str(DEFAULT_TRAINING_PACKET_MATERIALIZATION_QUEUE_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if training_packet_materialization_queue_preview is not None
                else None
            ),
            "external_dataset_assessment_preview": (
                str(DEFAULT_EXTERNAL_DATASET_ASSESSMENT_PREVIEW).replace("\\", "/")
                if external_dataset_assessment_preview is not None
                else None
            ),
            "external_dataset_flaw_taxonomy_preview": (
                str(DEFAULT_EXTERNAL_DATASET_FLAW_TAXONOMY_PREVIEW).replace("\\", "/")
                if external_dataset_flaw_taxonomy_preview is not None
                else None
            ),
            "external_dataset_risk_register_preview": (
                str(DEFAULT_EXTERNAL_DATASET_RISK_REGISTER_PREVIEW).replace("\\", "/")
                if external_dataset_risk_register_preview is not None
                else None
            ),
            "external_dataset_conflict_register_preview": (
                str(DEFAULT_EXTERNAL_DATASET_CONFLICT_REGISTER_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if external_dataset_conflict_register_preview is not None
                else None
            ),
            "external_dataset_issue_matrix_preview": (
                str(DEFAULT_EXTERNAL_DATASET_ISSUE_MATRIX_PREVIEW).replace("\\", "/")
                if external_dataset_issue_matrix_preview is not None
                else None
            ),
            "external_dataset_admission_decision_preview": (
                str(DEFAULT_EXTERNAL_DATASET_ADMISSION_DECISION_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if external_dataset_admission_decision_preview is not None
                else None
            ),
            "external_dataset_clearance_delta_preview": (
                str(DEFAULT_EXTERNAL_DATASET_CLEARANCE_DELTA_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if external_dataset_clearance_delta_preview is not None
                else None
            ),
            "external_dataset_acceptance_path_preview": (
                str(DEFAULT_EXTERNAL_DATASET_ACCEPTANCE_PATH_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if external_dataset_acceptance_path_preview is not None
                else None
            ),
            "external_dataset_remediation_readiness_preview": (
                str(DEFAULT_EXTERNAL_DATASET_REMEDIATION_READINESS_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if external_dataset_remediation_readiness_preview is not None
                else None
            ),
            "external_dataset_caveat_execution_preview": (
                str(DEFAULT_EXTERNAL_DATASET_CAVEAT_EXECUTION_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if external_dataset_caveat_execution_preview is not None
                else None
            ),
            "external_dataset_blocked_acquisition_batch_preview": (
                str(DEFAULT_EXTERNAL_DATASET_BLOCKED_ACQUISITION_BATCH_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if external_dataset_blocked_acquisition_batch_preview is not None
                else None
            ),
            "external_dataset_acquisition_unblock_preview": (
                str(DEFAULT_EXTERNAL_DATASET_ACQUISITION_UNBLOCK_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if external_dataset_acquisition_unblock_preview is not None
                else None
            ),
            "external_dataset_advisory_followup_register_preview": (
                str(DEFAULT_EXTERNAL_DATASET_ADVISORY_FOLLOWUP_REGISTER_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if external_dataset_advisory_followup_register_preview is not None
                else None
            ),
            "external_dataset_caveat_exit_criteria_preview": (
                str(DEFAULT_EXTERNAL_DATASET_CAVEAT_EXIT_CRITERIA_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if external_dataset_caveat_exit_criteria_preview is not None
                else None
            ),
            "external_dataset_caveat_review_batch_preview": (
                str(DEFAULT_EXTERNAL_DATASET_CAVEAT_REVIEW_BATCH_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if external_dataset_caveat_review_batch_preview is not None
                else None
            ),
            "external_dataset_resolution_diff_preview": (
                str(DEFAULT_EXTERNAL_DATASET_RESOLUTION_DIFF_PREVIEW).replace("\\", "/")
                if external_dataset_resolution_diff_preview is not None
                else None
            ),
            "external_dataset_remediation_template_preview": (
                str(DEFAULT_EXTERNAL_DATASET_REMEDIATION_TEMPLATE_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if external_dataset_remediation_template_preview is not None
                else None
            ),
            "external_dataset_fixture_catalog_preview": (
                str(DEFAULT_EXTERNAL_DATASET_FIXTURE_CATALOG_PREVIEW).replace("\\", "/")
                if external_dataset_fixture_catalog_preview is not None
                else None
            ),
            "sample_external_dataset_assessment_bundle_preview": (
                str(DEFAULT_SAMPLE_EXTERNAL_DATASET_ASSESSMENT_BUNDLE_PREVIEW).replace(
                    "\\",
                    "/",
                )
                if sample_external_dataset_assessment_bundle_preview is not None
                else None
            ),
            "scrape_gap_matrix_preview": (
                str(DEFAULT_SCRAPE_GAP_MATRIX_PREVIEW).replace("\\", "/")
                if scrape_gap_matrix_preview is not None
                else None
            ),
            "scrape_backlog_remaining_preview": (
                str(DEFAULT_SCRAPE_BACKLOG_REMAINING_PREVIEW).replace("\\", "/")
                if scrape_backlog_remaining_preview is not None
                else None
            ),
            "scrape_execution_wave_preview": (
                str(DEFAULT_SCRAPE_EXECUTION_WAVE_PREVIEW).replace("\\", "/")
                if scrape_execution_wave_preview is not None
                else None
            ),
            "download_location_audit_preview": (
                str(DEFAULT_DOWNLOAD_LOCATION_AUDIT_PREVIEW).replace("\\", "/")
                if download_location_audit_preview is not None
                else None
            ),
            "procurement_stale_part_audit_preview": (
                str(DEFAULT_PROCUREMENT_STALE_PART_AUDIT_PREVIEW).replace("\\", "/")
                if procurement_stale_part_audit_preview is not None
                else None
            ),
            "post_tail_unlock_dry_run_preview": (
                str(DEFAULT_POST_TAIL_UNLOCK_DRY_RUN_PREVIEW).replace("\\", "/")
                if post_tail_unlock_dry_run_preview is not None
                else None
            ),
            "overnight_execution_contract_preview": (
                str(DEFAULT_OVERNIGHT_EXECUTION_CONTRACT_PREVIEW).replace("\\", "/")
                if overnight_execution_contract_preview is not None
                else None
            ),
            "overnight_queue_repair_status": (
                str(DEFAULT_OVERNIGHT_QUEUE_REPAIR_STATUS).replace("\\", "/")
                if overnight_queue_repair_status is not None
                else None
            ),
            "overnight_idle_status_preview": (
                str(DEFAULT_OVERNIGHT_IDLE_STATUS_PREVIEW).replace("\\", "/")
                if overnight_idle_status_preview is not None
                else None
            ),
            "overnight_pending_reconciliation_preview": (
                str(DEFAULT_OVERNIGHT_PENDING_RECONCILIATION_PREVIEW).replace("\\", "/")
                if overnight_pending_reconciliation_preview is not None
                else None
            ),
            "overnight_worker_launch_gap_preview": (
                str(DEFAULT_OVERNIGHT_WORKER_LAUNCH_GAP_PREVIEW).replace("\\", "/")
                if overnight_worker_launch_gap_preview is not None
                else None
            ),
            "procurement_supervisor_freshness_preview": (
                str(DEFAULT_PROCUREMENT_SUPERVISOR_FRESHNESS_PREVIEW).replace("\\", "/")
                if procurement_supervisor_freshness_preview is not None
                else None
            ),
            "procurement_tail_signal_reconciliation_preview": (
                str(DEFAULT_PROCUREMENT_TAIL_SIGNAL_RECONCILIATION_PREVIEW).replace("\\", "/")
                if procurement_tail_signal_reconciliation_preview is not None
                else None
            ),
            "procurement_tail_growth_preview": (
                str(DEFAULT_PROCUREMENT_TAIL_GROWTH_PREVIEW).replace("\\", "/")
                if procurement_tail_growth_preview is not None
                else None
            ),
            "procurement_headroom_guard_preview": (
                str(DEFAULT_PROCUREMENT_HEADROOM_GUARD_PREVIEW).replace("\\", "/")
                if procurement_headroom_guard_preview is not None
                else None
            ),
            "procurement_tail_space_drift_preview": (
                str(DEFAULT_PROCUREMENT_TAIL_SPACE_DRIFT_PREVIEW).replace("\\", "/")
                if procurement_tail_space_drift_preview is not None
                else None
            ),
            "procurement_tail_source_pressure_preview": (
                str(DEFAULT_PROCUREMENT_TAIL_SOURCE_PRESSURE_PREVIEW).replace("\\", "/")
                if procurement_tail_source_pressure_preview is not None
                else None
            ),
            "procurement_tail_log_progress_registry_preview": (
                str(DEFAULT_PROCUREMENT_TAIL_LOG_PROGRESS_REGISTRY_PREVIEW).replace("\\", "/")
                if procurement_tail_log_progress_registry_preview is not None
                else None
            ),
            "procurement_tail_completion_margin_preview": (
                str(DEFAULT_PROCUREMENT_TAIL_COMPLETION_MARGIN_PREVIEW).replace("\\", "/")
                if procurement_tail_completion_margin_preview is not None
                else None
            ),
            "procurement_space_recovery_target_preview": (
                str(DEFAULT_PROCUREMENT_SPACE_RECOVERY_TARGET_PREVIEW).replace("\\", "/")
                if procurement_space_recovery_target_preview is not None
                else None
            ),
            "procurement_space_recovery_candidates_preview": (
                str(DEFAULT_PROCUREMENT_SPACE_RECOVERY_CANDIDATES_PREVIEW).replace("\\", "/")
                if procurement_space_recovery_candidates_preview is not None
                else None
            ),
            "procurement_space_recovery_execution_batch_preview": (
                str(DEFAULT_PROCUREMENT_SPACE_RECOVERY_EXECUTION_BATCH_PREVIEW).replace("\\", "/")
                if procurement_space_recovery_execution_batch_preview is not None
                else None
            ),
            "procurement_space_recovery_safety_register_preview": (
                str(DEFAULT_PROCUREMENT_SPACE_RECOVERY_SAFETY_REGISTER_PREVIEW).replace("\\", "/")
                if procurement_space_recovery_safety_register_preview is not None
                else None
            ),
            "procurement_tail_fill_risk_preview": (
                str(DEFAULT_PROCUREMENT_TAIL_FILL_RISK_PREVIEW).replace("\\", "/")
                if procurement_tail_fill_risk_preview is not None
                else None
            ),
            "procurement_space_recovery_trigger_preview": (
                str(DEFAULT_PROCUREMENT_SPACE_RECOVERY_TRIGGER_PREVIEW).replace("\\", "/")
                if procurement_space_recovery_trigger_preview is not None
                else None
            ),
            "procurement_space_recovery_gap_drift_preview": (
                str(DEFAULT_PROCUREMENT_SPACE_RECOVERY_GAP_DRIFT_PREVIEW).replace("\\", "/")
                if procurement_space_recovery_gap_drift_preview is not None
                else None
            ),
            "procurement_space_recovery_coverage_preview": (
                str(DEFAULT_PROCUREMENT_SPACE_RECOVERY_COVERAGE_PREVIEW).replace("\\", "/")
                if procurement_space_recovery_coverage_preview is not None
                else None
            ),
            "procurement_recovery_intervention_priority_preview": (
                str(DEFAULT_PROCUREMENT_RECOVERY_INTERVENTION_PRIORITY_PREVIEW).replace("\\", "/")
                if procurement_recovery_intervention_priority_preview is not None
                else None
            ),
            "procurement_recovery_escalation_lane_preview": (
                str(DEFAULT_PROCUREMENT_RECOVERY_ESCALATION_LANE_PREVIEW).replace("\\", "/")
                if procurement_recovery_escalation_lane_preview is not None
                else None
            ),
            "procurement_space_recovery_concentration_preview": (
                str(DEFAULT_PROCUREMENT_SPACE_RECOVERY_CONCENTRATION_PREVIEW).replace("\\", "/")
                if procurement_space_recovery_concentration_preview is not None
                else None
            ),
            "procurement_recovery_shortfall_bridge_preview": (
                str(DEFAULT_PROCUREMENT_RECOVERY_SHORTFALL_BRIDGE_PREVIEW).replace("\\", "/")
                if procurement_recovery_shortfall_bridge_preview is not None
                else None
            ),
            "procurement_recovery_lane_fragility_preview": (
                str(DEFAULT_PROCUREMENT_RECOVERY_LANE_FRAGILITY_PREVIEW).replace("\\", "/")
                if procurement_recovery_lane_fragility_preview is not None
                else None
            ),
            "procurement_broader_search_trigger_preview": (
                str(DEFAULT_PROCUREMENT_BROADER_SEARCH_TRIGGER_PREVIEW).replace("\\", "/")
                if procurement_broader_search_trigger_preview is not None
                else None
            ),
            "overnight_wave_advance_preview": (
                str(DEFAULT_OVERNIGHT_WAVE_ADVANCE_PREVIEW).replace("\\", "/")
                if overnight_wave_advance_preview is not None
                else None
            ),
            "interaction_string_merge_impact_preview": (
                str(DEFAULT_INTERACTION_STRING_MERGE_IMPACT_PREVIEW).replace("\\", "/")
                if interaction_string_merge_impact_preview is not None
                else None
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export the operator dashboard for the real-data benchmark.",
    )
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--packet-deficit", type=Path, default=DEFAULT_PACKET_DEFICIT)
    parser.add_argument("--tier1-direct-pipeline", type=Path, default=DEFAULT_TIER1_DIRECT)
    parser.add_argument("--canonical-latest", type=Path, default=DEFAULT_CANONICAL_LATEST)
    parser.add_argument(
        "--summary-library-inventory",
        type=Path,
        default=DEFAULT_SUMMARY_LIBRARY_INVENTORY,
    )
    parser.add_argument(
        "--structure-unit-library-inventory",
        type=Path,
        default=DEFAULT_STRUCTURE_UNIT_LIBRARY_INVENTORY,
    )
    parser.add_argument(
        "--protein-similarity-signature-preview",
        type=Path,
        default=DEFAULT_PROTEIN_SIMILARITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--dictionary-preview",
        type=Path,
        default=DEFAULT_DICTIONARY_PREVIEW,
    )
    parser.add_argument(
        "--motif-domain-compact-preview-family",
        type=Path,
        default=DEFAULT_MOTIF_DOMAIN_COMPACT_PREVIEW_FAMILY,
    )
    parser.add_argument(
        "--interaction-similarity-signature-preview",
        type=Path,
        default=DEFAULT_INTERACTION_SIMILARITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--interaction-similarity-signature-validation",
        type=Path,
        default=DEFAULT_INTERACTION_SIMILARITY_SIGNATURE_VALIDATION,
    )
    parser.add_argument(
        "--sabio-rk-support-preview",
        type=Path,
        default=DEFAULT_SABIO_RK_SUPPORT_PREVIEW,
    )
    parser.add_argument(
        "--kinetics-support-preview",
        type=Path,
        default=DEFAULT_KINETICS_SUPPORT_PREVIEW,
    )
    parser.add_argument(
        "--compact-enrichment-policy-preview",
        type=Path,
        default=DEFAULT_COMPACT_ENRICHMENT_POLICY_PREVIEW,
    )
    parser.add_argument(
        "--scrape-readiness-registry-preview",
        type=Path,
        default=DEFAULT_SCRAPE_READINESS_REGISTRY_PREVIEW,
    )
    parser.add_argument(
        "--procurement-source-completion-preview",
        type=Path,
        default=DEFAULT_PROCUREMENT_SOURCE_COMPLETION_PREVIEW,
    )
    parser.add_argument(
        "--string-interaction-materialization-plan-preview",
        type=Path,
        default=DEFAULT_STRING_INTERACTION_MATERIALIZATION_PLAN_PREVIEW,
    )
    parser.add_argument(
        "--uniref-cluster-materialization-plan-preview",
        type=Path,
        default=DEFAULT_UNIREF_CLUSTER_MATERIALIZATION_PLAN_PREVIEW,
    )
    parser.add_argument(
        "--pdb-enrichment-scrape-registry-preview",
        type=Path,
        default=DEFAULT_PDB_ENRICHMENT_SCRAPE_REGISTRY_PREVIEW,
    )
    parser.add_argument(
        "--structure-entry-context-preview",
        type=Path,
        default=DEFAULT_STRUCTURE_ENTRY_CONTEXT_PREVIEW,
    )
    parser.add_argument(
        "--pdb-enrichment-harvest-preview",
        type=Path,
        default=DEFAULT_PDB_ENRICHMENT_HARVEST_PREVIEW,
    )
    parser.add_argument(
        "--pdb-enrichment-validation-preview",
        type=Path,
        default=DEFAULT_PDB_ENRICHMENT_VALIDATION_PREVIEW,
    )
    parser.add_argument(
        "--ligand-context-scrape-registry-preview",
        type=Path,
        default=DEFAULT_LIGAND_CONTEXT_SCRAPE_REGISTRY_PREVIEW,
    )
    parser.add_argument(
        "--protein-origin-context-preview",
        type=Path,
        default=DEFAULT_PROTEIN_ORIGIN_CONTEXT_PREVIEW,
    )
    parser.add_argument(
        "--catalytic-site-context-preview",
        type=Path,
        default=DEFAULT_CATALYTIC_SITE_CONTEXT_PREVIEW,
    )
    parser.add_argument(
        "--targeted-page-scrape-registry-preview",
        type=Path,
        default=DEFAULT_TARGETED_PAGE_SCRAPE_REGISTRY_PREVIEW,
    )
    parser.add_argument(
        "--seed-plus-neighbors-structured-corpus-preview",
        type=Path,
        default=DEFAULT_SEED_PLUS_NEIGHBORS_STRUCTURED_CORPUS_PREVIEW,
    )
    parser.add_argument(
        "--training-set-baseline-sidecar-preview",
        type=Path,
        default=DEFAULT_TRAINING_SET_BASELINE_SIDECAR_PREVIEW,
    )
    parser.add_argument(
        "--training-set-multimodal-sidecar-preview",
        type=Path,
        default=DEFAULT_TRAINING_SET_MULTIMODAL_SIDECAR_PREVIEW,
    )
    parser.add_argument(
        "--bindingdb-dump-inventory-preview",
        type=Path,
        default=DEFAULT_BINDINGDB_DUMP_INVENTORY_PREVIEW,
    )
    parser.add_argument(
        "--bindingdb-target-polymer-context-preview",
        type=Path,
        default=DEFAULT_BINDINGDB_TARGET_POLYMER_CONTEXT_PREVIEW,
    )
    parser.add_argument(
        "--bindingdb-structure-bridge-preview",
        type=Path,
        default=DEFAULT_BINDINGDB_STRUCTURE_BRIDGE_PREVIEW,
    )
    parser.add_argument(
        "--archive-cleanup-keeper-rules-preview",
        type=Path,
        default=DEFAULT_ARCHIVE_CLEANUP_KEEPER_RULES_PREVIEW,
    )
    parser.add_argument(
        "--procurement-tail-freeze-gate-preview",
        type=Path,
        default=DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE_PREVIEW,
    )
    parser.add_argument(
        "--ligand-support-readiness-preview",
        type=Path,
        default=DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW,
    )
    parser.add_argument(
        "--ligand-identity-pilot-preview",
        type=Path,
        default=DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW,
    )
    parser.add_argument(
        "--ligand-stage1-operator-queue-preview",
        type=Path,
        default=DEFAULT_LIGAND_STAGE1_OPERATOR_QUEUE_PREVIEW,
    )
    parser.add_argument(
        "--p00387-ligand-extraction-validation-preview",
        type=Path,
        default=DEFAULT_P00387_LIGAND_EXTRACTION_VALIDATION_PREVIEW,
    )
    parser.add_argument(
        "--q9nzd4-bridge-validation-preview",
        type=Path,
        default=DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW,
    )
    parser.add_argument(
        "--ligand-stage1-validation-panel-preview",
        type=Path,
        default=DEFAULT_LIGAND_STAGE1_VALIDATION_PANEL_PREVIEW,
    )
    parser.add_argument(
        "--ligand-identity-core-materialization-preview",
        type=Path,
        default=DEFAULT_LIGAND_IDENTITY_CORE_MATERIALIZATION_PREVIEW,
    )
    parser.add_argument(
        "--next-real-ligand-row-gate-preview",
        type=Path,
        default=DEFAULT_NEXT_REAL_LIGAND_ROW_GATE_PREVIEW,
    )
    parser.add_argument(
        "--next-real-ligand-row-decision-preview",
        type=Path,
        default=DEFAULT_NEXT_REAL_LIGAND_ROW_DECISION_PREVIEW,
    )
    parser.add_argument(
        "--ligand-row-materialization-preview",
        type=Path,
        default=DEFAULT_LIGAND_ROW_MATERIALIZATION_PREVIEW,
    )
    parser.add_argument(
        "--ligand-similarity-signature-preview",
        type=Path,
        default=DEFAULT_LIGAND_SIMILARITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--ligand-similarity-signature-gate-preview",
        type=Path,
        default=DEFAULT_LIGAND_SIMILARITY_SIGNATURE_GATE_PREVIEW,
    )
    parser.add_argument(
        "--structure-similarity-signature-preview",
        type=Path,
        default=DEFAULT_STRUCTURE_SIMILARITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--structure-variant-bridge-summary",
        type=Path,
        default=DEFAULT_STRUCTURE_VARIANT_BRIDGE_SUMMARY,
    )
    parser.add_argument(
        "--structure-variant-candidate-map",
        type=Path,
        default=DEFAULT_STRUCTURE_VARIANT_CANDIDATE_MAP,
    )
    parser.add_argument(
        "--structure-followup-payload-preview",
        type=Path,
        default=DEFAULT_STRUCTURE_FOLLOWUP_PAYLOAD_PREVIEW,
    )
    parser.add_argument(
        "--structure-followup-single-accession-preview",
        type=Path,
        default=DEFAULT_STRUCTURE_FOLLOWUP_SINGLE_ACCESSION_PREVIEW,
    )
    parser.add_argument(
        "--structure-followup-single-accession-validation-preview",
        type=Path,
        default=DEFAULT_STRUCTURE_FOLLOWUP_SINGLE_ACCESSION_VALIDATION_PREVIEW,
    )
    parser.add_argument(
        "--operator-accession-coverage-matrix",
        type=Path,
        default=DEFAULT_OPERATOR_ACCESSION_COVERAGE_MATRIX,
    )
    parser.add_argument(
        "--leakage-signature-preview",
        type=Path,
        default=DEFAULT_LEAKAGE_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--leakage-group-preview",
        type=Path,
        default=DEFAULT_LEAKAGE_GROUP_PREVIEW,
    )
    parser.add_argument(
        "--entity-split-recipe-preview",
        type=Path,
        default=DEFAULT_ENTITY_SPLIT_RECIPE_PREVIEW,
    )
    parser.add_argument(
        "--entity-split-assignment-preview",
        type=Path,
        default=DEFAULT_ENTITY_SPLIT_ASSIGNMENT_PREVIEW,
    )
    parser.add_argument(
        "--split-engine-input-preview",
        type=Path,
        default=DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW,
    )
    parser.add_argument(
        "--split-engine-dry-run-validation",
        type=Path,
        default=DEFAULT_SPLIT_ENGINE_DRY_RUN_VALIDATION,
    )
    parser.add_argument(
        "--split-fold-export-gate-preview",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_GATE_PREVIEW,
    )
    parser.add_argument(
        "--split-fold-export-gate-validation",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_GATE_VALIDATION,
    )
    parser.add_argument(
        "--split-fold-export-staging-preview",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_STAGING_PREVIEW,
    )
    parser.add_argument(
        "--split-fold-export-staging-validation",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_STAGING_VALIDATION,
    )
    parser.add_argument(
        "--split-post-staging-gate-check-preview",
        type=Path,
        default=DEFAULT_SPLIT_POST_STAGING_GATE_CHECK_PREVIEW,
    )
    parser.add_argument(
        "--split-post-staging-gate-check-validation",
        type=Path,
        default=DEFAULT_SPLIT_POST_STAGING_GATE_CHECK_VALIDATION,
    )
    parser.add_argument(
        "--split-fold-export-request-preview",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_REQUEST_PREVIEW,
    )
    parser.add_argument(
        "--split-fold-export-request-validation",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_REQUEST_VALIDATION,
    )
    parser.add_argument(
        "--duplicate-first-execution-preview",
        type=Path,
        default=DEFAULT_DUPLICATE_FIRST_EXECUTION_PREVIEW,
    )
    parser.add_argument(
        "--duplicate-delete-ready-manifest-preview",
        type=Path,
        default=DEFAULT_DUPLICATE_DELETE_READY_MANIFEST_PREVIEW,
    )
    parser.add_argument(
        "--duplicate-post-delete-verification-contract-preview",
        type=Path,
        default=DEFAULT_DUPLICATE_POST_DELETE_VERIFICATION_CONTRACT_PREVIEW,
    )
    parser.add_argument(
        "--duplicate-first-execution-batch-manifest-preview",
        type=Path,
        default=DEFAULT_DUPLICATE_FIRST_EXECUTION_BATCH_MANIFEST_PREVIEW,
    )
    parser.add_argument(
        "--operator-next-actions-preview",
        type=Path,
        default=DEFAULT_OPERATOR_NEXT_ACTIONS_PREVIEW,
    )
    parser.add_argument(
        "--training-set-eligibility-matrix-preview",
        type=Path,
        default=DEFAULT_TRAINING_SET_ELIGIBILITY_MATRIX_PREVIEW,
    )
    parser.add_argument(
        "--missing-data-policy-preview",
        type=Path,
        default=DEFAULT_MISSING_DATA_POLICY_PREVIEW,
    )
    parser.add_argument(
        "--final-structured-dataset-bundle-preview",
        type=Path,
        default=DEFAULT_FINAL_STRUCTURED_DATASET_BUNDLE_PREVIEW,
    )
    parser.add_argument(
        "--release-grade-readiness-preview",
        type=Path,
        default=DEFAULT_RELEASE_GRADE_READINESS_PREVIEW,
    )
    parser.add_argument(
        "--release-grade-closure-queue-preview",
        type=Path,
        default=DEFAULT_RELEASE_GRADE_CLOSURE_QUEUE_PREVIEW,
    )
    parser.add_argument(
        "--release-runtime-maturity-preview",
        type=Path,
        default=DEFAULT_RELEASE_RUNTIME_MATURITY_PREVIEW,
    )
    parser.add_argument(
        "--release-source-coverage-depth-preview",
        type=Path,
        default=DEFAULT_RELEASE_SOURCE_COVERAGE_DEPTH_PREVIEW,
    )
    parser.add_argument(
        "--release-provenance-depth-preview",
        type=Path,
        default=DEFAULT_RELEASE_PROVENANCE_DEPTH_PREVIEW,
    )
    parser.add_argument(
        "--release-grade-runbook-preview",
        type=Path,
        default=DEFAULT_RELEASE_GRADE_RUNBOOK_PREVIEW,
    )
    parser.add_argument(
        "--release-accession-closure-matrix-preview",
        type=Path,
        default=DEFAULT_RELEASE_ACCESSION_CLOSURE_MATRIX_PREVIEW,
    )
    parser.add_argument(
        "--release-accession-action-queue-preview",
        type=Path,
        default=DEFAULT_RELEASE_ACCESSION_ACTION_QUEUE_PREVIEW,
    )
    parser.add_argument(
        "--release-promotion-gate-preview",
        type=Path,
        default=DEFAULT_RELEASE_PROMOTION_GATE_PREVIEW,
    )
    parser.add_argument(
        "--release-source-fix-followup-batch-preview",
        type=Path,
        default=DEFAULT_RELEASE_SOURCE_FIX_FOLLOWUP_BATCH_PREVIEW,
    )
    parser.add_argument(
        "--release-candidate-promotion-preview",
        type=Path,
        default=DEFAULT_RELEASE_CANDIDATE_PROMOTION_PREVIEW,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    dashboard = build_operator_dashboard(
        coverage_path=args.coverage,
        metrics_path=args.metrics,
        summary_path=args.summary,
        packet_deficit_path=args.packet_deficit,
        tier1_direct_pipeline_path=args.tier1_direct_pipeline,
        canonical_latest_path=args.canonical_latest,
        summary_library_inventory_path=args.summary_library_inventory,
        protein_variant_library_inventory_path=DEFAULT_PROTEIN_VARIANT_LIBRARY_INVENTORY,
        structure_unit_library_inventory_path=args.structure_unit_library_inventory,
        protein_similarity_signature_preview_path=args.protein_similarity_signature_preview,
        dictionary_preview_path=args.dictionary_preview,
        motif_domain_compact_preview_family_path=args.motif_domain_compact_preview_family,
        interaction_similarity_signature_preview_path=(
            args.interaction_similarity_signature_preview
        ),
        interaction_similarity_signature_validation_path=(
            args.interaction_similarity_signature_validation
        ),
        sabio_rk_support_preview_path=args.sabio_rk_support_preview,
        kinetics_support_preview_path=args.kinetics_support_preview,
        compact_enrichment_policy_preview_path=args.compact_enrichment_policy_preview,
        scrape_readiness_registry_preview_path=args.scrape_readiness_registry_preview,
        procurement_source_completion_preview_path=args.procurement_source_completion_preview,
        string_interaction_materialization_plan_preview_path=(
            args.string_interaction_materialization_plan_preview
        ),
        uniref_cluster_materialization_plan_preview_path=(
            args.uniref_cluster_materialization_plan_preview
        ),
        pdb_enrichment_scrape_registry_preview_path=(args.pdb_enrichment_scrape_registry_preview),
        structure_entry_context_preview_path=args.structure_entry_context_preview,
        pdb_enrichment_harvest_preview_path=args.pdb_enrichment_harvest_preview,
        pdb_enrichment_validation_preview_path=args.pdb_enrichment_validation_preview,
        ligand_context_scrape_registry_preview_path=(args.ligand_context_scrape_registry_preview),
        protein_origin_context_preview_path=args.protein_origin_context_preview,
        catalytic_site_context_preview_path=args.catalytic_site_context_preview,
        targeted_page_scrape_registry_preview_path=(args.targeted_page_scrape_registry_preview),
        seed_plus_neighbors_structured_corpus_preview_path=(
            args.seed_plus_neighbors_structured_corpus_preview
        ),
        training_set_baseline_sidecar_preview_path=args.training_set_baseline_sidecar_preview,
        training_set_multimodal_sidecar_preview_path=(args.training_set_multimodal_sidecar_preview),
        bindingdb_dump_inventory_preview_path=args.bindingdb_dump_inventory_preview,
        bindingdb_target_polymer_context_preview_path=(
            args.bindingdb_target_polymer_context_preview
        ),
        bindingdb_structure_bridge_preview_path=args.bindingdb_structure_bridge_preview,
        archive_cleanup_keeper_rules_preview_path=(args.archive_cleanup_keeper_rules_preview),
        procurement_tail_freeze_gate_preview_path=(args.procurement_tail_freeze_gate_preview),
        ligand_support_readiness_preview_path=args.ligand_support_readiness_preview,
        ligand_identity_pilot_preview_path=args.ligand_identity_pilot_preview,
        ligand_stage1_operator_queue_preview_path=(args.ligand_stage1_operator_queue_preview),
        p00387_ligand_extraction_validation_preview_path=(
            args.p00387_ligand_extraction_validation_preview
        ),
        q9nzd4_bridge_validation_preview_path=args.q9nzd4_bridge_validation_preview,
        ligand_stage1_validation_panel_preview_path=(args.ligand_stage1_validation_panel_preview),
        ligand_identity_core_materialization_preview_path=(
            args.ligand_identity_core_materialization_preview
        ),
        next_real_ligand_row_gate_preview_path=(args.next_real_ligand_row_gate_preview),
        next_real_ligand_row_decision_preview_path=(args.next_real_ligand_row_decision_preview),
        ligand_row_materialization_preview_path=args.ligand_row_materialization_preview,
        ligand_similarity_signature_preview_path=args.ligand_similarity_signature_preview,
        ligand_similarity_signature_gate_preview_path=(
            args.ligand_similarity_signature_gate_preview
        ),
        structure_similarity_signature_preview_path=(args.structure_similarity_signature_preview),
        structure_variant_bridge_summary_path=args.structure_variant_bridge_summary,
        structure_variant_candidate_map_path=args.structure_variant_candidate_map,
        structure_followup_payload_preview_path=args.structure_followup_payload_preview,
        structure_followup_single_accession_preview_path=(
            args.structure_followup_single_accession_preview
        ),
        structure_followup_single_accession_validation_preview_path=(
            args.structure_followup_single_accession_validation_preview
        ),
        operator_accession_coverage_matrix_path=args.operator_accession_coverage_matrix,
        leakage_signature_preview_path=args.leakage_signature_preview,
        leakage_group_preview_path=args.leakage_group_preview,
        entity_split_recipe_preview_path=args.entity_split_recipe_preview,
        entity_split_assignment_preview_path=args.entity_split_assignment_preview,
        split_engine_input_preview_path=args.split_engine_input_preview,
        split_engine_dry_run_validation_path=args.split_engine_dry_run_validation,
        split_fold_export_gate_preview_path=args.split_fold_export_gate_preview,
        split_fold_export_gate_validation_path=args.split_fold_export_gate_validation,
        split_fold_export_staging_preview_path=args.split_fold_export_staging_preview,
        split_fold_export_staging_validation_path=args.split_fold_export_staging_validation,
        split_post_staging_gate_check_preview_path=(args.split_post_staging_gate_check_preview),
        split_post_staging_gate_check_validation_path=(
            args.split_post_staging_gate_check_validation
        ),
        split_fold_export_request_preview_path=args.split_fold_export_request_preview,
        split_fold_export_request_validation_path=(args.split_fold_export_request_validation),
        bundle_manifest_validation_path=DEFAULT_BUNDLE_MANIFEST_VALIDATION,
        duplicate_executor_status_path=DEFAULT_DUPLICATE_EXECUTOR_STATUS,
        duplicate_first_execution_preview_path=args.duplicate_first_execution_preview,
        duplicate_delete_ready_manifest_preview_path=(args.duplicate_delete_ready_manifest_preview),
        duplicate_post_delete_verification_contract_preview_path=(
            args.duplicate_post_delete_verification_contract_preview
        ),
        duplicate_first_execution_batch_manifest_preview_path=(
            args.duplicate_first_execution_batch_manifest_preview
        ),
        operator_next_actions_preview_path=args.operator_next_actions_preview,
        training_set_eligibility_matrix_preview_path=(args.training_set_eligibility_matrix_preview),
        missing_data_policy_preview_path=args.missing_data_policy_preview,
        final_structured_dataset_bundle_preview_path=args.final_structured_dataset_bundle_preview,
        release_grade_readiness_preview_path=args.release_grade_readiness_preview,
        release_grade_closure_queue_preview_path=args.release_grade_closure_queue_preview,
        release_runtime_maturity_preview_path=args.release_runtime_maturity_preview,
        release_source_coverage_depth_preview_path=args.release_source_coverage_depth_preview,
        release_provenance_depth_preview_path=args.release_provenance_depth_preview,
        release_grade_runbook_preview_path=args.release_grade_runbook_preview,
        release_accession_closure_matrix_preview_path=args.release_accession_closure_matrix_preview,
        release_accession_action_queue_preview_path=(
            args.release_accession_action_queue_preview
        ),
        release_promotion_gate_preview_path=args.release_promotion_gate_preview,
        release_source_fix_followup_batch_preview_path=(
            args.release_source_fix_followup_batch_preview
        ),
        release_candidate_promotion_preview_path=args.release_candidate_promotion_preview,
    )
    _write_json(args.output, dashboard)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
