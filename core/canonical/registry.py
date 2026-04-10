from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from core.canonical.assay import CanonicalAssay
from core.canonical.ligand import CanonicalLigand
from core.canonical.protein import CanonicalProtein

type EntityType = Literal["protein", "ligand", "assay"]
type CanonicalEntity = CanonicalProtein | CanonicalLigand | CanonicalAssay

_TYPE_ALIASES: dict[str, EntityType] = {
    "protein": "protein",
    "proteins": "protein",
    "canonicalprotein": "protein",
    "canonical_protein": "protein",
    "ligand": "ligand",
    "ligands": "ligand",
    "canonicalligand": "ligand",
    "canonical_ligand": "ligand",
    "assay": "assay",
    "assays": "assay",
    "canonicalassay": "assay",
    "canonical_assay": "assay",
}


def _normalize_reference(value: str) -> str:
    return value.strip()


def _normalize_reference_key(value: str) -> str:
    return _normalize_reference(value).casefold()


def _normalize_entity_type(value: str | None) -> EntityType | None:
    if value is None:
        return None
    normalized = value.strip().replace(" ", "_").replace("-", "_").casefold()
    entity_type = _TYPE_ALIASES.get(normalized)
    if entity_type is None:
        raise ValueError(f"unsupported entity_type: {value!r}")
    return entity_type


def _canonical_id_for(entity: CanonicalEntity) -> str:
    if isinstance(entity, CanonicalProtein):
        return entity.canonical_id
    if isinstance(entity, CanonicalLigand):
        return f"ligand:{entity.ligand_id}"
    if isinstance(entity, CanonicalAssay):
        return entity.canonical_id
    raise TypeError(f"unsupported entity type: {type(entity)!r}")


def _entity_type_for(entity: CanonicalEntity) -> EntityType:
    if isinstance(entity, CanonicalProtein):
        return "protein"
    if isinstance(entity, CanonicalLigand):
        return "ligand"
    if isinstance(entity, CanonicalAssay):
        return "assay"
    raise TypeError(f"unsupported entity type: {type(entity)!r}")


def _stable_aliases(entity: CanonicalEntity) -> tuple[str, ...]:
    canonical_id = _canonical_id_for(entity)
    aliases: list[str] = [canonical_id]
    if isinstance(entity, CanonicalProtein):
        aliases.extend(
            [
                entity.accession,
                f"uniprot:{entity.accession}",
                entity.canonical_protein_id,
            ]
        )
    elif isinstance(entity, CanonicalLigand):
        aliases.extend(
            [
                entity.ligand_id,
                f"{entity.source.casefold()}:{entity.source_id}",
            ]
        )
        if entity.inchikey:
            aliases.append(entity.inchikey)
    elif isinstance(entity, CanonicalAssay):
        aliases.extend(
            [
                entity.assay_id,
                entity.canonical_assay_id,
                f"{entity.source.casefold()}:{entity.source_id}",
            ]
        )
    return tuple(dict.fromkeys(alias for alias in aliases if _normalize_reference(alias)))


@dataclass(frozen=True, slots=True)
class UnresolvedCanonicalReference:
    reference: str
    entity_type: EntityType | None = None
    reason: str = "missing"
    candidates: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        reference = _normalize_reference(self.reference)
        if not reference:
            reference = "<empty>"
        object.__setattr__(self, "reference", reference)
        object.__setattr__(self, "entity_type", _normalize_entity_type(self.entity_type))
        object.__setattr__(self, "reason", self.reason.strip() or "missing")
        object.__setattr__(self, "candidates", tuple(dict.fromkeys(self.candidates)))

    @property
    def is_ambiguous(self) -> bool:
        return self.reason == "ambiguous"

    def to_dict(self) -> dict[str, object]:
        return {
            "reference": self.reference,
            "entity_type": self.entity_type,
            "reason": self.reason,
            "candidates": list(self.candidates),
        }


class CanonicalEntityRegistry:
    """Conservative registry for canonical entity references."""

    def __init__(
        self,
        *,
        proteins: Iterable[CanonicalProtein] = (),
        ligands: Iterable[CanonicalLigand] = (),
        assays: Iterable[CanonicalAssay] = (),
    ) -> None:
        self._entities: dict[EntityType, dict[str, CanonicalEntity]] = {
            "protein": {},
            "ligand": {},
            "assay": {},
        }
        self._aliases: dict[EntityType, dict[str, str]] = {
            "protein": {},
            "ligand": {},
            "assay": {},
        }
        self._ambiguous_aliases: dict[EntityType, dict[str, tuple[str, ...]]] = {
            "protein": {},
            "ligand": {},
            "assay": {},
        }
        self.register_many(proteins)
        self.register_many(ligands)
        self.register_many(assays)

    def register_many(self, entities: Iterable[CanonicalEntity]) -> None:
        for entity in entities:
            self.register(entity)

    def register(self, entity: CanonicalEntity) -> str:
        entity_type = _entity_type_for(entity)
        canonical_id = _canonical_id_for(entity)
        existing = self._entities[entity_type].get(canonical_id)
        if existing is not None:
            if existing != entity:
                raise ValueError(
                    f"conflicting {entity_type} registration for canonical id {canonical_id}"
                )
            return canonical_id

        self._entities[entity_type][canonical_id] = entity
        for alias in _stable_aliases(entity):
            self._register_alias(entity_type, alias, canonical_id)
        return canonical_id

    def canonical_reference(self, entity: CanonicalEntity) -> str:
        return _canonical_id_for(entity)

    def get(self, entity_type: str, reference: str) -> CanonicalEntity | None:
        resolved = self.resolve(reference, entity_type=entity_type)
        if isinstance(resolved, UnresolvedCanonicalReference):
            return None
        return resolved

    def require(self, reference: str, *, entity_type: str | None = None) -> CanonicalEntity:
        resolved = self.resolve(reference, entity_type=entity_type)
        if isinstance(resolved, UnresolvedCanonicalReference):
            target = resolved.entity_type or "entity"
            raise KeyError(
                f"could not resolve {target} reference {resolved.reference!r}: {resolved.reason}"
            )
        return resolved

    def resolve(
        self,
        reference: str | CanonicalEntity | UnresolvedCanonicalReference,
        *,
        entity_type: str | None = None,
    ) -> CanonicalEntity | UnresolvedCanonicalReference:
        if isinstance(reference, UnresolvedCanonicalReference):
            return reference
        if isinstance(reference, (CanonicalProtein, CanonicalLigand, CanonicalAssay)):
            return reference

        raw_reference = _normalize_reference(str(reference))
        normalized_entity_type = _normalize_entity_type(entity_type)
        if not raw_reference:
            return UnresolvedCanonicalReference(
                "<empty>",
                entity_type=normalized_entity_type,
                reason="empty_reference",
            )

        resolved_matches: list[CanonicalEntity] = []
        candidate_ids: list[str] = []
        search_types = (
            (normalized_entity_type,)
            if normalized_entity_type is not None
            else ("protein", "ligand", "assay")
        )

        for search_type in search_types:
            matches = self._resolve_candidates(search_type, raw_reference)
            if not matches:
                continue
            candidate_ids.extend(_canonical_id_for(match) for match in matches)
            resolved_matches.extend(matches)

        unique_matches = {
            (_entity_type_for(match), _canonical_id_for(match)): match for match in resolved_matches
        }
        if len(unique_matches) == 1:
            return next(iter(unique_matches.values()))
        if unique_matches:
            return UnresolvedCanonicalReference(
                raw_reference,
                entity_type=normalized_entity_type,
                reason="ambiguous",
                candidates=tuple(dict.fromkeys(candidate_ids)),
            )
        return UnresolvedCanonicalReference(
            raw_reference,
            entity_type=normalized_entity_type,
            reason="missing",
        )

    def list_entities(self, entity_type: str) -> tuple[CanonicalEntity, ...]:
        normalized_entity_type = _normalize_entity_type(entity_type)
        if normalized_entity_type is None:
            raise ValueError("entity_type is required")
        return tuple(self._entities[normalized_entity_type].values())

    def _register_alias(self, entity_type: EntityType, alias: str, canonical_id: str) -> None:
        key = _normalize_reference_key(alias)
        if not key:
            return
        ambiguous = self._ambiguous_aliases[entity_type].get(key)
        if ambiguous is not None:
            if canonical_id not in ambiguous:
                self._ambiguous_aliases[entity_type][key] = tuple(
                    sorted((*ambiguous, canonical_id))
                )
            return

        current = self._aliases[entity_type].get(key)
        if current is None:
            self._aliases[entity_type][key] = canonical_id
            return
        if current == canonical_id:
            return

        self._aliases[entity_type].pop(key, None)
        self._ambiguous_aliases[entity_type][key] = tuple(sorted((current, canonical_id)))

    def _resolve_candidates(
        self,
        entity_type: EntityType,
        reference: str,
    ) -> tuple[CanonicalEntity, ...]:
        key = _normalize_reference_key(reference)
        if not key:
            return ()

        ambiguous_ids = self._ambiguous_aliases[entity_type].get(key)
        if ambiguous_ids is not None:
            return tuple(
                self._entities[entity_type][canonical_id] for canonical_id in ambiguous_ids
            )

        canonical_id = self._aliases[entity_type].get(key)
        if canonical_id is None:
            return ()
        return (self._entities[entity_type][canonical_id],)


__all__ = [
    "CanonicalEntity",
    "CanonicalEntityRegistry",
    "EntityType",
    "UnresolvedCanonicalReference",
]
