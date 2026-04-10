from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from core.provenance.record import ProvenanceRecord


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _required_text(value: Any, field_name: str) -> str:
    text = _clean_text(value)
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


@dataclass(frozen=True, slots=True)
class ProvenanceLineageLink:
    parent_id: str
    child_id: str

    def __post_init__(self) -> None:
        parent_id = _required_text(self.parent_id, "parent_id")
        child_id = _required_text(self.child_id, "child_id")
        if parent_id == child_id:
            raise ValueError("parent_id and child_id must be different")
        object.__setattr__(self, "parent_id", parent_id)
        object.__setattr__(self, "child_id", child_id)

    def to_dict(self) -> dict[str, str]:
        return {
            "parent_id": self.parent_id,
            "child_id": self.child_id,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProvenanceLineageLink:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            parent_id=payload.get("parent_id") or payload.get("parent") or "",
            child_id=payload.get("child_id") or payload.get("child") or "",
        )


def _normalize_records(records: object) -> tuple[ProvenanceRecord, ...]:
    if isinstance(records, ProvenanceRecord):
        normalized_records = (records,)
    else:
        normalized_records = tuple(records or ())  # type: ignore[arg-type]
    for record in normalized_records:
        if not isinstance(record, ProvenanceRecord):
            raise TypeError("records must contain ProvenanceRecord instances")
    return tuple(sorted(normalized_records, key=lambda record: record.provenance_id))


def _build_links(records: tuple[ProvenanceRecord, ...]) -> tuple[ProvenanceLineageLink, ...]:
    links: list[ProvenanceLineageLink] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        for parent_id in record.parent_ids:
            edge = (parent_id, record.provenance_id)
            if edge in seen:
                continue
            seen.add(edge)
            links.append(ProvenanceLineageLink(*edge))
        for child_id in record.child_ids:
            edge = (record.provenance_id, child_id)
            if edge in seen:
                continue
            seen.add(edge)
            links.append(ProvenanceLineageLink(*edge))
    return tuple(links)


def _build_parent_index(
    links: tuple[ProvenanceLineageLink, ...],
) -> dict[str, tuple[str, ...]]:
    parents: dict[str, list[str]] = {}
    for link in links:
        parents.setdefault(link.child_id, []).append(link.parent_id)
    return {child_id: tuple(parent_ids) for child_id, parent_ids in parents.items()}


def _build_child_index(
    links: tuple[ProvenanceLineageLink, ...],
) -> dict[str, tuple[str, ...]]:
    children: dict[str, list[str]] = {}
    for link in links:
        children.setdefault(link.parent_id, []).append(link.child_id)
    return {parent_id: tuple(child_ids) for parent_id, child_ids in children.items()}


def _ordered_unique(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _walk_transitively(
    start_id: str,
    next_ids: Mapping[str, tuple[str, ...]],
) -> tuple[str, ...]:
    discovered: list[str] = []
    visited: set[str] = {start_id}
    queue: deque[str] = deque(next_ids.get(start_id, ()))

    while queue:
        current_id = queue.popleft()
        if current_id in visited:
            continue
        visited.add(current_id)
        discovered.append(current_id)
        for next_id in next_ids.get(current_id, ()):
            if next_id not in visited:
                queue.append(next_id)
    return tuple(discovered)


def _assert_closed_graph(
    records: tuple[ProvenanceRecord, ...],
    links: tuple[ProvenanceLineageLink, ...],
) -> None:
    record_ids = {record.provenance_id for record in records}
    missing_ids = sorted(
        {
            endpoint
            for link in links
            for endpoint in (link.parent_id, link.child_id)
            if endpoint not in record_ids
        }
    )
    if missing_ids:
        raise ValueError(
            "lineage references must resolve to known provenance records: "
            + ", ".join(missing_ids),
        )

    children_index = _build_child_index(links)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        if node_id in visiting:
            raise ValueError("lineage graph must be acyclic")
        visiting.add(node_id)
        for child_id in children_index.get(node_id, ()):
            visit(child_id)
        visiting.remove(node_id)
        visited.add(node_id)

    for record_id in sorted(record_ids):
        visit(record_id)


@dataclass(frozen=True, slots=True)
class ProvenanceLineage:
    records: tuple[ProvenanceRecord, ...] = field(default_factory=tuple)
    links: tuple[ProvenanceLineageLink, ...] = field(default_factory=tuple)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")

        records = _normalize_records(self.records)
        if len({record.provenance_id for record in records}) != len(records):
            raise ValueError("provenance_id values must be unique")

        derived_links = _build_links(records)
        explicit_links = tuple(
            link
            if isinstance(link, ProvenanceLineageLink)
            else ProvenanceLineageLink.from_dict(link)
            for link in (self.links or ())
        )
        if explicit_links and set(explicit_links) != set(derived_links):
            raise ValueError("links do not match the lineage implied by records")

        object.__setattr__(self, "records", records)
        object.__setattr__(self, "links", derived_links)
        _assert_closed_graph(records, derived_links)

    @property
    def record_ids(self) -> tuple[str, ...]:
        return tuple(record.provenance_id for record in self.records)

    @property
    def root_ids(self) -> tuple[str, ...]:
        parent_index = _build_parent_index(self.links)
        return tuple(
            record.provenance_id
            for record in self.records
            if record.provenance_id not in parent_index
        )

    @property
    def leaf_ids(self) -> tuple[str, ...]:
        child_index = _build_child_index(self.links)
        return tuple(
            record.provenance_id
            for record in self.records
            if record.provenance_id not in child_index
        )

    def has_record(self, provenance_id: str) -> bool:
        normalized_id = _required_text(provenance_id, "provenance_id")
        return any(record.provenance_id == normalized_id for record in self.records)

    def record(self, provenance_id: str) -> ProvenanceRecord:
        normalized_id = _required_text(provenance_id, "provenance_id")
        for record in self.records:
            if record.provenance_id == normalized_id:
                return record
        raise KeyError(normalized_id)

    def parent_ids_of(self, provenance_id: str) -> tuple[str, ...]:
        normalized_id = _required_text(provenance_id, "provenance_id")
        parent_index = _build_parent_index(self.links)
        return parent_index.get(normalized_id, ())

    def child_ids_of(self, provenance_id: str) -> tuple[str, ...]:
        normalized_id = _required_text(provenance_id, "provenance_id")
        child_index = _build_child_index(self.links)
        return child_index.get(normalized_id, ())

    def ancestor_ids_of(self, provenance_id: str) -> tuple[str, ...]:
        normalized_id = _required_text(provenance_id, "provenance_id")
        parent_index = _build_parent_index(self.links)
        return _walk_transitively(normalized_id, parent_index)

    def descendant_ids_of(self, provenance_id: str) -> tuple[str, ...]:
        normalized_id = _required_text(provenance_id, "provenance_id")
        child_index = _build_child_index(self.links)
        return _walk_transitively(normalized_id, child_index)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "records": [record.to_dict() for record in self.records],
            "links": [link.to_dict() for link in self.links],
        }

    @classmethod
    def from_records(
        cls,
        records: object,
        *,
        schema_version: int = 1,
    ) -> ProvenanceLineage:
        return cls(records=_normalize_records(records), schema_version=schema_version)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProvenanceLineage:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        records_payload = payload.get("records") or ()
        links_payload = payload.get("links") or ()
        return cls(
            records=tuple(ProvenanceRecord.from_dict(item) for item in records_payload),
            links=tuple(ProvenanceLineageLink.from_dict(item) for item in links_payload),
            schema_version=int(payload.get("schema_version") or 1),
        )


def validate_lineage_payload(payload: Mapping[str, Any]) -> ProvenanceLineage:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return ProvenanceLineage.from_dict(payload)


__all__ = [
    "ProvenanceLineage",
    "ProvenanceLineageLink",
    "validate_lineage_payload",
]
