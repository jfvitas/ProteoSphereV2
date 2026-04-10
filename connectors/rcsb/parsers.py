from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


class RCSBParserError(ValueError):
    """Raised when an RCSB payload cannot be normalized."""


def _normalize_pdb_id(pdb_id: str | None) -> str:
    value = str(pdb_id or "").strip().upper()
    if len(value) != 4 or not value.isalnum():
        raise RCSBParserError("payload does not contain a valid PDB identifier")
    return value


def _normalize_id(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text or not text.isdigit():
        raise RCSBParserError(f"payload does not contain a valid {field_name}")
    return text


def _unique_strings(values: Iterable[Any]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for value in values:
        text = str(value or "").strip()
        if text:
            seen[text] = None
    return tuple(seen)


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
        return _unique_strings(value)
    return _unique_strings([value])


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
        elif value not in (None, ""):
            return str(value)
    return ""


def _normalize_structure_pdb_id(payload: dict[str, Any], identifiers: dict[str, Any]) -> str:
    return _normalize_pdb_id(
        _first_non_empty(
            identifiers.get("entry_id"),
            payload.get("entry_id"),
            payload.get("rcsb_id"),
            payload.get("id"),
        )
    )


def _dig(payload: dict[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class RCSBEntryRecord:
    pdb_id: str
    title: str
    experimental_methods: tuple[str, ...]
    resolution: float | None
    release_date: str
    assembly_ids: tuple[str, ...]
    polymer_entity_ids: tuple[str, ...]
    nonpolymer_entity_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RCSBEntityRecord:
    pdb_id: str
    entity_id: str
    description: str
    polymer_type: str
    sequence: str
    sequence_length: int | None
    chain_ids: tuple[str, ...]
    uniprot_ids: tuple[str, ...]
    organism_names: tuple[str, ...]
    taxonomy_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RCSBAssemblyRecord:
    pdb_id: str
    assembly_id: str
    method: str
    oligomeric_state: str
    oligomeric_count: int | None
    stoichiometry: str
    chain_ids: tuple[str, ...]
    polymer_entity_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RCSBStructureBundle:
    entry: RCSBEntryRecord
    entities: tuple[RCSBEntityRecord, ...]
    assemblies: tuple[RCSBAssemblyRecord, ...]

    @property
    def pdb_id(self) -> str:
        return self.entry.pdb_id

    @property
    def chain_to_entity_ids(self) -> dict[str, tuple[str, ...]]:
        mapping: dict[str, list[str]] = {}
        for entity in self.entities:
            for chain_id in entity.chain_ids:
                mapping.setdefault(chain_id, []).append(entity.entity_id)
        return {chain_id: tuple(entity_ids) for chain_id, entity_ids in mapping.items()}


def parse_entry(payload: dict[str, Any]) -> RCSBEntryRecord:
    if not isinstance(payload, dict):
        raise RCSBParserError("entry payload must be a mapping")

    pdb_id = _normalize_pdb_id(
        payload.get("rcsb_id") or payload.get("entry_id") or payload.get("id")
    )
    title = _first_non_empty(
        _dig(payload, "struct", "title"),
        _dig(payload, "struct_keywords", "pdbx_keywords"),
        _dig(payload, "struct_keywords", "text"),
    )
    methods = _as_tuple(
        _dig(payload, "rcsb_entry_info", "experimental_method")
        or _dig(payload, "exptl", "method")
    )
    resolution = _optional_float(
        _first_non_empty(
            (_dig(payload, "rcsb_entry_info", "resolution_combined") or [None])[0]
            if isinstance(_dig(payload, "rcsb_entry_info", "resolution_combined"), list)
            else _dig(payload, "rcsb_entry_info", "resolution_combined"),
            _dig(payload, "refine", "ls_d_res_high"),
        )
    )
    release_date = _first_non_empty(
        _dig(payload, "rcsb_accession_info", "initial_release_date"),
        _dig(payload, "rcsb_accession_info", "deposit_date"),
    )
    identifiers = payload.get("rcsb_entry_container_identifiers") or {}
    assembly_ids = _as_tuple(identifiers.get("assembly_ids"))
    polymer_entity_ids = _as_tuple(identifiers.get("polymer_entity_ids"))
    nonpolymer_entity_ids = _as_tuple(identifiers.get("nonpolymer_entity_ids"))
    return RCSBEntryRecord(
        pdb_id=pdb_id,
        title=title,
        experimental_methods=methods,
        resolution=resolution,
        release_date=release_date,
        assembly_ids=assembly_ids,
        polymer_entity_ids=polymer_entity_ids,
        nonpolymer_entity_ids=nonpolymer_entity_ids,
    )


def parse_entity(payload: dict[str, Any]) -> RCSBEntityRecord:
    if not isinstance(payload, dict):
        raise RCSBParserError("entity payload must be a mapping")

    identifiers = payload.get("rcsb_polymer_entity_container_identifiers") or {}
    pdb_id = _normalize_structure_pdb_id(payload, identifiers)
    entity_id = _normalize_id(
        identifiers.get("entity_id") or payload.get("entity", {}).get("id"),
        field_name="entity_id",
    )
    entity = payload.get("entity") or {}
    polymer = payload.get("entity_poly") or {}
    sources = payload.get("rcsb_entity_source_organism") or []
    if isinstance(sources, dict):
        sources = [sources]
    return RCSBEntityRecord(
        pdb_id=pdb_id,
        entity_id=entity_id,
        description=_first_non_empty(
            entity.get("pdbx_description"),
            entity.get("description"),
            polymer.get("pdbx_description"),
        ),
        polymer_type=_first_non_empty(
            polymer.get("type"),
            polymer.get("rcsb_entity_polymer_type"),
            entity.get("type"),
        ),
        sequence=_first_non_empty(
            polymer.get("pdbx_seq_one_letter_code_can"),
            polymer.get("pdbx_seq_one_letter_code"),
        ),
        sequence_length=_optional_int(
            polymer.get("rcsb_sample_sequence_length")
            or polymer.get("entity_poly_seq_length")
        ),
        chain_ids=_as_tuple(identifiers.get("auth_asym_ids")),
        uniprot_ids=_as_tuple(identifiers.get("uniprot_ids")),
        organism_names=_as_tuple(
            source.get("scientific_name") or source.get("tax_id")
            for source in sources
        ),
        taxonomy_ids=_as_tuple(
            source.get("ncbi_taxonomy_id") or source.get("taxonomy_id")
            for source in sources
        ),
    )


def parse_assembly(payload: dict[str, Any]) -> RCSBAssemblyRecord:
    if not isinstance(payload, dict):
        raise RCSBParserError("assembly payload must be a mapping")

    identifiers = payload.get("rcsb_assembly_container_identifiers") or {}
    pdb_id = _normalize_structure_pdb_id(payload, identifiers)
    info = payload.get("rcsb_assembly_info") or {}
    return RCSBAssemblyRecord(
        pdb_id=pdb_id,
        assembly_id=_normalize_id(
            identifiers.get("assembly_id") or payload.get("id"),
            field_name="assembly_id",
        ),
        method=_first_non_empty(payload.get("method"), info.get("method"), payload.get("details")),
        oligomeric_state=_first_non_empty(
            info.get("oligomeric_state"),
            payload.get("oligomeric_state"),
        ),
        oligomeric_count=_optional_int(
            info.get("oligomeric_count") or payload.get("oligomeric_count")
        ),
        stoichiometry=_first_non_empty(info.get("stoichiometry"), payload.get("stoichiometry")),
        chain_ids=_as_tuple(identifiers.get("auth_asym_ids")),
        polymer_entity_ids=_as_tuple(identifiers.get("polymer_entity_ids")),
    )


def parse_structure_bundle(
    entry_payload: dict[str, Any],
    entity_payloads: Iterable[dict[str, Any]],
    assembly_payloads: Iterable[dict[str, Any]],
) -> RCSBStructureBundle:
    entry = parse_entry(entry_payload)
    entities = tuple(parse_entity(payload) for payload in entity_payloads)
    assemblies = tuple(parse_assembly(payload) for payload in assembly_payloads)
    return RCSBStructureBundle(entry=entry, entities=entities, assemblies=assemblies)
