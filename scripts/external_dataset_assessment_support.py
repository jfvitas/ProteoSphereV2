from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SPLIT_LABELS = REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "split_labels.json"
DEFAULT_LIBRARY_CONTRACT = (
    REPO_ROOT / "artifacts" / "status" / "p50_training_set_creator_library_contract.json"
)
DEFAULT_EXTERNAL_COHORT_AUDIT = REPO_ROOT / "artifacts" / "status" / "external_cohort_audit.json"
DEFAULT_ELIGIBILITY_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_BINDING_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "binding_measurement_registry_preview.json"
)
DEFAULT_ACCESSION_BINDING_SUPPORT = (
    REPO_ROOT / "artifacts" / "status" / "accession_binding_support_preview.json"
)
DEFAULT_OPERATOR_ACCESSION_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "summary_library_operator_accession_matrix.json"
)
DEFAULT_FUTURE_STRUCTURE_TRIAGE = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_triage_preview.json"
)
DEFAULT_OFF_TARGET_ADJACENT_PROFILE = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "bindingdb_off_target_adjacent_context_profile_preview.json"
)
DEFAULT_INTERACTION_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "interaction_context_preview.json"
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _listify(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    seen: dict[str, str] = {}
    for value in values:
        text = str(value or "").strip()
        if text:
            seen.setdefault(text.casefold(), text)
    return list(seen.values())


def _index_by_accession(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        accession = str(row.get("accession") or "").strip()
        if accession:
            indexed[accession] = row
    return indexed


def build_external_dataset_intake_contract_preview() -> dict[str, Any]:
    return {
        "artifact_id": "external_dataset_intake_contract_preview",
        "schema_id": "proteosphere-external-dataset-intake-contract-preview-2026-04-03",
        "status": "report_only",
        "generated_at": utc_now(),
        "accepted_shapes": [
            {
                "shape_id": "json_manifest",
                "priority": 1,
                "required_top_level_keys": ["manifest_id", "rows"],
                "required_row_keys": ["accession", "split"],
                "notes": [
                    "Preferred intake shape for machine-readable external dataset assessment.",
                    (
                        "Rows may optionally include pdb_id, ligand rows, "
                        "measurement family fields, provenance, and modality "
                        "claims."
                    ),
                ],
            },
            {
                "shape_id": "folder_package_manifest",
                "priority": 2,
                "required_top_level_keys": ["manifest_path"],
                "required_row_keys": ["accession"],
                "notes": [
                    (
                        "Folder/package manifest intake is accepted when the "
                        "dataset already ships a package manifest or packet "
                        "index."
                    ),
                    "The assessor remains read-only and does not mutate internal library state.",
                ],
            },
        ],
        "secondary_shapes": [
            {
                "shape_id": "csv_or_tsv_tabular",
                "status": "deferred_until_primary_shapes_stable",
                "notes": [
                    "Add only after JSON manifest and folder/package manifest flows are stable."
                ],
            }
        ],
        "verdict_vocabulary": [
            "usable_with_caveats",
            "audit_only",
            "blocked_pending_cleanup",
            "blocked_pending_mapping",
            "unsafe_for_training",
        ],
        "truth_boundary": {
            "summary": (
                "The intake contract defines what the external assessor can "
                "evaluate. It does not ingest, "
                "materialize, or mutate external datasets."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_external_dataset_audits(
    split_labels: dict[str, Any],
    library_contract: dict[str, Any],
    external_cohort_audit: dict[str, Any],
    eligibility_matrix: dict[str, Any],
    binding_registry: dict[str, Any],
    accession_binding_support: dict[str, Any],
    operator_accession_matrix: dict[str, Any],
    future_structure_triage: dict[str, Any],
    off_target_adjacent_profile: dict[str, Any],
    interaction_context: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    labels = [dict(item) for item in (split_labels.get("labels") or []) if isinstance(item, dict)]
    label_accessions = [
        str(item.get("accession") or "").strip()
        for item in labels
        if str(item.get("accession") or "").strip()
    ]
    label_accession_set = set(label_accessions)
    duplicate_accessions = sorted(
        accession for accession, count in Counter(label_accessions).items() if count > 1
    )
    leakage_ready = split_labels.get("leakage_ready") or {}

    eligibility_rows = _index_by_accession(eligibility_matrix.get("rows") or [])
    matrix_rows = _index_by_accession(operator_accession_matrix.get("rows") or [])
    binding_rows = _index_by_accession(accession_binding_support.get("rows") or [])

    missing_accessions = sorted(
        accession for accession in label_accession_set if accession not in eligibility_rows
    )
    candidate_only_accessions = sorted(
        accession
        for accession in label_accession_set
        if (
            (eligibility_rows.get(accession, {}).get("task_eligibility") or {})
            .get("grounded_ligand_similarity_preview", {})
            .get("status")
        )
        == "candidate_only_non_governing"
    )
    blocked_accessions = sorted(
        accession
        for accession in label_accession_set
        if (
            (eligibility_rows.get(accession, {}).get("task_eligibility") or {})
            .get("full_packet_current_latest", {})
            .get("status")
        )
        == "blocked_pending_acquisition"
    )
    structure_seed_overlap = sorted(
        accession
        for accession in label_accession_set
        if int(matrix_rows.get(accession, {}).get("structure_unit_count") or 0) > 0
    )
    measured_accessions = sorted(
        accession for accession in label_accession_set if accession in binding_rows
    )

    binding_summary = binding_registry.get("summary") or {}
    future_summary = future_structure_triage.get("summary") or {}
    adjacent_summary = off_target_adjacent_profile.get("summary") or {}
    interaction_summary = interaction_context.get("summary") or {}
    cohort_results = external_cohort_audit.get("audit_results") or {}

    leakage_audit = {
        "artifact_id": "external_dataset_leakage_audit_preview",
        "schema_id": "proteosphere-external-dataset-leakage-audit-preview-2026-04-03",
        "status": "attention_needed" if duplicate_accessions else "ok",
        "generated_at": utc_now(),
        "summary": {
            "dataset_accession_count": len(label_accession_set),
            "duplicate_accession_count": len(duplicate_accessions),
            "split_policy": split_labels.get("split_policy"),
            "accession_level_only": leakage_ready.get("accession_level_only"),
            "cross_split_duplicates": _listify(leakage_ready.get("cross_split_duplicates")),
            "blocked_accessions": blocked_accessions,
        },
        "findings": {
            "duplicate_accessions": duplicate_accessions,
            "cross_split_duplicates": _listify(leakage_ready.get("cross_split_duplicates")),
            "notes": _listify((cohort_results.get("leakage") or {}).get("notes")),
        },
        "verdict": "usable_with_caveats" if not duplicate_accessions else "blocked_pending_cleanup",
    }

    modality_audit = {
        "artifact_id": "external_dataset_modality_audit_preview",
        "schema_id": "proteosphere-external-dataset-modality-audit-preview-2026-04-03",
        "status": (cohort_results.get("modality_readiness") or {}).get("status")
        or "attention_needed",
        "generated_at": utc_now(),
        "summary": {
            "candidate_only_accession_count": len(candidate_only_accessions),
            "missing_mapping_accession_count": len(missing_accessions),
            "blocked_full_packet_accession_count": len(blocked_accessions),
            "modality_counts": (cohort_results.get("modality_readiness") or {}).get(
                "modality_counts"
            )
            or {},
        },
        "findings": {
            "candidate_only_accessions": candidate_only_accessions,
            "missing_accessions": missing_accessions,
            "blocked_accessions": blocked_accessions,
            "coverage_gap_notes": _listify(
                (
                    (cohort_results.get("coverage_gaps") or {}).get(
                        "missing_modalities_by_accession"
                    )
                    or {}
                ).keys()
            ),
        },
        "verdict": "usable_with_caveats" if not missing_accessions else "blocked_pending_mapping",
    }

    binding_audit = {
        "artifact_id": "external_dataset_binding_audit_preview",
        "schema_id": "proteosphere-external-dataset-binding-audit-preview-2026-04-03",
        "status": "attention_needed",
        "generated_at": utc_now(),
        "summary": {
            "measured_accession_count": len(measured_accessions),
            "measurement_type_counts": dict(binding_summary.get("measurement_type_counts") or {}),
            "complex_type_counts": dict(binding_summary.get("complex_type_counts") or {}),
            "supported_measurement_accessions": measured_accessions,
        },
        "findings": {
            "notes": [
                (
                    "Assess concentration-style rows only when relation and "
                    "units permit normalization."
                ),
                "Keep direct ΔG and derived ΔG separate, and never derive ΔG from IC50/EC50.",
                (
                    "Treat missing units, impossible values, and relation-only "
                    "rows as blocking flaws for training use."
                ),
            ],
            "verdict_basis": "registry_summary_plus_accession_binding_support",
        },
        "verdict": "usable_with_caveats" if measured_accessions else "audit_only",
    }

    structure_audit = {
        "artifact_id": "external_dataset_structure_audit_preview",
        "schema_id": "proteosphere-external-dataset-structure-audit-preview-2026-04-03",
        "status": "attention_needed",
        "generated_at": utc_now(),
        "summary": {
            "seed_structure_overlap_accession_count": len(structure_seed_overlap),
            "seed_structure_overlap_accessions": structure_seed_overlap,
            "future_direct_grounding_candidate_count": future_summary.get(
                "direct_grounding_candidate_count"
            ),
            "future_off_target_adjacent_context_only_count": future_summary.get(
                "off_target_adjacent_context_only_count"
            ),
            "adjacent_target_accession_count": adjacent_summary.get(
                "unique_mapped_target_accession_count"
            ),
        },
        "findings": {
            "notes": [
                (
                    "Off-target adjacent structures must stay explanatory only "
                    "and must not be misrepresented as direct grounding evidence."
                ),
                (
                    "PDB/chain/entity to UniProt alignment should remain the "
                    "hard floor for structure claims."
                ),
            ],
            "mismatch_risk": "present"
            if int(future_summary.get("off_target_adjacent_context_only_count") or 0) > 0
            else "not_observed",
        },
        "verdict": "usable_with_caveats" if structure_seed_overlap else "audit_only",
    }

    provenance_audit = {
        "artifact_id": "external_dataset_provenance_audit_preview",
        "schema_id": "proteosphere-external-dataset-provenance-audit-preview-2026-04-03",
        "status": "attention_needed",
        "generated_at": utc_now(),
        "summary": {
            "library_contract_id": library_contract.get("artifact_id")
            or library_contract.get("contract_id"),
            "contract_status": library_contract.get("status"),
            "row_level_resolution_supported": True,
            "interaction_source_count": interaction_summary.get("source_count"),
            "binding_registry_source_counts": dict(binding_summary.get("source_counts") or {}),
        },
        "findings": {
            "notes": [
                (
                    "External datasets should expose stable source provenance, "
                    "PMIDs or equivalent publication anchors, and avoid "
                    "page-scraped-only claims as sole evidence."
                ),
                (
                    "Mixed trust tiers should remain explicit and should never "
                    "silently collapse into one consensus truth source."
                ),
            ],
            "missing_accessions": missing_accessions,
        },
        "verdict": "usable_with_caveats" if not missing_accessions else "blocked_pending_mapping",
    }

    overall_verdict = "usable_with_caveats"
    if duplicate_accessions:
        overall_verdict = "blocked_pending_cleanup"
    elif missing_accessions:
        overall_verdict = "blocked_pending_mapping"
    elif candidate_only_accessions and not measured_accessions:
        overall_verdict = "audit_only"

    top_level = {
        "artifact_id": "external_dataset_assessment_preview",
        "schema_id": "proteosphere-external-dataset-assessment-preview-2026-04-03",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "dataset_accession_count": len(label_accession_set),
            "overall_verdict": overall_verdict,
            "split_policy": split_labels.get("split_policy"),
            "missing_mapping_accession_count": len(missing_accessions),
            "candidate_only_accession_count": len(candidate_only_accessions),
            "measured_accession_count": len(measured_accessions),
            "seed_structure_overlap_accession_count": len(structure_seed_overlap),
        },
        "sub_audits": {
            "leakage": leakage_audit["verdict"],
            "modality": modality_audit["verdict"],
            "binding": binding_audit["verdict"],
            "structure": structure_audit["verdict"],
            "provenance": provenance_audit["verdict"],
        },
        "flaw_categories": [
            "leakage_risk",
            "duplicate_entities",
            "conflicting_accession_mapping",
            "ungrounded_ligand_rows",
            "off_target_adjacent_context_misuse",
            "impossible_assay_normalization",
            "split_contamination",
            "taxonomic_mismatch",
            "partial_coverage_overclaiming",
        ],
        "truth_boundary": {
            "summary": (
                "This assessor is advisory and fail-closed. It evaluates an "
                "external dataset against internal truth surfaces without "
                "mutating library state or blessing the dataset for training."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }

    return {
        "top_level": top_level,
        "leakage": leakage_audit,
        "modality": modality_audit,
        "binding": binding_audit,
        "structure": structure_audit,
        "provenance": provenance_audit,
    }


def render_markdown(title: str, payload: dict[str, Any]) -> str:
    lines = [f"# {title}", "", f"- Status: `{payload.get('status')}`"]
    summary = payload.get("summary") or {}
    if isinstance(summary, dict):
        for key, value in summary.items():
            lines.append(f"- `{key}`: `{json.dumps(value, sort_keys=True)}`")
    lines.append("")
    return "\n".join(lines)
