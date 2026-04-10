from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from core.canonical.ligand import CanonicalLigand, validate_ligand_payload

LigandConflictStatus = Literal["resolved", "ambiguous", "unresolved"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalized_text(value: Any) -> str:
    return _clean_text(value).casefold()


def _source_key(ligand: CanonicalLigand) -> str:
    return f"{_normalized_text(ligand.source)}:{_normalized_text(ligand.source_id)}"


def _record_key(ligand: CanonicalLigand) -> tuple[str, str, str, str, str]:
    return (
        _normalized_text(ligand.ligand_id),
        _normalized_text(ligand.source),
        _normalized_text(ligand.source_id),
        _normalized_text(ligand.name),
        _normalized_text(ligand.inchikey or ligand.inchi or ligand.smiles),
    )


def _strong_keys(ligand: CanonicalLigand) -> tuple[str, ...]:
    keys = [f"ligand_id:{_normalized_text(ligand.ligand_id)}"]
    source_key = _source_key(ligand)
    if source_key != ":":
        keys.append(f"source_key:{source_key}")
    for field_name in ("smiles", "inchi", "inchikey"):
        value = _clean_text(getattr(ligand, field_name))
        if value:
            normalized = value.upper() if field_name == "inchikey" else value
            keys.append(f"{field_name}:{normalized}")
    return tuple(dict.fromkeys(keys))


def _synonym_keys(ligand: CanonicalLigand) -> tuple[str, ...]:
    keys: dict[str, str] = {}
    for candidate in (ligand.name, *ligand.synonyms):
        text = _clean_text(candidate)
        if text:
            keys[text.casefold()] = text
    return tuple(keys)


def _field_value(ligand: CanonicalLigand, field_name: str) -> str | int | None:
    value = getattr(ligand, field_name)
    if value is None:
        return None
    if field_name == "charge":
        return int(value)
    text = _clean_text(value)
    return text or None


def _ordered_unique(values: Iterable[Any]) -> tuple[str, ...]:
    seen: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            seen[text.casefold()] = text
    return tuple(seen.values())


def _merge_provenance(ligands: Iterable[CanonicalLigand]) -> tuple[str, ...]:
    provenance: dict[str, str] = {}
    for ligand in ligands:
        entries = ligand.provenance or (
            f"{_normalized_text(ligand.source)}:{_clean_text(ligand.source_id)}",
        )
        for entry in entries:
            text = _clean_text(entry)
            if text:
                provenance[text.casefold()] = text
    return tuple(sorted(provenance.values(), key=str.casefold))


def _field_conflicts(ligands: Iterable[CanonicalLigand]) -> tuple[str, ...]:
    conflicts: list[str] = []
    for field_name in ("smiles", "inchi", "inchikey", "formula", "charge"):
        values = {
            _field_value(ligand, field_name)
            for ligand in ligands
            if _field_value(ligand, field_name) is not None
        }
        if len(values) > 1:
            conflicts.append(field_name)
    return tuple(conflicts)


def _component_ids(ligands: Iterable[CanonicalLigand]) -> tuple[str, ...]:
    return _ordered_unique(ligand.ligand_id for ligand in ligands)


def _component_source_keys(ligands: Iterable[CanonicalLigand]) -> tuple[str, ...]:
    return _ordered_unique(_source_key(ligand) for ligand in ligands)


def _component_structure_keys(ligands: Iterable[CanonicalLigand]) -> tuple[str, ...]:
    keys: list[str] = []
    for ligand in ligands:
        for field_name in ("smiles", "inchi", "inchikey"):
            value = _clean_text(getattr(ligand, field_name))
            if value:
                normalized = value.upper() if field_name == "inchikey" else value
                keys.append(f"{field_name}:{normalized}")
    return _ordered_unique(keys)


def _component_synonym_keys(ligands: Iterable[CanonicalLigand]) -> tuple[str, ...]:
    keys: list[str] = []
    for ligand in ligands:
        keys.extend(_synonym_keys(ligand))
    return _ordered_unique(keys)


def _select_ligand_id(ligands: Iterable[CanonicalLigand]) -> str:
    ligand_ids = _ordered_unique(ligand.ligand_id for ligand in ligands)
    if not ligand_ids:
        return "ligand"
    return ligand_ids[0]


def _select_primary_name(ligands: tuple[CanonicalLigand, ...]) -> str:
    for ligand in ligands:
        name = _clean_text(ligand.name)
        if name:
            return name
    return _select_ligand_id(ligands)


def _merge_synonyms(ligands: Iterable[CanonicalLigand], *, primary_name: str) -> tuple[str, ...]:
    candidates: list[str] = [primary_name]
    for ligand in ligands:
        candidates.append(ligand.name)
        candidates.extend(ligand.synonyms)
    return _ordered_unique(candidates)


def _choose_source_metadata(
    ligands: tuple[CanonicalLigand, ...],
    ligand_id: str,
) -> tuple[str, str]:
    if len(ligands) == 1:
        ligand = ligands[0]
        return ligand.source, ligand.source_id
    return "CANONICAL", f"merge:{ligand_id}"


def _build_resolved_ligand(ligands: tuple[CanonicalLigand, ...]) -> CanonicalLigand:
    ligand_id = _select_ligand_id(ligands)
    primary_name = _select_primary_name(ligands)
    source, source_id = _choose_source_metadata(ligands, ligand_id)
    return CanonicalLigand(
        ligand_id=ligand_id,
        name=primary_name,
        source=source,
        source_id=source_id,
        smiles=_consensus_value(ligands, "smiles"),
        inchi=_consensus_value(ligands, "inchi"),
        inchikey=_consensus_value(ligands, "inchikey"),
        formula=_consensus_value(ligands, "formula"),
        charge=_consensus_charge(ligands),
        synonyms=_merge_synonyms(ligands, primary_name=primary_name),
        provenance=_merge_provenance(ligands),
    )


def _consensus_value(
    ligands: Iterable[CanonicalLigand],
    field_name: str,
) -> str | None:
    values = []
    for ligand in ligands:
        value = _field_value(ligand, field_name)
        if isinstance(value, str) and value:
            values.append(value)
    unique_values = tuple(dict.fromkeys(values))
    if not unique_values:
        return None
    return unique_values[0]


def _consensus_charge(ligands: Iterable[CanonicalLigand]) -> int | None:
    values = []
    for ligand in ligands:
        value = _field_value(ligand, "charge")
        if isinstance(value, int):
            values.append(value)
    unique_values = tuple(dict.fromkeys(values))
    if not unique_values:
        return None
    return unique_values[0]


def _records_from_input(
    records: Iterable[CanonicalLigand | Mapping[str, Any]],
) -> tuple[CanonicalLigand, ...]:
    ligands: list[CanonicalLigand] = []
    for record in records:
        if isinstance(record, CanonicalLigand):
            ligands.append(record)
            continue
        if isinstance(record, Mapping):
            ligands.append(validate_ligand_payload(dict(record)))
            continue
        raise TypeError("ligand records must be CanonicalLigand instances or mappings")
    return tuple(ligands)


def _component_indices(
    ligands: tuple[CanonicalLigand, ...],
) -> tuple[tuple[int, ...], ...]:
    if not ligands:
        return ()

    parent = list(range(len(ligands)))
    seen_keys: dict[str, int] = {}

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for index, ligand in enumerate(ligands):
        for key in _strong_keys(ligand):
            previous_index = seen_keys.get(key)
            if previous_index is None:
                seen_keys[key] = index
            else:
                union(index, previous_index)

    components: dict[int, list[int]] = {}
    for index in range(len(ligands)):
        root = find(index)
        components.setdefault(root, []).append(index)
    return tuple(tuple(indices) for indices in components.values())


@dataclass(frozen=True, slots=True)
class LigandConflictIssue:
    kind: str
    message: str
    identifiers: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    records: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "identifiers": list(self.identifiers),
            "fields": list(self.fields),
            "records": list(self.records),
        }


@dataclass(frozen=True, slots=True)
class LigandConflictResolution:
    status: LigandConflictStatus
    reason: str
    resolved_ligand: CanonicalLigand | None
    preserved_ligands: tuple[CanonicalLigand, ...]
    issues: tuple[LigandConflictIssue, ...] = ()
    observed_ligand_ids: tuple[str, ...] = ()
    observed_source_keys: tuple[str, ...] = ()
    observed_structure_keys: tuple[str, ...] = ()

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved" and self.resolved_ligand is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "resolved_ligand": (
                self.resolved_ligand.to_dict() if self.resolved_ligand is not None else None
            ),
            "preserved_ligands": [ligand.to_dict() for ligand in self.preserved_ligands],
            "issues": [issue.to_dict() for issue in self.issues],
            "observed_ligand_ids": list(self.observed_ligand_ids),
            "observed_source_keys": list(self.observed_source_keys),
            "observed_structure_keys": list(self.observed_structure_keys),
        }


def resolve_ligand_conflicts(
    records: Iterable[CanonicalLigand | Mapping[str, Any]],
) -> LigandConflictResolution:
    ligands = _records_from_input(records)
    if not ligands:
        return LigandConflictResolution(
            status="unresolved",
            reason="no_records",
            resolved_ligand=None,
            preserved_ligands=(),
            issues=(
                LigandConflictIssue(
                    kind="no_records",
                    message="no ligand observations were supplied",
                ),
            ),
        )

    ordered_ligands = tuple(sorted(ligands, key=_record_key))
    components = _component_indices(ordered_ligands)

    if len(components) > 1:
        component_synonyms = [
            _component_synonym_keys(ordered_ligands[index] for index in component)
            for component in components
        ]
        shared_synonyms = set(component_synonyms[0]).intersection(*component_synonyms[1:])
        if shared_synonyms:
            return LigandConflictResolution(
                status="ambiguous",
                reason="synonym_only_ambiguity",
                resolved_ligand=None,
                preserved_ligands=ordered_ligands,
                issues=(
                    LigandConflictIssue(
                        kind="synonym_only_ambiguity",
                        message=(
                            "records share only synonym or name evidence and cannot be "
                            "collapsed deterministically"
                        ),
                        identifiers=tuple(sorted(shared_synonyms, key=str.casefold)),
                    ),
                ),
                observed_ligand_ids=_component_ids(ordered_ligands),
                observed_source_keys=_component_source_keys(ordered_ligands),
                observed_structure_keys=_component_structure_keys(ordered_ligands),
            )

        return LigandConflictResolution(
            status="unresolved",
            reason="disconnected_candidate_set",
            resolved_ligand=None,
            preserved_ligands=ordered_ligands,
            issues=(
                LigandConflictIssue(
                    kind="disconnected_candidate_set",
                    message=(
                        "the provided observations do not form a single canonical ligand "
                        "cluster"
                    ),
                    identifiers=_component_ids(ordered_ligands),
                ),
            ),
            observed_ligand_ids=_component_ids(ordered_ligands),
            observed_source_keys=_component_source_keys(ordered_ligands),
            observed_structure_keys=_component_structure_keys(ordered_ligands),
        )

    component = tuple(ordered_ligands[index] for index in components[0])
    blocking_fields = _field_conflicts(component)
    ligand_ids = _component_ids(component)
    source_keys = _component_source_keys(component)
    structure_keys = _component_structure_keys(component)

    if blocking_fields:
        return LigandConflictResolution(
            status="unresolved",
            reason="identifier_collision",
            resolved_ligand=None,
            preserved_ligands=ordered_ligands,
            issues=(
                LigandConflictIssue(
                    kind="identifier_collision",
                    message=(
                        "records with the same canonical ligand cluster disagree on chemical "
                        "identity"
                    ),
                    identifiers=_component_ids(component),
                    fields=blocking_fields,
                    records=tuple(_source_key(ligand) for ligand in component),
                ),
            ),
            observed_ligand_ids=_component_ids(component),
            observed_source_keys=_component_source_keys(component),
            observed_structure_keys=_component_structure_keys(component),
        )

    if len(ligand_ids) > 1 and not structure_keys:
        return LigandConflictResolution(
            status="unresolved",
            reason="identifier_collision",
            resolved_ligand=None,
            preserved_ligands=ordered_ligands,
            issues=(
                LigandConflictIssue(
                    kind="identifier_collision",
                    message=(
                        "distinct ligand identifiers cannot be collapsed without a structural "
                        "anchor"
                    ),
                    identifiers=ligand_ids,
                    records=tuple(_source_key(ligand) for ligand in component),
                ),
            ),
            observed_ligand_ids=ligand_ids,
            observed_source_keys=source_keys,
            observed_structure_keys=structure_keys,
        )

    resolved_ligand = _build_resolved_ligand(component)
    issues: list[LigandConflictIssue] = []

    if len(ligand_ids) > 1 or len(source_keys) > 1:
        issues.append(
            LigandConflictIssue(
                kind="identifier_collision_resolved",
                message=(
                    "compatible ligand observations were merged while preserving the original "
                    "identifier trail"
                ),
                identifiers=ligand_ids or source_keys,
                fields=structure_keys,
                records=tuple(_source_key(ligand) for ligand in component),
            )
        )

    return LigandConflictResolution(
        status="resolved",
        reason="compatible_merge" if not issues else "identifier_collision_resolved",
        resolved_ligand=resolved_ligand,
        preserved_ligands=ordered_ligands,
        issues=tuple(issues),
        observed_ligand_ids=ligand_ids,
        observed_source_keys=source_keys,
        observed_structure_keys=structure_keys,
    )


__all__ = [
    "LigandConflictIssue",
    "LigandConflictResolution",
    "LigandConflictStatus",
    "resolve_ligand_conflicts",
]
