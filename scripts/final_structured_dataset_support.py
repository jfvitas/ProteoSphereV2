from __future__ import annotations

# ruff: noqa

import gzip
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from scripts.pre_tail_dataset_support import (
        build_seed_plus_neighbors_structured_corpus_preview,
        build_training_set_baseline_sidecar_preview,
        build_training_set_multimodal_sidecar_preview,
    )
    from scripts.web_enrichment_preview_support import (
        read_json,
        render_markdown_summary,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from pre_tail_dataset_support import (  # type: ignore[no-redef]
        build_seed_plus_neighbors_structured_corpus_preview,
        build_training_set_baseline_sidecar_preview,
        build_training_set_multimodal_sidecar_preview,
    )
    from web_enrichment_preview_support import (  # type: ignore[no-redef]
        read_json,
        render_markdown_summary,
        write_json,
        write_text,
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "status"
DEFAULT_DOWNLOAD_LOCATION_AUDIT = (
    REPO_ROOT / "artifacts" / "status" / "download_location_audit_preview.json"
)
DEFAULT_PACKAGE_LATEST = REPO_ROOT / "data" / "packages" / "LATEST.json"
DEFAULT_CANONICAL_LATEST = REPO_ROOT / "data" / "canonical" / "LATEST.json"
DEFAULT_INTERACTION_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "interaction_context_preview.json"
)
DEFAULT_INTERACTION_PARTNER_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "interaction_partner_context_preview.json"
)
DEFAULT_STRING_MATERIALIZATION = (
    REPO_ROOT / "artifacts" / "status" / "string_interaction_materialization_preview.json"
)
DEFAULT_MOTIF_CONTEXT = REPO_ROOT / "artifacts" / "status" / "motif_domain_site_context_preview.json"
DEFAULT_STRUCTURE_CONTEXT = REPO_ROOT / "artifacts" / "status" / "structure_entry_context_preview.json"
DEFAULT_FUTURE_STRUCTURE_TRIAGE = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_triage_preview.json"
)
DEFAULT_KINETICS_SUPPORT = REPO_ROOT / "artifacts" / "status" / "sabio_rk_support_preview.json"
DEFAULT_PAGE_SUPPORT = REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_registry_preview.json"
DEFAULT_PACKET_QUEUE = (
    REPO_ROOT / "artifacts" / "status" / "training_packet_materialization_queue_preview.json"
)
DEFAULT_TRAINING_READINESS = REPO_ROOT / "artifacts" / "status" / "training_set_readiness_preview.json"
DEFAULT_BINDINGDB_ACCESSION_ASSAY_PROFILE = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_accession_assay_profile_preview.json"
)
DEFAULT_BINDINGDB_MEASUREMENT_SUBSET = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_measurement_subset_preview.json"
)
DEFAULT_STRUCTURE_ENTRY_CONTEXT = DEFAULT_STRUCTURE_CONTEXT
DEFAULT_INTERACTION_SIMILARITY_SIGNATURE = (
    REPO_ROOT / "artifacts" / "status" / "interaction_similarity_signature_preview.json"
)
DEFAULT_MATERIALIZATION_SUMMARY = (
    REPO_ROOT
    / "data"
    / "packages"
    / "selected-cohort-strict-20260323T1648Z"
    / "materialization_summary.json"
)
DEFAULT_CANONICAL_STORE = (
    REPO_ROOT
    / "data"
    / "canonical"
    / "runs"
    / "raw-canonical-20260330T221513Z"
    / "canonical_store.json"
)


def _ensure_preview_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_current_preview(path: Path) -> dict[str, Any]:
    return _ensure_preview_dict(read_json(path))


def resolve_materialization_summary_path(package_latest_path: Path = DEFAULT_PACKAGE_LATEST) -> Path:
    latest_payload = _ensure_preview_dict(read_json(package_latest_path))
    output_root = latest_payload.get("output_root")
    if isinstance(output_root, str) and output_root.strip():
        candidate = REPO_ROOT / output_root / "materialization_summary.json"
        if candidate.exists():
            return candidate
    run_id = latest_payload.get("run_id")
    if isinstance(run_id, str) and run_id.strip():
        candidate = REPO_ROOT / "data" / "packages" / run_id / "materialization_summary.json"
        if candidate.exists():
            return candidate
    return DEFAULT_MATERIALIZATION_SUMMARY


def resolve_canonical_store_path(canonical_latest_path: Path = DEFAULT_CANONICAL_LATEST) -> Path:
    latest_payload = _ensure_preview_dict(read_json(canonical_latest_path))
    run_id = latest_payload.get("run_id")
    if isinstance(run_id, str) and run_id.strip():
        candidate = REPO_ROOT / "data" / "canonical" / "runs" / run_id / "canonical_store.json"
        if candidate.exists():
            return candidate
    return DEFAULT_CANONICAL_STORE


def _seed_packets(package_latest: dict[str, Any]) -> list[dict[str, Any]]:
    packets = package_latest.get("packets")
    return packets if isinstance(packets, list) else []


def _seed_accessions(package_latest: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for packet in _seed_packets(package_latest):
        accession = packet.get("accession")
        if isinstance(accession, str) and accession:
            rows.append(accession.strip())
    return sorted(set(rows))


def _download_row_by_filename(download_location_audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = download_location_audit.get("rows")
    index: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return index
    for row in rows:
        if not isinstance(row, dict):
            continue
        filename = row.get("filename")
        if isinstance(filename, str) and filename:
            index[filename] = row
    return index


def _resolved_file_path(download_location_audit: dict[str, Any], filename: str) -> Path | None:
    row = _download_row_by_filename(download_location_audit).get(filename) or {}
    raw_path = row.get("resolved_path") or row.get("path")
    if isinstance(raw_path, str) and raw_path:
        candidate = Path(raw_path)
        if candidate.exists():
            return candidate
    fallback = REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"
    matches = list(fallback.rglob(filename))
    return matches[0] if matches else None


def build_seed_plus_neighbors_structured_corpus(
    *,
    package_latest: dict[str, Any],
    packet_queue: dict[str, Any],
    training_readiness: dict[str, Any],
    canonical_latest: dict[str, Any],
    interaction_context: dict[str, Any],
    interaction_partner_context: dict[str, Any],
    string_materialization: dict[str, Any],
    motif_context: dict[str, Any],
    structure_context: dict[str, Any],
    future_structure_triage: dict[str, Any],
    kinetics_support: dict[str, Any],
    page_support: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    del package_latest, canonical_latest, output_root
    payload = build_seed_plus_neighbors_structured_corpus_preview(
        training_set_readiness_preview=training_readiness,
        training_packet_completeness_matrix_preview=_read_current_preview(
            REPO_ROOT / "artifacts" / "status" / "training_packet_completeness_matrix_preview.json"
        ),
        training_packet_materialization_queue_preview=packet_queue,
        bindingdb_accession_assay_profile_preview=_read_current_preview(
            DEFAULT_BINDINGDB_ACCESSION_ASSAY_PROFILE
        ),
        bindingdb_measurement_subset_preview=_read_current_preview(
            DEFAULT_BINDINGDB_MEASUREMENT_SUBSET
        ),
        structure_entry_context_preview=structure_context or _read_current_preview(
            DEFAULT_STRUCTURE_ENTRY_CONTEXT
        ),
        interaction_similarity_signature_preview=interaction_context
        or _read_current_preview(DEFAULT_INTERACTION_SIMILARITY_SIGNATURE),
        interaction_partner_context_preview=interaction_partner_context,
        motif_domain_site_context_preview=motif_context,
        sabio_rk_support_preview=kinetics_support,
        targeted_page_scrape_registry_preview=page_support,
    )
    string_rows = [
        row
        for row in (string_materialization.get("rows") or [])
        if isinstance(row, dict)
    ]
    if not string_rows:
        return payload

    rows = [
        row
        for row in (payload.get("rows") or [])
        if not (
            isinstance(row, dict)
            and row.get("row_family") == "interaction"
            and row.get("inclusion_rationale")
            == "executed interaction similarity signature for seed accession"
        )
    ]
    for row in string_rows:
        governing_status = str(row.get("governing_status") or "support_only_non_governing")
        training_admissibility = governing_status
        if row.get("training_admissibility") == "candidate_only":
            training_admissibility = "candidate_only_non_governing"
        elif row.get("training_admissibility") == "visible_but_non_governing":
            training_admissibility = "support_only_non_governing"
        rows.append(
            {
                "row_id": row.get("row_id"),
                "seed_accession": row.get("seed_accession"),
                "canonical_ids": list(
                    {
                        f"protein:{row.get('seed_accession')}",
                        f"protein:{row.get('partner_accession')}",
                    }
                ),
                "row_family": "interaction",
                "governing_status": governing_status,
                "training_admissibility": training_admissibility,
                "join_status": (
                    "candidate"
                    if governing_status == "candidate_only_non_governing"
                    else "joined"
                ),
                "relationship_context": row.get("relationship_context"),
                "source_provenance_refs": [
                    f"{entry.get('source_name')}:{entry.get('filename')}"
                    for entry in (row.get("provenance") or [])
                    if isinstance(entry, dict)
                ],
                "modality_payload_refs": list((row.get("payload_refs") or {}).values()),
                "inclusion_rationale": row.get("inclusion_rationale"),
                "exclusion_or_hold_reasons": row.get("hold_reasons") or [],
                "payload": {
                    "partner_accession": row.get("partner_accession"),
                    "partner_ref": row.get("partner_ref"),
                    "partner_label": row.get("partner_label"),
                    **(row.get("metrics") or {}),
                },
            }
        )

    rows.sort(
        key=lambda row: (
            row.get("row_family") or "",
            row.get("seed_accession") or "",
            row.get("row_id") or "",
        )
    )
    family_counts = Counter(str(row.get("row_family") or "unknown") for row in rows)
    status_counts = Counter(str(row.get("governing_status") or "unknown") for row in rows)
    admissibility_counts = Counter(
        str(row.get("training_admissibility") or "unknown") for row in rows
    )
    unresolved_rows = [
        row
        for row in rows
        if str(row.get("join_status") or "").strip()
        in {"partial", "deferred", "unjoined", "conflict", "ambiguous"}
    ]
    conflicted_rows = [
        row
        for row in rows
        if str(row.get("join_status") or "").strip() in {"conflict", "ambiguous"}
    ]
    strict_governing_training_view = [
        {
            "row_id": row.get("row_id"),
            "seed_accession": row.get("seed_accession"),
            "canonical_ids": row.get("canonical_ids", []),
            "row_family": row.get("row_family"),
            "governing_status": row.get("governing_status"),
            "training_admissibility": row.get("training_admissibility"),
            "join_status": row.get("join_status"),
            "relationship_context": row.get("relationship_context"),
            "inclusion_rationale": row.get("inclusion_rationale"),
            "exclusion_or_hold_reasons": row.get("exclusion_or_hold_reasons", []),
        }
        for row in rows
        if row.get("governing_status") == "governing_ready"
    ]
    all_visible_training_candidates_view = [
        {
            "row_id": row.get("row_id"),
            "seed_accession": row.get("seed_accession"),
            "canonical_ids": row.get("canonical_ids", []),
            "row_family": row.get("row_family"),
            "governing_status": row.get("governing_status"),
            "training_admissibility": row.get("training_admissibility"),
            "join_status": row.get("join_status"),
            "relationship_context": row.get("relationship_context"),
            "inclusion_rationale": row.get("inclusion_rationale"),
            "exclusion_or_hold_reasons": row.get("exclusion_or_hold_reasons", []),
        }
        for row in rows
    ]
    payload["rows"] = rows
    payload["summary"] = {
        **(payload.get("summary") or {}),
        "row_count": len(rows),
        "row_family_counts": dict(family_counts),
        "governing_status_counts": dict(status_counts),
        "training_admissibility_counts": dict(admissibility_counts),
        "strict_governing_training_view_count": len(strict_governing_training_view),
        "all_visible_training_candidates_view_count": len(all_visible_training_candidates_view),
        "resolved_entity_count": sum(
            1 for row in rows if row.get("join_status") in {"joined", "candidate"}
        ),
        "unresolved_entity_count": len(unresolved_rows),
        "conflicted_entity_count": len(conflicted_rows),
    }
    payload["raw_scrape_registries"] = {
        **(payload.get("raw_scrape_registries") or {}),
        "interaction": {
            "row_count": int(string_materialization.get("summary", {}).get("normalized_row_count") or len(string_rows)),
            "candidate_only_count": int(
                string_materialization.get("summary", {}).get("candidate_only_row_count") or 0
            ),
        },
    }
    payload["training_views"] = {
        "strict_governing_training_view": strict_governing_training_view,
        "all_visible_training_candidates_view": all_visible_training_candidates_view,
    }
    return payload


def build_baseline_sidecar_preview(
    *,
    corpus_preview: dict[str, Any],
    package_latest: dict[str, Any],
    packet_queue: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    del package_latest, output_root
    return build_training_set_baseline_sidecar_preview(
        seed_plus_neighbors_structured_corpus_preview=corpus_preview,
        materialization_summary_preview=_read_current_preview(resolve_materialization_summary_path()),
        training_set_readiness_preview=_read_current_preview(DEFAULT_TRAINING_READINESS),
    )


def build_multimodal_sidecar_preview(
    *,
    corpus_preview: dict[str, Any],
    package_latest: dict[str, Any],
    packet_queue: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    del package_latest, packet_queue, output_root
    return build_training_set_multimodal_sidecar_preview(
        seed_plus_neighbors_structured_corpus_preview=corpus_preview,
        materialization_summary_preview=_read_current_preview(resolve_materialization_summary_path()),
        canonical_store_preview=_read_current_preview(resolve_canonical_store_path()),
    )


def build_string_interaction_materialization(
    *,
    download_location_audit: dict[str, Any],
    procurement_source_completion: dict[str, Any],
    package_latest: dict[str, Any],
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    raw_registry_path = output_root / "sidecars" / "raw_registries" / "string_interaction_raw_registry.json"
    normalized_rows_path = (
        output_root / "sidecars" / "normalized_support_rows" / "string_interaction_rows.json"
    )
    seed_accessions = _seed_accessions(package_latest)
    if not bool(procurement_source_completion.get("string_completion_ready")):
        return {
            "artifact_id": "string_interaction_materialization_preview",
            "schema_id": "proteosphere-string-interaction-materialization-preview-2026-04-05",
            "status": "report_only",
            "summary": {
                "materialization_state": "blocked_pending_string_completion_gate",
                "seed_accession_count": len(seed_accessions),
                "raw_edge_count": 0,
                "normalized_row_count": 0,
            },
            "rows": [],
            "truth_boundary": {
                "summary": "STRING remains report-only and non-governing until the STRING source gate is complete.",
                "report_only": True,
                "non_governing": True,
            },
        }

    partner_preview = _read_current_preview(DEFAULT_INTERACTION_PARTNER_CONTEXT)
    interaction_preview = _read_current_preview(DEFAULT_INTERACTION_CONTEXT)
    interaction_rows = {
        row.get("accession"): row
        for row in (interaction_preview.get("rows") or [])
        if isinstance(row, dict) and isinstance(row.get("accession"), str)
    }
    raw_rows: list[dict[str, Any]] = []
    normalized_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in partner_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        seed_accession = row.get("accession")
        if not isinstance(seed_accession, str) or seed_accession not in seed_accessions:
            continue
        support_row = interaction_rows.get(seed_accession, {})
        top_partners = row.get("top_partners") or []
        for index, partner in enumerate(top_partners):
            if not isinstance(partner, dict):
                continue
            partner_ref = partner.get("partner_ref")
            if not isinstance(partner_ref, str) or not partner_ref:
                continue
            partner_accession = partner_ref.split(":")[-1]
            row_id = f"string::{seed_accession}::{partner_accession}"
            if row_id in seen_ids:
                continue
            seen_ids.add(row_id)
            raw_rows.append(
                {
                    "seed_accession": seed_accession,
                    "partner_ref": partner_ref,
                    "interaction_count": partner.get("interaction_count"),
                    "best_intact_miscore": partner.get("best_intact_miscore"),
                    "top_partner_alias": partner.get("top_partner_alias"),
                }
            )
            evidence_classes = ["text_or_network_context"]
            if index == 0 or (partner.get("interaction_count") or 0) >= 2:
                evidence_classes.append("functional_association")
            governing_status = (
                "support_only_non_governing"
                if "functional_association" in evidence_classes
                else "candidate_only_non_governing"
            )
            normalized_rows.append(
                {
                    "row_id": row_id,
                    "seed_accession": seed_accession,
                    "partner_accession": partner_accession,
                    "partner_ref": partner_ref,
                    "partner_label": partner.get("top_partner_alias") or partner_accession,
                    "row_family": "interaction",
                    "governing_status": governing_status,
                    "training_admissibility": (
                        "visible_but_non_governing"
                        if governing_status == "support_only_non_governing"
                        else "candidate_only"
                    ),
                    "relationship_context": "direct_partner",
                    "provenance": [
                        {
                            "source_name": "STRING v12",
                            "filename": "protein.links.full.v12.0.txt.gz",
                            "evidence_classes": evidence_classes,
                        }
                    ],
                    "payload_refs": {
                        "raw_registry_path": str(raw_registry_path).replace("\\", "/"),
                        "normalized_rows_path": str(normalized_rows_path).replace("\\", "/"),
                    },
                    "inclusion_rationale": "STRING-ready partner materialization derived from current one-hop interaction partner context after STRING completion.",
                    "hold_reasons": [
                        "string_rows_remain_non_governing_after_tail_completion",
                    ],
                    "metrics": {
                        "interaction_count": partner.get("interaction_count"),
                        "best_intact_miscore": partner.get("best_intact_miscore"),
                        "biogrid_row_count": support_row.get("biogrid_row_count"),
                        "string_disk_state": "complete",
                    },
                }
            )

    write_json(raw_registry_path, {"rows": raw_rows})
    write_json(normalized_rows_path, {"rows": normalized_rows})
    return {
        "artifact_id": "string_interaction_materialization_preview",
        "schema_id": "proteosphere-string-interaction-materialization-preview-2026-04-05",
        "status": "report_only",
        "summary": {
            "materialization_state": "string_complete_materialized_non_governing",
            "seed_accession_count": len(seed_accessions),
            "raw_edge_count": len(raw_rows),
            "normalized_row_count": len(normalized_rows),
            "support_only_row_count": sum(
                1 for row in normalized_rows if row["governing_status"] == "support_only_non_governing"
            ),
            "candidate_only_row_count": sum(
                1 for row in normalized_rows if row["governing_status"] == "candidate_only_non_governing"
            ),
        },
        "rows": normalized_rows,
        "truth_boundary": {
            "summary": "STRING rows are materialized but remain report-only and non-governing.",
            "report_only": True,
            "non_governing": True,
        },
    }


def build_packet_summary_preview(
    *,
    package_latest: dict[str, Any],
    packet_queue: dict[str, Any],
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    queue_rows = packet_queue.get("rows")
    queue_index: dict[str, dict[str, Any]] = {}
    if isinstance(queue_rows, list):
        for row in queue_rows:
            if not isinstance(row, dict):
                continue
            accession = row.get("accession")
            if isinstance(accession, str) and accession:
                queue_index[accession] = row

    rows: list[dict[str, Any]] = []
    lane_counts = Counter()
    for packet in _seed_packets(package_latest):
        accession = packet.get("accession")
        if not isinstance(accession, str) or not accession:
            continue
        queue_row = queue_index.get(accession, {})
        packet_lane = queue_row.get("packet_lane") if isinstance(queue_row, dict) else None
        packet_lane = packet_lane if isinstance(packet_lane, str) and packet_lane else "unknown"
        lane_counts[packet_lane] += 1
        rows.append(
            {
                "accession": accession,
                "packet_status": packet.get("status"),
                "packet_lane": packet_lane,
                "manifest_path": packet.get("manifest_path"),
                "packet_dir": packet.get("packet_dir"),
                "present_modalities": packet.get("present_modalities") or [],
                "missing_modalities": packet.get("missing_modalities") or [],
            }
        )

    payload = {
        "artifact_id": "training_packet_summary_preview",
        "schema_id": "proteosphere-training-packet-summary-preview-2026-04-05",
        "status": "report_only",
        "summary": {
            "packet_count": len(rows),
            "packet_lane_counts": dict(lane_counts),
        },
        "rows": rows,
        "truth_boundary": {
            "summary": "This is a report-only packet/materialization completion summary.",
            "report_only": True,
            "non_mutating": True,
        },
    }
    write_json(output_root / "packet_summary.json", payload)
    return payload
