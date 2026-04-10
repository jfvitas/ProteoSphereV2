from __future__ import annotations

import hashlib
import json
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from execution.acquire.local_source_registry import (
    DEFAULT_LOCAL_SOURCE_REGISTRY,
    LocalSourceEntry,
    LocalSourceRegistry,
)

DEFAULT_SAMPLE_LIMIT = 4
DEFAULT_PREFIX_HASH_BYTES = 1_048_576
DEFAULT_REPORT_ID = "local-corpus-fingerprint-report:v1"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, list | tuple):  # type: ignore[arg-type]
        return tuple(values)
    return (values,)


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _json_ready(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _stable_checksum(payload: dict[str, Any]) -> str:
    blob = json.dumps(_json_ready(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _path_string(path: Path) -> str:
    return str(path).replace("\\", "/")


def _file_hash(path: Path, *, prefix_bytes: int = DEFAULT_PREFIX_HASH_BYTES) -> tuple[str, str]:
    hasher = hashlib.sha256()
    size = path.stat().st_size
    hash_mode = "full"

    with path.open("rb") as handle:
        if size > prefix_bytes:
            hash_mode = f"prefix:{prefix_bytes}"
            remaining = prefix_bytes
            while remaining > 0:
                chunk = handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                hasher.update(chunk)
                remaining -= len(chunk)
        else:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)

    return hash_mode, hasher.hexdigest()


def _walk_sample_files(root: Path, *, limit: int) -> tuple[Path, ...]:
    if limit <= 0:
        return ()
    if root.is_file():
        return (root,)
    if not root.is_dir():
        return ()

    sampled: list[Path] = []
    queue: deque[Path] = deque([root])
    while queue and len(sampled) < limit:
        current = queue.popleft()
        try:
            entries = sorted(
                os.scandir(current),
                key=lambda entry: entry.name.casefold(),
            )
        except OSError:
            continue
        child_dirs: list[Path] = []
        for entry in entries:
            try:
                if entry.is_file(follow_symlinks=False):
                    sampled.append(Path(entry.path))
                    if len(sampled) >= limit:
                        break
                elif entry.is_dir(follow_symlinks=False):
                    child_dirs.append(Path(entry.path))
            except OSError:
                continue
        queue.extend(child_dirs)
    return tuple(sampled)


def _sample_roots(
    roots: tuple[str, ...],
    *,
    limit: int,
) -> tuple[Path, ...]:
    sampled: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        if len(sampled) >= limit:
            break
        root_path = Path(root)
        for sample_path in _walk_sample_files(root_path, limit=limit - len(sampled)):
            key = _path_string(sample_path)
            if key in seen:
                continue
            seen.add(key)
            sampled.append(sample_path)
            if len(sampled) >= limit:
                break
    return tuple(sampled)


@dataclass(frozen=True, slots=True)
class LocalCorpusFileSample:
    path: str
    size_bytes: int
    modified_ns: int
    hash_mode: str
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "modified_ns": self.modified_ns,
            "hash_mode": self.hash_mode,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class LocalCorpusFingerprint:
    source_name: str
    category: str
    coverage_status: str
    candidate_roots: tuple[str, ...]
    present_roots: tuple[str, ...]
    missing_roots: tuple[str, ...]
    sampled_files: tuple[LocalCorpusFileSample, ...]
    likely_join_anchors: tuple[str, ...] = ()
    load_hints: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    fingerprint: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _clean_text(self.source_name))
        object.__setattr__(self, "category", _clean_text(self.category))
        object.__setattr__(self, "coverage_status", _clean_text(self.coverage_status))
        object.__setattr__(self, "candidate_roots", _clean_text_tuple(self.candidate_roots))
        object.__setattr__(self, "present_roots", _clean_text_tuple(self.present_roots))
        object.__setattr__(self, "missing_roots", _clean_text_tuple(self.missing_roots))
        object.__setattr__(self, "likely_join_anchors", _clean_text_tuple(self.likely_join_anchors))
        object.__setattr__(self, "load_hints", _clean_text_tuple(self.load_hints))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        object.__setattr__(
            self,
            "fingerprint",
            _stable_checksum(
                {
                    "source_name": self.source_name,
                    "category": self.category,
                    "coverage_status": self.coverage_status,
                    "candidate_roots": self.candidate_roots,
                    "present_roots": self.present_roots,
                    "missing_roots": self.missing_roots,
                    "sampled_files": [sample.to_dict() for sample in self.sampled_files],
                    "likely_join_anchors": self.likely_join_anchors,
                    "load_hints": self.load_hints,
                    "notes": self.notes,
                }
            )[:16],
        )

    @property
    def sampled_paths(self) -> tuple[str, ...]:
        return tuple(sample.path for sample in self.sampled_files)

    @property
    def sampled_file_count(self) -> int:
        return len(self.sampled_files)

    @property
    def sampled_byte_count(self) -> int:
        return sum(sample.size_bytes for sample in self.sampled_files)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "category": self.category,
            "coverage_status": self.coverage_status,
            "candidate_roots": list(self.candidate_roots),
            "present_roots": list(self.present_roots),
            "missing_roots": list(self.missing_roots),
            "sampled_paths": list(self.sampled_paths),
            "sampled_file_count": self.sampled_file_count,
            "sampled_byte_count": self.sampled_byte_count,
            "sampled_files": [sample.to_dict() for sample in self.sampled_files],
            "likely_join_anchors": list(self.likely_join_anchors),
            "load_hints": list(self.load_hints),
            "notes": list(self.notes),
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True, slots=True)
class LocalCorpusFingerprintReport:
    report_id: str
    registry_id: str
    storage_root: str
    sample_limit: int
    entries: tuple[LocalCorpusFingerprint, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "report_id", _clean_text(self.report_id))
        object.__setattr__(self, "registry_id", _clean_text(self.registry_id))
        object.__setattr__(self, "storage_root", _clean_text(self.storage_root))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.report_id:
            raise ValueError("report_id must not be empty")
        if not self.registry_id:
            raise ValueError("registry_id must not be empty")
        if not self.storage_root:
            raise ValueError("storage_root must not be empty")

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    @property
    def present_entry_count(self) -> int:
        return sum(1 for entry in self.entries if entry.coverage_status == "present")

    @property
    def partial_entry_count(self) -> int:
        return sum(1 for entry in self.entries if entry.coverage_status == "partial")

    @property
    def missing_entry_count(self) -> int:
        return sum(1 for entry in self.entries if entry.coverage_status == "missing")

    @property
    def sampled_file_count(self) -> int:
        return sum(entry.sampled_file_count for entry in self.entries)

    @property
    def sampled_byte_count(self) -> int:
        return sum(entry.sampled_byte_count for entry in self.entries)

    @property
    def missing_sources(self) -> tuple[str, ...]:
        return tuple(
            entry.source_name for entry in self.entries if entry.coverage_status == "missing"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "report_id": self.report_id,
            "registry_id": self.registry_id,
            "storage_root": self.storage_root,
            "sample_limit": self.sample_limit,
            "entry_count": self.entry_count,
            "present_entry_count": self.present_entry_count,
            "partial_entry_count": self.partial_entry_count,
            "missing_entry_count": self.missing_entry_count,
            "sampled_file_count": self.sampled_file_count,
            "sampled_byte_count": self.sampled_byte_count,
            "missing_sources": list(self.missing_sources),
            "notes": list(self.notes),
            "entries": [entry.to_dict() for entry in self.entries],
        }


def fingerprint_local_corpus_entry(
    entry: LocalSourceEntry,
    *,
    sample_limit: int = DEFAULT_SAMPLE_LIMIT,
    prefix_hash_bytes: int = DEFAULT_PREFIX_HASH_BYTES,
) -> LocalCorpusFingerprint:
    sampled_files: list[LocalCorpusFileSample] = []
    for sample_path in _sample_roots(entry.present_roots, limit=sample_limit):
        try:
            stat = sample_path.stat()
        except OSError:
            continue
        hash_mode, sha256 = _file_hash(sample_path, prefix_bytes=prefix_hash_bytes)
        sampled_files.append(
            LocalCorpusFileSample(
                path=_path_string(sample_path),
                size_bytes=stat.st_size,
                modified_ns=stat.st_mtime_ns,
                hash_mode=hash_mode,
                sha256=sha256,
            )
        )

    return LocalCorpusFingerprint(
        source_name=entry.source_name,
        category=entry.category,
        coverage_status=entry.status,
        candidate_roots=entry.candidate_roots,
        present_roots=entry.present_roots,
        missing_roots=entry.missing_roots,
        sampled_files=tuple(sampled_files),
        likely_join_anchors=entry.likely_join_anchors,
        load_hints=entry.load_hints,
        notes=entry.notes,
    )


def fingerprint_local_source_registry(
    registry: LocalSourceRegistry = DEFAULT_LOCAL_SOURCE_REGISTRY,
    *,
    sample_limit: int = DEFAULT_SAMPLE_LIMIT,
    prefix_hash_bytes: int = DEFAULT_PREFIX_HASH_BYTES,
    report_id: str = DEFAULT_REPORT_ID,
) -> LocalCorpusFingerprintReport:
    entries = tuple(
        fingerprint_local_corpus_entry(
            entry,
            sample_limit=sample_limit,
            prefix_hash_bytes=prefix_hash_bytes,
        )
        for entry in registry.entries
    )
    return LocalCorpusFingerprintReport(
        report_id=report_id,
        registry_id=registry.registry_id,
        storage_root=registry.storage_root,
        sample_limit=sample_limit,
        entries=entries,
        notes=registry.notes,
    )


def build_default_local_corpus_fingerprint_report() -> LocalCorpusFingerprintReport:
    return fingerprint_local_source_registry()


__all__ = [
    "DEFAULT_PREFIX_HASH_BYTES",
    "DEFAULT_REPORT_ID",
    "DEFAULT_SAMPLE_LIMIT",
    "LocalCorpusFileSample",
    "LocalCorpusFingerprint",
    "LocalCorpusFingerprintReport",
    "build_default_local_corpus_fingerprint_report",
    "fingerprint_local_corpus_entry",
    "fingerprint_local_source_registry",
]
