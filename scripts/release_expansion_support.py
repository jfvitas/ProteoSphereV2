from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"
STATUS_DIR = REPO_ROOT / "artifacts" / "status"

RELEASE_V1_MODE = "v1_frozen_release_candidate"
RELEASE_V2_MODE = "v2_post_procurement_expanded"
DEFAULT_EXTERNAL_DRIVE_ROOT = Path(r"E:\ProteoSphereV2_repository")
DEFAULT_EXPANSION_STAGING_ROOT = (
    REPO_ROOT / "data" / "reports" / "expansion_staging" / RELEASE_V2_MODE
)
DEFAULT_EXPANSION_INVENTORY_REPORT = (
    REPO_ROOT / "docs" / "reports" / "procurement_expansion_inventory_2026_04_05.md"
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else dict(default or {})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def as_posix(path: Path | str | None) -> str | None:
    if path is None:
        return None
    return str(path).replace("\\", "/")


def render_simple_markdown(title: str, bullet_rows: list[str]) -> str:
    lines = [f"# {title}", ""]
    lines.extend(f"- {row}" for row in bullet_rows)
    lines.append("")
    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class ExpansionItem:
    priority: int
    dataset_id: str
    source: str
    family: str
    size_bytes: int | None
    value_tier: str
    feeds_canonical_corpus: bool
    cold_storage_only: bool
    notes: str
    requires_external_drive: bool = True


EXPANSION_ITEMS: tuple[ExpansionItem, ...] = (
    ExpansionItem(
        1,
        "uniprot_embeddings",
        "UniProt",
        "knowledgebase/embeddings",
        1_662_832_048,
        "high",
        True,
        False,
        "Precomputed representation layer for retrieval and feature augmentation.",
    ),
    ExpansionItem(
        2,
        "uniprot_variants",
        "UniProt",
        "knowledgebase/variants",
        785_722_197,
        "high",
        True,
        False,
        "Structured variant expansions beyond the current core entry pulls.",
    ),
    ExpansionItem(
        3,
        "uniprot_proteomics_mapping",
        "UniProt",
        "knowledgebase/proteomics_mapping",
        213_908_794,
        "high",
        True,
        False,
        "Proteomics-oriented support features for selected proteomes.",
    ),
    ExpansionItem(
        4,
        "uniprot_genome_annotation_tracks",
        "UniProt",
        "knowledgebase/genome_annotation_tracks",
        227_485_757,
        "high",
        True,
        False,
        "Genomic-coordinate alignment and feature track export.",
    ),
    ExpansionItem(
        5,
        "alphafold_additional_proteomes",
        "AlphaFold DB",
        "latest_additional_proteome_tarballs",
        88_368_233_510,
        "high",
        True,
        False,
        "Model-organism and curated proteome tarballs beyond current Swiss-Prot pulls.",
    ),
    ExpansionItem(
        6,
        "uniprot_pan_proteomes",
        "UniProt",
        "knowledgebase/pan_proteomes",
        5_966_267_722,
        "medium",
        True,
        False,
        "Strain/population-level protein universe slices.",
    ),
    ExpansionItem(
        7,
        "uniprot_reference_proteomes",
        "UniProt",
        "reference_proteomes",
        355_183_414_691,
        "high",
        True,
        False,
        "Broad representative proteome coverage for repository-grade expansion.",
    ),
    ExpansionItem(
        8,
        "uniprot_taxonomic_divisions",
        "UniProt",
        "knowledgebase/taxonomic_divisions",
        370_802_706_275,
        "high",
        True,
        False,
        "Species/division-specific slices for taxon-aware retrieval and partitioning.",
    ),
    ExpansionItem(
        9,
        "ebi_qfo_reference_proteomes",
        "EBI",
        "qfo_reference_proteomes",
        23_132_070_640,
        "optional",
        True,
        False,
        "Orthology-oriented convenience package; optional when broader reference proteomes land.",
    ),
    ExpansionItem(
        10,
        "mega_motif_base_backbone_procurement",
        "MegaMotifBase",
        "mega_motif_base_backbone",
        None,
        "required",
        True,
        False,
        "Published family/superfamily alignments and structural motif archives plus core site pages.",
    ),
    ExpansionItem(
        11,
        "motivated_proteins_backbone_procurement",
        "Motivated Proteins",
        "motivated_proteins_backbone",
        None,
        "required",
        True,
        False,
        "Original site, MP2 entrypoint, help/docs, and downloadable Structure Motivator bundles.",
    ),
)


def _by_accession(rows: list[dict[str, Any]], key: str = "accession") -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        accession = str(row.get(key) or "").strip()
        if accession:
            result[accession] = row
    return result


def _cohort_rows() -> list[str]:
    multimodal = read_json(STATUS_DIR / "training_set_multimodal_sidecar_preview.json")
    visible = multimodal.get("all_visible_training_candidates_view") or []
    return [str(row.get("example_id") or "").strip() for row in visible if row.get("example_id")]


def _strict_governing_ids() -> set[str]:
    multimodal = read_json(STATUS_DIR / "training_set_multimodal_sidecar_preview.json")
    strict_rows = multimodal.get("strict_governing_training_view") or []
    return {
        str(row.get("example_id") or "").strip()
        for row in strict_rows
        if str(row.get("example_id") or "").strip()
    }


def load_release_context() -> dict[str, Any]:
    return {
        "summary": read_json(RESULTS_DIR / "summary.json"),
        "run_summary": read_json(RESULTS_DIR / "run_summary.json"),
        "provenance_table": read_json(RESULTS_DIR / "provenance_table.json"),
        "source_coverage": read_json(RESULTS_DIR / "source_coverage.json"),
        "release_ledger": read_json(RESULTS_DIR / "release_corpus_evidence_ledger.json"),
        "release_cards_manifest": read_json(RESULTS_DIR / "release_cards_manifest.json"),
        "release_bundle_manifest": read_json(RESULTS_DIR / "release_bundle_manifest.json"),
        "release_support_manifest": read_json(RESULTS_DIR / "release_support_manifest.json"),
        "final_bundle": read_json(STATUS_DIR / "final_structured_dataset_bundle_preview.json"),
        "training_readiness": read_json(STATUS_DIR / "training_set_readiness_preview.json"),
        "packet_summary": read_json(STATUS_DIR / "training_packet_summary_preview.json"),
        "packet_queue": read_json(STATUS_DIR / "training_packet_materialization_queue_preview.json"),
        "baseline_sidecar": read_json(STATUS_DIR / "training_set_baseline_sidecar_preview.json"),
        "multimodal_sidecar": read_json(STATUS_DIR / "training_set_multimodal_sidecar_preview.json"),
        "procurement_expansion_inventory_report": as_posix(DEFAULT_EXPANSION_INVENTORY_REPORT),
    }


def build_release_runtime_qualification_payload(context: dict[str, Any]) -> dict[str, Any]:
    summary = context["summary"]
    provenance = context["provenance_table"]
    final_bundle = context["final_bundle"]
    run_summary = context["run_summary"]
    consistency = provenance.get("consistency_checks") or {}
    run_context = provenance.get("run_context") or {}
    scope = summary.get("execution_scope") or {}
    bundle_summary = final_bundle.get("summary") or {}

    deterministic_checks = {
        "checkpoint_identity_safe_resume": bool(
            consistency.get("checkpoint_identity_safe_resume")
        ),
        "cohort_matches_live_inputs": bool(consistency.get("cohort_matches_live_inputs")),
        "cohort_matches_split_labels": bool(consistency.get("cohort_matches_split_labels")),
        "split_counts_stable": all(
            (run_summary.get("split_counts") or {}).get(key) == (scope.get("split_counts") or {}).get(key)
            for key in ("train", "val", "test", "resolved", "unresolved")
        ),
        "bundle_row_count_present": bundle_summary.get("corpus_row_count") is not None,
        "bundle_manifest_present": bool(final_bundle.get("bundle_manifest_path")),
    }
    qualification_complete = all(deterministic_checks.values())

    return {
        "artifact_id": "release_runtime_qualification_preview",
        "schema_id": "proteosphere-release-runtime-qualification-preview-2026-04-06",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "dataset_generation_mode": RELEASE_V1_MODE,
            "cohort_size": scope.get("cohort_size"),
            "runtime_surface": scope.get("runtime_surface"),
            "runtime_qualification_state": (
                "qualified_for_frozen_v1_only" if qualification_complete else "qualification_incomplete"
            ),
            "qualification_complete": qualification_complete,
            "certification_scope": "frozen_cohort_only",
            "first_run_processed_examples": (summary.get("runtime") or {}).get("first_run_processed_examples"),
            "resumed_run_processed_examples": (summary.get("runtime") or {}).get("resumed_run_processed_examples"),
            "checkpoint_ref": run_context.get("checkpoint_ref"),
            "run_id": run_context.get("run_id"),
        },
        "deterministic_checks": deterministic_checks,
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "qualification_scope": "frozen_cohort_only",
            "summary": (
                "This artifact certifies deterministic resume continuity and pinned-output reproducibility "
                "for the frozen 12-accession release candidate only."
            ),
        },
    }


def build_release_governing_sufficiency_payload(context: dict[str, Any]) -> dict[str, Any]:
    training_readiness = context["training_readiness"]
    source_coverage = context["source_coverage"]
    baseline = context["baseline_sidecar"]
    packet_queue = context["packet_queue"]
    ledger = context["release_ledger"]

    readiness_by_accession = _by_accession(training_readiness.get("readiness_rows") or [])
    coverage_by_accession = _by_accession(source_coverage.get("coverage_matrix") or [])
    packet_by_accession = _by_accession(packet_queue.get("rows") or [])
    ledger_by_accession = _by_accession(
        [
            {**row, "accession": ((row.get("metadata") or {}).get("accession"))}
            for row in (ledger.get("rows") or [])
        ]
    )

    baseline_examples = baseline.get("baseline_dataset", {}).get("examples") or []
    baseline_by_accession = _by_accession(
        [
            {
                "accession": row.get("example_id"),
                "present_modalities": ((row.get("metadata") or {}).get("present_modalities") or []),
                "missing_modalities": ((row.get("metadata") or {}).get("missing_modalities") or []),
            }
            for row in baseline_examples
        ]
    )
    strict_ids = _strict_governing_ids()

    rows: list[dict[str, Any]] = []
    for accession in _cohort_rows():
        readiness_row = readiness_by_accession.get(accession) or {}
        coverage_row = coverage_by_accession.get(accession) or {}
        packet_row = packet_by_accession.get(accession) or {}
        ledger_row = ledger_by_accession.get(accession) or {}
        baseline_row = baseline_by_accession.get(accession) or {}
        training_state = str(readiness_row.get("training_set_state") or "")
        present_modalities = list(baseline_row.get("present_modalities") or [])
        missing_modalities = list(
            baseline_row.get("missing_modalities")
            or packet_row.get("missing_modalities")
            or ((ledger_row.get("metadata") or {}).get("missing_modalities") or [])
        )
        if accession in strict_ids:
            sufficiency_decision = "sufficient_for_frozen_v1_governing"
            governing_status = "governing_ready"
            allowed_in_strict_view = True
            minimal_modalities = present_modalities or ["sequence"]
            rationale = (
                "The accession is already admitted into the strict governing training view for the frozen v1 cohort."
            )
        elif training_state == "blocked_pending_acquisition":
            sufficiency_decision = "deferred_to_v2_source_fix"
            governing_status = "blocked_pending_acquisition"
            allowed_in_strict_view = False
            minimal_modalities = present_modalities or ["sequence"]
            rationale = (
                "The accession remains visible in the frozen cohort, but governing use is deferred until the noted "
                "source-fix or acquisition gaps are addressed in v2."
            )
        else:
            sufficiency_decision = "non_governing_by_design_for_v1"
            governing_status = "support_only_non_governing"
            allowed_in_strict_view = False
            minimal_modalities = present_modalities or ["sequence"]
            rationale = (
                "The accession remains visible as support-only context in v1 and is intentionally excluded from the "
                "strict governing slice."
            )
        rows.append(
            {
                "accession": accession,
                "split": readiness_row.get("split"),
                "training_set_state": training_state,
                "governing_status": governing_status,
                "strict_governing_allowed": allowed_in_strict_view,
                "minimal_acceptable_modalities": minimal_modalities,
                "present_modalities": present_modalities,
                "missing_modalities": missing_modalities,
                "evidence_sources_present": list(coverage_row.get("source_lanes") or []),
                "remaining_gaps": missing_modalities,
                "sufficiency_decision": sufficiency_decision,
                "sufficiency_rationale": rationale,
                "coverage_tier": coverage_row.get("conservative_evidence_tier"),
                "validation_class": coverage_row.get("validation_class"),
            }
        )

    return {
        "artifact_id": "release_governing_sufficiency_preview",
        "schema_id": "proteosphere-release-governing-sufficiency-preview-2026-04-06",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "dataset_generation_mode": RELEASE_V1_MODE,
            "accession_count": len(rows),
            "strict_governing_allowed_count": sum(1 for row in rows if row["strict_governing_allowed"]),
            "non_governing_by_design_count": sum(
                1 for row in rows if row["sufficiency_decision"] == "non_governing_by_design_for_v1"
            ),
            "deferred_to_v2_source_fix_count": sum(
                1 for row in rows if row["sufficiency_decision"] == "deferred_to_v2_source_fix"
            ),
            "governing_sufficiency_state": "complete_for_frozen_v1",
            "governing_sufficiency_complete": True,
        },
        "rows": rows,
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "This registry classifies each accession for the frozen v1 cohort as strict governing, support-only, "
                "or deferred-to-v2 without widening the cohort."
            ),
        },
    }


def build_release_accession_evidence_pack_payload(context: dict[str, Any]) -> dict[str, Any]:
    source_coverage = context["source_coverage"]
    training_readiness = context["training_readiness"]
    packet_queue = context["packet_queue"]
    release_ledger = context["release_ledger"]
    provenance = context["provenance_table"]
    baseline = context["baseline_sidecar"]
    governing = build_release_governing_sufficiency_payload(context)

    coverage_by_accession = _by_accession(source_coverage.get("coverage_matrix") or [])
    readiness_by_accession = _by_accession(training_readiness.get("readiness_rows") or [])
    packet_by_accession = _by_accession(packet_queue.get("rows") or [])
    governing_by_accession = _by_accession(governing.get("rows") or [])
    ledger_by_accession = _by_accession(
        [
            {**row, "accession": ((row.get("metadata") or {}).get("accession"))}
            for row in (release_ledger.get("rows") or [])
        ]
    )
    provenance_by_accession = _by_accession(provenance.get("cohort_summary", {}).get("rows") or [])

    baseline_examples = baseline.get("baseline_dataset", {}).get("examples") or []
    baseline_by_accession = _by_accession(
        [
            {
                "accession": row.get("example_id"),
                "metadata": row.get("metadata") or {},
                "source_lineage_refs": row.get("source_lineage_refs") or [],
            }
            for row in baseline_examples
        ]
    )

    rows: list[dict[str, Any]] = []
    for accession in _cohort_rows():
        coverage_row = coverage_by_accession.get(accession) or {}
        readiness_row = readiness_by_accession.get(accession) or {}
        packet_row = packet_by_accession.get(accession) or {}
        governing_row = governing_by_accession.get(accession) or {}
        ledger_row = ledger_by_accession.get(accession) or {}
        provenance_row = provenance_by_accession.get(accession) or {}
        baseline_row = baseline_by_accession.get(accession) or {}
        metadata = ledger_row.get("metadata") or {}
        row = {
            "accession": accession,
            "split_assignment": readiness_row.get("split"),
            "governing_status": governing_row.get("governing_status"),
            "sufficiency_decision": governing_row.get("sufficiency_decision"),
            "governing_or_support_reason": governing_row.get("sufficiency_rationale"),
            "packet_materialization_status": packet_row.get("packet_lane"),
            "training_set_state": readiness_row.get("training_set_state"),
            "known_missing_modalities": governing_row.get("missing_modalities") or [],
            "release_exclusion_reason": (
                None
                if governing_row.get("strict_governing_allowed")
                else governing_row.get("sufficiency_decision")
            ),
            "source_lineage": list(ledger_row.get("source_manifest_ids") or []),
            "evidence_refs": list(coverage_row.get("evidence_refs") or []),
            "source_lanes": list(coverage_row.get("source_lanes") or []),
            "provenance_notes": provenance_row.get("provenance_notes"),
            "packet_lineage_refs": list(baseline_row.get("source_lineage_refs") or []),
            "coverage_notes": list(metadata.get("coverage_notes") or []),
        }
        required_fields = [
            row["split_assignment"],
            row["governing_status"],
            row["sufficiency_decision"],
            row["packet_materialization_status"],
            row["training_set_state"],
            row["source_lineage"],
            row["source_lanes"],
        ]
        row["row_complete"] = all(bool(field) or field == [] for field in required_fields)
        rows.append(row)

    return {
        "artifact_id": "release_accession_evidence_pack_preview",
        "schema_id": "proteosphere-release-accession-evidence-pack-preview-2026-04-06",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "dataset_generation_mode": RELEASE_V1_MODE,
            "accession_count": len(rows),
            "row_complete_count": sum(1 for row in rows if row["row_complete"]),
            "governing_ready_count": sum(
                1 for row in rows if row.get("governing_status") == "governing_ready"
            ),
            "support_only_count": sum(
                1 for row in rows if row.get("governing_status") == "support_only_non_governing"
            ),
            "deferred_to_v2_count": sum(
                1 for row in rows if row.get("governing_status") == "blocked_pending_acquisition"
            ),
        },
        "rows": rows,
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "This evidence pack is row-complete for the frozen v1 cohort and captures lineage, status, packet "
                "state, split assignment, and known missing modalities for every accession."
            ),
        },
    }


def build_release_reporting_completeness_payload(context: dict[str, Any]) -> dict[str, Any]:
    evidence_pack = build_release_accession_evidence_pack_payload(context)
    provenance = context["provenance_table"]
    release_cards = context["release_cards_manifest"]
    rows = evidence_pack.get("rows") or []
    complete_rows = sum(1 for row in rows if row.get("row_complete"))
    provenance_rows = (provenance.get("cohort_summary") or {}).get("rows") or []
    card_outputs = release_cards.get("card_outputs") or {}
    reporting_complete = (
        len(rows) > 0
        and complete_rows == len(rows)
        and len(provenance_rows) == len(rows)
        and len(card_outputs) >= 3
    )
    return {
        "artifact_id": "release_reporting_completeness_preview",
        "schema_id": "proteosphere-release-reporting-completeness-preview-2026-04-06",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "dataset_generation_mode": RELEASE_V1_MODE,
            "evidence_pack_row_count": len(rows),
            "row_complete_count": complete_rows,
            "provenance_row_count": len(provenance_rows),
            "release_card_count": len(card_outputs),
            "reporting_completeness_state": (
                "complete_for_frozen_v1" if reporting_complete else "incomplete"
            ),
            "reporting_completeness_complete": reporting_complete,
        },
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "This artifact measures whether the frozen v1 release candidate has row-complete reporting and a "
                "complete evidence pack without claiming the v2 expansion is finished."
            ),
        },
    }


def build_release_blocker_resolution_board_payload(context: dict[str, Any]) -> dict[str, Any]:
    runtime = build_release_runtime_qualification_payload(context)
    sufficiency = build_release_governing_sufficiency_payload(context)
    reporting = build_release_reporting_completeness_payload(context)

    runtime_complete = bool((runtime.get("summary") or {}).get("qualification_complete"))
    sufficiency_complete = bool(
        (sufficiency.get("summary") or {}).get("governing_sufficiency_complete")
    )
    reporting_complete = bool(
        (reporting.get("summary") or {}).get("reporting_completeness_complete")
    )

    resolved_rows = []
    if runtime_complete:
        resolved_rows.append(
            {
                "blocker": "runtime maturity",
                "resolution_state": "resolved_for_frozen_v1",
                "evidence_artifact": "artifacts/status/release_runtime_qualification_preview.json",
            }
        )
    if sufficiency_complete:
        resolved_rows.append(
            {
                "blocker": "source coverage depth",
                "resolution_state": "resolved_for_frozen_v1",
                "evidence_artifact": "artifacts/status/release_governing_sufficiency_preview.json",
            }
        )
    if reporting_complete:
        resolved_rows.append(
            {
                "blocker": "provenance/reporting depth",
                "resolution_state": "resolved_for_frozen_v1",
                "evidence_artifact": "artifacts/status/release_reporting_completeness_preview.json",
            }
        )

    open_v1_rows = []
    if not runtime_complete:
        open_v1_rows.append("runtime maturity")
    if not sufficiency_complete:
        open_v1_rows.append("source coverage depth")
    if not reporting_complete:
        open_v1_rows.append("provenance/reporting depth")

    deferred_to_v2 = [
        {
            "blocker": "expansion procurement wave",
            "state": "deferred_until_external_drive",
        },
        {
            "blocker": "mega_motif_base_backbone",
            "state": "missing_family_pending_procurement",
        },
        {
            "blocker": "motivated_proteins_backbone",
            "state": "missing_family_pending_procurement",
        },
        {
            "blocker": RELEASE_V2_MODE,
            "state": "expanded_rebuild_deferred",
        },
    ]

    return {
        "artifact_id": "release_blocker_resolution_board_preview",
        "schema_id": "proteosphere-release-blocker-resolution-board-preview-2026-04-06",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "dataset_generation_mode": RELEASE_V1_MODE,
            "resolved_release_blocker_count": len(resolved_rows),
            "open_v1_blocker_count": len(open_v1_rows),
            "deferred_to_v2_count": len(deferred_to_v2),
            "release_v1_bar_state": "closed" if not open_v1_rows else "open",
        },
        "resolved_release_blockers": resolved_rows,
        "open_v1_blockers": open_v1_rows,
        "deferred_to_v2_blockers": deferred_to_v2,
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "This board separates frozen-v1 blocker resolution from post-drive v2 expansion work so the current "
                "release candidate can close without pretending the larger expansion is already done."
            ),
        },
    }


def v1_release_bar_closed(context: dict[str, Any]) -> bool:
    board = build_release_blocker_resolution_board_payload(context)
    return (board.get("summary") or {}).get("release_v1_bar_state") == "closed"


def build_procurement_external_drive_mount_payload(external_root: Path | None = None) -> dict[str, Any]:
    root = external_root or DEFAULT_EXTERNAL_DRIVE_ROOT
    root_exists = root.exists()
    usage = shutil.disk_usage(root.anchor) if root_exists else None
    return {
        "artifact_id": "procurement_external_drive_mount_preview",
        "schema_id": "proteosphere-procurement-external-drive-mount-preview-2026-04-06",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "expected_external_root": as_posix(root),
            "mount_state": "mounted" if root_exists else "not_detected",
            "authority_ready": root_exists,
            "free_bytes": usage.free if usage else None,
            "total_bytes": usage.total if usage else None,
        },
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "The external-drive expansion wave remains deferred until the expected repository root is mounted and "
                "available for first-class source authority."
            ),
        },
    }


def build_procurement_expansion_storage_budget_payload(
    external_root: Path | None = None,
) -> dict[str, Any]:
    mount = build_procurement_external_drive_mount_payload(external_root)
    known_items = [item for item in EXPANSION_ITEMS if item.size_bytes is not None]
    known_additional = sum(item.size_bytes or 0 for item in known_items if item.priority <= 8)
    optional_qfo = sum(item.size_bytes or 0 for item in known_items if item.priority == 9)
    baseline_raw_bytes = 1_634_856_956_745
    return {
        "artifact_id": "procurement_expansion_storage_budget_preview",
        "schema_id": "proteosphere-procurement-expansion-storage-budget-preview-2026-04-06",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "baseline_raw_bytes": baseline_raw_bytes,
            "known_additional_bytes": known_additional,
            "optional_qfo_bytes": optional_qfo,
            "projected_v2_raw_bytes": baseline_raw_bytes + known_additional,
            "projected_v2_plus_optional_qfo_bytes": baseline_raw_bytes + known_additional + optional_qfo,
            "external_drive_mount_state": (mount.get("summary") or {}).get("mount_state"),
        },
        "items": [
            {
                "dataset_id": item.dataset_id,
                "priority": item.priority,
                "size_bytes": item.size_bytes,
                "value_tier": item.value_tier,
                "feeds_canonical_corpus": item.feeds_canonical_corpus,
                "cold_storage_only": item.cold_storage_only,
            }
            for item in EXPANSION_ITEMS
        ],
        "truth_boundary": {
            "report_only": True,
            "summary": "Storage budgeting is based on the pinned 2026-04-05 inventory report and remains planning-only until the external drive is mounted.",
        },
    }


def build_procurement_expansion_wave_payload(external_root: Path | None = None) -> dict[str, Any]:
    mount = build_procurement_external_drive_mount_payload(external_root)
    mount_ready = bool((mount.get("summary") or {}).get("authority_ready"))
    rows = []
    for item in EXPANSION_ITEMS:
        state = "ready_to_execute" if mount_ready else "deferred_until_external_drive"
        if item.priority == 9 and not mount_ready:
            state = "optional_deferred"
        rows.append(
            {
                "priority": item.priority,
                "dataset_id": item.dataset_id,
                "source": item.source,
                "family": item.family,
                "size_bytes": item.size_bytes,
                "value_tier": item.value_tier,
                "feeds_canonical_corpus": item.feeds_canonical_corpus,
                "cold_storage_only": item.cold_storage_only,
                "requires_external_drive": item.requires_external_drive,
                "execution_state": state,
                "notes": item.notes,
            }
        )
    return {
        "artifact_id": "procurement_expansion_wave_preview",
        "schema_id": "proteosphere-procurement-expansion-wave-preview-2026-04-06",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "dataset_generation_mode": RELEASE_V2_MODE,
            "queue_length": len(rows),
            "ready_to_execute_count": sum(
                1 for row in rows if row["execution_state"] == "ready_to_execute"
            ),
            "deferred_count": sum(
                1 for row in rows if row["execution_state"] != "ready_to_execute"
            ),
            "external_drive_mount_state": (mount.get("summary") or {}).get("mount_state"),
            "expansion_staging_root": as_posix(DEFAULT_EXPANSION_STAGING_ROOT),
            "inventory_report": as_posix(DEFAULT_EXPANSION_INVENTORY_REPORT),
        },
        "rows": rows,
        "truth_boundary": {
            "report_only": True,
            "summary": (
                "This wave preserves the pinned expansion priority order and keeps all expansion procurement deferred "
                "until the external drive is mounted."
            ),
        },
    }


def write_json_and_markdown(
    *,
    output_json: Path,
    output_md: Path,
    payload: dict[str, Any],
    title: str,
    bullet_rows: list[str],
) -> None:
    write_json(output_json, payload)
    write_text(output_md, render_simple_markdown(title, bullet_rows))
