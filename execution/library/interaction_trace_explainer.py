from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from core.library.entity_card import (
    ProteinEntityCard,
    ProteinLigandEntityCard,
    ProteinProteinEntityCard,
)

InteractionTraceState = Literal["resolved", "partial", "unresolved"]
InteractionTraceKind = Literal["protein_protein", "protein_ligand"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        iterable = (values,)
    else:
        iterable = tuple(values)
    ordered: dict[str, str] = {}
    for value in iterable:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


@dataclass(frozen=True, slots=True)
class TraceAnchor:
    canonical_id: str
    card_id: str
    title: str
    coverage_state: str
    evidence_lanes: tuple[str, ...] = ()
    blocker_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_id", _clean_text(self.canonical_id))
        object.__setattr__(self, "card_id", _clean_text(self.card_id))
        object.__setattr__(self, "title", _clean_text(self.title))
        object.__setattr__(self, "coverage_state", _clean_text(self.coverage_state))
        object.__setattr__(self, "evidence_lanes", _clean_text_tuple(self.evidence_lanes))
        object.__setattr__(self, "blocker_ids", _clean_text_tuple(self.blocker_ids))
        if not self.canonical_id:
            raise ValueError("canonical_id must not be empty")
        if not self.card_id:
            raise ValueError("card_id must not be empty")
        if not self.title:
            raise ValueError("title must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "card_id": self.card_id,
            "title": self.title,
            "coverage_state": self.coverage_state,
            "evidence_lanes": list(self.evidence_lanes),
            "blocker_ids": list(self.blocker_ids),
        }


@dataclass(frozen=True, slots=True)
class InteractionTraceExplanation:
    trace_kind: InteractionTraceKind
    canonical_id: str
    card_id: str
    trace_state: InteractionTraceState
    anchors: tuple[TraceAnchor, ...]
    missing_anchor_refs: tuple[str, ...] = ()
    supporting_refs: tuple[str, ...] = ()
    evidence_lanes: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    blocker_ids: tuple[str, ...] = ()
    coverage_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "trace_kind", _clean_text(self.trace_kind))
        object.__setattr__(self, "canonical_id", _clean_text(self.canonical_id))
        object.__setattr__(self, "card_id", _clean_text(self.card_id))
        object.__setattr__(self, "trace_state", _clean_text(self.trace_state))
        object.__setattr__(self, "anchors", tuple(self.anchors))
        object.__setattr__(self, "missing_anchor_refs", _clean_text_tuple(self.missing_anchor_refs))
        object.__setattr__(self, "supporting_refs", _clean_text_tuple(self.supporting_refs))
        object.__setattr__(self, "evidence_lanes", _clean_text_tuple(self.evidence_lanes))
        object.__setattr__(self, "provenance_refs", _clean_text_tuple(self.provenance_refs))
        object.__setattr__(self, "blocker_ids", _clean_text_tuple(self.blocker_ids))
        object.__setattr__(self, "coverage_notes", _clean_text_tuple(self.coverage_notes))
        if self.trace_kind not in {"protein_protein", "protein_ligand"}:
            raise ValueError("trace_kind must be protein_protein or protein_ligand")
        if self.trace_state not in {"resolved", "partial", "unresolved"}:
            raise ValueError("trace_state must be resolved, partial, or unresolved")
        if not self.canonical_id:
            raise ValueError("canonical_id must not be empty")
        if not self.card_id:
            raise ValueError("card_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_kind": self.trace_kind,
            "canonical_id": self.canonical_id,
            "card_id": self.card_id,
            "trace_state": self.trace_state,
            "anchors": [anchor.to_dict() for anchor in self.anchors],
            "missing_anchor_refs": list(self.missing_anchor_refs),
            "supporting_refs": list(self.supporting_refs),
            "evidence_lanes": list(self.evidence_lanes),
            "provenance_refs": list(self.provenance_refs),
            "blocker_ids": list(self.blocker_ids),
            "coverage_notes": list(self.coverage_notes),
        }


def _build_anchor(card: ProteinEntityCard) -> TraceAnchor:
    return TraceAnchor(
        canonical_id=card.canonical_id,
        card_id=card.card_id,
        title=card.title,
        coverage_state=card.evidence_summary.coverage_state,
        evidence_lanes=card.evidence_summary.evidence_lanes,
        blocker_ids=card.evidence_summary.blocker_ids,
    )


def _resolve_state(
    *,
    missing_anchor_refs: tuple[str, ...],
    blocker_ids: tuple[str, ...],
) -> InteractionTraceState:
    if missing_anchor_refs:
        return "unresolved"
    if blocker_ids:
        return "partial"
    return "resolved"


def explain_pair_trace(
    card: ProteinProteinEntityCard,
    protein_cards_by_ref: Mapping[str, ProteinEntityCard],
) -> InteractionTraceExplanation:
    anchor_cards = []
    missing_anchor_refs = []
    for protein_ref in (card.protein_a_ref, card.protein_b_ref):
        anchor = protein_cards_by_ref.get(protein_ref)
        if anchor is None:
            missing_anchor_refs.append(protein_ref)
        else:
            anchor_cards.append(_build_anchor(anchor))
    blocker_ids = _clean_text_tuple(
        card.evidence_summary.blocker_ids
        + tuple(f"missing_anchor:{ref}" for ref in missing_anchor_refs)
    )
    return InteractionTraceExplanation(
        trace_kind="protein_protein",
        canonical_id=card.canonical_id,
        card_id=card.card_id,
        trace_state=_resolve_state(
            missing_anchor_refs=tuple(missing_anchor_refs),
            blocker_ids=blocker_ids,
        ),
        anchors=tuple(anchor_cards),
        missing_anchor_refs=tuple(missing_anchor_refs),
        supporting_refs=card.interaction_refs,
        evidence_lanes=card.evidence_summary.evidence_lanes,
        provenance_refs=card.evidence_summary.provenance_refs,
        blocker_ids=blocker_ids,
        coverage_notes=card.evidence_summary.coverage_notes,
    )


def explain_ligand_trace(
    card: ProteinLigandEntityCard,
    protein_cards_by_ref: Mapping[str, ProteinEntityCard],
) -> InteractionTraceExplanation:
    protein_anchor = protein_cards_by_ref.get(card.protein_ref)
    missing_anchor_refs = () if protein_anchor is not None else (card.protein_ref,)
    blocker_ids = _clean_text_tuple(
        card.evidence_summary.blocker_ids
        + tuple(f"missing_anchor:{ref}" for ref in missing_anchor_refs)
    )
    return InteractionTraceExplanation(
        trace_kind="protein_ligand",
        canonical_id=card.canonical_id,
        card_id=card.card_id,
        trace_state=_resolve_state(
            missing_anchor_refs=missing_anchor_refs,
            blocker_ids=blocker_ids,
        ),
        anchors=(() if protein_anchor is None else (_build_anchor(protein_anchor),)),
        missing_anchor_refs=missing_anchor_refs,
        supporting_refs=card.assay_refs + card.structure_refs,
        evidence_lanes=card.evidence_summary.evidence_lanes,
        provenance_refs=card.evidence_summary.provenance_refs,
        blocker_ids=blocker_ids,
        coverage_notes=card.evidence_summary.coverage_notes,
    )


__all__ = [
    "InteractionTraceExplanation",
    "InteractionTraceKind",
    "InteractionTraceState",
    "TraceAnchor",
    "explain_ligand_trace",
    "explain_pair_trace",
]
