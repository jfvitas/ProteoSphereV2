from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from connectors.rcsb.parsers import RCSBEntityRecord
from connectors.uniprot.parsers import UniProtSequenceRecord
from normalization.mapping.chain_exact import (
    ExactChainMapping,
    map_chain_sequence_exact,
)
from normalization.mapping.mmseqs2_chain_alignment import (
    ChainUniProtMapping,
    map_chain_sequence_to_uniprot,
)

AmbiguityStatus = Literal["resolved", "ambiguous", "unresolved"]
AmbiguityBackend = Literal["exact_sequence_match", "local_smith_waterman_fallback"]


@dataclass(frozen=True, slots=True)
class ChainAmbiguityCandidate:
    accession: str
    entry_name: str
    source_backends: tuple[AmbiguityBackend, ...]
    exact_sequence_match: bool
    query_length: int
    target_length: int
    is_reference_hint: bool
    score: int | None = None
    identity: float | None = None
    query_coverage: float | None = None
    target_coverage: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "accession": self.accession,
            "entry_name": self.entry_name,
            "source_backends": list(self.source_backends),
            "exact_sequence_match": self.exact_sequence_match,
            "query_length": self.query_length,
            "target_length": self.target_length,
            "is_reference_hint": self.is_reference_hint,
            "score": self.score,
            "identity": self.identity,
            "query_coverage": self.query_coverage,
            "target_coverage": self.target_coverage,
        }


@dataclass(frozen=True, slots=True)
class ChainAmbiguityMapping:
    pdb_id: str | None
    entity_id: str | None
    chain_id: str | None
    status: AmbiguityStatus
    resolved_accession: str | None
    reason: str
    query_sequence_length: int
    provided_uniprot_ids: tuple[str, ...]
    candidates: tuple[ChainAmbiguityCandidate, ...]

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved" and self.resolved_accession is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "pdb_id": self.pdb_id,
            "entity_id": self.entity_id,
            "chain_id": self.chain_id,
            "status": self.status,
            "resolved_accession": self.resolved_accession,
            "reason": self.reason,
            "query_sequence_length": self.query_sequence_length,
            "provided_uniprot_ids": list(self.provided_uniprot_ids),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def map_chain_sequence_preserving_ambiguity(
    query_sequence: str,
    uniprot_records: Iterable[UniProtSequenceRecord],
    *,
    pdb_id: str | None = None,
    entity_id: str | None = None,
    chain_id: str | None = None,
    provided_uniprot_ids: Sequence[str] = (),
    min_identity: float = 0.85,
    min_query_coverage: float = 0.9,
    ambiguity_margin: float = 0.02,
) -> ChainAmbiguityMapping:
    records = tuple(uniprot_records)
    exact_mapping = map_chain_sequence_exact(
        query_sequence,
        records,
        pdb_id=pdb_id,
        entity_id=entity_id,
        chain_id=chain_id,
        provided_uniprot_ids=provided_uniprot_ids,
    )
    alignment_mapping = map_chain_sequence_to_uniprot(
        query_sequence,
        records,
        pdb_id=pdb_id,
        entity_id=entity_id,
        chain_id=chain_id,
        provided_uniprot_ids=provided_uniprot_ids,
        min_identity=min_identity,
        min_query_coverage=min_query_coverage,
        ambiguity_margin=ambiguity_margin,
    )
    candidates = _merge_candidates(exact_mapping, alignment_mapping)
    status, resolved_accession, reason = _resolve_status(exact_mapping, alignment_mapping)

    return ChainAmbiguityMapping(
        pdb_id=pdb_id,
        entity_id=entity_id,
        chain_id=chain_id,
        status=status,
        resolved_accession=resolved_accession,
        reason=reason,
        query_sequence_length=_normalized_sequence_length(query_sequence),
        provided_uniprot_ids=_normalize_accessions(provided_uniprot_ids),
        candidates=candidates,
    )


def map_entity_chains_preserving_ambiguity(
    entity: RCSBEntityRecord,
    uniprot_records: Iterable[UniProtSequenceRecord],
    *,
    min_identity: float = 0.85,
    min_query_coverage: float = 0.9,
    ambiguity_margin: float = 0.02,
) -> tuple[ChainAmbiguityMapping, ...]:
    chain_ids = entity.chain_ids or ("",)
    records = tuple(uniprot_records)
    return tuple(
        map_chain_sequence_preserving_ambiguity(
            entity.sequence,
            records,
            pdb_id=entity.pdb_id,
            entity_id=entity.entity_id,
            chain_id=chain_id,
            provided_uniprot_ids=entity.uniprot_ids,
            min_identity=min_identity,
            min_query_coverage=min_query_coverage,
            ambiguity_margin=ambiguity_margin,
        )
        for chain_id in chain_ids
    )


def _merge_candidates(
    exact_mapping: ExactChainMapping,
    alignment_mapping: ChainUniProtMapping,
) -> tuple[ChainAmbiguityCandidate, ...]:
    merged: dict[str, ChainAmbiguityCandidate] = {}

    for candidate in exact_mapping.candidates:
        merged[candidate.accession.upper()] = ChainAmbiguityCandidate(
            accession=candidate.accession,
            entry_name=candidate.entry_name,
            source_backends=("exact_sequence_match",),
            exact_sequence_match=candidate.exact_sequence_match,
            query_length=candidate.query_length,
            target_length=candidate.target_length,
            is_reference_hint=candidate.is_reference_hint,
        )

    for candidate in alignment_mapping.candidates:
        accession = candidate.accession.upper()
        existing = merged.get(accession)
        source_backends: tuple[AmbiguityBackend, ...]
        if existing is None:
            source_backends = ("local_smith_waterman_fallback",)
            merged[accession] = ChainAmbiguityCandidate(
                accession=candidate.accession,
                entry_name=candidate.entry_name,
                source_backends=source_backends,
                exact_sequence_match=False,
                query_length=candidate.aligned_query_length,
                target_length=candidate.aligned_target_length,
                is_reference_hint=candidate.is_reference_hint,
                score=candidate.score,
                identity=candidate.identity,
                query_coverage=candidate.query_coverage,
                target_coverage=candidate.target_coverage,
            )
            continue

        merged[accession] = ChainAmbiguityCandidate(
            accession=existing.accession,
            entry_name=existing.entry_name or candidate.entry_name,
            source_backends=_merge_backends(
                existing.source_backends,
                "local_smith_waterman_fallback",
            ),
            exact_sequence_match=existing.exact_sequence_match or False,
            query_length=max(existing.query_length, candidate.aligned_query_length),
            target_length=max(existing.target_length, candidate.aligned_target_length),
            is_reference_hint=existing.is_reference_hint or candidate.is_reference_hint,
            score=candidate.score if candidate.score is not None else existing.score,
            identity=candidate.identity if candidate.identity is not None else existing.identity,
            query_coverage=(
                candidate.query_coverage
                if candidate.query_coverage is not None
                else existing.query_coverage
            ),
            target_coverage=(
                candidate.target_coverage
                if candidate.target_coverage is not None
                else existing.target_coverage
            ),
        )

    return tuple(sorted(merged.values(), key=_candidate_sort_key))


def _resolve_status(
    exact_mapping: ExactChainMapping,
    alignment_mapping: ChainUniProtMapping,
) -> tuple[AmbiguityStatus, str | None, str]:
    exact_unique = tuple(
        candidate
        for candidate in exact_mapping.candidates
        if candidate.exact_sequence_match
    )
    alignment_qualified = tuple(
        candidate
        for candidate in alignment_mapping.candidates
        if candidate.identity >= 0.85 and candidate.query_coverage >= 0.9
    )

    if exact_mapping.status == "ambiguous":
        return "ambiguous", None, exact_mapping.reason
    if alignment_mapping.status == "ambiguous":
        return "ambiguous", None, alignment_mapping.reason
    if exact_mapping.is_resolved:
        return "resolved", exact_mapping.resolved_accession, exact_mapping.reason
    if alignment_mapping.is_resolved:
        return "resolved", alignment_mapping.resolved_accession, alignment_mapping.reason
    if exact_unique or alignment_qualified:
        return "ambiguous", None, "preserved_candidate_set"
    return "unresolved", None, alignment_mapping.reason or exact_mapping.reason


def _candidate_sort_key(candidate: ChainAmbiguityCandidate) -> tuple[int, int, int, float, str]:
    return (
        -int(candidate.exact_sequence_match),
        -int(candidate.is_reference_hint),
        -int("exact_sequence_match" in candidate.source_backends),
        -(candidate.score if candidate.score is not None else 0.0),
        candidate.accession,
    )


def _merge_backends(
    existing: tuple[AmbiguityBackend, ...],
    backend: AmbiguityBackend,
) -> tuple[AmbiguityBackend, ...]:
    ordered: dict[AmbiguityBackend, None] = {value: None for value in existing}
    ordered.setdefault(backend, None)
    return tuple(ordered)


def _normalize_accessions(values: Sequence[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        accession = str(value or "").strip().upper()
        if accession:
            ordered.setdefault(accession, accession)
    return tuple(ordered.values())


def _normalized_sequence_length(sequence: str) -> int:
    return len("".join(str(sequence or "").strip().upper().split()))


__all__ = [
    "ChainAmbiguityCandidate",
    "ChainAmbiguityMapping",
    "map_chain_sequence_preserving_ambiguity",
    "map_entity_chains_preserving_ambiguity",
]
