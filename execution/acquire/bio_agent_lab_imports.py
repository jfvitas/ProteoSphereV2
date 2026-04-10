from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from execution.acquire.local_source_registry import (
    DEFAULT_LOCAL_SOURCE_ROOT,
    LocalSourceCategory,
    LocalSourceEntry,
    LocalSourceLoadHint,
    LocalSourceRegistry,
    LocalSourceStatus,
    build_default_local_source_registry,
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _dedupe_names(values: Sequence[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _normalize_source_names(values: Any) -> tuple[str, ...]:
    return _dedupe_names(tuple(str(item) for item in _iter_values(values)))


def _source_provenance(entry: LocalSourceEntry, registry: LocalSourceRegistry) -> dict[str, Any]:
    return {
        "registry_id": registry.registry_id,
        "storage_root": registry.storage_root,
        "source_name": entry.source_name,
        "category": entry.category,
        "status": entry.status,
        "candidate_root_count": len(entry.candidate_roots),
        "present_root_count": len(entry.present_roots),
        "missing_root_count": len(entry.missing_roots),
        "load_hints": list(entry.load_hints),
        "notes": list(entry.notes),
    }


@dataclass(frozen=True, slots=True)
class BioAgentLabImportSource:
    source_name: str
    category: LocalSourceCategory
    status: LocalSourceStatus
    candidate_roots: tuple[str, ...]
    present_roots: tuple[str, ...]
    missing_roots: tuple[str, ...]
    join_keys: tuple[str, ...]
    load_hints: tuple[LocalSourceLoadHint, ...]
    provenance: dict[str, Any]
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "category": self.category,
            "status": self.status,
            "candidate_roots": list(self.candidate_roots),
            "present_roots": list(self.present_roots),
            "missing_roots": list(self.missing_roots),
            "join_keys": list(self.join_keys),
            "load_hints": list(self.load_hints),
            "provenance": dict(self.provenance),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class BioAgentLabImportManifest:
    manifest_id: str
    storage_root: str
    registry_id: str
    sources: tuple[BioAgentLabImportSource, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "manifest_id", _clean_text(self.manifest_id))
        object.__setattr__(self, "storage_root", _clean_text(self.storage_root))
        object.__setattr__(self, "registry_id", _clean_text(self.registry_id))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.manifest_id:
            raise ValueError("manifest_id must not be empty")
        if not self.storage_root:
            raise ValueError("storage_root must not be empty")
        if not self.registry_id:
            raise ValueError("registry_id must not be empty")

        sources_by_name: dict[str, BioAgentLabImportSource] = {}
        for source in self.sources:
            if not isinstance(source, BioAgentLabImportSource):
                raise TypeError("sources must contain BioAgentLabImportSource objects")
            if source.source_name in sources_by_name:
                raise ValueError(f"duplicate source_name: {source.source_name}")
            sources_by_name[source.source_name] = source
        object.__setattr__(self, "sources", tuple(sources_by_name.values()))

    @property
    def source_count(self) -> int:
        return len(self.sources)

    @property
    def present_source_count(self) -> int:
        return sum(1 for source in self.sources if source.status == "present")

    @property
    def partial_source_count(self) -> int:
        return sum(1 for source in self.sources if source.status == "partial")

    @property
    def missing_source_count(self) -> int:
        return sum(1 for source in self.sources if source.status == "missing")

    @property
    def join_key_index(self) -> dict[str, tuple[str, ...]]:
        index: dict[str, list[str]] = {}
        for source in self.sources:
            for join_key in source.join_keys:
                index.setdefault(join_key, []).append(source.source_name)
        return {join_key: tuple(source_names) for join_key, source_names in index.items()}

    def get_source(self, source_name: str) -> BioAgentLabImportSource | None:
        normalized = _clean_text(source_name)
        for source in self.sources:
            if source.source_name == normalized:
                return source
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "storage_root": self.storage_root,
            "registry_id": self.registry_id,
            "source_count": self.source_count,
            "present_source_count": self.present_source_count,
            "partial_source_count": self.partial_source_count,
            "missing_source_count": self.missing_source_count,
            "join_key_index": {
                join_key: list(source_names)
                for join_key, source_names in self.join_key_index.items()
            },
            "sources": [source.to_dict() for source in self.sources],
            "notes": list(self.notes),
        }


def _resolve_sources(
    registry: LocalSourceRegistry,
    source_names: Sequence[str] | None,
) -> tuple[LocalSourceEntry, ...]:
    if source_names is None:
        return registry.entries

    resolved: list[LocalSourceEntry] = []
    for source_name in _normalize_source_names(source_names):
        entry = registry.get(source_name)
        if entry is None:
            raise KeyError(f"source_name not found in local registry: {source_name}")
        resolved.append(entry)
    return tuple(resolved)


def build_bio_agent_lab_import_manifest(
    storage_root: str | Path = DEFAULT_LOCAL_SOURCE_ROOT,
    *,
    registry: LocalSourceRegistry | None = None,
    source_names: Sequence[str] | None = None,
    manifest_id: str = "bio-agent-lab-import-manifest:v1",
    notes: Sequence[str] = (),
) -> BioAgentLabImportManifest:
    root = Path(storage_root)
    resolved_registry = registry or build_default_local_source_registry(root)
    sources = tuple(
        BioAgentLabImportSource(
            source_name=entry.source_name,
            category=entry.category,
            status=entry.status,
            candidate_roots=entry.candidate_roots,
            present_roots=entry.present_roots,
            missing_roots=entry.missing_roots,
            join_keys=entry.likely_join_anchors,
            load_hints=entry.load_hints,
            provenance=_source_provenance(entry, resolved_registry),
            notes=entry.notes,
        )
        for entry in _resolve_sources(resolved_registry, source_names)
    )
    return BioAgentLabImportManifest(
        manifest_id=manifest_id,
        storage_root=str(root),
        registry_id=resolved_registry.registry_id,
        sources=sources,
        notes=tuple(notes)
        + (
            "first-wave local corpora and metadata resolved from the local source registry",
            "missing roots remain explicit so downstream import planning stays truthful",
        ),
    )


DEFAULT_BIO_AGENT_LAB_IMPORT_MANIFEST = build_bio_agent_lab_import_manifest()


__all__ = [
    "BioAgentLabImportManifest",
    "BioAgentLabImportSource",
    "DEFAULT_BIO_AGENT_LAB_IMPORT_MANIFEST",
    "build_bio_agent_lab_import_manifest",
]
