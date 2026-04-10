from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.library.summary_record import (
    ProteinSummaryRecord,
    ProteinVariantSummaryRecord,
    StructureUnitSummaryRecord,
    SummaryLibrarySchema,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _protein_library() -> SummaryLibrarySchema:
    return SummaryLibrarySchema(
        library_id="summary-library:protein-materialized:v1",
        source_manifest_id="UniProt:2026-03-23|IntAct:20260323T002625Z",
        records=(
            ProteinSummaryRecord(
                summary_id="protein:P04637",
                protein_ref="protein:P04637",
                protein_name="Cellular tumor antigen p53",
                organism_name="Homo sapiens",
                taxon_id=9606,
                sequence_checksum="checksum:p53",
                sequence_version="1",
                sequence_length=393,
                aliases=("P04637",),
            ),
        ),
    )


def _variant_library() -> SummaryLibrarySchema:
    return SummaryLibrarySchema(
        library_id="summary-library:protein-variants:v1",
        source_manifest_id="UniProt:2026-03-23|IntAct:20260323T002625Z|VariantSupport:p54",
        schema_version=2,
        records=(
            ProteinVariantSummaryRecord(
                summary_id="protein_variant:protein:P04637:R175H",
                protein_ref="protein:P04637",
                parent_protein_ref="protein:P04637",
                variant_signature="R175H",
                variant_kind="point_mutation",
                mutation_list=("R175H",),
                sequence_delta_signature="R175H",
                organism_name="Homo sapiens",
                taxon_id=9606,
            ),
        ),
    )


def _structure_library() -> SummaryLibrarySchema:
    return SummaryLibrarySchema(
        library_id="summary-library:structure-units:v1",
        source_manifest_id="UniProt:2026-03-23|SIFTS:2026-03-30",
        schema_version=2,
        records=(
            StructureUnitSummaryRecord(
                summary_id="structure_unit:protein:P04637:2AC0:A",
                protein_ref="protein:P04637",
                structure_source="PDB",
                structure_id="2AC0",
                structure_kind="experimental_chain",
                chain_id="A",
                experimental_or_predicted="experimental",
            ),
        ),
    )


def test_export_bundle_manifest_example_mode(tmp_path: Path) -> None:
    protein_path = tmp_path / "protein_summary_library.json"
    protein_path.write_text(json.dumps(_protein_library().to_dict(), indent=2), encoding="utf-8")
    variant_path = tmp_path / "protein_variant_summary_library.json"
    variant_path.write_text(json.dumps(_variant_library().to_dict(), indent=2), encoding="utf-8")
    structure_path = tmp_path / "structure_unit_summary_library.json"
    protein_similarity_signature_preview_path = (
        tmp_path / "protein_similarity_signature_preview.json"
    )
    dictionary_preview_path = tmp_path / "dictionary_preview.json"
    structure_followup_payload_preview_path = (
        tmp_path / "structure_followup_payload_preview.json"
    )
    ligand_support_readiness_preview_path = (
        tmp_path / "ligand_support_readiness_preview.json"
    )
    ligand_identity_pilot_preview_path = tmp_path / "ligand_identity_pilot_preview.json"
    ligand_stage1_validation_panel_preview_path = (
        tmp_path / "ligand_stage1_validation_panel_preview.json"
    )
    ligand_identity_core_materialization_preview_path = (
        tmp_path / "ligand_identity_core_materialization_preview.json"
    )
    ligand_row_materialization_preview_path = (
        tmp_path / "ligand_row_materialization_preview.json"
    )
    ligand_similarity_signature_preview_path = (
        tmp_path / "ligand_similarity_signature_preview.json"
    )
    q9nzd4_bridge_validation_preview_path = (
        tmp_path / "q9nzd4_bridge_validation_preview.json"
    )
    motif_domain_compact_preview_family_path = (
        tmp_path / "motif_domain_compact_preview_family.json"
    )
    kinetics_support_preview_path = tmp_path / "kinetics_support_preview.json"
    compact_enrichment_policy_preview_path = (
        tmp_path / "compact_enrichment_policy_preview.json"
    )
    structure_signature_preview_path = tmp_path / "structure_similarity_signature_preview.json"
    leakage_group_preview_path = tmp_path / "leakage_group_preview.json"
    structure_path.write_text(
        json.dumps(_structure_library().to_dict(), indent=2),
        encoding="utf-8",
    )
    protein_similarity_signature_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 1,
                "rows": [
                    {
                        "signature_id": "protein_similarity:protein:P04637",
                        "protein_ref": "protein:P04637",
                        "accession": "P04637",
                        "protein_similarity_group": "checksum:p53",
                        "sequence_equivalence_group": "checksum:p53",
                        "similarity_basis": "sequence_equivalence_group",
                        "provenance_ref": "sequence:P04637",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    dictionary_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 1,
                "rows": [
                    {
                        "dictionary_id": "dictionary:domain:InterPro:IPR002117",
                        "reference_kind": "domain",
                        "namespace": "InterPro",
                        "identifier": "IPR002117",
                        "label": "p53_tumour_suppressor",
                        "source_name": "InterPro",
                        "usage_count": 1,
                        "supporting_record_count": 1,
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    structure_followup_payload_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "payload_row_count": 1,
                "payload_rows": [
                    {
                        "accession": "P04637",
                        "protein_ref": "protein:P04637",
                        "variant_ref": "protein_variant:protein:P04637:R175H",
                        "structure_id": "2AC0",
                        "chain_id": "A",
                        "coverage": 0.8,
                        "join_status": "candidate_only",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_support_readiness_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 1,
                "rows": [
                    {
                        "accession": "P04637",
                        "source_ref": "ligand:P04637",
                        "pilot_role": "lead_anchor",
                        "pilot_lane_status": "rescuable_now",
                        "packet_status": "partial",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_identity_pilot_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 1,
                "rows": [
                    {
                        "accession": "P04637",
                        "source_ref": "ligand:P04637",
                        "pilot_role": "lead_anchor",
                        "pilot_lane_status": "rescuable_now",
                        "grounded_evidence_kind": "local_chembl_bulk_assay_summary",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_stage1_validation_panel_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 1,
                "rows": [
                    {
                        "accession": "P04637",
                        "lane_kind": "bulk_assay_anchor",
                        "status": "aligned",
                        "evidence_kind": "local_chembl_bulk_assay_summary",
                        "target_or_structure": "CHEMBL2146",
                        "next_truthful_stage": "ingest_local_bulk_assay",
                        "candidate_only": False,
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_identity_core_materialization_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 1,
                "rows": [
                    {
                        "accession": "P04637",
                        "source_ref": "ligand:P04637",
                        "materialization_status": "grounded_ready_identity_core_candidate",
                        "grounded_evidence_kind": "local_chembl_bulk_assay_summary",
                        "next_truthful_stage": "ingest_local_bulk_assay",
                        "candidate_only": False,
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_row_materialization_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 2,
                "rows": [
                    {
                        "row_id": "ligand_row:protein:P04637:chembl:CHEMBL1",
                        "accession": "P04637",
                        "protein_ref": "protein:P04637",
                        "source_ref": "ligand:P04637",
                        "ligand_ref": "chembl:CHEMBL1",
                        "ligand_namespace": "ChEMBL",
                        "materialization_status": "grounded_lightweight_ligand_row",
                        "evidence_kind": "local_chembl_bulk_assay_row",
                        "candidate_only": False,
                    },
                    {
                        "row_id": "ligand_row:protein:Q9NZD4:pdb_ccd:CHK",
                        "accession": "Q9NZD4",
                        "protein_ref": "protein:Q9NZD4",
                        "source_ref": "ligand:Q9NZD4",
                        "ligand_ref": "pdb_ccd:CHK",
                        "ligand_namespace": "PDB_CCD",
                        "materialization_status": "candidate_bridge_lightweight_ligand_row",
                        "evidence_kind": "local_structure_bridge_component",
                        "candidate_only": True,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_similarity_signature_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 2,
                "rows": [
                    {
                        "signature_id": "ligand_similarity:protein:P04637:chembl:CHEMBL1",
                        "entity_ref": "ligand_row:protein:P04637:chembl:CHEMBL1",
                        "protein_ref": "protein:P04637",
                        "accession": "P04637",
                        "ligand_ref": "chembl:CHEMBL1",
                        "exact_ligand_identity_group": "chembl:CHEMBL1",
                        "chemical_series_group": "smiles:aaa",
                        "candidate_only": False,
                    },
                    {
                        "signature_id": "ligand_similarity:protein:Q9NZD4:pdb_ccd:CHK",
                        "entity_ref": "ligand_row:protein:Q9NZD4:pdb_ccd:CHK",
                        "protein_ref": "protein:Q9NZD4",
                        "accession": "Q9NZD4",
                        "ligand_ref": "pdb_ccd:CHK",
                        "exact_ligand_identity_group": "pdb_ccd:CHK",
                        "chemical_series_group": "pdb_ccd:CHK",
                        "candidate_only": True,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    q9nzd4_bridge_validation_preview_path.write_text(
        json.dumps(
            {
                "status": "aligned",
                "accession": "Q9NZD4",
                "best_pdb_id": "1Y01",
                "component_id": "CHK",
                "component_role": "primary_binder",
                "matched_pdb_id_count": 3,
                "truth_boundary": {"candidate_only": True},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    motif_domain_compact_preview_family_path.write_text(
        json.dumps({"status": "complete", "row_count": 1}),
        encoding="utf-8",
    )
    kinetics_support_preview_path.write_text(
        json.dumps({"status": "complete", "row_count": 1}),
        encoding="utf-8",
    )
    compact_enrichment_policy_preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "family_name": "interaction_similarity_preview",
                        "policy_label": "report_only_non_governing",
                    },
                    {
                        "family_name": "motif_domain_compact_preview_family",
                        "policy_label": "preview_bundle_safe_non_governing",
                    },
                    {
                        "family_name": "kinetics_support_preview",
                        "policy_label": "preview_bundle_safe_non_governing",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    structure_signature_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 1,
                "rows": [
                    {
                        "entity_ref": "structure_unit:protein:P04637:2AC0:A",
                        "protein_ref": "protein:P04637",
                        "structure_ref": "2AC0:A",
                        "fold_signature_id": "foldsig-1",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    leakage_group_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 1,
                "rows": [
                    {
                        "linked_group_id": "protein:P04637",
                        "protein_ref": "protein:P04637",
                        "accession": "P04637",
                        "split_name": "train",
                        "leakage_risk_class": "structure_followup",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    canonical_path = tmp_path / "canonical.json"
    canonical_path.write_text(
        json.dumps(
            {
                "status": "ready",
                "run_id": "raw-canonical-1",
                "record_counts": {"protein": 1},
                "unresolved_counts": {"assay_unresolved_cases": 0},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "summary": {
                    "source_count": 10,
                    "present_source_count": 9,
                    "partial_source_count": 1,
                    "missing_source_count": 0,
                    "procurement_priority_sources": ["elm"],
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "primary_bundle_shape": {
                    "required_assets": [
                        "proteosphere-lite.sqlite.zst",
                        "proteosphere-lite.release_manifest.json",
                        "proteosphere-lite.sha256",
                    ],
                    "optional_assets": [
                        "proteosphere-lite.contents.md",
                        "proteosphere-lite.schema.md",
                    ],
                    "content_scope": "planning_governance_only",
                },
                "table_family_contract": [
                    "proteins",
                    "protein_variants",
                    "structures",
                    "ligands",
                    "interactions",
                    "motif_annotations",
                    "pathway_annotations",
                    "provenance_records",
                    "protein_similarity_signatures",
                    "structure_followup_payloads",
                    "ligand_support_readiness",
                    "ligand_identity_pilot",
                    "ligand_stage1_validation_panel",
                    "ligand_identity_core_materialization_preview",
                    "q9nzd4_bridge_validation_preview",
                    "structure_similarity_signatures",
                    "ligand_similarity_signatures",
                    "interaction_similarity_signatures",
                    "leakage_groups",
                    "dictionaries",
                ],
                "budget_classes": [
                    {"class_id": "A", "compressed_size_max_bytes": 67108864},
                    {
                        "class_id": "B",
                        "compressed_size_min_exclusive_bytes": 67108864,
                        "compressed_size_max_bytes": 134217728,
                    },
                    {
                        "class_id": "C",
                        "compressed_size_min_exclusive_bytes": 134217728,
                        "compressed_size_max_bytes": 268435456,
                    },
                    {"class_id": "D", "compressed_size_min_exclusive_bytes": 268435456},
                ],
                "default_exclusions": ["raw_mmcif"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "manifest.json"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_bundle_manifest.py"),
            "--summary-library",
            str(protein_path),
            "--protein-variant-library",
            str(variant_path),
            "--structure-library",
            str(structure_path),
            "--protein-similarity-signature-preview",
            str(protein_similarity_signature_preview_path),
            "--dictionary-preview",
            str(dictionary_preview_path),
            "--structure-followup-payload-preview",
            str(structure_followup_payload_preview_path),
            "--ligand-support-readiness-preview",
            str(ligand_support_readiness_preview_path),
            "--ligand-identity-pilot-preview",
            str(ligand_identity_pilot_preview_path),
            "--ligand-stage1-validation-panel-preview",
            str(ligand_stage1_validation_panel_preview_path),
            "--ligand-identity-core-materialization-preview",
            str(ligand_identity_core_materialization_preview_path),
            "--ligand-row-materialization-preview",
            str(ligand_row_materialization_preview_path),
            "--ligand-similarity-signature-preview",
            str(ligand_similarity_signature_preview_path),
            "--q9nzd4-bridge-validation-preview",
            str(q9nzd4_bridge_validation_preview_path),
            "--motif-domain-compact-preview-family",
            str(motif_domain_compact_preview_family_path),
            "--kinetics-support-preview",
            str(kinetics_support_preview_path),
            "--compact-enrichment-policy-preview",
            str(compact_enrichment_policy_preview_path),
            "--structure-signature-preview",
            str(structure_signature_preview_path),
            "--leakage-group-preview",
            str(leakage_group_preview_path),
            "--canonical-status",
            str(canonical_path),
            "--coverage-status",
            str(coverage_path),
            "--contract",
            str(contract_path),
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    counts = payload["record_counts"]
    assert counts["proteins"] == 1
    assert counts["protein_variants"] == 1
    assert counts["structures"] == 1
    assert counts["ligands"] == 2
    assert counts["ligand_similarity_signatures"] == 2
    assert counts["dictionaries"] == 1
    assert counts["structure_followup_payloads"] == 1
    assert counts["ligand_support_readiness"] == 1
    assert counts["ligand_identity_pilot"] == 1
    assert counts["ligand_stage1_validation_panel"] == 1
    assert counts["ligand_identity_core_materialization_preview"] == 1
    assert counts["ligand_row_materialization_preview"] == 2
    assert counts["q9nzd4_bridge_validation_preview"] == 1
    assert counts["motif_domain_compact_preview_family"] == 1
    assert counts["kinetics_support_preview"] == 1
    assert counts["protein_similarity_signatures"] == 1
    assert counts["structure_similarity_signatures"] == 1
    assert counts["leakage_groups"] == 1
    assert payload["manifest_status"] == "example_only_not_built"
    assert payload["validation_status"] == "warning"


def test_export_bundle_manifest_release_mode_fails_without_assets(tmp_path: Path) -> None:
    protein_path = tmp_path / "protein_summary_library.json"
    protein_path.write_text(json.dumps(_protein_library().to_dict(), indent=2), encoding="utf-8")
    canonical_path = tmp_path / "canonical.json"
    protein_similarity_signature_preview_path = (
        tmp_path / "protein_similarity_signature_preview.json"
    )
    dictionary_preview_path = tmp_path / "dictionary_preview.json"
    structure_followup_payload_preview_path = (
        tmp_path / "structure_followup_payload_preview.json"
    )
    ligand_support_readiness_preview_path = (
        tmp_path / "ligand_support_readiness_preview.json"
    )
    ligand_identity_pilot_preview_path = tmp_path / "ligand_identity_pilot_preview.json"
    ligand_stage1_validation_panel_preview_path = (
        tmp_path / "ligand_stage1_validation_panel_preview.json"
    )
    ligand_identity_core_materialization_preview_path = (
        tmp_path / "ligand_identity_core_materialization_preview.json"
    )
    ligand_row_materialization_preview_path = (
        tmp_path / "ligand_row_materialization_preview.json"
    )
    ligand_similarity_signature_preview_path = (
        tmp_path / "ligand_similarity_signature_preview.json"
    )
    q9nzd4_bridge_validation_preview_path = (
        tmp_path / "q9nzd4_bridge_validation_preview.json"
    )
    motif_domain_compact_preview_family_path = (
        tmp_path / "motif_domain_compact_preview_family.json"
    )
    kinetics_support_preview_path = tmp_path / "kinetics_support_preview.json"
    compact_enrichment_policy_preview_path = (
        tmp_path / "compact_enrichment_policy_preview.json"
    )
    structure_signature_preview_path = tmp_path / "structure_similarity_signature_preview.json"
    leakage_group_preview_path = tmp_path / "leakage_group_preview.json"
    canonical_path.write_text(
        json.dumps(
            {
                "status": "ready",
                "run_id": "raw-canonical-1",
                "record_counts": {"protein": 1},
                "unresolved_counts": {"assay_unresolved_cases": 0},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "summary": {
                    "source_count": 1,
                    "present_source_count": 1,
                    "partial_source_count": 0,
                    "missing_source_count": 0,
                    "procurement_priority_sources": [],
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "primary_bundle_shape": {
                    "required_assets": [
                        "proteosphere-lite.sqlite.zst",
                        "proteosphere-lite.release_manifest.json",
                        "proteosphere-lite.sha256",
                    ],
                    "optional_assets": [],
                    "content_scope": "planning_governance_only",
                },
                "table_family_contract": ["proteins"],
                "budget_classes": [{"class_id": "A", "compressed_size_max_bytes": 67108864}],
                "default_exclusions": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    structure_signature_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 0,
                "rows": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    protein_similarity_signature_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 0,
                "rows": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    dictionary_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 0,
                "rows": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    structure_followup_payload_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "payload_row_count": 0,
                "payload_rows": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_support_readiness_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 0,
                "rows": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_identity_pilot_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 0,
                "rows": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_stage1_validation_panel_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 0,
                "rows": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_identity_core_materialization_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 0,
                "rows": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_row_materialization_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 0,
                "rows": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ligand_similarity_signature_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 0,
                "rows": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    q9nzd4_bridge_validation_preview_path.write_text(
        json.dumps(
            {
                "status": "aligned",
                "accession": "Q9NZD4",
                "best_pdb_id": "1Y01",
                "component_id": "CHK",
                "component_role": "primary_binder",
                "matched_pdb_id_count": 3,
                "truth_boundary": {"candidate_only": True},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    motif_domain_compact_preview_family_path.write_text(
        json.dumps({"status": "complete", "row_count": 1}),
        encoding="utf-8",
    )
    kinetics_support_preview_path.write_text(
        json.dumps({"status": "complete", "row_count": 1}),
        encoding="utf-8",
    )
    compact_enrichment_policy_preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "family_name": "motif_domain_compact_preview_family",
                        "policy_label": "preview_bundle_safe_non_governing",
                    },
                    {
                        "family_name": "kinetics_support_preview",
                        "policy_label": "preview_bundle_safe_non_governing",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    leakage_group_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 0,
                "rows": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "manifest.json"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_bundle_manifest.py"),
            "--summary-library",
            str(protein_path),
            "--canonical-status",
            str(canonical_path),
            "--protein-similarity-signature-preview",
            str(protein_similarity_signature_preview_path),
            "--dictionary-preview",
            str(dictionary_preview_path),
            "--structure-followup-payload-preview",
            str(structure_followup_payload_preview_path),
            "--ligand-support-readiness-preview",
            str(ligand_support_readiness_preview_path),
            "--ligand-identity-pilot-preview",
            str(ligand_identity_pilot_preview_path),
            "--ligand-stage1-validation-panel-preview",
            str(ligand_stage1_validation_panel_preview_path),
            "--ligand-identity-core-materialization-preview",
            str(ligand_identity_core_materialization_preview_path),
            "--ligand-row-materialization-preview",
            str(ligand_row_materialization_preview_path),
            "--ligand-similarity-signature-preview",
            str(ligand_similarity_signature_preview_path),
            "--q9nzd4-bridge-validation-preview",
            str(q9nzd4_bridge_validation_preview_path),
            "--motif-domain-compact-preview-family",
            str(motif_domain_compact_preview_family_path),
            "--kinetics-support-preview",
            str(kinetics_support_preview_path),
            "--compact-enrichment-policy-preview",
            str(compact_enrichment_policy_preview_path),
            "--structure-signature-preview",
            str(structure_signature_preview_path),
            "--leakage-group-preview",
            str(leakage_group_preview_path),
            "--coverage-status",
            str(coverage_path),
            "--contract",
            str(contract_path),
            "--bundle-file",
            str(tmp_path / "missing.sqlite.zst"),
            "--manifest-file",
            str(tmp_path / "missing.release_manifest.json"),
            "--checksum-file",
            str(tmp_path / "missing.sha256"),
            "--mode",
            "release",
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["manifest_status"] == "export_failed"
    assert payload["validation_status"] == "failed"
    assert "missing_required_asset:bundle_file" in payload["validation_errors"]
