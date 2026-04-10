"""Conservative chain-to-UniProt mapper with explicit local-backend provenance.

The lockdown specification calls for MMseqs2 alignment, but this slice only
provides a local Smith-Waterman fallback. The public mapping contract records
that fact explicitly instead of implying MMseqs2-backed behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from connectors.rcsb.parsers import RCSBEntityRecord
from connectors.uniprot.parsers import UniProtSequenceRecord

MappingStatus = Literal["resolved", "ambiguous", "unresolved"]
AlignmentBackend = Literal["local_smith_waterman_fallback"]

_MATCH_SCORE = 2
_MISMATCH_SCORE = -1
_GAP_SCORE = -2
_DEFAULT_MIN_IDENTITY = 0.85
_DEFAULT_MIN_QUERY_COVERAGE = 0.9
_DEFAULT_AMBIGUITY_MARGIN = 0.02
ALIGNMENT_BACKEND: AlignmentBackend = "local_smith_waterman_fallback"


@dataclass(frozen=True, slots=True)
class ChainAlignmentCandidate:
    accession: str
    entry_name: str
    alignment_backend: AlignmentBackend
    score: int
    identity: float
    query_coverage: float
    target_coverage: float
    aligned_query_length: int
    aligned_target_length: int
    is_reference_hint: bool


@dataclass(frozen=True, slots=True)
class ChainUniProtMapping:
    pdb_id: str | None
    entity_id: str | None
    chain_id: str | None
    status: MappingStatus
    alignment_backend: AlignmentBackend
    resolved_accession: str | None
    reason: str
    query_sequence_length: int
    provided_uniprot_ids: tuple[str, ...]
    candidates: tuple[ChainAlignmentCandidate, ...]

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved" and self.resolved_accession is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "pdb_id": self.pdb_id,
            "entity_id": self.entity_id,
            "chain_id": self.chain_id,
            "status": self.status,
            "alignment_backend": self.alignment_backend,
            "resolved_accession": self.resolved_accession,
            "reason": self.reason,
            "query_sequence_length": self.query_sequence_length,
            "provided_uniprot_ids": list(self.provided_uniprot_ids),
            "candidates": [
                {
                    "accession": candidate.accession,
                    "entry_name": candidate.entry_name,
                    "alignment_backend": candidate.alignment_backend,
                    "score": candidate.score,
                    "identity": candidate.identity,
                    "query_coverage": candidate.query_coverage,
                    "target_coverage": candidate.target_coverage,
                    "aligned_query_length": candidate.aligned_query_length,
                    "aligned_target_length": candidate.aligned_target_length,
                    "is_reference_hint": candidate.is_reference_hint,
                }
                for candidate in self.candidates
            ],
        }


@dataclass(frozen=True, slots=True)
class _AlignmentTrace:
    score: int
    alignment_length: int
    matches: int
    aligned_query_length: int
    aligned_target_length: int


def map_chain_sequence_to_uniprot(
    query_sequence: str,
    uniprot_records: Iterable[UniProtSequenceRecord],
    *,
    pdb_id: str | None = None,
    entity_id: str | None = None,
    chain_id: str | None = None,
    provided_uniprot_ids: Sequence[str] = (),
    min_identity: float = _DEFAULT_MIN_IDENTITY,
    min_query_coverage: float = _DEFAULT_MIN_QUERY_COVERAGE,
    ambiguity_margin: float = _DEFAULT_AMBIGUITY_MARGIN,
) -> ChainUniProtMapping:
    normalized_query = _normalize_sequence(query_sequence)
    normalized_hints = tuple(_normalize_accessions(provided_uniprot_ids))

    if not normalized_query:
        return ChainUniProtMapping(
            pdb_id=pdb_id,
            entity_id=entity_id,
            chain_id=chain_id,
            status="unresolved",
            alignment_backend=ALIGNMENT_BACKEND,
            resolved_accession=None,
            reason="empty_query_sequence",
            query_sequence_length=0,
            provided_uniprot_ids=normalized_hints,
            candidates=(),
        )

    candidates = tuple(
        sorted(
            (
                _score_candidate(
                    normalized_query,
                    record,
                    reference_hints=normalized_hints,
                )
                for record in uniprot_records
            ),
            key=_candidate_sort_key,
        )
    )

    if not candidates:
        return ChainUniProtMapping(
            pdb_id=pdb_id,
            entity_id=entity_id,
            chain_id=chain_id,
            status="unresolved",
            alignment_backend=ALIGNMENT_BACKEND,
            resolved_accession=None,
            reason="no_candidate_sequences",
            query_sequence_length=len(normalized_query),
            provided_uniprot_ids=normalized_hints,
            candidates=(),
        )

    qualified = tuple(
        candidate
        for candidate in candidates
        if candidate.identity >= min_identity and candidate.query_coverage >= min_query_coverage
    )

    if not qualified:
        return ChainUniProtMapping(
            pdb_id=pdb_id,
            entity_id=entity_id,
            chain_id=chain_id,
            status="unresolved",
            alignment_backend=ALIGNMENT_BACKEND,
            resolved_accession=None,
            reason="no_alignment_passed_thresholds",
            query_sequence_length=len(normalized_query),
            provided_uniprot_ids=normalized_hints,
            candidates=candidates,
        )

    winner = qualified[0]
    runner_up = qualified[1] if len(qualified) > 1 else None
    if runner_up is not None and _is_ambiguous(
        winner,
        runner_up,
        query_length=len(normalized_query),
        ambiguity_margin=ambiguity_margin,
    ):
        return ChainUniProtMapping(
            pdb_id=pdb_id,
            entity_id=entity_id,
            chain_id=chain_id,
            status="ambiguous",
            alignment_backend=ALIGNMENT_BACKEND,
            resolved_accession=None,
            reason="ambiguous_top_alignment",
            query_sequence_length=len(normalized_query),
            provided_uniprot_ids=normalized_hints,
            candidates=candidates,
        )

    return ChainUniProtMapping(
        pdb_id=pdb_id,
        entity_id=entity_id,
        chain_id=chain_id,
        status="resolved",
        alignment_backend=ALIGNMENT_BACKEND,
        resolved_accession=winner.accession,
        reason="alignment_resolved",
        query_sequence_length=len(normalized_query),
        provided_uniprot_ids=normalized_hints,
        candidates=candidates,
    )


def map_entity_chains_to_uniprot(
    entity: RCSBEntityRecord,
    uniprot_records: Iterable[UniProtSequenceRecord],
    *,
    min_identity: float = _DEFAULT_MIN_IDENTITY,
    min_query_coverage: float = _DEFAULT_MIN_QUERY_COVERAGE,
    ambiguity_margin: float = _DEFAULT_AMBIGUITY_MARGIN,
) -> tuple[ChainUniProtMapping, ...]:
    chain_ids = entity.chain_ids or ("",)
    records = tuple(uniprot_records)
    return tuple(
        map_chain_sequence_to_uniprot(
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


def _candidate_sort_key(
    candidate: ChainAlignmentCandidate,
) -> tuple[float, float, float, float, str]:
    return (
        -float(candidate.score),
        -candidate.identity,
        -candidate.query_coverage,
        -candidate.target_coverage,
        candidate.accession,
    )


def _score_candidate(
    query_sequence: str,
    record: UniProtSequenceRecord,
    *,
    reference_hints: Sequence[str],
) -> ChainAlignmentCandidate:
    normalized_target = _normalize_sequence(record.sequence)
    trace = _smith_waterman(query_sequence, normalized_target)
    identity = trace.matches / trace.alignment_length if trace.alignment_length else 0.0
    query_coverage = trace.aligned_query_length / len(query_sequence) if query_sequence else 0.0
    target_coverage = (
        trace.aligned_target_length / len(normalized_target) if normalized_target else 0.0
    )
    return ChainAlignmentCandidate(
        accession=record.accession,
        entry_name=record.entry_name,
        alignment_backend=ALIGNMENT_BACKEND,
        score=trace.score,
        identity=identity,
        query_coverage=query_coverage,
        target_coverage=target_coverage,
        aligned_query_length=trace.aligned_query_length,
        aligned_target_length=trace.aligned_target_length,
        is_reference_hint=record.accession.upper() in reference_hints,
    )


def _is_ambiguous(
    winner: ChainAlignmentCandidate,
    runner_up: ChainAlignmentCandidate,
    *,
    query_length: int,
    ambiguity_margin: float,
) -> bool:
    score_margin = max(1, query_length // 20)
    return (
        winner.score - runner_up.score <= score_margin
        and abs(winner.identity - runner_up.identity) <= ambiguity_margin
        and abs(winner.query_coverage - runner_up.query_coverage) <= ambiguity_margin
    )


def _smith_waterman(query_sequence: str, target_sequence: str) -> _AlignmentTrace:
    if not query_sequence or not target_sequence:
        return _AlignmentTrace(0, 0, 0, 0, 0)

    query_length = len(query_sequence)
    target_length = len(target_sequence)
    scores = [[0] * (target_length + 1) for _ in range(query_length + 1)]
    trace = [[0] * (target_length + 1) for _ in range(query_length + 1)]

    best_score = 0
    best_position = (0, 0)

    for query_index in range(1, query_length + 1):
        query_residue = query_sequence[query_index - 1]
        for target_index in range(1, target_length + 1):
            target_residue = target_sequence[target_index - 1]
            diagonal = scores[query_index - 1][target_index - 1] + (
                _MATCH_SCORE if query_residue == target_residue else _MISMATCH_SCORE
            )
            up = scores[query_index - 1][target_index] + _GAP_SCORE
            left = scores[query_index][target_index - 1] + _GAP_SCORE

            best_cell_score = 0
            direction = 0
            if diagonal >= up and diagonal >= left and diagonal > 0:
                best_cell_score = diagonal
                direction = 1
            elif up >= left and up > 0:
                best_cell_score = up
                direction = 2
            elif left > 0:
                best_cell_score = left
                direction = 3

            scores[query_index][target_index] = best_cell_score
            trace[query_index][target_index] = direction

            if best_cell_score > best_score:
                best_score = best_cell_score
                best_position = (query_index, target_index)

    if best_score == 0:
        return _AlignmentTrace(0, 0, 0, 0, 0)

    alignment_length = 0
    matches = 0
    aligned_query_length = 0
    aligned_target_length = 0
    query_index, target_index = best_position

    while query_index > 0 and target_index > 0 and scores[query_index][target_index] > 0:
        direction = trace[query_index][target_index]
        if direction == 1:
            alignment_length += 1
            aligned_query_length += 1
            aligned_target_length += 1
            if query_sequence[query_index - 1] == target_sequence[target_index - 1]:
                matches += 1
            query_index -= 1
            target_index -= 1
            continue
        if direction == 2:
            alignment_length += 1
            aligned_query_length += 1
            query_index -= 1
            continue
        if direction == 3:
            alignment_length += 1
            aligned_target_length += 1
            target_index -= 1
            continue
        break

    return _AlignmentTrace(
        score=best_score,
        alignment_length=alignment_length,
        matches=matches,
        aligned_query_length=aligned_query_length,
        aligned_target_length=aligned_target_length,
    )


def _normalize_accessions(accessions: Sequence[str]) -> Iterable[str]:
    seen: dict[str, None] = {}
    for accession in accessions:
        normalized = str(accession or "").strip().upper()
        if normalized:
            seen[normalized] = None
    return tuple(seen)


def _normalize_sequence(sequence: str | None) -> str:
    return "".join(
        character for character in str(sequence or "").upper() if not character.isspace()
    )
