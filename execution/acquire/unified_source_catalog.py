from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOOTSTRAP_SUMMARY = ROOT / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
DEFAULT_LOCAL_REGISTRY_SUMMARY = ROOT / "data" / "raw" / "local_registry_runs" / "LATEST.json"

SourceFacetKind = Literal["online_raw", "local_registry"]
UnifiedSourceStatus = Literal["present", "partial", "missing"]
SourceSnapshotState = Literal["healthy", "degraded", "missing", "unknown"]
SourceDriftState = Literal["stable", "drifted", "regressed", "new", "unknown"]

SOURCE_FAMILY_ALIASES: dict[str, str] = {
    "alphafold_db": "alphafold",
    "pdbbind_pl": "pdbbind",
    "pdbbind_pp": "pdbbind",
    "pdbbind_na_l": "pdbbind",
    "pdbbind_p_na": "pdbbind",
    "raw_rcsb": "rcsb_pdbe",
    "structures_rcsb": "rcsb_pdbe",
}

SOURCE_FAMILY_DISPLAY_NAMES: dict[str, str] = {
    "alphafold": "alphafold",
    "bindingdb": "bindingdb",
    "intact": "intact",
    "pdbbind": "pdbbind",
    "rcsb_pdbe": "rcsb_pdbe",
    "reactome": "reactome",
    "uniprot": "uniprot",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_name(value: Any) -> str:
    return _clean_text(value).casefold()


def _normalize_source_family(value: Any) -> str:
    normalized = _normalize_name(value)
    return SOURCE_FAMILY_ALIASES.get(normalized, normalized)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_json_if_exists(path: Path) -> Any | None:
    if not path.exists():
        return None
    return _read_json(path)


def _previous_history_summary_path(summary_path: Path) -> Path | None:
    if not summary_path.parent.exists():
        return None
    candidates = [
        path
        for path in summary_path.parent.glob("*.json")
        if path.resolve() != summary_path.resolve() and path.name.casefold() != "latest.json"
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.name.casefold())[-1]


def _repo_relative(path: str | Path, *, repo_root: Path = ROOT) -> str:
    resolved = Path(path)
    try:
        return str(resolved.relative_to(repo_root)).replace("\\", "/")
    except ValueError:
        return str(resolved).replace("\\", "/")


def _online_status(result: Mapping[str, Any]) -> UnifiedSourceStatus:
    status = _clean_text(result.get("status")).casefold()
    downloaded_files = tuple(str(item) for item in result.get("downloaded_files") or ())
    if status == "ok" and downloaded_files:
        return "present"
    if status == "ok":
        return "partial"
    return "missing"


def _local_status(item: Mapping[str, Any]) -> UnifiedSourceStatus:
    status = _clean_text(item.get("status")).casefold()
    if status in {"present", "partial", "missing"}:
        return status  # type: ignore[return-value]
    return "missing"


def _merge_statuses(*statuses: UnifiedSourceStatus) -> UnifiedSourceStatus:
    if "present" in statuses:
        return "present"
    if "partial" in statuses:
        return "partial"
    return "missing"


def _merge_source_names(normalized_name: str, source_names: list[str]) -> str:
    preferred = SOURCE_FAMILY_DISPLAY_NAMES.get(normalized_name)
    if preferred:
        return preferred
    if source_names:
        return sorted(dict.fromkeys(source_names), key=str.casefold)[0]
    return normalized_name


def _online_snapshot_state(result: Mapping[str, Any]) -> SourceSnapshotState:
    status = _clean_text(result.get("status")).casefold()
    downloaded_files = tuple(str(item) for item in result.get("downloaded_files") or ())
    if status == "ok" and downloaded_files:
        return "healthy"
    if status == "ok":
        return "degraded"
    if status in {"failed", "error", "missing"}:
        return "degraded" if status != "missing" else "missing"
    return "unknown"


def _local_snapshot_state(item: Mapping[str, Any]) -> SourceSnapshotState:
    status = _clean_text(item.get("status")).casefold()
    if status == "present":
        return "healthy"
    if status == "partial":
        return "degraded"
    if status == "missing":
        return "missing"
    return "unknown"


def _merge_snapshot_states(*states: SourceSnapshotState) -> SourceSnapshotState:
    if any(state == "degraded" for state in states):
        return "degraded"
    if any(state == "healthy" for state in states):
        return "healthy"
    if any(state == "missing" for state in states):
        return "missing"
    return "unknown"


def _merge_drift_states(*states: SourceDriftState) -> SourceDriftState:
    if any(state == "regressed" for state in states):
        return "regressed"
    if any(state == "drifted" for state in states):
        return "drifted"
    if any(state == "new" for state in states):
        return "new"
    if any(state == "stable" for state in states):
        return "stable"
    return "unknown"


def _status_change_state(
    current_status: UnifiedSourceStatus | None,
    previous_status: UnifiedSourceStatus | None,
) -> SourceDriftState:
    if previous_status is None:
        return "new"
    if current_status is None:
        return "unknown"
    current_rank = _status_rank(current_status)
    previous_rank = _status_rank(previous_status)
    if current_rank < previous_rank:
        return "regressed"
    if current_rank > previous_rank:
        return "drifted"
    return "stable"


def _status_rank(status: UnifiedSourceStatus) -> int:
    return {"present": 2, "partial": 1, "missing": 0}.get(status, 0)


def _compare_numeric_change(current: int, previous: int | None) -> SourceDriftState:
    if previous is None:
        return "new"
    if current < previous:
        return "regressed"
    if current > previous:
        return "drifted"
    return "stable"


def _load_manifest_snapshot(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    manifest_path = Path(path)
    if not manifest_path.exists():
        return {}
    payload = _read_json(manifest_path)
    return dict(payload) if isinstance(payload, Mapping) else {}


@dataclass(frozen=True, slots=True)
class SourceFacet:
    facet_kind: SourceFacetKind
    status: UnifiedSourceStatus
    snapshot_state: SourceSnapshotState
    drift_state: SourceDriftState
    detail: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "facet_kind": self.facet_kind,
            "status": self.status,
            "snapshot_state": self.snapshot_state,
            "drift_state": self.drift_state,
            "detail": dict(self.detail),
        }


@dataclass(frozen=True, slots=True)
class UnifiedSourceEntry:
    source_name: str
    normalized_name: str
    effective_status: UnifiedSourceStatus
    snapshot_state: SourceSnapshotState
    drift_state: SourceDriftState
    available_via: tuple[SourceFacetKind, ...]
    facets: tuple[SourceFacet, ...]
    notes: tuple[str, ...] = ()
    category: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "normalized_name": self.normalized_name,
            "effective_status": self.effective_status,
            "snapshot_state": self.snapshot_state,
            "drift_state": self.drift_state,
            "available_via": list(self.available_via),
            "category": self.category,
            "notes": list(self.notes),
            "facets": [facet.to_dict() for facet in self.facets],
        }


@dataclass(frozen=True, slots=True)
class UnifiedSourceCatalog:
    bootstrap_summary_path: str
    local_registry_summary_path: str
    entries: tuple[UnifiedSourceEntry, ...]
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bootstrap_summary_path": self.bootstrap_summary_path,
            "local_registry_summary_path": self.local_registry_summary_path,
            "entry_count": len(self.entries),
            "entries": [entry.to_dict() for entry in self.entries],
            "summary": dict(self.summary),
        }


def build_unified_source_catalog(
    *,
    bootstrap_summary_path: Path = DEFAULT_BOOTSTRAP_SUMMARY,
    local_registry_summary_path: Path = DEFAULT_LOCAL_REGISTRY_SUMMARY,
) -> UnifiedSourceCatalog:
    bootstrap_payload = _read_json(bootstrap_summary_path)
    local_payload = _read_json(local_registry_summary_path)
    previous_bootstrap_path = _previous_history_summary_path(Path(bootstrap_summary_path))
    previous_local_path = _previous_history_summary_path(Path(local_registry_summary_path))
    previous_bootstrap_payload = (
        _read_json_if_exists(previous_bootstrap_path)
        if previous_bootstrap_path is not None
        else None
    )
    previous_local_payload = (
        _read_json_if_exists(previous_local_path) if previous_local_path is not None else None
    )

    online_by_name: dict[str, dict[str, Any]] = {}
    for result in bootstrap_payload.get("results") or ():
        if not isinstance(result, Mapping):
            continue
        source_name = _clean_text(result.get("source"))
        if not source_name:
            continue
        normalized = _normalize_source_family(source_name)
        manifest = result.get("manifest") if isinstance(result.get("manifest"), Mapping) else {}
        downloaded_files = tuple(str(item) for item in result.get("downloaded_files") or ())
        previous_result = {}
        if isinstance(previous_bootstrap_payload, Mapping):
            for candidate in previous_bootstrap_payload.get("results") or ():
                if not isinstance(candidate, Mapping):
                    continue
                if _normalize_source_family(candidate.get("source")) == normalized:
                    previous_result = dict(candidate)
                    break
        current_status = _online_status(result)
        previous_status = _online_status(previous_result) if previous_result else None
        current_snapshot_state = _online_snapshot_state(result)
        current_fingerprint = _clean_text(manifest.get("snapshot_fingerprint")) or None
        previous_manifest = (
            previous_result.get("manifest")
            if isinstance(previous_result.get("manifest"), Mapping)
            else {}
        )
        previous_fingerprint = _clean_text(previous_manifest.get("snapshot_fingerprint")) or None
        current_count = len(downloaded_files)
        previous_count = (
            len(previous_result.get("downloaded_files") or ())
            if previous_result
            else None
        )
        if previous_result:
            if (
                current_status == previous_status
                and current_count == previous_count
                and current_fingerprint == previous_fingerprint
            ):
                drift_state = "stable"
            elif _status_rank(current_status) < _status_rank(previous_status):
                drift_state = "regressed"
            else:
                drift_state = "drifted"
        else:
            drift_state = "new"
        aggregated = online_by_name.setdefault(
            normalized,
            {
                "source_names": [],
                "statuses": [],
                "snapshot_states": [],
                "drift_states": [],
                "details": [],
            },
        )
        aggregated["source_names"].append(source_name)
        aggregated["statuses"].append(current_status)
        aggregated["snapshot_states"].append(current_snapshot_state)
        aggregated["drift_states"].append(drift_state)
        aggregated["details"].append(
            {
                "source": source_name,
                "downloaded_file_count": len(downloaded_files),
                "downloaded_files": list(downloaded_files[:10]),
                "manifest_id": manifest.get("manifest_id"),
                "release_version": manifest.get("release_version"),
                "source_locator": manifest.get("source_locator"),
                "snapshot_fingerprint": current_fingerprint,
                "previous_snapshot_fingerprint": previous_fingerprint,
                "previous_downloaded_file_count": previous_count,
                "previous_status": previous_status,
            }
        )

    normalized_online_by_name: dict[str, dict[str, Any]] = {}
    for normalized, aggregated in online_by_name.items():
        normalized_online_by_name[normalized] = {
            "source_name": _merge_source_names(normalized, aggregated["source_names"]),
            "status": _merge_statuses(*aggregated["statuses"]),
            "snapshot_state": _merge_snapshot_states(*aggregated["snapshot_states"]),
            "drift_state": _merge_drift_states(*aggregated["drift_states"]),
            "detail": {
                "source_members": sorted(dict.fromkeys(aggregated["source_names"]), key=str.casefold),
                "downloaded_file_count": sum(
                    int(item.get("downloaded_file_count") or 0) for item in aggregated["details"]
                ),
                "member_details": aggregated["details"],
            },
        }

    local_by_name: dict[str, dict[str, Any]] = {}
    for item in local_payload.get("imported_sources") or ():
        if not isinstance(item, Mapping):
            continue
        source_name = _clean_text(item.get("source_name"))
        if not source_name:
            continue
        normalized = _normalize_source_family(source_name)
        previous_item = {}
        if isinstance(previous_local_payload, Mapping):
            for candidate in previous_local_payload.get("imported_sources") or ():
                if not isinstance(candidate, Mapping):
                    continue
                if _normalize_source_family(candidate.get("source_name")) == normalized:
                    previous_item = dict(candidate)
                    break
        current_manifest = _load_manifest_snapshot(
            _clean_text(item.get("manifest_path")) or None
        )
        previous_manifest = _load_manifest_snapshot(
            _clean_text(previous_item.get("manifest_path")) or None
        )
        current_status = _local_status(item)
        previous_status = _local_status(previous_item) if previous_item else None
        current_snapshot_state = _local_snapshot_state(item)
        current_fingerprint = _clean_text(current_manifest.get("snapshot_fingerprint")) or None
        previous_fingerprint = _clean_text(previous_manifest.get("snapshot_fingerprint")) or None
        current_count = int(item.get("present_file_count") or 0)
        previous_count = (
            int(previous_item.get("present_file_count") or 0) if previous_item else None
        )
        current_bytes = int(item.get("present_total_bytes") or 0)
        previous_bytes = (
            int(previous_item.get("present_total_bytes") or 0) if previous_item else None
        )
        if previous_item:
            if (
                current_status == previous_status
                and current_count == previous_count
                and current_bytes == previous_bytes
                and current_fingerprint == previous_fingerprint
            ):
                drift_state = "stable"
            elif _status_rank(current_status) < _status_rank(previous_status):
                drift_state = "regressed"
            else:
                drift_state = "drifted"
        else:
            drift_state = "new"
        aggregated = local_by_name.setdefault(
            normalized,
            {
                "source_names": [],
                "statuses": [],
                "snapshot_states": [],
                "drift_states": [],
                "details": [],
            },
        )
        aggregated["source_names"].append(source_name)
        aggregated["statuses"].append(current_status)
        aggregated["snapshot_states"].append(current_snapshot_state)
        aggregated["drift_states"].append(drift_state)
        aggregated["details"].append(
            {
                "source_name": source_name,
                "category": _clean_text(item.get("category")) or None,
                "present_root_count": int(item.get("present_root_count") or 0),
                "present_file_count": current_count,
                "present_total_bytes": current_bytes,
                "inventory_path": item.get("inventory_path"),
                "manifest_path": item.get("manifest_path"),
                "load_hints": [str(value) for value in item.get("load_hints") or ()],
                "snapshot_fingerprint": current_fingerprint,
                "previous_snapshot_fingerprint": previous_fingerprint,
                "previous_present_file_count": previous_count,
                "previous_present_total_bytes": previous_bytes,
                "previous_status": previous_status,
                "manifest_release_version": current_manifest.get("release_version"),
                "manifest_source_locator": current_manifest.get("source_locator"),
            }
        )

    normalized_local_by_name: dict[str, dict[str, Any]] = {}
    for normalized, aggregated in local_by_name.items():
        categories = sorted(
            {
                str(item.get("category"))
                for item in aggregated["details"]
                if item.get("category") is not None
            },
            key=str.casefold,
        )
        normalized_local_by_name[normalized] = {
            "source_name": _merge_source_names(normalized, aggregated["source_names"]),
            "status": _merge_statuses(*aggregated["statuses"]),
            "snapshot_state": _merge_snapshot_states(*aggregated["snapshot_states"]),
            "drift_state": _merge_drift_states(*aggregated["drift_states"]),
            "detail": {
                "source_members": sorted(dict.fromkeys(aggregated["source_names"]), key=str.casefold),
                "category": categories[0] if len(categories) == 1 else None,
                "categories": categories,
                "present_root_count": sum(
                    int(item.get("present_root_count") or 0) for item in aggregated["details"]
                ),
                "present_file_count": sum(
                    int(item.get("present_file_count") or 0) for item in aggregated["details"]
                ),
                "present_total_bytes": sum(
                    int(item.get("present_total_bytes") or 0) for item in aggregated["details"]
                ),
                "inventory_paths": [
                    item.get("inventory_path")
                    for item in aggregated["details"]
                    if item.get("inventory_path")
                ],
                "manifest_paths": [
                    item.get("manifest_path")
                    for item in aggregated["details"]
                    if item.get("manifest_path")
                ],
                "load_hints": sorted(
                    {
                        str(value)
                        for item in aggregated["details"]
                        for value in item.get("load_hints") or ()
                    },
                    key=str.casefold,
                ),
                "member_details": aggregated["details"],
            },
        }

    entries: list[UnifiedSourceEntry] = []
    for normalized in sorted(set(normalized_online_by_name).union(normalized_local_by_name)):
        online = normalized_online_by_name.get(normalized)
        local = normalized_local_by_name.get(normalized)
        source_name = (
            online["source_name"]
            if online is not None
            else local["source_name"]
            if local is not None
            else normalized
        )
        facets: list[SourceFacet] = []
        statuses: list[UnifiedSourceStatus] = []
        available_via: list[SourceFacetKind] = []
        notes: list[str] = []
        category: str | None = None
        entry_snapshot_states: list[SourceSnapshotState] = []
        entry_drift_states: list[SourceDriftState] = []

        if online is not None:
            statuses.append(online["status"])
            entry_snapshot_states.append(online["snapshot_state"])
            entry_drift_states.append(online["drift_state"])
            facets.append(
                SourceFacet(
                    facet_kind="online_raw",
                    status=online["status"],
                    snapshot_state=online["snapshot_state"],
                    drift_state=online["drift_state"],
                    detail=dict(online["detail"]),
                )
            )
            if online["status"] != "missing":
                available_via.append("online_raw")

        if local is not None:
            statuses.append(local["status"])
            entry_snapshot_states.append(local["snapshot_state"])
            entry_drift_states.append(local["drift_state"])
            category = local["detail"].get("category")
            facets.append(
                SourceFacet(
                    facet_kind="local_registry",
                    status=local["status"],
                    snapshot_state=local["snapshot_state"],
                    drift_state=local["drift_state"],
                    detail=dict(local["detail"]),
                )
            )
            if local["status"] != "missing":
                available_via.append("local_registry")

        effective_status = _merge_statuses(*statuses) if statuses else "missing"
        snapshot_state = _merge_snapshot_states(*entry_snapshot_states)
        drift_state = _merge_drift_states(*entry_drift_states)
        if online is not None and online["status"] != "missing" and (
            local is None or local["status"] == "missing"
        ):
            notes.append("available via online raw snapshot only")
        if local is not None and local["status"] != "missing" and (
            online is None or online["status"] == "missing"
        ):
            notes.append("available via local bio-agent-lab registry only")
        if online is not None and local is not None and effective_status == "present":
            notes.append("available via both online raw and local registry")
        if online is not None and online["status"] == "partial":
            notes.append("online raw snapshot is partial")
        if online is not None and online["snapshot_state"] == "degraded":
            notes.append("latest online snapshot is degraded")
        if local is not None and local["snapshot_state"] == "degraded":
            notes.append("local registry snapshot is degraded")
        if local is not None and local["status"] == "partial":
            notes.append("local registry coverage is partial")
        if local is not None and local["drift_state"] in {"drifted", "regressed"}:
            notes.append("local source fingerprint drift detected")
        if online is not None and online["drift_state"] in {"drifted", "regressed"}:
            notes.append("online snapshot changed relative to previous run")

        entries.append(
            UnifiedSourceEntry(
                source_name=source_name,
                normalized_name=normalized,
                effective_status=effective_status,
                snapshot_state=snapshot_state,
                drift_state=drift_state,
                available_via=tuple(dict.fromkeys(available_via)),
                facets=tuple(facets),
                notes=tuple(dict.fromkeys(notes)),
                category=category,
            )
        )

    status_counts = Counter(entry.effective_status for entry in entries)
    online_only_sources = [
        entry.source_name
        for entry in entries
        if "online_raw" in entry.available_via and "local_registry" not in entry.available_via
    ]
    local_only_sources = [
        entry.source_name
        for entry in entries
        if "local_registry" in entry.available_via and "online_raw" not in entry.available_via
    ]
    dual_sources = [
        entry.source_name
        for entry in entries
        if set(entry.available_via) == {"online_raw", "local_registry"}
    ]
    summary = {
        "effective_status_counts": dict(sorted(status_counts.items())),
        "snapshot_state_counts": dict(
            sorted(Counter(entry.snapshot_state for entry in entries).items())
        ),
        "drift_state_counts": dict(sorted(Counter(entry.drift_state for entry in entries).items())),
        "degraded_online_sources": sorted(
            [
                entry.source_name
                for entry in entries
                if any(
                    facet.facet_kind == "online_raw" and facet.snapshot_state == "degraded"
                    for facet in entry.facets
                )
            ],
            key=str.casefold,
        ),
        "drifted_local_sources": sorted(
            [
                entry.source_name
                for entry in entries
                if any(
                    facet.facet_kind == "local_registry"
                    and facet.drift_state in {"drifted", "regressed"}
                    for facet in entry.facets
                )
            ],
            key=str.casefold,
        ),
        "online_only_sources": sorted(online_only_sources, key=str.casefold),
        "local_only_sources": sorted(local_only_sources, key=str.casefold),
        "dual_sources": sorted(dual_sources, key=str.casefold),
    }

    return UnifiedSourceCatalog(
        bootstrap_summary_path=_repo_relative(bootstrap_summary_path),
        local_registry_summary_path=_repo_relative(local_registry_summary_path),
        entries=tuple(entries),
        summary=summary,
    )


__all__ = [
    "DEFAULT_BOOTSTRAP_SUMMARY",
    "DEFAULT_LOCAL_REGISTRY_SUMMARY",
    "SourceFacet",
    "UnifiedSourceCatalog",
    "UnifiedSourceEntry",
    "build_unified_source_catalog",
]
