from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from connectors.rcsb.parsers import RCSBEntityRecord
from connectors.uniprot.parsers import UniProtSequenceRecord

ExactMappingStatus = Literal["resolved", "ambiguous", "unresolved"]
ExactMappingBackend = Literal["exact_sequence_match"]

EXACT_MAPPING_BACKEND: ExactMappingBackend = "exact_sequence_match"


@dataclass(frozen=True, slots=True)
class ExactChainMappingCandidate:
    accession: str
    entry_name: str
    exact_sequence_match: bool
    query_length: int
    target_length: int
    is_reference_hint: bool
    alignment_backend: ExactMappingBackend = EXACT_MAPPING_BACKEND


@dataclass(frozen=True, slots=True)
class ExactChainMapping:
    pdb_id: str | None
    entity_id: str | None
    chain_id: str | None
    status: ExactMappingStatus
    resolved_accession: str | None
    reason: str
    query_sequence_length: int
    provided_uniprot_ids: tuple[str, ...]
    candidates: tuple[ExactChainMappingCandidate, ...]
    alignment_backend: ExactMappingBackend = EXACT_MAPPING_BACKEND

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
            "alignment_backend": self.alignment_backend,
            "candidates": [
                {
                    "accession": candidate.accession,
                    "entry_name": candidate.entry_name,
                    "exact_sequence_match": candidate.exact_sequence_match,
                    "query_length": candidate.query_length,
                    "target_length": candidate.target_length,
                    "is_reference_hint": candidate.is_reference_hint,
                    "alignment_backend": candidate.alignment_backend,
                }
                for candidate in self.candidates
            ],
        }


def map_chain_sequence_exact(
    query_sequence: str,
    uniprot_records: Iterable[UniProtSequenceRecord],
    *,
    pdb_id: str | None = None,
    entity_id: str | None = None,
    chain_id: str | None = None,
    provided_uniprot_ids: Sequence[str] = (),
) -> ExactChainMapping:
    normalized_query = _normalize_sequence(query_sequence)
    normalized_hints = _normalize_accessions(provided_uniprot_ids)

    if not normalized_query:
        return ExactChainMapping(
            pdb_id=pdb_id,
            entity_id=entity_id,
            chain_id=chain_id,
            status="unresolved",
            resolved_accession=None,
            reason="empty_query_sequence",
            query_sequence_length=0,
            provided_uniprot_ids=normalized_hints,
            candidates=(),
        )

    candidates = tuple(
        _candidate_from_record(normalized_query, record, normalized_hints)
        for record in uniprot_records
    )
    exact_candidates = tuple(
        candidate
        for candidate in candidates
        if candidate.exact_sequence_match
    )

    if not exact_candidates:
        return ExactChainMapping(
            pdb_id=pdb_id,
            entity_id=entity_id,
            chain_id=chain_id,
            status="unresolved",
            resolved_accession=None,
            reason="no_exact_sequence_match",
            query_sequence_length=len(normalized_query),
            provided_uniprot_ids=normalized_hints,
            candidates=candidates,
        )

    hinted_exact = tuple(candidate for candidate in exact_candidates if candidate.is_reference_hint)
    if len(hinted_exact) == 1:
        winner = hinted_exact[0]
        return ExactChainMapping(
            pdb_id=pdb_id,
            entity_id=entity_id,
            chain_id=chain_id,
            status="resolved",
            resolved_accession=winner.accession,
            reason="exact_sequence_match_with_reference_hint",
            query_sequence_length=len(normalized_query),
            provided_uniprot_ids=normalized_hints,
            candidates=_sort_candidates(candidates),
        )

    if len(hinted_exact) > 1:
        return ExactChainMapping(
            pdb_id=pdb_id,
            entity_id=entity_id,
            chain_id=chain_id,
            status="ambiguous",
            resolved_accession=None,
            reason="multiple_reference_hint_exact_matches",
            query_sequence_length=len(normalized_query),
            provided_uniprot_ids=normalized_hints,
            candidates=_sort_candidates(candidates),
        )

    if len(exact_candidates) == 1:
        winner = exact_candidates[0]
        return ExactChainMapping(
            pdb_id=pdb_id,
            entity_id=entity_id,
            chain_id=chain_id,
            status="resolved",
            resolved_accession=winner.accession,
            reason="exact_sequence_match",
            query_sequence_length=len(normalized_query),
            provided_uniprot_ids=normalized_hints,
            candidates=_sort_candidates(candidates),
        )

    return ExactChainMapping(
        pdb_id=pdb_id,
        entity_id=entity_id,
        chain_id=chain_id,
        status="ambiguous",
        resolved_accession=None,
        reason="multiple_exact_sequence_matches",
        query_sequence_length=len(normalized_query),
        provided_uniprot_ids=normalized_hints,
        candidates=_sort_candidates(candidates),
    )


def map_entity_chains_exact(
    entity: RCSBEntityRecord,
    uniprot_records: Iterable[UniProtSequenceRecord],
) -> tuple[ExactChainMapping, ...]:
    chain_ids = entity.chain_ids or ("",)
    records = tuple(uniprot_records)
    return tuple(
        map_chain_sequence_exact(
            entity.sequence,
            records,
            pdb_id=entity.pdb_id,
            entity_id=entity.entity_id,
            chain_id=chain_id,
            provided_uniprot_ids=entity.uniprot_ids,
        )
        for chain_id in chain_ids
    )


def _candidate_from_record(
    query_sequence: str,
    record: UniProtSequenceRecord,
    reference_hints: Sequence[str],
) -> ExactChainMappingCandidate:
    normalized_target = _normalize_sequence(record.sequence)
    accession = record.accession.strip().upper()
    return ExactChainMappingCandidate(
        accession=record.accession,
        entry_name=record.entry_name,
        exact_sequence_match=bool(normalized_target) and normalized_target == query_sequence,
        query_length=len(query_sequence),
        target_length=len(normalized_target),
        is_reference_hint=accession in reference_hints,
    )


def _sort_candidates(
    candidates: Sequence[ExactChainMappingCandidate],
) -> tuple[ExactChainMappingCandidate, ...]:
    return tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                -int(candidate.exact_sequence_match),
                -int(candidate.is_reference_hint),
                candidate.accession,
            ),
        )
    )


def _normalize_accessions(values: Sequence[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        accession = str(value or "").strip().upper()
        if accession:
            ordered.setdefault(accession, accession)
    return tuple(ordered.values())


def _normalize_sequence(value: str) -> str:
    return "".join(str(value or "").strip().upper().split())


__all__ = [
    "EXACT_MAPPING_BACKEND",
    "ExactChainMapping",
    "ExactChainMappingCandidate",
    "map_chain_sequence_exact",
    "map_entity_chains_exact",
]
