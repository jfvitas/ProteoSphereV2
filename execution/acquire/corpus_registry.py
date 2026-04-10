from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOOTSTRAP_SUMMARY = ROOT / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
DEFAULT_LOCAL_REGISTRY_SUMMARY = ROOT / "data" / "raw" / "local_registry_runs" / "LATEST.json"
DEFAULT_REGISTRY_ID = "corpus-registry:v1"

CandidateKind = Literal["protein", "pair", "ligand", "annotation"]
SourceStatus = Literal["present", "partial", "missing"]
SourceFacetKind = Literal["online_raw", "local_registry"]

_ONLINE_KIND_MAP: dict[str, tuple[CandidateKind, ...]] = {
    "alphafold": ("protein",),
    "bindingdb": ("ligand",),
    "biogrid": ("pair",),
    "disprot": ("annotation",),
    "evolutionary": ("annotation",),
    "intact": ("pair",),
    "interpro": ("annotation",),
    "pdbbind": ("ligand",),
    "rcsb_pdbe": ("protein",),
    "reactome": ("annotation",),
    "string": ("pair",),
    "uniprot": ("protein",),
}
_LOCAL_CATEGORY_KIND_MAP: dict[str, tuple[CandidateKind, ...]] = {
    "annotation": ("annotation",),
    "domain_annotation": ("annotation",),
    "evolutionary": ("annotation",),
    "interaction_network": ("pair",),
    "motif_annotation": ("annotation",),
    "pathway_annotation": ("annotation",),
    "protein_ligand": ("ligand",),
    "protein_protein": ("pair",),
    "sequence": ("protein",),
    "structure": ("protein",),
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        iterable: Sequence[Any] = (values,)
    elif isinstance(values, Sequence):
        iterable = values
    else:
        iterable = (values,)
    ordered: dict[str, str] = {}
    for value in iterable:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _normalize_name(value: Any) -> str:
    return _clean_text(value).casefold()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _source_status_from_online(result: Mapping[str, Any]) -> SourceStatus:
    status = _clean_text(result.get("status")).casefold()
    downloaded_files = _clean_text_tuple(result.get("downloaded_files"))
    if status == "ok" and downloaded_files:
        return "present"
    if status == "ok":
        return "partial"
    return "missing"


def _source_status_from_local(result: Mapping[str, Any]) -> SourceStatus:
    status = _clean_text(result.get("status")).casefold()
    if status in {"present", "partial", "missing"}:
        return status  # type: ignore[return-value]
    return "missing"


def _merge_statuses(*statuses: SourceStatus) -> SourceStatus:
    if "present" in statuses:
        return "present"
    if "partial" in statuses:
        return "partial"
    return "missing"


def _candidate_kinds(
    *,
    source_name: str,
    local_category: str | None,
) -> tuple[CandidateKind, ...]:
    kinds = list(_ONLINE_KIND_MAP.get(_normalize_name(source_name), ()))
    if local_category:
        kinds.extend(_LOCAL_CATEGORY_KIND_MAP.get(_normalize_name(local_category), ()))
    ordered: dict[str, CandidateKind] = {}
    for kind in kinds:
        ordered.setdefault(kind, kind)
    return tuple(ordered.values())


@dataclass(frozen=True, slots=True)
class CorpusRegistryRow:
    row_id: str
    candidate_kind: CandidateKind
    source_name: str
    normalized_name: str
    effective_status: SourceStatus
    available_via: tuple[SourceFacetKind, ...] = ()
    local_status: SourceStatus | None = None
    online_status: SourceStatus | None = None
    source_category: str | None = None
    online_downloaded_file_count: int = 0
    online_release_version: str | None = None
    source_locator: str | None = None
    local_present_file_count: int = 0
    local_present_total_bytes: int = 0
    local_join_keys: tuple[str, ...] = ()
    local_load_hints: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "row_id", _clean_text(self.row_id))
        object.__setattr__(self, "candidate_kind", _clean_text(self.candidate_kind))
        object.__setattr__(self, "source_name", _clean_text(self.source_name))
        object.__setattr__(self, "normalized_name", _normalize_name(self.normalized_name))
        object.__setattr__(self, "effective_status", _clean_text(self.effective_status))
        object.__setattr__(self, "available_via", _clean_text_tuple(self.available_via))
        object.__setattr__(
            self,
            "local_status",
            _clean_text(self.local_status) or None,
        )
        object.__setattr__(
            self,
            "online_status",
            _clean_text(self.online_status) or None,
        )
        object.__setattr__(self, "source_category", _clean_text(self.source_category) or None)
        object.__setattr__(
            self,
            "online_downloaded_file_count",
            int(self.online_downloaded_file_count),
        )
        object.__setattr__(
            self,
            "online_release_version",
            _clean_text(self.online_release_version) or None,
        )
        object.__setattr__(self, "source_locator", _clean_text(self.source_locator) or None)
        object.__setattr__(self, "local_present_file_count", int(self.local_present_file_count))
        object.__setattr__(self, "local_present_total_bytes", int(self.local_present_total_bytes))
        object.__setattr__(self, "local_join_keys", _clean_text_tuple(self.local_join_keys))
        object.__setattr__(self, "local_load_hints", _clean_text_tuple(self.local_load_hints))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if self.candidate_kind not in {"protein", "pair", "ligand", "annotation"}:
            raise ValueError("candidate_kind must be protein, pair, ligand, or annotation")
        if self.effective_status not in {"present", "partial", "missing"}:
            raise ValueError("effective_status must be present, partial, or missing")
        if not self.row_id:
            raise ValueError("row_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "candidate_kind": self.candidate_kind,
            "source_name": self.source_name,
            "normalized_name": self.normalized_name,
            "effective_status": self.effective_status,
            "available_via": list(self.available_via),
            "local_status": self.local_status,
            "online_status": self.online_status,
            "source_category": self.source_category,
            "online_downloaded_file_count": self.online_downloaded_file_count,
            "online_release_version": self.online_release_version,
            "source_locator": self.source_locator,
            "local_present_file_count": self.local_present_file_count,
            "local_present_total_bytes": self.local_present_total_bytes,
            "local_join_keys": list(self.local_join_keys),
            "local_load_hints": list(self.local_load_hints),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class CorpusRegistry:
    registry_id: str
    bootstrap_summary_path: str
    local_registry_summary_path: str
    rows: tuple[CorpusRegistryRow, ...]
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "registry_id": self.registry_id,
            "bootstrap_summary_path": self.bootstrap_summary_path,
            "local_registry_summary_path": self.local_registry_summary_path,
            "row_count": len(self.rows),
            "rows": [row.to_dict() for row in self.rows],
            "summary": dict(self.summary),
        }


def build_corpus_registry(
    *,
    bootstrap_summary_path: Path = DEFAULT_BOOTSTRAP_SUMMARY,
    local_registry_summary_path: Path = DEFAULT_LOCAL_REGISTRY_SUMMARY,
    registry_id: str = DEFAULT_REGISTRY_ID,
) -> CorpusRegistry:
    bootstrap_payload = _read_json(bootstrap_summary_path)
    local_payload = _read_json(local_registry_summary_path)

    online_by_name: dict[str, dict[str, Any]] = {}
    for result in bootstrap_payload.get("results") or ():
        if not isinstance(result, Mapping):
            continue
        source_name = _clean_text(result.get("source"))
        if not source_name:
            continue
        manifest = result.get("manifest")
        manifest_payload = dict(manifest) if isinstance(manifest, Mapping) else {}
        downloaded_files = _clean_text_tuple(result.get("downloaded_files"))
        online_by_name[_normalize_name(source_name)] = {
            "source_name": source_name,
            "status": _source_status_from_online(result),
            "downloaded_file_count": len(downloaded_files),
            "release_version": _clean_text(manifest_payload.get("release_version")) or None,
            "source_locator": _clean_text(manifest_payload.get("source_locator")) or None,
        }

    local_by_name: dict[str, dict[str, Any]] = {}
    for item in local_payload.get("imported_sources") or ():
        if not isinstance(item, Mapping):
            continue
        source_name = _clean_text(item.get("source_name"))
        if not source_name:
            continue
        local_by_name[_normalize_name(source_name)] = {
            "source_name": source_name,
            "status": _source_status_from_local(item),
            "category": _clean_text(item.get("category")) or None,
            "present_file_count": int(item.get("present_file_count") or 0),
            "present_total_bytes": int(item.get("present_total_bytes") or 0),
            "join_keys": _clean_text_tuple(item.get("join_keys")),
            "load_hints": _clean_text_tuple(item.get("load_hints")),
        }

    rows: list[CorpusRegistryRow] = []
    for normalized_name in sorted(set(online_by_name) | set(local_by_name)):
        online = online_by_name.get(normalized_name)
        local = local_by_name.get(normalized_name)
        source_name = (
            online["source_name"]
            if online is not None
            else local["source_name"]
            if local is not None
            else normalized_name
        )
        candidate_kinds = _candidate_kinds(
            source_name=source_name,
            local_category=local.get("category") if local else None,
        )
        if not candidate_kinds:
            continue

        statuses: list[SourceStatus] = []
        available_via: list[SourceFacetKind] = []
        notes: list[str] = []
        if online is not None:
            statuses.append(online["status"])
            if online["status"] != "missing":
                available_via.append("online_raw")
            if online["status"] == "partial":
                notes.append("online_raw_partial")
        if local is not None:
            statuses.append(local["status"])
            if local["status"] != "missing":
                available_via.append("local_registry")
            if local["status"] == "partial":
                notes.append("local_registry_partial")
        effective_status = _merge_statuses(*statuses) if statuses else "missing"
        if not available_via:
            notes.append("no_current_source_copy")
        elif tuple(dict.fromkeys(available_via)) == ("online_raw",):
            notes.append("online_only")
        elif tuple(dict.fromkeys(available_via)) == ("local_registry",):
            notes.append("local_only")
        else:
            notes.append("online_and_local")

        for candidate_kind in candidate_kinds:
            rows.append(
                CorpusRegistryRow(
                    row_id=f"{candidate_kind}:{normalized_name}",
                    candidate_kind=candidate_kind,
                    source_name=source_name,
                    normalized_name=normalized_name,
                    effective_status=effective_status,
                    available_via=tuple(dict.fromkeys(available_via)),
                    local_status=local["status"] if local else None,
                    online_status=online["status"] if online else None,
                    source_category=local.get("category") if local else None,
                    online_downloaded_file_count=online.get("downloaded_file_count", 0)
                    if online
                    else 0,
                    online_release_version=online.get("release_version") if online else None,
                    source_locator=online.get("source_locator") if online else None,
                    local_present_file_count=local.get("present_file_count", 0) if local else 0,
                    local_present_total_bytes=local.get("present_total_bytes", 0) if local else 0,
                    local_join_keys=local.get("join_keys", ()) if local else (),
                    local_load_hints=local.get("load_hints", ()) if local else (),
                    notes=tuple(dict.fromkeys(notes)),
                )
            )

    kind_counts = Counter(row.candidate_kind for row in rows)
    status_counts = Counter(row.effective_status for row in rows)
    by_kind_status: dict[str, dict[str, int]] = {}
    for kind in ("protein", "pair", "ligand", "annotation"):
        subset = [row for row in rows if row.candidate_kind == kind]
        by_kind_status[kind] = dict(sorted(Counter(row.effective_status for row in subset).items()))

    return CorpusRegistry(
        registry_id=registry_id,
        bootstrap_summary_path=str(bootstrap_summary_path),
        local_registry_summary_path=str(local_registry_summary_path),
        rows=tuple(rows),
        summary={
            "candidate_kind_counts": dict(sorted(kind_counts.items())),
            "effective_status_counts": dict(sorted(status_counts.items())),
            "candidate_kind_status_counts": by_kind_status,
        },
    )
