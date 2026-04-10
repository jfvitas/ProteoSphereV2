from __future__ import annotations

# ruff: noqa

from pathlib import Path
from typing import Any

try:
    from scripts.final_structured_dataset_support import (
        DEFAULT_CANONICAL_LATEST,
        DEFAULT_FUTURE_STRUCTURE_TRIAGE,
        DEFAULT_INTERACTION_CONTEXT,
        DEFAULT_INTERACTION_PARTNER_CONTEXT,
        DEFAULT_KINETICS_SUPPORT,
        DEFAULT_MOTIF_CONTEXT,
        DEFAULT_OUTPUT_ROOT,
        DEFAULT_PACKAGE_LATEST,
        DEFAULT_PACKET_QUEUE,
        DEFAULT_PAGE_SUPPORT,
        DEFAULT_STRING_MATERIALIZATION,
        DEFAULT_STRUCTURE_CONTEXT,
        DEFAULT_TRAINING_READINESS,
        build_baseline_sidecar_preview as _build_baseline_sidecar_preview,
        build_multimodal_sidecar_preview as _build_multimodal_sidecar_preview,
        build_seed_plus_neighbors_structured_corpus as _build_seed_plus_neighbors_structured_corpus,
        read_json,
        write_json,
        write_text,
    )
    from scripts.run_post_tail_unlock import (
        DEFAULT_DOWNLOAD_LOCATION_AUDIT,
        DEFAULT_PROCUREMENT_SOURCE_COMPLETION,
        DEFAULT_PROCUREMENT_STATUS_BOARD,
        DEFAULT_STALE_PART_AUDIT,
        build_post_tail_unlock_dry_run_preview as _build_post_tail_unlock_dry_run_preview,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from final_structured_dataset_support import (  # type: ignore[no-redef]
        DEFAULT_CANONICAL_LATEST,
        DEFAULT_FUTURE_STRUCTURE_TRIAGE,
        DEFAULT_INTERACTION_CONTEXT,
        DEFAULT_INTERACTION_PARTNER_CONTEXT,
        DEFAULT_KINETICS_SUPPORT,
        DEFAULT_MOTIF_CONTEXT,
        DEFAULT_OUTPUT_ROOT,
        DEFAULT_PACKAGE_LATEST,
        DEFAULT_PACKET_QUEUE,
        DEFAULT_PAGE_SUPPORT,
        DEFAULT_STRING_MATERIALIZATION,
        DEFAULT_STRUCTURE_CONTEXT,
        DEFAULT_TRAINING_READINESS,
        build_baseline_sidecar_preview as _build_baseline_sidecar_preview,
        build_multimodal_sidecar_preview as _build_multimodal_sidecar_preview,
        build_seed_plus_neighbors_structured_corpus as _build_seed_plus_neighbors_structured_corpus,
        read_json,
        write_json,
        write_text,
    )
    from run_post_tail_unlock import (  # type: ignore[no-redef]
        DEFAULT_DOWNLOAD_LOCATION_AUDIT,
        DEFAULT_PROCUREMENT_SOURCE_COMPLETION,
        DEFAULT_PROCUREMENT_STATUS_BOARD,
        DEFAULT_STALE_PART_AUDIT,
        build_post_tail_unlock_dry_run_preview as _build_post_tail_unlock_dry_run_preview,
    )


def build_seed_plus_neighbors_structured_corpus_preview(
    *,
    package_latest_path: Path = DEFAULT_PACKAGE_LATEST,
    packet_queue_path: Path = DEFAULT_PACKET_QUEUE,
    training_readiness_path: Path = DEFAULT_TRAINING_READINESS,
    canonical_latest_path: Path = DEFAULT_CANONICAL_LATEST,
    interaction_context_path: Path = DEFAULT_INTERACTION_CONTEXT,
    interaction_partner_context_path: Path = DEFAULT_INTERACTION_PARTNER_CONTEXT,
    string_materialization_path: Path = DEFAULT_STRING_MATERIALIZATION,
    motif_context_path: Path = DEFAULT_MOTIF_CONTEXT,
    structure_context_path: Path = DEFAULT_STRUCTURE_CONTEXT,
    future_structure_triage_path: Path = DEFAULT_FUTURE_STRUCTURE_TRIAGE,
    kinetics_support_path: Path = DEFAULT_KINETICS_SUPPORT,
    page_support_path: Path = DEFAULT_PAGE_SUPPORT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    return _build_seed_plus_neighbors_structured_corpus(
        package_latest=read_json(package_latest_path),
        packet_queue=read_json(packet_queue_path),
        training_readiness=read_json(training_readiness_path),
        canonical_latest=read_json(canonical_latest_path),
        interaction_context=read_json(interaction_context_path),
        interaction_partner_context=read_json(interaction_partner_context_path),
        string_materialization=read_json(string_materialization_path),
        motif_context=read_json(motif_context_path),
        structure_context=read_json(structure_context_path),
        future_structure_triage=read_json(future_structure_triage_path),
        kinetics_support=read_json(kinetics_support_path),
        page_support=read_json(page_support_path),
        output_root=output_root,
    )


def build_seed_plus_neighbors_baseline_sidecar_preview(
    *,
    corpus_preview: dict[str, Any] | None = None,
    package_latest_path: Path = DEFAULT_PACKAGE_LATEST,
    packet_queue_path: Path = DEFAULT_PACKET_QUEUE,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    corpus_preview = corpus_preview or build_seed_plus_neighbors_structured_corpus_preview(
        package_latest_path=package_latest_path,
        packet_queue_path=packet_queue_path,
        output_root=output_root,
    )
    return _build_baseline_sidecar_preview(
        corpus_preview=corpus_preview,
        package_latest=read_json(package_latest_path),
        packet_queue=read_json(packet_queue_path),
        output_root=output_root,
    )


def build_seed_plus_neighbors_multimodal_sidecar_preview(
    *,
    corpus_preview: dict[str, Any] | None = None,
    package_latest_path: Path = DEFAULT_PACKAGE_LATEST,
    packet_queue_path: Path = DEFAULT_PACKET_QUEUE,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    corpus_preview = corpus_preview or build_seed_plus_neighbors_structured_corpus_preview(
        package_latest_path=package_latest_path,
        packet_queue_path=packet_queue_path,
        output_root=output_root,
    )
    return _build_multimodal_sidecar_preview(
        corpus_preview=corpus_preview,
        package_latest=read_json(package_latest_path),
        packet_queue=read_json(packet_queue_path),
        output_root=output_root,
    )


def build_seed_plus_neighbors_entity_resolution_preview(
    *,
    corpus_preview: dict[str, Any] | None = None,
    package_latest_path: Path = DEFAULT_PACKAGE_LATEST,
    packet_queue_path: Path = DEFAULT_PACKET_QUEUE,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    corpus_preview = corpus_preview or build_seed_plus_neighbors_structured_corpus_preview(
        package_latest_path=package_latest_path,
        packet_queue_path=packet_queue_path,
        output_root=output_root,
    )
    rows = []
    for row in corpus_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        governing_status = str(row.get("governing_status") or "").strip()
        join_status = str(row.get("join_status") or "").strip()
        if join_status == "joined" and governing_status not in {
            "candidate_only_non_governing",
            "blocked_pending_acquisition",
            "tail_blocked",
        }:
            continue
        rows.append(
            {
                "row_id": row.get("row_id"),
                "entity_kind": row.get("entity_kind"),
                "canonical_id": row.get("canonical_id"),
                "governing_status": governing_status or "unknown",
                "join_status": join_status or "unknown",
                "relationship_context": row.get("relationship_context"),
                "seed_accessions": list(row.get("seed_accessions") or []),
                "source_provenance_pointers": list(row.get("source_provenance_pointers") or []),
                "unresolved": join_status != "joined",
                "conflicting": governing_status == "tail_blocked",
            }
        )
    return {
        "artifact_id": "seed_plus_neighbors_entity_resolution_preview",
        "schema_id": "proteosphere-seed-plus-neighbors-entity-resolution-preview-2026-04-05",
        "status": "report_only",
        "generated_at": corpus_preview.get("generated_at"),
        "summary": {
            "row_count": len(rows),
            "unresolved_count": sum(1 for row in rows if row["unresolved"]),
            "conflicting_count": sum(1 for row in rows if row["conflicting"]),
        },
        "rows": rows,
        "truth_boundary": {
            "summary": "Entity resolution remains report-only and preserves unresolved and conflicting joins.",
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_post_tail_unlock_dry_run_preview(
    *,
    download_location_audit_path: Path = DEFAULT_DOWNLOAD_LOCATION_AUDIT,
    procurement_status_board_path: Path = DEFAULT_PROCUREMENT_STATUS_BOARD,
    stale_part_audit_path: Path = DEFAULT_STALE_PART_AUDIT,
    procurement_source_completion_path: Path = DEFAULT_PROCUREMENT_SOURCE_COMPLETION,
) -> dict[str, Any]:
    return _build_post_tail_unlock_dry_run_preview(
        read_json(download_location_audit_path),
        read_json(procurement_status_board_path),
        read_json(stale_part_audit_path),
        read_json(procurement_source_completion_path),
    )


__all__ = [
    "build_post_tail_unlock_dry_run_preview",
    "build_seed_plus_neighbors_entity_resolution_preview",
    "build_seed_plus_neighbors_baseline_sidecar_preview",
    "build_seed_plus_neighbors_multimodal_sidecar_preview",
    "build_seed_plus_neighbors_structured_corpus_preview",
    "read_json",
    "write_json",
    "write_text",
]
