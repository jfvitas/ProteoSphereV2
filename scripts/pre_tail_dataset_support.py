from __future__ import annotations

# ruff: noqa

from collections import Counter
from pathlib import Path
from typing import Any

try:
    from scripts.pre_tail_readiness_support import (
        listify,
        rows_by_accession,
        utc_now,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from pre_tail_readiness_support import (  # type: ignore[no-redef]
        listify,
        rows_by_accession,
        utc_now,
    )


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
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


def _governing_status(training_state: str) -> str:
    training_state = str(training_state or "").strip()
    if training_state == "governing_ready":
        return "governing_ready"
    if training_state == "blocked_pending_acquisition":
        return "blocked_pending_acquisition"
    if training_state == "tail_blocked":
        return "tail_blocked"
    if training_state == "candidate_only_non_governing":
        return "candidate_only_non_governing"
    return "support_only_non_governing"


def _join_status(governing_status: str) -> str:
    if governing_status == "governing_ready":
        return "joined"
    if governing_status == "blocked_pending_acquisition":
        return "partial"
    if governing_status == "tail_blocked":
        return "deferred"
    if governing_status == "candidate_only_non_governing":
        return "candidate"
    return "joined"


def _admissibility(governing_status: str) -> str:
    if governing_status in {
        "governing_ready",
        "support_only_non_governing",
        "candidate_only_non_governing",
        "blocked_pending_acquisition",
        "tail_blocked",
    }:
        return governing_status
    return "support_only_non_governing"


def _accession_from_partner_ref(partner_ref: Any) -> str:
    text = str(partner_ref or "").strip()
    if text.casefold().startswith("uniprotkb:"):
        return text.split(":", 1)[1].strip()
    return text


def _rows_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = str(row.get("row_id") or "").strip()
        if row_id:
            indexed[row_id] = dict(row)
    return indexed


def build_seed_plus_neighbors_structured_corpus_preview(
    training_set_readiness_preview: dict[str, Any],
    training_packet_completeness_matrix_preview: dict[str, Any],
    training_packet_materialization_queue_preview: dict[str, Any],
    bindingdb_accession_assay_profile_preview: dict[str, Any],
    bindingdb_measurement_subset_preview: dict[str, Any],
    structure_entry_context_preview: dict[str, Any],
    interaction_similarity_signature_preview: dict[str, Any],
    interaction_partner_context_preview: dict[str, Any],
    motif_domain_site_context_preview: dict[str, Any],
    sabio_rk_support_preview: dict[str, Any],
    targeted_page_scrape_registry_preview: dict[str, Any],
) -> dict[str, Any]:
    readiness_rows = rows_by_accession(training_set_readiness_preview.get("readiness_rows") or [])
    completeness_rows = rows_by_accession(
        training_packet_completeness_matrix_preview.get("rows") or []
    )
    queue_rows = rows_by_accession(training_packet_materialization_queue_preview.get("rows") or [])
    assay_rows = rows_by_accession(bindingdb_accession_assay_profile_preview.get("rows") or [])
    interaction_rows = rows_by_accession(interaction_similarity_signature_preview.get("rows") or [])
    partner_rows = rows_by_accession(interaction_partner_context_preview.get("rows") or [])
    motif_rows = rows_by_accession(motif_domain_site_context_preview.get("rows") or [])
    sabio_rows = rows_by_accession(sabio_rk_support_preview.get("rows") or [])
    page_rows = rows_by_accession(targeted_page_scrape_registry_preview.get("rows") or [])
    structure_rows = [
        row for row in structure_entry_context_preview.get("rows") or [] if isinstance(row, dict)
    ]
    measurement_rows = [
        row
        for row in bindingdb_measurement_subset_preview.get("rows") or []
        if isinstance(row, dict) and str(row.get("accession") or "").strip()
    ]

    rows: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    admissibility_counts: Counter[str] = Counter()
    unresolved_rows: list[dict[str, Any]] = []
    conflicted_rows: list[dict[str, Any]] = []
    seed_accessions: list[str] = []
    neighbor_accessions: set[str] = set()

    def add_row(row: dict[str, Any]) -> None:
        rows.append(row)
        family_counts[str(row.get("row_family") or "unknown")] += 1
        status_counts[str(row.get("governing_status") or "unknown")] += 1
        admissibility_counts[str(row.get("training_admissibility") or "unknown")] += 1
        if row.get("join_status") in {"partial", "deferred", "unjoined", "conflict", "ambiguous"}:
            unresolved_rows.append(_compact_row(row))
        if row.get("join_status") in {"conflict", "ambiguous"}:
            conflicted_rows.append(_compact_row(row))

    for readiness_row in readiness_rows.values():
        accession = str(readiness_row.get("accession") or "").strip()
        if not accession:
            continue
        seed_accessions.append(accession)
        packet_row = completeness_rows.get(accession, {})
        queue_row = queue_rows.get(accession, {})
        governing_status = _governing_status(str(readiness_row.get("training_set_state") or ""))
        if packet_row.get("packet_lane") == "governing_ready_but_package_blocked":
            governing_status = "governing_ready"
        missing_modalities = listify(packet_row.get("missing_modalities"))
        add_row(
            {
                "row_id": f"protein:{accession}:seed",
                "seed_accession": accession,
                "canonical_ids": [f"protein:{accession}"],
                "row_family": "protein",
                "governing_status": governing_status,
                "training_admissibility": _admissibility(governing_status),
                "join_status": _join_status(governing_status),
                "relationship_context": "direct_seed",
                "source_provenance_refs": listify(
                    [
                        packet_row.get("packet_manifest_path"),
                        queue_row.get("stub_path"),
                        f"training_set_readiness:{accession}",
                    ]
                ),
                "modality_payload_refs": listify(
                    [packet_row.get("packet_manifest_path"), queue_row.get("stub_path")]
                ),
                "inclusion_rationale": "current seed accession in the 12-accession cohort",
                "exclusion_or_hold_reasons": missing_modalities
                if governing_status == "blocked_pending_acquisition"
                else [],
                "payload": {
                    "training_set_state": readiness_row.get("training_set_state"),
                    "packet_status": readiness_row.get("packet_status"),
                    "recommended_next_step": readiness_row.get("recommended_next_step"),
                    "packet_lane": packet_row.get("packet_lane"),
                    "present_modalities": packet_row.get("present_modalities") or [],
                    "missing_modalities": missing_modalities,
                },
            }
        )

    for interaction_row in interaction_rows.values():
        accession = str(interaction_row.get("accession") or "").strip()
        if not accession:
            continue
        add_row(
            {
                "row_id": f"interaction:{accession}",
                "seed_accession": accession,
                "canonical_ids": [f"protein:{accession}"],
                "row_family": "interaction",
                "governing_status": "support_only_non_governing",
                "training_admissibility": "support_only_non_governing",
                "join_status": "joined",
                "relationship_context": "direct_seed",
                "source_provenance_refs": listify(
                    [interaction_row.get("signature_id"), interaction_row.get("protein_ref")]
                ),
                "modality_payload_refs": listify(
                    [interaction_row.get("signature_id"), interaction_row.get("protein_ref")]
                ),
                "inclusion_rationale": "executed interaction similarity signature for seed accession",
                "exclusion_or_hold_reasons": [],
                "payload": {
                    "interaction_similarity_group": interaction_row.get(
                        "interaction_similarity_group"
                    ),
                    "biogrid_registry_state": interaction_row.get("biogrid_registry_state"),
                    "string_disk_state": interaction_row.get("string_disk_state"),
                    "intact_registry_state": interaction_row.get("intact_registry_state"),
                    "candidate_only": interaction_row.get("candidate_only"),
                },
            }
        )

    for partner_row in partner_rows.values():
        seed_accession = str(partner_row.get("accession") or "").strip()
        if not seed_accession:
            continue
        for partner in partner_row.get("top_partners") or []:
            partner_accession = _accession_from_partner_ref(partner.get("partner_ref"))
            if not partner_accession:
                continue
            neighbor_accessions.add(partner_accession)
            add_row(
                {
                    "row_id": f"protein:{partner_accession}:partner:{seed_accession}",
                    "seed_accession": seed_accession,
                    "canonical_ids": [f"protein:{partner_accession}"],
                    "row_family": "protein",
                    "governing_status": "candidate_only_non_governing",
                    "training_admissibility": "candidate_only_non_governing",
                    "join_status": "candidate",
                    "relationship_context": "direct_partner",
                    "source_provenance_refs": listify(
                        [
                            f"interaction_partner_context:{seed_accession}",
                            partner.get("partner_ref"),
                        ]
                    ),
                    "modality_payload_refs": listify([partner.get("partner_ref"), seed_accession]),
                    "inclusion_rationale": "direct interaction partner surfaced by executed interaction context enrichment",
                    "exclusion_or_hold_reasons": [],
                    "payload": dict(partner),
                }
            )

    for structure_row in structure_rows:
        structure_id = str(structure_row.get("structure_id") or "").strip()
        if not structure_id:
            continue
        add_row(
            {
                "row_id": f"structure:{structure_id}",
                "seed_accession": ",".join(listify(structure_row.get("seed_accessions"))),
                "canonical_ids": [f"structure:{structure_id}"],
                "row_family": "structure",
                "governing_status": "support_only_non_governing",
                "training_admissibility": "support_only_non_governing",
                "join_status": "joined",
                "relationship_context": "direct_structure",
                "source_provenance_refs": listify(
                    [
                        structure_row.get("source_urls", {}).get("rcsb_core_entry"),
                        structure_row.get("source_urls", {}).get("pdbe_entry_summary"),
                        structure_row.get("source_urls", {}).get("sifts_uniprot_mapping"),
                    ]
                ),
                "modality_payload_refs": listify(
                    [
                        f"structure:{structure_id}",
                        *listify(structure_row.get("mapped_uniprot_accessions")),
                    ]
                ),
                "inclusion_rationale": "directly linked structure surfaced by RCSB/PDBe/SIFTS enrichment",
                "exclusion_or_hold_reasons": [],
                "payload": dict(structure_row),
            }
        )

    for assay_row in assay_rows.values():
        accession = str(assay_row.get("accession") or "").strip()
        if not accession:
            continue
        add_row(
            {
                "row_id": f"ligand:{accession}",
                "seed_accession": accession,
                "canonical_ids": [f"ligand:{accession}"],
                "row_family": "ligand",
                "governing_status": "support_only_non_governing",
                "training_admissibility": "support_only_non_governing",
                "join_status": "joined",
                "relationship_context": "direct_ligand",
                "source_provenance_refs": listify(
                    [
                        f"bindingdb_accession_assay_profile:{accession}",
                        assay_row.get("top_assay_names", [None])[0],
                    ]
                ),
                "modality_payload_refs": listify(
                    [
                        f"bindingdb_accession_assay_profile:{accession}",
                        f"bindingdb_measurement_subset:{accession}",
                    ]
                ),
                "inclusion_rationale": "direct ligand/assay support from BindingDB profile",
                "exclusion_or_hold_reasons": [],
                "payload": dict(assay_row),
            }
        )

    for measurement_row in measurement_rows:
        accession = str(measurement_row.get("accession") or "").strip()
        if not accession:
            continue
        add_row(
            {
                "row_id": str(measurement_row.get("measurement_id") or f"measurement:{accession}"),
                "seed_accession": accession,
                "canonical_ids": [
                    str(measurement_row.get("measurement_id") or f"measurement:{accession}"),
                    f"protein:{accession}",
                ],
                "row_family": "measurement",
                "governing_status": "candidate_only_non_governing",
                "training_admissibility": "candidate_only_non_governing",
                "join_status": "joined",
                "relationship_context": "direct_ligand",
                "source_provenance_refs": listify(
                    [
                        measurement_row.get("source_name"),
                        measurement_row.get("source_record_id"),
                        measurement_row.get("bindingdb_assay_name"),
                    ]
                ),
                "modality_payload_refs": listify(
                    [
                        measurement_row.get("measurement_id"),
                        measurement_row.get("raw_affinity_string"),
                    ]
                ),
                "inclusion_rationale": "directly linked BindingDB measurement surfaced by executed assay/bridge enrichment",
                "exclusion_or_hold_reasons": [],
                "payload": dict(measurement_row),
            }
        )

    for motif_row in motif_rows.values():
        accession = str(motif_row.get("accession") or "").strip()
        if not accession:
            continue
        add_row(
            {
                "row_id": f"motif_site:{accession}",
                "seed_accession": accession,
                "canonical_ids": [f"protein:{accession}", f"motif_site:{accession}"],
                "row_family": "motif_site",
                "governing_status": "support_only_non_governing",
                "training_admissibility": "support_only_non_governing",
                "join_status": "joined",
                "relationship_context": "direct_seed",
                "source_provenance_refs": listify([motif_row.get("source_url")]),
                "modality_payload_refs": listify([accession, motif_row.get("source_url")]),
                "inclusion_rationale": "direct motif/domain/site support from UniProt feature extraction",
                "exclusion_or_hold_reasons": [],
                "payload": dict(motif_row),
            }
        )

    for sabio_row in sabio_rows.values():
        accession = str(sabio_row.get("accession") or "").strip()
        if not accession:
            continue
        add_row(
            {
                "row_id": f"pathway_kinetics:{accession}",
                "seed_accession": accession,
                "canonical_ids": [f"protein:{accession}", f"pathway_kinetics:{accession}"],
                "row_family": "pathway_kinetics",
                "governing_status": "support_only_non_governing",
                "training_admissibility": "support_only_non_governing",
                "join_status": "joined",
                "relationship_context": "direct_seed",
                "source_provenance_refs": listify(sabio_row.get("source_provenance_refs")),
                "modality_payload_refs": listify([accession, sabio_row.get("truth_note")]),
                "inclusion_rationale": "accession-scoped SABIO-RK support surface surfaced by query-scoped support lane",
                "exclusion_or_hold_reasons": [],
                "payload": dict(sabio_row),
            }
        )

    for page_row in page_rows.values():
        accession = str(page_row.get("accession") or "").strip()
        if not accession:
            continue
        add_row(
            {
                "row_id": f"page_support:{accession}",
                "seed_accession": accession,
                "canonical_ids": [f"protein:{accession}", f"page_support:{accession}"],
                "row_family": "page_support",
                "governing_status": "candidate_only_non_governing",
                "training_admissibility": "candidate_only_non_governing",
                "join_status": "candidate",
                "relationship_context": "direct_seed",
                "source_provenance_refs": listify(page_row.get("candidate_pages")),
                "modality_payload_refs": listify(page_row.get("candidate_pages")),
                "inclusion_rationale": "targeted page capture for the requested seed accession",
                "exclusion_or_hold_reasons": [],
                "payload": dict(page_row),
            }
        )

    rows.sort(
        key=lambda row: (
            row.get("row_family") or "",
            row.get("seed_accession") or "",
            row.get("row_id") or "",
        )
    )
    strict_governing_training_view = [
        _compact_row(row) for row in rows if row.get("governing_status") == "governing_ready"
    ]
    all_visible_training_candidates_view = [_compact_row(row) for row in rows]
    return {
        "artifact_id": "seed_plus_neighbors_structured_corpus_preview",
        "schema_id": "proteosphere-seed-plus-neighbors-structured-corpus-preview-2026-04-05",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "seed_accession_count": len(seed_accessions),
            "one_hop_neighbor_accession_count": len(neighbor_accessions),
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
        },
        "seed_accessions": seed_accessions,
        "rows": rows,
        "raw_scrape_registries": {
            "interaction": {
                "row_count": len(interaction_rows),
                "candidate_only_count": sum(
                    1 for row in interaction_rows.values() if row.get("candidate_only")
                ),
            },
            "structure": {
                "row_count": len(structure_rows),
                "structure_ids": [row.get("structure_id") for row in structure_rows],
            },
            "bindingdb": {
                "profile_row_count": len(assay_rows),
                "measurement_row_count": len(measurement_rows),
            },
            "motif": {"row_count": len(motif_rows)},
            "sabio": {"row_count": len(sabio_rows)},
            "page_support": {"row_count": len(page_rows)},
        },
        "normalized_support_rows": [
            _compact_row(row)
            for row in rows
            if row.get("row_family") != "protein"
            or row.get("governing_status") != "governing_ready"
        ],
        "entity_resolution": {
            "summary": {
                "resolved_count": len(rows) - len(unresolved_rows),
                "unresolved_count": len(unresolved_rows),
                "conflicted_count": len(conflicted_rows),
            },
            "unresolved_rows": unresolved_rows,
            "conflicted_rows": conflicted_rows,
        },
        "training_views": {
            "strict_governing_training_view": strict_governing_training_view,
            "all_visible_training_candidates_view": all_visible_training_candidates_view,
        },
        "truth_boundary": {
            "summary": (
                "This corpus is report-only and one-hop bounded from the 12-accession seed cohort. "
                "It preserves governing, support-only, candidate-only, blocked, and tail-blocked "
                "rows with explicit status tags and does not authorize training or packaging."
            ),
            "report_only": True,
            "non_mutating": True,
            "one_hop_bounded": True,
        },
    }


def build_training_set_baseline_sidecar_preview(
    seed_plus_neighbors_structured_corpus_preview: dict[str, Any],
    materialization_summary_preview: dict[str, Any],
    training_set_readiness_preview: dict[str, Any],
) -> dict[str, Any]:
    readiness_rows = rows_by_accession(training_set_readiness_preview.get("readiness_rows") or [])
    corpus_seed_rows = {
        str(row.get("seed_accession") or "").strip(): dict(row)
        for row in seed_plus_neighbors_structured_corpus_preview.get("rows") or []
        if isinstance(row, dict)
        and row.get("row_family") == "protein"
        and str(row.get("row_id") or "").endswith(":seed")
        and str(row.get("seed_accession") or "").strip()
    }
    packets = {
        str(packet.get("accession") or "").strip(): dict(packet)
        for packet in materialization_summary_preview.get("packets") or []
        if isinstance(packet, dict) and str(packet.get("accession") or "").strip()
    }

    examples: list[dict[str, Any]] = []
    modality_counts: Counter[str] = Counter()
    governing_ready_count = 0
    blocked_pending_acquisition_count = 0

    for accession, readiness_row in readiness_rows.items():
        packet_row = packets.get(accession, {})
        training_state = str(readiness_row.get("training_set_state") or "").strip()
        corpus_seed_row = corpus_seed_rows.get(accession, {})
        governing_status = str(corpus_seed_row.get("governing_status") or "").strip()
        if not governing_status:
            governing_status = _governing_status(training_state)
        if governing_status == "governing_ready":
            governing_ready_count += 1
        if governing_status == "blocked_pending_acquisition":
            blocked_pending_acquisition_count += 1

        feature_pointers: list[dict[str, Any]] = []
        structure_ref = None
        ligand_ref = None
        observation_ref = None
        for artifact in packet_row.get("artifacts") or []:
            modality = str(artifact.get("modality") or "").strip()
            if not modality:
                continue
            rel_path = str(artifact.get("relative_path") or "").replace("\\", "/")
            pointer = str(Path(packet_row.get("packet_dir") or "").joinpath(rel_path).as_posix())
            feature_pointers.append(
                {
                    "modality": modality,
                    "pointer": pointer,
                    "feature_family": modality,
                    "source_name": packet_row.get("packet_id"),
                    "source_record_id": artifact.get("source_ref"),
                    "notes": [str(artifact.get("payload_kind") or "")],
                }
            )
            modality_counts[modality] += 1
            if modality == "structure" and structure_ref is None:
                structure_ref = {
                    "entity_kind": "structure",
                    "canonical_id": f"structure:{accession}",
                    "source_record_id": accession,
                    "join_status": governing_status,
                }
            if modality == "ligand" and ligand_ref is None:
                ligand_ref = {
                    "entity_kind": "ligand",
                    "canonical_id": f"ligand:{accession}",
                    "source_record_id": accession,
                    "join_status": governing_status,
                }
            if modality == "ppi" and observation_ref is None:
                observation_ref = {
                    "entity_kind": "observation",
                    "canonical_id": f"observation:{accession}",
                    "source_record_id": accession,
                    "join_status": governing_status,
                }

        if not feature_pointers:
            feature_pointers.append({"modality": "sequence", "pointer": accession})

        example = {
            "example_id": accession,
            "protein_ref": {
                "entity_kind": "protein",
                "canonical_id": f"protein:{accession}",
                "source_record_id": accession,
                "join_status": governing_status,
            },
            "feature_pointers": feature_pointers,
            "structure_ref": structure_ref,
            "ligand_ref": ligand_ref,
            "observation_ref": observation_ref,
            "labels": [
                {
                    "label_name": "training_set_state",
                    "label_kind": "categorical",
                    "value": training_state,
                },
                {
                    "label_name": "packet_status",
                    "label_kind": "categorical",
                    "value": readiness_row.get("packet_status"),
                },
                {
                    "label_name": "governing_status",
                    "label_kind": "categorical",
                    "value": governing_status,
                },
                {
                    "label_name": "split",
                    "label_kind": "categorical",
                    "value": readiness_row.get("split"),
                },
            ],
            "source_lineage_refs": listify(
                [
                    packet_row.get("manifest_path"),
                    packet_row.get("packet_id"),
                    packet_row.get("packet_dir"),
                    *listify(packet_row.get("provenance_refs")),
                ]
            ),
            "split": readiness_row.get("split"),
            "metadata": {
                "training_set_state": training_state,
                "packet_status": readiness_row.get("packet_status"),
                "governing_status": governing_status,
                "training_admissibility": corpus_seed_row.get("training_admissibility")
                or governing_status,
                "requested_modalities": packet_row.get("requested_modalities") or [],
                "present_modalities": packet_row.get("present_modalities") or [],
                "missing_modalities": packet_row.get("missing_modalities") or [],
            },
            "notes": listify(
                [
                    readiness_row.get("recommended_next_step"),
                    packet_row.get("latest_promotion_state"),
                ]
            ),
        }
        examples.append(example)

    baseline_dataset = {
        "dataset_id": "pretail-selected-cohort-baseline",
        "schema_version": 1,
        "examples": examples,
        "requested_modalities": ["sequence", "structure", "ligand", "ppi", "variant"],
        "package_id": materialization_summary_preview.get("run_id"),
        "package_state": materialization_summary_preview.get("status"),
        "created_at": materialization_summary_preview.get("created_at"),
        "source_packages": [str(materialization_summary_preview.get("output_root") or "")],
        "notes": ["pre-tail baseline sidecar", "report-only visibility export"],
        "metadata": {
            "seed_accession_count": len(examples),
            "governing_ready_count": governing_ready_count,
            "blocked_pending_acquisition_count": blocked_pending_acquisition_count,
        },
    }
    strict_governing_training_view = [
        {
            "example_id": example["example_id"],
            "training_set_state": example["labels"][0]["value"],
            "packet_status": example["labels"][1]["value"],
            "governing_status": example["labels"][2]["value"],
            "split": example["split"],
            "feature_modalities": [pointer["modality"] for pointer in example["feature_pointers"]],
        }
        for example in examples
        if example["labels"][2]["value"] == "governing_ready"
    ]
    all_visible_training_candidates_view = [
        {
            "example_id": example["example_id"],
            "training_set_state": example["labels"][0]["value"],
            "packet_status": example["labels"][1]["value"],
            "governing_status": example["labels"][2]["value"],
            "split": example["split"],
            "feature_modalities": [pointer["modality"] for pointer in example["feature_pointers"]],
            "missing_modalities": example["metadata"]["missing_modalities"],
        }
        for example in examples
    ]
    return {
        "artifact_id": "training_set_baseline_sidecar_preview",
        "schema_id": "proteosphere-training-set-baseline-sidecar-preview-2026-04-05",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "example_count": len(examples),
            "requested_modalities": baseline_dataset["requested_modalities"],
            "governing_ready_example_count": governing_ready_count,
            "blocked_pending_acquisition_example_count": blocked_pending_acquisition_count,
            "feature_modality_counts": dict(modality_counts),
            "strict_governing_training_view_count": len(strict_governing_training_view),
            "all_visible_training_candidates_view_count": len(all_visible_training_candidates_view),
        },
        "baseline_dataset": baseline_dataset,
        "strict_governing_training_view": strict_governing_training_view,
        "all_visible_training_candidates_view": all_visible_training_candidates_view,
        "truth_boundary": {
            "summary": (
                "This baseline sidecar is report-only and derived from the current packet/materialization "
                "summary. It does not mutate package state or widen the training boundary."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_training_set_multimodal_sidecar_preview(
    seed_plus_neighbors_structured_corpus_preview: dict[str, Any],
    materialization_summary_preview: dict[str, Any],
    canonical_store_preview: dict[str, Any],
) -> dict[str, Any]:
    corpus_row_list = [
        row
        for row in (seed_plus_neighbors_structured_corpus_preview.get("rows") or [])
        if isinstance(row, dict)
    ]
    corpus_rows_by_id = _rows_by_id(corpus_row_list)
    packets = [
        row for row in materialization_summary_preview.get("packets") or [] if isinstance(row, dict)
    ]
    canonical_record_count = int(
        canonical_store_preview.get("record_count")
        or len(canonical_store_preview.get("records") or [])
    )
    selected_examples: list[dict[str, Any]] = []
    issue_count = 0

    for packet in packets:
        accession = str(packet.get("accession") or "").strip()
        if not accession:
            continue
        packet_dir = str(packet.get("packet_dir") or "").replace("\\", "/")
        artifacts: list[dict[str, Any]] = []
        for artifact in packet.get("artifacts") or []:
            modality = str(artifact.get("modality") or "").strip()
            rel_path = str(artifact.get("relative_path") or "").replace("\\", "/")
            pointer = f"{packet_dir}/{rel_path}" if packet_dir else rel_path
            artifacts.append(
                {
                    "artifact_kind": {
                        "sequence": "feature",
                        "structure": "structure",
                        "ligand": "table",
                        "ppi": "evidence_text",
                    }.get(modality, "other"),
                    "pointer": pointer,
                    "selector": modality,
                    "source_name": packet.get("packet_id"),
                    "source_record_id": artifact.get("source_ref"),
                    "notes": [str(artifact.get("payload_kind") or "")],
                }
            )
        selected_examples.append(
            {
                "example_id": accession,
                "planning_index_ref": f"planning:{accession}",
                "source_record_refs": listify(
                    [packet.get("packet_id"), packet.get("manifest_path")]
                ),
                "canonical_ids": [str(packet.get("canonical_id") or f"protein:{accession}")],
                "artifact_pointers": artifacts,
                "notes": listify([packet.get("status"), packet.get("latest_promotion_state")]),
            }
        )
        if packet.get("status") != "complete":
            issue_count += 1

    multimodal_dataset = {
        "dataset_id": "pretail-selected-cohort-multimodal",
        "schema_version": 1,
        "selected_examples": selected_examples,
        "example_count": len(selected_examples),
        "issue_count": issue_count,
        "requested_modalities": ["sequence", "structure", "ligand", "ppi", "variant"],
        "package_state": materialization_summary_preview.get("status"),
        "canonical_record_count": canonical_record_count,
        "corpus_row_count": len(corpus_row_list),
        "source_packages": [str(materialization_summary_preview.get("output_root") or "")],
    }
    strict_governing_training_view = [
        {
            "example_id": example["example_id"],
            "feature_modalities": [pointer["selector"] for pointer in example["artifact_pointers"]],
            "status": "governing_ready",
        }
        for example in selected_examples
        if corpus_rows_by_id.get(f"protein:{example['example_id']}:seed", {}).get(
            "governing_status"
        )
        == "governing_ready"
    ]
    all_visible_training_candidates_view = [
        {
            "example_id": example["example_id"],
            "feature_modalities": [pointer["selector"] for pointer in example["artifact_pointers"]],
            "selected_example": True,
        }
        for example in selected_examples
    ]
    return {
        "artifact_id": "training_set_multimodal_sidecar_preview",
        "schema_id": "proteosphere-training-set-multimodal-sidecar-preview-2026-04-05",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "example_count": len(selected_examples),
            "issue_count": issue_count,
            "canonical_record_count": canonical_record_count,
            "corpus_row_count": len(corpus_row_list),
            "strict_governing_training_view_count": len(strict_governing_training_view),
            "all_visible_training_candidates_view_count": len(all_visible_training_candidates_view),
        },
        "multimodal_dataset": multimodal_dataset,
        "storage_runtime": {
            "status": "report_only_preview",
            "selected_example_count": len(selected_examples),
            "canonical_record_count": canonical_record_count,
        },
        "strict_governing_training_view": strict_governing_training_view,
        "all_visible_training_candidates_view": all_visible_training_candidates_view,
        "truth_boundary": {
            "summary": (
                "This multimodal sidecar is report-only and derived from the current packet and "
                "canonical-store summaries. It does not mutate package state or authorize training."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }
