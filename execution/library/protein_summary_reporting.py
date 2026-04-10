from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from core.library.summary_record import ProteinSummaryRecord, SummaryLibrarySchema

REFERENCE_LIBRARY_EXAMPLE_FIELDS = (
    "protein_name",
    "organism_name",
    "taxon_id",
    "sequence_checksum",
    "sequence_version",
)

CONSENSUS_REFERENCE_FIELDS = (
    "protein_name",
    "organism_name",
    "taxon_id",
    "sequence_length",
    "sequence_checksum",
    "sequence_version",
    "gene_names",
    "aliases",
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIGAND_BRIDGE_PAYLOAD_PATH = (
    ROOT / "artifacts" / "status" / "local_bridge_ligand_payloads.real.json"
)
DEFAULT_MOTIF_SCOPE_COMPLETENESS_VIEW_PATH = (
    ROOT / "artifacts" / "status" / "p40_motif_scope_completeness_view.json"
)
DEFAULT_MOTIF_BREADTH_ACTION_MAP_PATH = (
    ROOT / "artifacts" / "status" / "p41_motif_breadth_action_map.json"
)


def _connection_summary(connection: Any) -> dict[str, Any]:
    return {
        "connection_kind": connection.connection_kind,
        "join_mode": connection.join_mode,
        "join_status": connection.join_status,
        "source_names": list(connection.source_names),
        "direct_sources": list(connection.direct_sources),
        "indirect_sources": list(connection.indirect_sources),
        "bridge_source": connection.bridge_source,
        "bridge_ids": list(connection.bridge_ids),
    }


def _cross_source_view_summary(record: ProteinSummaryRecord) -> dict[str, Any]:
    view = record.context.cross_source_view
    if view is None:
        return {}
    return {
        "direct_joins": [_connection_summary(connection) for connection in view.direct_joins],
        "indirect_bridges": [
            _connection_summary(connection) for connection in view.indirect_bridges
        ],
        "partial_joins": [_connection_summary(connection) for connection in view.partial_joins],
    }


def _pathway_summary(record: ProteinSummaryRecord, *, example_limit: int = 2) -> dict[str, Any]:
    pathways = list(record.context.pathway_references)
    if not pathways:
        return {}
    return {
        "pathway_reference_count": len(pathways),
        "examples": [
            {
                "identifier": ref.identifier,
                "label": ref.label,
                "join_status": ref.join_status,
                "evidence_refs": list(ref.evidence_refs),
            }
            for ref in pathways[:example_limit]
        ],
    }


def _ligand_bridge_lookup(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    lookup: dict[str, dict[str, Any]] = {}
    for entry in payload.get("entries") or ():
        if not isinstance(entry, Mapping):
            continue
        accession = str(entry.get("accession") or "").strip()
        if accession:
            lookup[accession] = dict(entry)
    return lookup


def _ligand_bridge_summary(entry: Mapping[str, Any]) -> dict[str, Any]:
    ligand = entry.get("selected_ligand") or {}
    bridge_record = entry.get("bridge_record") or {}
    return {
        "status": entry.get("status"),
        "bridge_state": entry.get("bridge_state"),
        "bridge_kind": entry.get("bridge_kind"),
        "pdb_id": entry.get("pdb_id"),
        "ligand_id": ligand.get("component_id"),
        "ligand_name": ligand.get("component_name"),
        "ligand_role": ligand.get("component_role"),
        "bridge_source_record_id": bridge_record.get("source_record_id"),
    }


def _load_json_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return {}
    return dict(payload)


def _rollup_summary(record: ProteinSummaryRecord) -> list[dict[str, Any]]:
    rollups_by_field = {
        rollup.field_name: rollup for rollup in record.context.source_rollups
    }
    summaries: list[dict[str, Any]] = []
    for field_name in REFERENCE_LIBRARY_EXAMPLE_FIELDS:
        rollup = rollups_by_field.get(field_name)
        if rollup is None:
            continue
        summaries.append(
            {
                "field_name": rollup.field_name,
                "source_precedence": list(rollup.source_precedence),
                "status": rollup.status,
                "winner_source": rollup.winner_source,
                "corroborating_sources": list(rollup.corroborating_sources),
                "disagreeing_sources": list(rollup.disagreeing_sources),
                "partial_reason": rollup.partial_reason,
            }
        )
    return summaries


def _reference_library_use_summary(
    *,
    direct_count: int,
    indirect_count: int,
    partial_count: int,
    rollups: list[dict[str, Any]],
) -> str:
    status_bits = ", ".join(
        f"{rollup['field_name']}={rollup['status']}" for rollup in rollups[:3]
    )
    return (
        f"direct={direct_count}, indirect={indirect_count}, partial={partial_count}; "
        f"focus_rollups: {status_bits}"
    )


def _consensus_reference_summary(
    *,
    direct_count: int,
    indirect_count: int,
    partial_count: int,
    field_statuses: list[dict[str, Any]],
) -> str:
    resolved = [
        status["field_name"] for status in field_statuses if status["status"] == "resolved"
    ]
    partial = [status["field_name"] for status in field_statuses if status["status"] == "partial"]
    conflict = [status["field_name"] for status in field_statuses if status["status"] == "conflict"]
    parts = [
        f"resolved={len(resolved)}"
        + (f"({', '.join(resolved[:3])})" if resolved else ""),
        f"partial={len(partial)}"
        + (f"({', '.join(partial[:3])})" if partial else ""),
        f"conflict={len(conflict)}"
        + (f"({', '.join(conflict[:3])})" if conflict else ""),
        f"cross_source_view=direct:{direct_count},indirect:{indirect_count},partial:{partial_count}",
    ]
    return "; ".join(parts)


def _reference_summary_line(
    *,
    label: str,
    source_precedence: list[str],
    field_statuses: list[dict[str, Any]],
    direct_count: int,
    indirect_count: int,
    partial_count: int,
    extras: list[str] | None = None,
) -> str:
    resolved = [status["field_name"] for status in field_statuses if status["status"] == "resolved"]
    partial = [status["field_name"] for status in field_statuses if status["status"] == "partial"]
    conflict = [status["field_name"] for status in field_statuses if status["status"] == "conflict"]
    parts = [
        f"{label}: precedence {' > '.join(source_precedence) if source_precedence else 'none'}",
        f"join trace {direct_count} direct / {indirect_count} indirect / {partial_count} partial",
        f"resolved {', '.join(resolved) if resolved else 'none'}",
        f"partial {', '.join(partial) if partial else 'none'}",
        f"conflict {', '.join(conflict) if conflict else 'none'}",
    ]
    if extras:
        parts.extend(extras)
    return "; ".join(parts)


def build_protein_summary_cross_source_view_report(
    library: SummaryLibrarySchema,
    *,
    example_limit: int = 3,
) -> dict[str, Any]:
    examples: list[dict[str, Any]] = []
    selected_records = sorted(
        (
            record
            for record in library.protein_records
            if record.context.cross_source_view is not None
        ),
        key=lambda record: (
            -(
                len(record.context.cross_source_view.direct_joins)
                + len(record.context.cross_source_view.indirect_bridges)
                + len(record.context.cross_source_view.partial_joins)
            ),
            -len(record.context.cross_source_view.indirect_bridges),
            record.summary_id,
        ),
    )
    for record in selected_records[:example_limit]:
        view = record.context.cross_source_view
        if view is None:
            continue
        examples.append(
            {
                "summary_id": record.summary_id,
                "join_status": record.join_status,
                "join_reason": record.join_reason,
                "cross_source_view": _cross_source_view_summary(record),
                "connection_counts": {
                    "direct_joins": len(view.direct_joins),
                    "indirect_bridges": len(view.indirect_bridges),
                    "partial_joins": len(view.partial_joins),
                },
            }
        )
    return {
        "report_id": "protein-summary-cross-source-view-report",
        "library_id": library.library_id,
        "source_manifest_id": library.source_manifest_id,
        "record_count": library.record_count,
        "example_count": len(examples),
        "selection_rule": "top protein records by total cross_source_view connections",
        "examples": examples,
    }


def _consensus_reference_field_statuses(record: ProteinSummaryRecord) -> list[dict[str, Any]]:
    rollups_by_field = {
        rollup.field_name: rollup for rollup in record.context.source_rollups
    }
    field_statuses: list[dict[str, Any]] = []
    for field_name in CONSENSUS_REFERENCE_FIELDS:
        rollup = rollups_by_field.get(field_name)
        if rollup is None:
            continue
        field_statuses.append(
            {
                "field_name": rollup.field_name,
                "source_precedence": list(rollup.source_precedence),
                "status": rollup.status,
                "winner_source": rollup.winner_source,
                "corroborating_sources": list(rollup.corroborating_sources),
                "disagreeing_sources": list(rollup.disagreeing_sources),
                "partial_reason": rollup.partial_reason,
            }
        )
    return field_statuses


def build_protein_summary_reference_library_examples_report(
    library: SummaryLibrarySchema,
    *,
    accessions: tuple[str, ...],
) -> dict[str, Any]:
    records_by_accession = {
        record.protein_ref.removeprefix("protein:"): record for record in library.protein_records
    }
    examples: list[dict[str, Any]] = []
    for accession in accessions:
        record = records_by_accession.get(accession)
        if record is None or record.context.cross_source_view is None:
            raise ValueError(f"missing materialized protein summary for accession: {accession}")
        view = record.context.cross_source_view
        rollups = _rollup_summary(record)
        examples.append(
            {
                "summary_id": record.summary_id,
                "join_status": record.join_status,
                "join_reason": record.join_reason,
                "reference_library_use_summary": _reference_library_use_summary(
                    direct_count=len(view.direct_joins),
                    indirect_count=len(view.indirect_bridges),
                    partial_count=len(view.partial_joins),
                    rollups=rollups,
                ),
                "rollups": rollups,
                "cross_source_view": {
                    "direct_joins": [
                        _connection_summary(connection) for connection in view.direct_joins
                    ],
                    "indirect_bridges": [
                        _connection_summary(connection) for connection in view.indirect_bridges
                    ],
                    "partial_joins": [
                        _connection_summary(connection) for connection in view.partial_joins
                    ],
                },
            }
        )
    return {
        "report_id": "protein-summary-reference-library-examples-report",
        "library_id": library.library_id,
        "source_manifest_id": library.source_manifest_id,
        "record_count": library.record_count,
        "selected_accessions": list(accessions),
        "selection_rule": "explicit accession list from current materialized output",
        "examples": examples,
    }


def build_protein_summary_consensus_reference_surface_report(
    library: SummaryLibrarySchema,
    *,
    accessions: tuple[str, ...],
) -> dict[str, Any]:
    records_by_accession = {
        record.protein_ref.removeprefix("protein:"): record for record in library.protein_records
    }
    examples: list[dict[str, Any]] = []
    for accession in accessions:
        record = records_by_accession.get(accession)
        if record is None or record.context.cross_source_view is None:
            raise ValueError(f"missing materialized protein summary for accession: {accession}")
        view = record.context.cross_source_view
        field_statuses = _consensus_reference_field_statuses(record)
        resolved_fields = [
            status for status in field_statuses if status["status"] == "resolved"
        ]
        stay_partial_fields = [
            status for status in field_statuses if status["status"] != "resolved"
        ]
        examples.append(
            {
                "summary_id": record.summary_id,
                "join_status": record.join_status,
                "join_reason": record.join_reason,
                "source_precedence": field_statuses[0]["source_precedence"]
                if field_statuses
                else [],
                "consensus_ready_summary": _consensus_reference_summary(
                    direct_count=len(view.direct_joins),
                    indirect_count=len(view.indirect_bridges),
                    partial_count=len(view.partial_joins),
                    field_statuses=field_statuses,
                ),
                "consensus_ready_fields": resolved_fields,
                "stay_partial_fields": stay_partial_fields,
                "cross_source_view": {
                    "direct_joins": [
                        _connection_summary(connection) for connection in view.direct_joins
                    ],
                    "indirect_bridges": [
                        _connection_summary(connection) for connection in view.indirect_bridges
                    ],
                    "partial_joins": [
                        _connection_summary(connection) for connection in view.partial_joins
                    ],
                },
            }
        )
    return {
        "report_id": "protein-summary-consensus-reference-surface-report",
        "library_id": library.library_id,
        "source_manifest_id": library.source_manifest_id,
        "record_count": library.record_count,
        "selected_accessions": list(accessions),
        "selection_rule": "explicit accession list from current materialized output",
        "consensus_policy": [
            "use source precedence and corroborating rollups to support reference-library summaries",
            "keep partial and conflict fields visible when the materialized sources do not agree",
            "treat cross_source_view as the join trace for direct, indirect, and partial support",
        ],
        "examples": examples,
    }


def _format_field_names(field_statuses: list[dict[str, Any]], status: str) -> str:
    fields = [field["field_name"] for field in field_statuses if field["status"] == status]
    return ", ".join(fields) if fields else "none"


def _format_conflict_fields(field_statuses: list[dict[str, Any]]) -> str:
    conflict_fields = [
        field for field in field_statuses if field["status"] == "conflict"
    ]
    if not conflict_fields:
        return "none"
    return ", ".join(
        f"{field['field_name']} ({', '.join(field['disagreeing_sources'])} disagree with {field['winner_source']})"
        for field in conflict_fields
    )


def _pluralize(count: int, singular: str, plural: str | None = None) -> str:
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural or singular + 's'}"


def render_protein_summary_consensus_reference_surface_markdown(
    report: Mapping[str, Any],
) -> str:
    lines: list[str] = [
        "# Protein Summary Consensus Reference Surface",
        "",
        f"- Library: `{report.get('library_id')}`",
        f"- Source manifest: `{report.get('source_manifest_id')}`",
        f"- Selected accessions: {', '.join(report.get('selected_accessions') or ())}",
        "",
        "This surface uses the current materialized protein summary library only.",
        "It treats resolved fields as consensus-ready, keeps partial fields visible, and refuses to hide conflicts.",
        "",
    ]
    for example in report.get("examples") or ():
        summary_id = example.get("summary_id", "unknown")
        join_reason = example.get("join_reason", "")
        source_precedence = example.get("source_precedence") or []
        consensus_ready_fields = example.get("consensus_ready_fields") or []
        stay_partial_fields = example.get("stay_partial_fields") or []
        cross_source_view = example.get("cross_source_view") or {}
        direct_count = len(cross_source_view.get("direct_joins") or [])
        indirect_count = len(cross_source_view.get("indirect_bridges") or [])
        partial_count = len(cross_source_view.get("partial_joins") or [])
        lines.extend(
            [
                f"## `{summary_id}`",
                f"- Join state: `{example.get('join_status')}` (`{join_reason}`)",
                (
                    "- Source precedence: "
                    f"{' > '.join(source_precedence) if source_precedence else 'none'}"
                ),
                (
                    "- Consensus-ready fields: "
                    f"{_format_field_names(consensus_ready_fields, 'resolved')}"
                ),
                (
                    "- Stay partial fields: "
                    f"{_format_field_names(stay_partial_fields, 'partial')}"
                    if _format_field_names(stay_partial_fields, "partial") != "none"
                    else "- Stay partial fields: none"
                ),
                f"- Keep conflict visible: {_format_conflict_fields(stay_partial_fields)}",
                (
                    "- Cross-source view: "
                    f"{_pluralize(direct_count, 'direct join')}, "
                    f"{_pluralize(indirect_count, 'indirect bridge')}, "
                    f"{_pluralize(partial_count, 'partial join')}"
                ),
            ]
        )
        if summary_id == "protein:P31749":
            lines.append(
                "- Why this is consensus-ready: Reactome and IntAct corroborate the protein name, organism, sequence length, and gene names, while aliases disagree and remain explicit."
            )
        elif summary_id == "protein:P00387":
            lines.append(
                "- Why this stays partial: the record is supported by direct joins, but the core summary fields still only have a single-source value."
            )
        elif summary_id == "protein:Q9NZD4":
            lines.append(
                "- Why this stays partial: the record has direct domain joins, but no resolved consensus fields beyond the UniProt spine."
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _consensus_examples_note_classification(field_statuses: list[dict[str, Any]]) -> str:
    resolved_count = sum(1 for status in field_statuses if status["status"] == "resolved")
    conflict_count = sum(1 for status in field_statuses if status["status"] == "conflict")
    if resolved_count >= 4 and conflict_count:
        return "strong-agreement-with-preserved-disagreement"
    if resolved_count:
        return "mixed-consensus"
    return "partial-reference-shell"


def _consensus_examples_note_line(
    *,
    source_precedence: list[str],
    field_statuses: list[dict[str, Any]],
    direct_count: int,
    indirect_count: int,
    partial_count: int,
) -> str:
    resolved = [status["field_name"] for status in field_statuses if status["status"] == "resolved"]
    partial = [status["field_name"] for status in field_statuses if status["status"] == "partial"]
    conflict = [status["field_name"] for status in field_statuses if status["status"] == "conflict"]
    parts = [
        f"precedence {' > '.join(source_precedence) if source_precedence else 'none'}",
        f"join trace {direct_count} direct / {indirect_count} indirect / {partial_count} partial",
    ]
    if resolved:
        parts.append(f"agreement on {', '.join(resolved)}")
    else:
        parts.append("no resolved consensus fields yet")
    if partial:
        parts.append(f"keep partial {', '.join(partial)}")
    if conflict:
        parts.append(f"preserve disagreement on {', '.join(conflict)}")
    return "; ".join(parts)


def build_protein_summary_consensus_examples_note_report(
    library: SummaryLibrarySchema,
    *,
    accessions: tuple[str, ...] = ("P00387", "P31749", "Q9NZD4"),
) -> dict[str, Any]:
    records_by_accession = {
        record.protein_ref.removeprefix("protein:"): record for record in library.protein_records
    }
    examples: list[dict[str, Any]] = []
    source_agreement_count = 0
    preserved_partial_count = 0
    for accession in accessions:
        record = records_by_accession.get(accession)
        if record is None or record.context.cross_source_view is None:
            raise ValueError(f"missing materialized protein summary for accession: {accession}")
        view = record.context.cross_source_view
        field_statuses = _consensus_reference_field_statuses(record)
        resolved_fields = [
            status["field_name"] for status in field_statuses if status["status"] == "resolved"
        ]
        partial_fields = [
            status["field_name"] for status in field_statuses if status["status"] == "partial"
        ]
        conflict_fields = [
            {
                "field_name": status["field_name"],
                "disagreeing_sources": status["disagreeing_sources"],
                "winner_source": status["winner_source"],
            }
            for status in field_statuses
            if status["status"] == "conflict"
        ]
        if resolved_fields:
            source_agreement_count += 1
        if partial_fields:
            preserved_partial_count += 1
        examples.append(
            {
                "summary_id": record.summary_id,
                "consensus_classification": _consensus_examples_note_classification(field_statuses),
                "note_line": _consensus_examples_note_line(
                    source_precedence=field_statuses[0]["source_precedence"]
                    if field_statuses
                    else [],
                    field_statuses=field_statuses,
                    direct_count=len(view.direct_joins),
                    indirect_count=len(view.indirect_bridges),
                    partial_count=len(view.partial_joins),
                ),
                "source_precedence": field_statuses[0]["source_precedence"]
                if field_statuses
                else [],
                "consensus_ready_fields": resolved_fields,
                "stay_partial_fields": partial_fields,
                "conflict_fields": conflict_fields,
                "cross_source_counts": {
                    "direct_joins": len(view.direct_joins),
                    "indirect_bridges": len(view.indirect_bridges),
                    "partial_joins": len(view.partial_joins),
                },
            }
        )
    return {
        "report_id": "protein-summary-consensus-examples-note-report",
        "library_id": library.library_id,
        "source_manifest_id": library.source_manifest_id,
        "record_count": library.record_count,
        "selected_accessions": list(accessions),
        "selection_rule": "explicit accession list from current materialized output",
        "summary": {
            "source_agreement_example_count": source_agreement_count,
            "preserved_partial_example_count": preserved_partial_count,
        },
        "examples": examples,
        "boundaries": [
            "source agreement is strong when the current rollups are resolved and corroborated",
            "partial fields stay visible when the materialized sources do not fully agree",
            "conflicts stay explicit instead of being collapsed into a false consensus",
        ],
    }


def render_protein_summary_consensus_examples_note_markdown(
    report: Mapping[str, Any],
) -> str:
    lines: list[str] = [
        "# Protein Summary Consensus Examples Note",
        "",
        f"- Library: `{report.get('library_id')}`",
        f"- Source manifest: `{report.get('source_manifest_id')}`",
        f"- Selected accessions: {', '.join(report.get('selected_accessions') or ())}",
        "",
        "This note is grounded in the current materialized protein summary artifacts only.",
        "It shows where the library already behaves like a consensus reference and where it must stay partial.",
        "",
    ]
    summary = report.get("summary") or {}
    lines.append(
        "- Coverage: "
        f"{summary.get('source_agreement_example_count', 0)} example(s) with resolved agreement; "
        f"{summary.get('preserved_partial_example_count', 0)} example(s) still carrying partial fields"
    )
    lines.append("")
    for example in report.get("examples") or ():
        lines.append(f"## `{example.get('summary_id')}` ({example.get('consensus_classification')})")
        lines.append(f"- {example.get('note_line')}")
        lines.append(
            "- Consensus-ready fields: "
            f"{', '.join(example.get('consensus_ready_fields') or ()) or 'none'}"
        )
        lines.append(
            "- Stay partial fields: "
            f"{', '.join(example.get('stay_partial_fields') or ()) or 'none'}"
        )
        conflict_fields = example.get("conflict_fields") or []
        if conflict_fields:
            conflict_bits = ", ".join(
                f"{field['field_name']} ({', '.join(field['disagreeing_sources'])} disagree with {field['winner_source']})"
                for field in conflict_fields
            )
        else:
            conflict_bits = "none"
        lines.append(f"- Conflicts kept explicit: {conflict_bits}")
        counts = example.get("cross_source_counts") or {}
        lines.append(
            "- Cross-source view: "
            f"{_pluralize(counts.get('direct_joins', 0), 'direct join')}, "
            f"{_pluralize(counts.get('indirect_bridges', 0), 'indirect bridge')}, "
            f"{_pluralize(counts.get('partial_joins', 0), 'partial join')}"
        )
        lines.append("")
    boundaries = report.get("boundaries") or []
    if boundaries:
        lines.append("## Boundary")
        for item in boundaries:
            lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _disagreement_priority_classification(field_statuses: list[dict[str, Any]]) -> str:
    resolved_count = sum(1 for status in field_statuses if status["status"] == "resolved")
    conflict_count = sum(1 for status in field_statuses if status["status"] == "conflict")
    if conflict_count and resolved_count:
        return "consensus-with-preserved-conflict"
    if conflict_count:
        return "conflict-preserved"
    if resolved_count:
        return "consensus-ready"
    return "partial-held-back"


def _disagreement_priority_note_line(
    *,
    source_precedence: list[str],
    field_statuses: list[dict[str, Any]],
    direct_count: int,
    indirect_count: int,
    partial_count: int,
) -> str:
    resolved = [status["field_name"] for status in field_statuses if status["status"] == "resolved"]
    partial = [status["field_name"] for status in field_statuses if status["status"] == "partial"]
    conflict = [status["field_name"] for status in field_statuses if status["status"] == "conflict"]
    parts = [
        f"precedence {' > '.join(source_precedence) if source_precedence else 'none'}",
        f"join trace {direct_count} direct / {indirect_count} indirect / {partial_count} partial",
    ]
    if resolved:
        parts.append(f"use consensus on {', '.join(resolved)}")
    else:
        parts.append("no resolved fields to promote")
    if conflict:
        parts.append(f"preserve disagreement on {', '.join(conflict)}")
    if partial:
        parts.append(f"keep partial {', '.join(partial)}")
    return "; ".join(parts)


def build_protein_summary_disagreement_priority_note_report(
    library: SummaryLibrarySchema,
    *,
    accessions: tuple[str, ...] = ("P00387", "P31749", "Q9NZD4"),
) -> dict[str, Any]:
    records_by_accession = {
        record.protein_ref.removeprefix("protein:"): record for record in library.protein_records
    }
    examples: list[dict[str, Any]] = []
    consensus_with_conflict_count = 0
    partial_hold_count = 0
    for accession in accessions:
        record = records_by_accession.get(accession)
        if record is None or record.context.cross_source_view is None:
            raise ValueError(f"missing materialized protein summary for accession: {accession}")
        view = record.context.cross_source_view
        field_statuses = _consensus_reference_field_statuses(record)
        resolved_fields = [
            status["field_name"] for status in field_statuses if status["status"] == "resolved"
        ]
        partial_fields = [
            status["field_name"] for status in field_statuses if status["status"] == "partial"
        ]
        conflict_fields = [
            {
                "field_name": status["field_name"],
                "disagreeing_sources": status["disagreeing_sources"],
                "winner_source": status["winner_source"],
            }
            for status in field_statuses
            if status["status"] == "conflict"
        ]
        if conflict_fields and resolved_fields:
            consensus_with_conflict_count += 1
        if not resolved_fields:
            partial_hold_count += 1
        examples.append(
            {
                "summary_id": record.summary_id,
                "priority_classification": _disagreement_priority_classification(field_statuses),
                "priority_line": _disagreement_priority_note_line(
                    source_precedence=field_statuses[0]["source_precedence"]
                    if field_statuses
                    else [],
                    field_statuses=field_statuses,
                    direct_count=len(view.direct_joins),
                    indirect_count=len(view.indirect_bridges),
                    partial_count=len(view.partial_joins),
                ),
                "source_precedence": field_statuses[0]["source_precedence"]
                if field_statuses
                else [],
                "resolved_fields": resolved_fields,
                "partial_fields": partial_fields,
                "conflict_fields": conflict_fields,
                "cross_source_counts": {
                    "direct_joins": len(view.direct_joins),
                    "indirect_bridges": len(view.indirect_bridges),
                    "partial_joins": len(view.partial_joins),
                },
            }
        )
    return {
        "report_id": "protein-summary-disagreement-priority-note-report",
        "library_id": library.library_id,
        "source_manifest_id": library.source_manifest_id,
        "record_count": library.record_count,
        "selected_accessions": list(accessions),
        "selection_rule": "explicit accession list from current materialized output",
        "summary": {
            "consensus_with_preserved_conflict_example_count": consensus_with_conflict_count,
            "partial_hold_example_count": partial_hold_count,
        },
        "priority_policy": [
            "use the highest-precedence source only when the field is corroborated in the rollup",
            "preserve disagreements explicitly instead of collapsing them into a single winner",
            "keep single-source fields partial when the materialized sources do not fully agree",
        ],
        "examples": examples,
    }


def render_protein_summary_disagreement_priority_note_markdown(
    report: Mapping[str, Any],
) -> str:
    lines: list[str] = [
        "# Protein Summary Disagreement and Priority Note",
        "",
        f"- Library: `{report.get('library_id')}`",
        f"- Source manifest: `{report.get('source_manifest_id')}`",
        f"- Selected accessions: {', '.join(report.get('selected_accessions') or ())}",
        "",
        "This note is grounded in the current materialized protein summary artifacts only.",
        "It makes the precedence rule readable: corroborated fields can become consensus, conflicts stay explicit, and single-source values stay partial.",
        "",
    ]
    summary = report.get("summary") or {}
    lines.append(
        "- Coverage: "
        f"{summary.get('consensus_with_preserved_conflict_example_count', 0)} consensus example(s) with preserved conflict; "
        f"{summary.get('partial_hold_example_count', 0)} example(s) held partial"
    )
    lines.append("")
    for example in report.get("examples") or ():
        lines.append(
            f"## `{example.get('summary_id')}` ({example.get('priority_classification')})"
        )
        lines.append(f"- {example.get('priority_line')}")
        lines.append(
            "- Resolved fields: "
            f"{', '.join(example.get('resolved_fields') or ()) or 'none'}"
        )
        lines.append(
            "- Partial fields: "
            f"{', '.join(example.get('partial_fields') or ()) or 'none'}"
        )
        conflict_fields = example.get("conflict_fields") or []
        if conflict_fields:
            conflict_bits = ", ".join(
                f"{field['field_name']} ({', '.join(field['disagreeing_sources'])} disagree with {field['winner_source']})"
                for field in conflict_fields
            )
        else:
            conflict_bits = "none"
        lines.append(f"- Preserved conflicts: {conflict_bits}")
        counts = example.get("cross_source_counts") or {}
        lines.append(
            "- Cross-source view: "
            f"{_pluralize(counts.get('direct_joins', 0), 'direct join')}, "
            f"{_pluralize(counts.get('indirect_bridges', 0), 'indirect bridge')}, "
            f"{_pluralize(counts.get('partial_joins', 0), 'partial join')}"
        )
        lines.append("")
    policy = report.get("priority_policy") or []
    if policy:
        lines.append("## Priority Rule")
        for item in policy:
            lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _source_fusion_priority_classification(field_statuses: list[dict[str, Any]]) -> str:
    resolved_count = sum(1 for status in field_statuses if status["status"] == "resolved")
    conflict_count = sum(1 for status in field_statuses if status["status"] == "conflict")
    if resolved_count and conflict_count:
        return "consensus-with-preserved-conflict"
    if resolved_count:
        return "mixed-consensus"
    return "partial-held-back"


def _source_fusion_priority_rationale(
    *,
    resolved_fields: list[str],
    partial_fields: list[str],
    conflict_fields: list[dict[str, Any]],
) -> str:
    if resolved_fields and conflict_fields:
        conflict_names = ", ".join(field["field_name"] for field in conflict_fields)
        return (
            f"core fields ({', '.join(resolved_fields)}) are corroborated, "
            f"but disagreement on {conflict_names} stays explicit because sources disagree."
        )
    if resolved_fields:
        return (
            f"precedence promotes {', '.join(resolved_fields)}, while "
            f"{', '.join(partial_fields) if partial_fields else 'no other fields'} stay partial."
        )
    return (
        "the record still has only single-source support for its summary fields, "
        "so precedence cannot safely promote a consensus value yet."
    )


def build_protein_summary_source_fusion_priority_note_report(
    library: SummaryLibrarySchema,
    *,
    accessions: tuple[str, ...] = ("P31749", "P69905", "P00387"),
) -> dict[str, Any]:
    records_by_accession = {
        record.protein_ref.removeprefix("protein:"): record for record in library.protein_records
    }
    examples: list[dict[str, Any]] = []
    consensus_example_count = 0
    preserved_conflict_count = 0
    partial_hold_count = 0
    for accession in accessions:
        record = records_by_accession.get(accession)
        if record is None or record.context.cross_source_view is None:
            raise ValueError(f"missing materialized protein summary for accession: {accession}")
        view = record.context.cross_source_view
        field_statuses = _consensus_reference_field_statuses(record)
        resolved_fields = [
            status["field_name"] for status in field_statuses if status["status"] == "resolved"
        ]
        partial_fields = [
            status["field_name"] for status in field_statuses if status["status"] == "partial"
        ]
        conflict_fields = [
            {
                "field_name": status["field_name"],
                "disagreeing_sources": status["disagreeing_sources"],
                "winner_source": status["winner_source"],
            }
            for status in field_statuses
            if status["status"] == "conflict"
        ]
        if resolved_fields:
            consensus_example_count += 1
        if conflict_fields:
            preserved_conflict_count += 1
        if not resolved_fields:
            partial_hold_count += 1
        examples.append(
            {
                "summary_id": record.summary_id,
                "priority_classification": _source_fusion_priority_classification(field_statuses),
                "priority_rationale": _source_fusion_priority_rationale(
                    resolved_fields=resolved_fields,
                    partial_fields=partial_fields,
                    conflict_fields=conflict_fields,
                ),
                "source_precedence": field_statuses[0]["source_precedence"]
                if field_statuses
                else [],
                "resolved_fields": resolved_fields,
                "partial_fields": partial_fields,
                "conflict_fields": conflict_fields,
                "cross_source_counts": {
                    "direct_joins": len(view.direct_joins),
                    "indirect_bridges": len(view.indirect_bridges),
                    "partial_joins": len(view.partial_joins),
                },
            }
        )
    return {
        "report_id": "protein-summary-source-fusion-priority-note-report",
        "library_id": library.library_id,
        "source_manifest_id": library.source_manifest_id,
        "record_count": library.record_count,
        "selected_accessions": list(accessions),
        "selection_rule": "explicit accession list from current materialized output",
        "summary": {
            "consensus_example_count": consensus_example_count,
            "preserved_conflict_example_count": preserved_conflict_count,
            "partial_hold_example_count": partial_hold_count,
        },
        "priority_rule": [
            "promote a field only when the rollup is corroborated by the higher-precedence sources",
            "keep conflicts explicit rather than collapsing them into a false consensus",
            "leave single-source fields partial when the materialized sources do not fully agree",
        ],
        "examples": examples,
    }


def render_protein_summary_source_fusion_priority_note_markdown(
    report: Mapping[str, Any],
) -> str:
    lines: list[str] = [
        "# Protein Summary Source Fusion Priority Note",
        "",
        f"- Library: `{report.get('library_id')}`",
        f"- Source manifest: `{report.get('source_manifest_id')}`",
        f"- Selected accessions: {', '.join(report.get('selected_accessions') or ())}",
        "",
        "This note is grounded in the current materialized protein summary artifacts only.",
        "It shows when precedence yields a usable consensus, when a disagreement must remain explicit, and when a record stays partial.",
        "",
    ]
    summary = report.get("summary") or {}
    lines.append(
        "- Coverage: "
        f"{summary.get('consensus_example_count', 0)} consensus example(s); "
        f"{summary.get('preserved_conflict_example_count', 0)} example(s) with preserved conflict; "
        f"{summary.get('partial_hold_example_count', 0)} example(s) held partial"
    )
    lines.append("")
    for example in report.get("examples") or ():
        lines.append(
            f"## `{example.get('summary_id')}` ({example.get('priority_classification')})"
        )
        lines.append(f"- Why: {example.get('priority_rationale')}")
        lines.append(
            "- Resolved fields: "
            f"{', '.join(example.get('resolved_fields') or ()) or 'none'}"
        )
        lines.append(
            "- Partial fields: "
            f"{', '.join(example.get('partial_fields') or ()) or 'none'}"
        )
        conflict_fields = example.get("conflict_fields") or []
        if conflict_fields:
            conflict_bits = ", ".join(
                f"{field['field_name']} ({', '.join(field['disagreeing_sources'])} disagree with {field['winner_source']})"
                for field in conflict_fields
            )
        else:
            conflict_bits = "none"
        lines.append(f"- Preserved conflicts: {conflict_bits}")
        counts = example.get("cross_source_counts") or {}
        lines.append(
            "- Cross-source view: "
            f"{_pluralize(counts.get('direct_joins', 0), 'direct join')}, "
            f"{_pluralize(counts.get('indirect_bridges', 0), 'indirect bridge')}, "
            f"{_pluralize(counts.get('partial_joins', 0), 'partial join')}"
        )
        lines.append("")
    policy = report.get("priority_rule") or []
    if policy:
        lines.append("## Priority Rule")
        for item in policy:
            lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


DEFAULT_TRAINING_PACKET_AUDIT_PATH = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "training_packet_audit.json"
)
DEFAULT_PACKET_DEFICIT_DASHBOARD_PATH = (
    ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
)
DEFAULT_PACKET_GAP_PRIORITY_RANKING_PATH = (
    ROOT / "artifacts" / "status" / "p35_packet_gap_priority_ranking.json"
)
DEFAULT_PACKET_STATE_DELTA_REPORT_PATH = (
    ROOT / "artifacts" / "status" / "packet_state_delta_report.json"
)
DEFAULT_PACKET_STATE_DELTA_SUMMARY_PATH = (
    ROOT / "artifacts" / "status" / "packet_state_delta_summary.json"
)


def _training_packet_audit_lookup(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return {}
    lookup: dict[str, Any] = {}
    for packet in payload.get("packets") or ():
        if not isinstance(packet, Mapping):
            continue
        accession = str(packet.get("accession") or "").strip()
        if accession:
            lookup[accession] = dict(packet)
    return {
        "summary": dict(payload.get("summary") or {}),
        "packets": lookup,
    }


def _packet_gap_line(packet: Mapping[str, Any]) -> str:
    missing_modalities = ", ".join(packet.get("missing_modalities") or ()) or "none"
    source_lanes = ", ".join(packet.get("source_lanes") or ()) or "none"
    return (
        f"packet {packet.get('judgment')} at lane depth {packet.get('lane_depth')}; "
        f"source lanes {source_lanes}; missing {missing_modalities}"
    )


def _packet_deficit_dashboard_lookup(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return {}
    packets_by_accession: dict[str, dict[str, Any]] = {}
    for packet in payload.get("packets") or ():
        if not isinstance(packet, Mapping):
            continue
        accession = str(packet.get("accession") or "").strip()
        if accession:
            packets_by_accession[accession] = dict(packet)
    return {
        "summary": dict(payload.get("summary") or {}),
        "packets": packets_by_accession,
        "source_fix_candidates": [dict(item) for item in payload.get("source_fix_candidates") or () if isinstance(item, Mapping)],
        "top_leverage_source_fixes": [
            dict(item) for item in (payload.get("summary") or {}).get("highest_leverage_source_fixes") or () if isinstance(item, Mapping)
        ],
    }


def _packet_state_delta_lookup(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return {}
    regressions_by_accession: dict[str, dict[str, Any]] = {}
    for item in payload.get("lower_layer_evidence_regressions") or ():
        if not isinstance(item, Mapping):
            continue
        accession = str(item.get("accession") or "").strip()
        if accession:
            regressions_by_accession[accession] = dict(item)
    unchanged_by_accession: dict[str, dict[str, Any]] = {}
    for item in payload.get("unchanged_remaining_gaps") or ():
        if not isinstance(item, Mapping):
            continue
        accession = str(item.get("accession") or "").strip()
        if accession:
            unchanged_by_accession[accession] = dict(item)
    return {
        "summary": dict(payload.get("summary") or {}),
        "regressions": regressions_by_accession,
        "unchanged": unchanged_by_accession,
        "truth_boundary": dict(payload.get("truth_boundary") or {}),
    }


def _packet_gap_priority_ranking_lookup(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return {}
    return {
        "state_snapshot": dict(payload.get("state_snapshot") or {}),
        "ranked_actions": [
            dict(item)
            for item in payload.get("ranked_actions") or ()
            if isinstance(item, Mapping)
        ],
        "excluded_from_rank_as_already_resolved_in_fresh_run": list(
            payload.get("excluded_from_rank_as_already_resolved_in_fresh_run") or ()
        ),
        "decision_note": payload.get("decision_note"),
        "truth_boundary": dict(payload.get("truth_boundary") or {}),
        "fresh_run_only": bool(payload.get("fresh_run_only")),
    }


def _packet_state_delta_summary_lookup(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return {}
    return {
        "summary": dict(payload.get("summary") or {}),
        "fresh_run_not_promotable": [
            dict(item)
            for item in payload.get("fresh_run_not_promotable") or ()
            if isinstance(item, Mapping)
        ],
        "latest_baseline_blockers": [
            dict(item)
            for item in payload.get("latest_baseline_blockers") or ()
            if isinstance(item, Mapping)
        ],
        "truth_boundary": dict(payload.get("truth_boundary") or {}),
    }


def build_protein_summary_packet_gap_library_strength_note_report(
    library: SummaryLibrarySchema,
    *,
    accessions: tuple[str, ...] = ("P31749", "P04637", "P00387"),
    training_packet_audit_path: Path = DEFAULT_TRAINING_PACKET_AUDIT_PATH,
) -> dict[str, Any]:
    source_fusion_report = build_protein_summary_source_fusion_priority_note_report(
        library,
        accessions=accessions,
    )
    audit = _training_packet_audit_lookup(training_packet_audit_path)
    packet_lookup = audit.get("packets") or {}
    examples: list[dict[str, Any]] = []
    for example in source_fusion_report.get("examples") or ():
        accession = str(example.get("summary_id") or "").removeprefix("protein:")
        packet = packet_lookup.get(accession)
        if packet is None:
            raise ValueError(f"missing training packet audit row for accession: {accession}")
        examples.append(
            {
                "summary_id": example.get("summary_id"),
                "library_priority_classification": example.get("priority_classification"),
                "library_priority_rationale": example.get("priority_rationale"),
                "library_resolved_fields": list(example.get("resolved_fields") or ()),
                "library_partial_fields": list(example.get("partial_fields") or ()),
                "library_conflict_fields": list(example.get("conflict_fields") or ()),
                "library_cross_source_counts": dict(example.get("cross_source_counts") or {}),
                "packet_judgment": packet.get("judgment"),
                "packet_completeness": packet.get("completeness"),
                "packet_lane_depth": packet.get("lane_depth"),
                "packet_source_lanes": list(packet.get("source_lanes") or ()),
                "packet_present_modalities": list(packet.get("present_modalities") or ()),
                "packet_missing_modalities": list(packet.get("missing_modalities") or ()),
                "packet_evidence_mode": packet.get("evidence_mode"),
                "packet_evidence_refs": list(packet.get("evidence_refs") or ()),
                "packet_gap_line": _packet_gap_line(packet),
                "packet_coverage_notes": list(packet.get("coverage_notes") or ()),
            }
        )
    summary = audit.get("summary") or {}
    useful_accessions = list(summary.get("useful_accessions") or [])
    return {
        "report_id": "protein-summary-packet-gap-library-strength-note-report",
        "library_id": library.library_id,
        "source_manifest_id": library.source_manifest_id,
        "record_count": library.record_count,
        "selected_accessions": list(accessions),
        "selection_rule": "explicit accession list from current materialized output",
        "packet_audit_summary": {
            "packet_count": summary.get("packet_count"),
            "completeness_counts": dict(summary.get("completeness_counts") or {}),
            "judgment_counts": dict(summary.get("judgment_counts") or {}),
            "missing_modality_counts": dict(summary.get("missing_modality_counts") or {}),
            "useful_accessions": useful_accessions,
            "weak_accessions": list(summary.get("weak_accessions") or []),
        },
        "current_packet_anchor": {
            "accession": useful_accessions[0] if useful_accessions else None,
            "note": (
                "P69905 is the only useful packet in the current audit, but it still stays partial "
                "because ligand and ppi are missing."
            ),
        },
        "examples": examples,
        "boundary": [
            "reference-library consensus can be stronger than the packet side because it merges corroborating sources",
            "packet partiality is still driven by missing modality lanes, even when the library can resolve core fields",
            "single-lane packet rows stay weak until the missing modalities land in the current audit",
        ],
    }


def build_protein_summary_packet_gap_operator_action_note_report(
    library: SummaryLibrarySchema,
    *,
    accessions: tuple[str, ...] = ("P31749", "P04637", "P69905"),
    packet_deficit_dashboard_path: Path = DEFAULT_PACKET_DEFICIT_DASHBOARD_PATH,
    packet_state_delta_report_path: Path = DEFAULT_PACKET_STATE_DELTA_REPORT_PATH,
) -> dict[str, Any]:
    source_fusion_report = build_protein_summary_source_fusion_priority_note_report(
        library,
        accessions=accessions,
    )
    dashboard = _packet_deficit_dashboard_lookup(packet_deficit_dashboard_path)
    delta = _packet_state_delta_lookup(packet_state_delta_report_path)
    dashboard_packets = dashboard.get("packets") or {}
    delta_regressions = delta.get("regressions") or {}
    examples: list[dict[str, Any]] = []
    repair_candidates: list[str] = []
    for example in source_fusion_report.get("examples") or ():
        accession = str(example.get("summary_id") or "").removeprefix("protein:")
        packet_row = dashboard_packets.get(accession)
        delta_row = delta_regressions.get(accession)
        if packet_row is None or delta_row is None:
            raise ValueError(f"missing packet dashboard or delta row for accession: {accession}")
        if packet_row.get("status") == "partial" or delta_row.get("freshest_status") == "partial":
            repair_candidates.append(accession)
        examples.append(
            {
                "summary_id": example.get("summary_id"),
                "library_priority_classification": example.get("priority_classification"),
                "library_priority_rationale": example.get("priority_rationale"),
                "library_resolved_fields": list(example.get("resolved_fields") or ()),
                "library_conflict_fields": list(example.get("conflict_fields") or ()),
                "protected_packet_status": packet_row.get("status"),
                "protected_packet_missing_modalities": list(packet_row.get("missing_modalities") or ()),
                "protected_packet_deficit_source_refs": list(packet_row.get("deficit_source_refs") or ()),
                "freshest_packet_status": delta_row.get("freshest_status"),
                "freshest_packet_missing_modalities": list(delta_row.get("freshest_missing_modalities") or ()),
                "freshest_packet_truth": delta_row.get("packet_level_truth"),
                "freshest_packet_delta_kind": delta_row.get("delta_kind"),
                "freshest_packet_delta_gap_count": delta_row.get("delta_gap_count"),
                "next_operator_action": (
                    "hold the protected latest packet baseline and repair the freshest run "
                    "before promotion"
                    if accession in {"P31749", "P04637"}
                    else "keep as the current packet anchor and do not overwrite the protected baseline"
                ),
            }
        )
    actionable_source_refs = list((dashboard.get("source_fix_candidates") or []))
    actionable_source_refs.extend(dashboard.get("top_leverage_source_fixes") or [])
    deduped_refs: list[dict[str, Any]] = []
    seen_refs: set[str] = set()
    for item in actionable_source_refs:
        source_ref = str(item.get("source_ref") or "").strip()
        if not source_ref or source_ref in seen_refs:
            continue
        seen_refs.add(source_ref)
        deduped_refs.append(item)
    return {
        "report_id": "protein-summary-packet-gap-operator-action-note-report",
        "library_id": library.library_id,
        "source_manifest_id": library.source_manifest_id,
        "record_count": library.record_count,
        "selected_accessions": list(accessions),
        "selection_rule": "current protected packet baseline plus freshest run delta for current summary-library examples",
        "packet_dashboard_summary": dashboard.get("summary") or {},
        "packet_delta_summary": delta.get("summary") or {},
        "current_packet_anchor": {
            "accession": "P69905",
            "why": "it is the only useful packet in the audit, but the freshest run still leaves it partial",
        },
        "actionable_source_refs": deduped_refs,
        "examples": examples,
        "repair_candidates": repair_candidates,
        "operator_actions": [
            "keep the protected latest packet baseline as the publication target",
            "repair the freshest-run regressions for P31749 and P04637 before promotion",
            "leave the source-fix candidate refs aimed at the true deficit rows, not the already-anchored library-strong examples",
        ],
    }


def render_protein_summary_packet_gap_operator_action_note_markdown(
    report: Mapping[str, Any],
) -> str:
    lines: list[str] = [
        "# Protein Summary Packet Gap Operator Action Note",
        "",
        f"- Library: `{report.get('library_id')}`",
        f"- Source manifest: `{report.get('source_manifest_id')}`",
        f"- Selected accessions: {', '.join(report.get('selected_accessions') or ())}",
        "",
        "This note is grounded in the protected packet dashboard, the packet delta report, and the current protein summary artifacts only.",
        "It tells an operator which examples are library-strong but packet-regressed, why, and what to do next.",
        "",
    ]
    dashboard_summary = report.get("packet_dashboard_summary") or {}
    delta_summary = report.get("packet_delta_summary") or {}
    lines.extend(
        [
            (
                "- Protected dashboard: "
                f"{dashboard_summary.get('complete_packet_count', 0)} complete, "
                f"{dashboard_summary.get('partial_packet_count', 0)} partial, "
                f"{dashboard_summary.get('packet_deficit_count', 0)} deficits"
            ),
            (
                "- Freshest delta: "
                f"{delta_summary.get('packet_level_regressed_count', 0)} regressed, "
                f"{delta_summary.get('packet_level_unchanged_count', 0)} unchanged, "
                f"{delta_summary.get('remaining_gap_packet_count', 0)} remaining gap packets"
            ),
        ]
    )
    anchor = report.get("current_packet_anchor") or {}
    if anchor.get("accession"):
        lines.append(f"- Current packet anchor: `{anchor.get('accession')}`. {anchor.get('why').capitalize()}")
    lines.append("")
    for example in report.get("examples") or ():
        lines.append(f"## `{example.get('summary_id')}`")
        lines.append(f"- Library class: {example.get('library_priority_classification')}")
        lines.append(f"- Library side: {example.get('library_priority_rationale')}")
        lines.append(
            "- Protected packet: "
            f"{example.get('protected_packet_status')} "
            f"(missing {', '.join(example.get('protected_packet_missing_modalities') or ()) or 'none'})"
        )
        lines.append(
            "- Freshest run: "
            f"{example.get('freshest_packet_status')} "
            f"({example.get('freshest_packet_truth')}; missing {', '.join(example.get('freshest_packet_missing_modalities') or ()) or 'none'})"
        )
        if example.get("protected_packet_deficit_source_refs"):
            lines.append(
                "- Protected deficit refs: "
                f"{', '.join(example.get('protected_packet_deficit_source_refs') or ())}"
            )
        lines.append(f"- Next operator action: {example.get('next_operator_action')}")
        lines.append("")
    refs = report.get("actionable_source_refs") or []
    if refs:
        lines.append("## Actionable Source Refs")
        for item in refs:
            lines.append(
                f"- {item.get('source_ref')}: {', '.join(item.get('missing_modalities') or ()) or 'none'}"
            )
    actions = report.get("operator_actions") or []
    if actions:
        lines.append("## Operator Actions")
        for item in actions:
            lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_protein_summary_packet_gap_next_actions_note_report(
    library: SummaryLibrarySchema,
    *,
    accessions: tuple[str, ...] = ("P31749", "P04637", "P69905"),
    packet_deficit_dashboard_path: Path = DEFAULT_PACKET_DEFICIT_DASHBOARD_PATH,
    packet_state_delta_report_path: Path = DEFAULT_PACKET_STATE_DELTA_REPORT_PATH,
    packet_gap_priority_ranking_path: Path = DEFAULT_PACKET_GAP_PRIORITY_RANKING_PATH,
    packet_state_delta_summary_path: Path = DEFAULT_PACKET_STATE_DELTA_SUMMARY_PATH,
) -> dict[str, Any]:
    operator_report = build_protein_summary_packet_gap_operator_action_note_report(
        library,
        accessions=accessions,
        packet_deficit_dashboard_path=packet_deficit_dashboard_path,
        packet_state_delta_report_path=packet_state_delta_report_path,
    )
    operator_delta_summary = dict(operator_report.get("packet_delta_summary") or {})
    ranking = _packet_gap_priority_ranking_lookup(packet_gap_priority_ranking_path)
    delta_summary = _packet_state_delta_summary_lookup(packet_state_delta_summary_path)
    next_data_actions: list[dict[str, Any]] = []
    for item in ranking.get("ranked_actions") or []:
        if item.get("status") == "current_run_present":
            continue
        next_data_actions.append(
            {
                "rank": item.get("rank"),
                "source_ref": item.get("source_ref"),
                "status": item.get("status"),
                "lane_type": item.get("lane_type"),
                "can_promote_now": item.get("can_promote_now"),
                "why": item.get("why"),
                "next_step": item.get("next_step"),
                "exact_local_evidence_files": list(item.get("exact_local_evidence_files") or ()),
                "evidence_artifacts": list(item.get("evidence_artifacts") or ()),
            }
        )
        if len(next_data_actions) == 5:
            break
    if not next_data_actions:
        raise ValueError("no ranked packet-gap data actions available")
    regression_boundary_examples = [
        {
            "summary_id": example.get("summary_id"),
            "library_priority_classification": example.get("library_priority_classification"),
            "library_priority_rationale": example.get("library_priority_rationale"),
            "protected_packet_status": example.get("protected_packet_status"),
            "freshest_packet_status": example.get("freshest_packet_status"),
            "freshest_packet_missing_modalities": list(
                example.get("freshest_packet_missing_modalities") or ()
            ),
            "next_operator_action": example.get("next_operator_action"),
        }
        for example in operator_report.get("examples") or ()
    ]
    return {
        "report_id": "protein-summary-packet-gap-next-actions-note-report",
        "library_id": library.library_id,
        "source_manifest_id": library.source_manifest_id,
        "record_count": library.record_count,
        "selected_accessions": list(accessions),
        "selection_rule": (
            "current protected packet baseline plus packet-gap priority ranking and delta summary"
        ),
        "packet_dashboard_summary": dict(operator_report.get("packet_dashboard_summary") or {}),
        "packet_delta_summary": dict(operator_report.get("packet_delta_summary") or {}),
        "packet_delta_summary_snapshot": {
            "packet_level_regressed_count": operator_delta_summary.get("packet_level_regressed_count"),
            "packet_level_unchanged_count": operator_delta_summary.get("packet_level_unchanged_count"),
            "fresh_run_not_promotable_count": len(
                delta_summary.get("fresh_run_not_promotable") or []
            ),
            "latest_baseline_blocker_count": len(
                delta_summary.get("latest_baseline_blockers") or []
            ),
            "regressed_accessions": list(operator_delta_summary.get("regressed_accessions") or []),
            "unchanged_accessions": list(operator_delta_summary.get("unchanged_accessions") or []),
        },
        "packet_priority_ranking_summary": {
            "state_snapshot": dict(ranking.get("state_snapshot") or {}),
            "excluded_from_rank_as_already_resolved_in_fresh_run": list(
                ranking.get("excluded_from_rank_as_already_resolved_in_fresh_run") or []
            ),
            "decision_note": ranking.get("decision_note"),
            "truth_boundary": dict(ranking.get("truth_boundary") or {}),
        },
        "current_packet_anchor": dict(operator_report.get("current_packet_anchor") or {}),
        "regression_boundary": {
            "regression_examples": regression_boundary_examples,
            "operator_actions": list(operator_report.get("operator_actions") or []),
        },
        "next_data_actions": next_data_actions,
        "boundary": [
            "fresh-run regressions stay in the repair lane and are not counted as promotable improvements",
            "the ranked packet-gap actions are current data actions, not latest-promotion changes",
            "current-run-present entries are reported separately and are not treated as unresolved gap work",
        ],
    }


def render_protein_summary_packet_gap_next_actions_note_markdown(
    report: Mapping[str, Any],
) -> str:
    lines: list[str] = [
        "# Protein Summary Packet Gap Next Actions Note",
        "",
        f"- Library: `{report.get('library_id')}`",
        f"- Source manifest: `{report.get('source_manifest_id')}`",
        f"- Selected accessions: {', '.join(report.get('selected_accessions') or ())}",
        "",
        "This note is grounded in the protected packet dashboard, the packet delta summary, the packet-gap priority ranking, and the current protein summary artifacts only.",
        "It keeps fresh-run regressions separate from the next data actions so operators do not confuse repair work with promotable improvement work.",
        "",
    ]
    dashboard_summary = report.get("packet_dashboard_summary") or {}
    delta_summary = report.get("packet_delta_summary") or {}
    delta_snapshot = report.get("packet_delta_summary_snapshot") or {}
    ranking_summary = report.get("packet_priority_ranking_summary") or {}
    lines.extend(
        [
            (
                "- Protected dashboard: "
                f"{dashboard_summary.get('complete_packet_count', 0)} complete, "
                f"{dashboard_summary.get('partial_packet_count', 0)} partial, "
                f"{dashboard_summary.get('packet_deficit_count', 0)} deficits"
            ),
            (
                "- Delta summary: "
                f"{delta_summary.get('packet_level_regressed_count', 0)} regressed, "
                f"{delta_summary.get('packet_level_unchanged_count', 0)} unchanged, "
                f"{delta_snapshot.get('fresh_run_not_promotable_count', 0)} fresh-run not promotable, "
                f"{delta_snapshot.get('latest_baseline_blocker_count', 0)} latest-baseline blockers"
            ),
            (
                "- Priority ranking: "
                f"{len(report.get('next_data_actions') or [])} unresolved data actions after filtering current-run-present entries"
            ),
        ]
    )
    anchor = report.get("current_packet_anchor") or {}
    if anchor.get("accession"):
        lines.append(f"- Current packet anchor: `{anchor.get('accession')}`. {anchor.get('why').capitalize()}")
    excluded_refs = ranking_summary.get("excluded_from_rank_as_already_resolved_in_fresh_run") or []
    if excluded_refs:
        lines.append(
            f"- Already resolved in fresh-run payload surfaces and excluded from rank: {', '.join(excluded_refs)}"
        )
    lines.append("")
    regression_boundary = report.get("regression_boundary") or {}
    regression_examples = regression_boundary.get("regression_examples") or []
    if regression_examples:
        lines.append("## Regression Boundary")
        for example in regression_examples:
            lines.append(f"### `{example.get('summary_id')}`")
            lines.append(f"- Library class: {example.get('library_priority_classification')}")
            lines.append(f"- Library side: {example.get('library_priority_rationale')}")
            lines.append(
                "- Fresh-run status: "
                f"{example.get('freshest_packet_status')} "
                f"(missing {', '.join(example.get('freshest_packet_missing_modalities') or ()) or 'none'})"
            )
            lines.append(f"- Next operator action: {example.get('next_operator_action')}")
            lines.append("")
    lines.append("## Next Data Actions")
    for item in report.get("next_data_actions") or ():
        lines.append(
            f"- rank {item.get('rank')}: `{item.get('source_ref')}` "
            f"({item.get('status')}; can_promote_now={str(item.get('can_promote_now')).lower()})"
        )
        lines.append(f"  - Why: {item.get('why')}")
        lines.append(f"  - Next step: {item.get('next_step')}")
    lines.append("")
    lines.append("## Boundary")
    for item in report.get("boundary") or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_protein_summary_packet_gap_library_strength_note_markdown(
    report: Mapping[str, Any],
) -> str:
    lines: list[str] = [
        "# Protein Summary Packet Gap and Library Strength Note",
        "",
        f"- Library: `{report.get('library_id')}`",
        f"- Source manifest: `{report.get('source_manifest_id')}`",
        f"- Selected accessions: {', '.join(report.get('selected_accessions') or ())}",
        "",
        "This note is grounded in the current materialized protein summary artifacts and the current training packet audit only.",
        "It shows why the reference library can already be consensus-ready while the training packets for the same accessions remain partial.",
        "",
    ]
    packet_summary = report.get("packet_audit_summary") or {}
    lines.append(
        "- Packet audit: "
        f"{packet_summary.get('packet_count', 0)} packets; "
        f"{packet_summary.get('completeness_counts', {}).get('partial', 0)} partial; "
        f"{packet_summary.get('judgment_counts', {}).get('useful', 0)} useful; "
        f"missing structure {packet_summary.get('missing_modality_counts', {}).get('structure', 0)}, "
        f"ligand {packet_summary.get('missing_modality_counts', {}).get('ligand', 0)}, "
        f"ppi {packet_summary.get('missing_modality_counts', {}).get('ppi', 0)}, "
        f"sequence {packet_summary.get('missing_modality_counts', {}).get('sequence', 0)}"
    )
    anchor = report.get("current_packet_anchor") or {}
    if anchor.get("accession"):
        lines.append(
            f"- Current packet anchor: `{anchor.get('accession')}`. {anchor.get('note')}"
        )
    lines.append("")
    for example in report.get("examples") or ():
        lines.append(f"## `{example.get('summary_id')}`")
        lines.append(f"- Library side: {example.get('library_priority_rationale')}")
        lines.append(
            "- Library resolved fields: "
            f"{', '.join(example.get('library_resolved_fields') or ()) or 'none'}"
        )
        lines.append(
            "- Library preserved conflicts: "
            + (
                ", ".join(
                    f"{field['field_name']} ({', '.join(field['disagreeing_sources'])} disagree with {field['winner_source']})"
                    for field in example.get("library_conflict_fields") or []
                )
                or "none"
            )
        )
        lines.append(f"- Packet side: {example.get('packet_gap_line')}")
        lines.append(
            "- Packet missing modalities: "
            f"{', '.join(example.get('packet_missing_modalities') or ()) or 'none'}"
        )
        lines.append(
            "- Packet source lanes: "
            f"{', '.join(example.get('packet_source_lanes') or ()) or 'none'}"
        )
        if example.get("packet_coverage_notes"):
            lines.append(
                "- Coverage notes: "
                f"{'; '.join(example.get('packet_coverage_notes') or ())}"
            )
        lines.append("")
    boundary = report.get("boundary") or []
    if boundary:
        lines.append("## Boundary")
        for item in boundary:
            lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_protein_summary_source_fusion_examples_report(
    library: SummaryLibrarySchema,
    *,
    accessions: tuple[str, ...] = ("P31749", "P69905", "P04637"),
    ligand_bridge_payload_path: Path = DEFAULT_LIGAND_BRIDGE_PAYLOAD_PATH,
) -> dict[str, Any]:
    records_by_accession = {
        record.protein_ref.removeprefix("protein:"): record for record in library.protein_records
    }
    ligand_lookup = _ligand_bridge_lookup(ligand_bridge_payload_path)
    case_labels = {
        "P31749": "ligand-heavy",
        "P69905": "pathway-heavy",
        "P04637": "conflict-heavy",
    }
    examples: list[dict[str, Any]] = []
    for accession in accessions:
        record = records_by_accession.get(accession)
        if record is None or record.context.cross_source_view is None:
            raise ValueError(f"missing materialized protein summary for accession: {accession}")
        view = record.context.cross_source_view
        rollups = _rollup_summary(record)
        field_statuses = _consensus_reference_field_statuses(record)
        example: dict[str, Any] = {
            "summary_id": record.summary_id,
            "case_kind": case_labels.get(accession, "reference"),
            "join_status": record.join_status,
            "join_reason": record.join_reason,
            "source_precedence": field_statuses[0]["source_precedence"] if field_statuses else [],
            "reference_summary": _reference_summary_line(
                label=case_labels.get(accession, "reference"),
                source_precedence=field_statuses[0]["source_precedence"] if field_statuses else [],
                field_statuses=field_statuses,
                direct_count=len(view.direct_joins),
                indirect_count=len(view.indirect_bridges),
                partial_count=len(view.partial_joins),
                extras=[],
            ),
            "consensus_ready_fields": [
                status["field_name"] for status in field_statuses if status["status"] == "resolved"
            ],
            "stay_partial_fields": [
                status["field_name"] for status in field_statuses if status["status"] == "partial"
            ],
            "conflict_fields": [
                {
                    "field_name": status["field_name"],
                    "disagreeing_sources": status["disagreeing_sources"],
                    "winner_source": status["winner_source"],
                }
                for status in field_statuses
                if status["status"] == "conflict"
            ],
            "source_rollups": rollups,
            "cross_source_view": _cross_source_view_summary(record),
        }
        if accession in ligand_lookup:
            example["ligand_bridge"] = _ligand_bridge_summary(ligand_lookup[accession])
        pathway_summary = _pathway_summary(record)
        if pathway_summary:
            example["pathway_summary"] = pathway_summary
        examples.append(example)
    return {
        "report_id": "protein-summary-source-fusion-examples-report",
        "library_id": library.library_id,
        "source_manifest_id": library.source_manifest_id,
        "record_count": library.record_count,
        "selected_accessions": list(accessions),
        "selection_rule": "explicit accession list from current materialized output",
        "consensus_policy": [
            "show source precedence, join trace, and rollup status together",
            "keep partial fields visible when the materialized sources do not fully agree",
            "use the ligand bridge artifact only as supplemental evidence for the ligand-heavy example",
        ],
        "examples": examples,
    }


def render_protein_summary_source_fusion_examples_markdown(
    report: Mapping[str, Any],
) -> str:
    lines: list[str] = [
        "# Protein Summary Source Fusion Examples",
        "",
        f"- Library: `{report.get('library_id')}`",
        f"- Source manifest: `{report.get('source_manifest_id')}`",
        f"- Selected accessions: {', '.join(report.get('selected_accessions') or ())}",
        "",
        "This report is grounded in the current materialized protein summary library.",
        "The ligand-heavy example is supplemented by the current real ligand bridge artifact.",
        "",
    ]
    for example in report.get("examples") or ():
        lines.append(f"## `{example.get('summary_id')}` ({example.get('case_kind')})")
        lines.append(f"- Reference summary: {example.get('reference_summary')}")
        lines.append(
            "- Consensus-ready fields: "
            f"{', '.join(example.get('consensus_ready_fields') or ()) or 'none'}"
        )
        lines.append(
            "- Stay partial fields: "
            f"{', '.join(example.get('stay_partial_fields') or ()) or 'none'}"
        )
        if example.get("conflict_fields"):
            conflict_bits = ", ".join(
                f"{field['field_name']} ({', '.join(field['disagreeing_sources'])} disagree with {field['winner_source']})"
                for field in example["conflict_fields"]
            )
        else:
            conflict_bits = "none"
        lines.append(f"- Conflicts to keep visible: {conflict_bits}")
        cross_source_view = example.get("cross_source_view") or {}
        lines.append(
            "- Cross-source view: "
            f"{len(cross_source_view.get('direct_joins') or [])} direct joins, "
            f"{len(cross_source_view.get('indirect_bridges') or [])} indirect bridges, "
            f"{len(cross_source_view.get('partial_joins') or [])} partial joins"
        )
        if example.get("ligand_bridge"):
            ligand = example["ligand_bridge"]
            lines.append(
                "- Ligand bridge: "
                f"{ligand.get('pdb_id')} / {ligand.get('ligand_id')} / {ligand.get('ligand_name')}"
            )
        if example.get("pathway_summary"):
            pathway = example["pathway_summary"]
            pathway_bits = ", ".join(
                f"{item['identifier']} ({item['label']})" for item in pathway.get("examples") or ()
            )
            lines.append(
                "- Pathway support: "
                f"{pathway.get('pathway_reference_count')} Reactome refs; {pathway_bits}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _motif_truth_summary(
    scope_view: Mapping[str, Any],
    breadth_map: Mapping[str, Any],
) -> dict[str, Any]:
    imported_coverage = list(scope_view.get("imported_coverage") or [])
    backbone_sources = [
        {
            "source_name": item.get("source_name"),
            "role": item.get("role"),
            "registry_status": item.get("registry_status"),
            "broad_mirror_status": item.get("broad_mirror_status"),
        }
        for item in imported_coverage
        if item.get("source_name") in {"interpro", "prosite", "pfam"}
    ]
    partial_sources = [
        {
            "source_name": item.get("source_name"),
            "role": item.get("role"),
            "registry_status": item.get("registry_status"),
            "broad_mirror_status": item.get("broad_mirror_status"),
        }
        for item in imported_coverage
        if item.get("registry_status") == "partial"
    ]
    external_gaps = [
        {
            "source_name": item.get("source_name"),
            "status": item.get("status"),
            "why_real": list(item.get("why_real") or ()),
        }
        for item in scope_view.get("external_gaps") or ()
    ]
    truth_boundary: list[str] = []
    for item in list(scope_view.get("truth_boundary") or ()) + list(
        breadth_map.get("truth_boundary") or ()
    ):
        if item not in truth_boundary:
            truth_boundary.append(item)
    return {
        "current_library_use_ready_source_count": breadth_map.get("summary", {}).get(
            "current_library_use_ready_source_count"
        ),
        "partial_current_use_source_count": breadth_map.get("summary", {}).get(
            "partial_current_use_source_count"
        ),
        "release_grade_breadth_gap_source_count": breadth_map.get("summary", {}).get(
            "release_grade_breadth_gap_source_count"
        ),
        "release_grade_ready": breadth_map.get("summary", {}).get("release_grade_ready"),
        "imported_motif_source_count": scope_view.get("summary", {}).get(
            "imported_motif_source_count"
        ),
        "complete_imported_source_count": scope_view.get("summary", {}).get(
            "complete_imported_source_count"
        ),
        "partial_imported_source_count": scope_view.get("summary", {}).get(
            "partial_imported_source_count"
        ),
        "genuinely_external_gap_count": scope_view.get("summary", {}).get(
            "genuinely_external_gap_count"
        ),
        "backbone_sources": backbone_sources,
        "partial_sources": partial_sources,
        "external_gaps": external_gaps,
        "readiness": {
            "scope_verdict": scope_view.get("readiness", {}).get("verdict"),
            "breadth_verdict": breadth_map.get("readiness", {}).get("verdict"),
        },
        "truth_boundary": truth_boundary,
    }


def build_protein_summary_integration_note_report(
    library: SummaryLibrarySchema,
    *,
    accessions: tuple[str, ...] = ("P31749", "P69905", "P04637"),
    ligand_bridge_payload_path: Path = DEFAULT_LIGAND_BRIDGE_PAYLOAD_PATH,
    motif_scope_completeness_view_path: Path = DEFAULT_MOTIF_SCOPE_COMPLETENESS_VIEW_PATH,
    motif_breadth_action_map_path: Path = DEFAULT_MOTIF_BREADTH_ACTION_MAP_PATH,
) -> dict[str, Any]:
    source_fusion_report = build_protein_summary_source_fusion_examples_report(
        library,
        accessions=accessions,
        ligand_bridge_payload_path=ligand_bridge_payload_path,
    )
    scope_view = _load_json_mapping(motif_scope_completeness_view_path)
    breadth_map = _load_json_mapping(motif_breadth_action_map_path)
    examples: list[dict[str, Any]] = []
    for example in source_fusion_report.get("examples") or ():
        cross_source_view = example.get("cross_source_view") or {}
        compact_example: dict[str, Any] = {
            "summary_id": example.get("summary_id"),
            "case_kind": example.get("case_kind"),
            "reference_summary": example.get("reference_summary"),
            "source_precedence": list(example.get("source_precedence") or ()),
            "consensus_ready_fields": list(example.get("consensus_ready_fields") or ()),
            "stay_partial_fields": list(example.get("stay_partial_fields") or ()),
            "conflict_fields": list(example.get("conflict_fields") or ()),
            "cross_source_counts": {
                "direct_joins": len(cross_source_view.get("direct_joins") or ()),
                "indirect_bridges": len(cross_source_view.get("indirect_bridges") or ()),
                "partial_joins": len(cross_source_view.get("partial_joins") or ()),
            },
        }
        if example.get("ligand_bridge"):
            compact_example["ligand_bridge"] = example["ligand_bridge"]
        if example.get("pathway_summary"):
            compact_example["pathway_summary"] = example["pathway_summary"]
        examples.append(compact_example)
    motif_truth = _motif_truth_summary(scope_view, breadth_map)
    return {
        "report_id": "protein-summary-integration-note-report",
        "library_id": library.library_id,
        "source_manifest_id": library.source_manifest_id,
        "record_count": library.record_count,
        "selected_accessions": list(accessions),
        "selection_rule": "current source-fusion examples plus motif breadth truth from materialized status artifacts",
        "source_fusion_examples": examples,
        "motif_breadth_truth": motif_truth,
        "integration_boundary": [
            "source precedence can support consensus-ready protein reference entries when fields are corroborated",
            "partial and conflict fields stay visible when sources do not agree",
            "motif breadth remains backbone-ready but not release-grade until the ELM partial and true external gaps are resolved",
        ],
    }


def render_protein_summary_integration_note_markdown(report: Mapping[str, Any]) -> str:
    lines: list[str] = [
        "# Protein Summary Integration Note",
        "",
        f"- Library: `{report.get('library_id')}`",
        f"- Source manifest: `{report.get('source_manifest_id')}`",
        f"- Selected accessions: {', '.join(report.get('selected_accessions') or ())}",
        "",
        "This note is grounded in the current materialized protein summary artifacts only.",
        "It keeps source precedence, source fusion examples, and motif breadth truth in one compact view.",
        "",
        "## Source Fusion",
    ]
    for example in report.get("source_fusion_examples") or ():
        lines.append(f"### `{example.get('summary_id')}` ({example.get('case_kind')})")
        lines.append(f"- Reference summary: {example.get('reference_summary')}")
        lines.append(
            "- Consensus-ready fields: "
            f"{', '.join(example.get('consensus_ready_fields') or ()) or 'none'}"
        )
        lines.append(
            "- Stay partial fields: "
            f"{', '.join(example.get('stay_partial_fields') or ()) or 'none'}"
        )
        conflict_fields = example.get("conflict_fields") or []
        if conflict_fields:
            conflict_bits = ", ".join(
                f"{field['field_name']} ({', '.join(field['disagreeing_sources'])} disagree with {field['winner_source']})"
                for field in conflict_fields
            )
        else:
            conflict_bits = "none"
        lines.append(f"- Conflicts to keep visible: {conflict_bits}")
        counts = example.get("cross_source_counts") or {}
        lines.append(
            "- Cross-source view: "
            f"{_pluralize(counts.get('direct_joins', 0), 'direct join')}, "
            f"{_pluralize(counts.get('indirect_bridges', 0), 'indirect bridge')}, "
            f"{_pluralize(counts.get('partial_joins', 0), 'partial join')}"
        )
        if example.get("ligand_bridge"):
            ligand = example["ligand_bridge"]
            lines.append(
                "- Ligand bridge: "
                f"{ligand.get('pdb_id')} / {ligand.get('ligand_id')} / {ligand.get('ligand_name')}"
            )
        if example.get("pathway_summary"):
            pathway = example["pathway_summary"]
            pathway_bits = ", ".join(
                f"{item['identifier']} ({item['label']})" for item in pathway.get("examples") or ()
            )
            lines.append(
                "- Pathway support: "
                f"{pathway.get('pathway_reference_count')} Reactome refs; {pathway_bits}"
            )
        lines.append("")
    motif_truth = report.get("motif_breadth_truth") or {}
    lines.extend(
        [
            "## Motif Breadth Truth",
            (
                "- Imported motif sources: "
                f"{motif_truth.get('imported_motif_source_count')} total, "
                f"{motif_truth.get('complete_imported_source_count')} complete, "
                f"{motif_truth.get('partial_imported_source_count')} partial, "
                f"{motif_truth.get('genuinely_external_gap_count')} true external gaps"
            ),
            (
                "- Library use: "
                f"{motif_truth.get('current_library_use_ready_source_count')} backbone-ready sources, "
                f"{motif_truth.get('partial_current_use_source_count')} partial source, "
                f"release-grade ready: {motif_truth.get('release_grade_ready')}"
            ),
            (
                "- Readiness: "
                f"{motif_truth.get('readiness', {}).get('scope_verdict')} / "
                f"{motif_truth.get('readiness', {}).get('breadth_verdict')}"
            ),
        ]
    )
    backbone_sources = motif_truth.get("backbone_sources") or []
    if backbone_sources:
        backbone_bits = ", ".join(
            f"{item['source_name']} ({item['registry_status']}, {item['broad_mirror_status']})"
            for item in backbone_sources
        )
        lines.append(f"- Backbone sources: {backbone_bits}")
    partial_sources = motif_truth.get("partial_sources") or []
    if partial_sources:
        partial_bits = ", ".join(
            f"{item['source_name']} ({item['registry_status']}, {item['broad_mirror_status']})"
            for item in partial_sources
        )
        lines.append(f"- Partial sources: {partial_bits}")
    external_gaps = motif_truth.get("external_gaps") or []
    if external_gaps:
        gap_bits = ", ".join(
            f"{item['source_name']} ({item['status']})" for item in external_gaps
        )
        lines.append(f"- External gaps: {gap_bits}")
    truth_boundary = motif_truth.get("truth_boundary") or []
    if truth_boundary:
        display_boundary = truth_boundary[:3]
        lines.append(f"- Truth boundary: {'; '.join(display_boundary)}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "build_protein_summary_cross_source_view_report",
    "build_protein_summary_consensus_reference_surface_report",
    "build_protein_summary_consensus_examples_note_report",
    "build_protein_summary_disagreement_priority_note_report",
    "build_protein_summary_integration_note_report",
    "build_protein_summary_packet_gap_operator_action_note_report",
    "build_protein_summary_packet_gap_next_actions_note_report",
    "build_protein_summary_packet_gap_library_strength_note_report",
    "build_protein_summary_reference_library_examples_report",
    "build_protein_summary_source_fusion_examples_report",
    "build_protein_summary_source_fusion_priority_note_report",
    "render_protein_summary_consensus_reference_surface_markdown",
    "render_protein_summary_consensus_examples_note_markdown",
    "render_protein_summary_disagreement_priority_note_markdown",
    "render_protein_summary_integration_note_markdown",
    "render_protein_summary_packet_gap_operator_action_note_markdown",
    "render_protein_summary_packet_gap_next_actions_note_markdown",
    "render_protein_summary_packet_gap_library_strength_note_markdown",
    "render_protein_summary_source_fusion_examples_markdown",
    "render_protein_summary_source_fusion_priority_note_markdown",
]
