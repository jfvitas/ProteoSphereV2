from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.bio_agent_lab_imports import (
    BioAgentLabImportManifest,
    BioAgentLabImportSource,
    build_bio_agent_lab_import_manifest,
)
from execution.acquire.local_source_registry import (
    DEFAULT_LOCAL_SOURCE_ROOT,
    LocalSourceDefinition,
    LocalSourceEntry,
    LocalSourceRegistry,
    build_default_local_source_registry,
    build_local_source_registry,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_ROOT = ROOT / "data" / "raw"


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


def _normalize_source_names(values: Sequence[str] | None) -> tuple[str, ...] | None:
    if values is None:
        return None
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _timestamp_slug() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _stable_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _path_ref(path: Path, *, repo_root: Path = ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return ()
    if root.is_file():
        return (root,)
    return (path for path in root.rglob("*") if path.is_file())


def _source_name_set(values: Iterable[str]) -> frozenset[str]:
    return frozenset(_clean_text(value) for value in values if _clean_text(value))


def _is_authoritative_refresh(
    manifest: BioAgentLabImportManifest,
    *,
    registry: LocalSourceRegistry,
) -> bool:
    return _source_name_set(source.source_name for source in manifest.sources) == _source_name_set(
        entry.source_name for entry in registry.entries
    )


def _dedupe_entries(entries: Iterable[LocalSourceEntry]) -> tuple[LocalSourceEntry, ...]:
    ordered: dict[str, LocalSourceEntry] = {}
    for entry in entries:
        if entry.source_name not in ordered:
            ordered[entry.source_name] = entry
    return tuple(ordered.values())


DEFAULT_CONTEXT_SOURCE_DEFINITIONS: tuple[LocalSourceDefinition, ...] = (
    LocalSourceDefinition(
        source_name="catalog",
        category="metadata",
        candidate_roots=("data/catalog",),
        load_hints=("preload",),
        notes=("workspace source catalog and stage metadata",),
    ),
    LocalSourceDefinition(
        source_name="features",
        category="derived_training",
        candidate_roots=("data/features",),
        load_hints=("index",),
        likely_join_anchors=("P69905", "1A00"),
        notes=("feature manifests and microstate/physics feature records",),
    ),
    LocalSourceDefinition(
        source_name="graph",
        category="derived_training",
        candidate_roots=("data/graph",),
        load_hints=("index",),
        likely_join_anchors=("P69905", "5JJM"),
        notes=("graph nodes, edges, and graph manifest",),
    ),
    LocalSourceDefinition(
        source_name="identity",
        category="metadata",
        candidate_roots=("data/identity",),
        load_hints=("lazy",),
        notes=(
            "lightweight identity/control lane; keep join keys empty "
            "until content is populated",
        ),
    ),
    LocalSourceDefinition(
        source_name="processed",
        category="derived_training",
        candidate_roots=("data/processed",),
        load_hints=("index", "lazy"),
        notes=("processed RCSB derivatives and other post-processing outputs",),
    ),
    LocalSourceDefinition(
        source_name="reports",
        category="metadata",
        candidate_roots=("data/reports",),
        load_hints=("preload",),
        notes=("operator-facing report outputs and diagnostics",),
    ),
    LocalSourceDefinition(
        source_name="risk",
        category="metadata",
        candidate_roots=("data/risk",),
        load_hints=("preload",),
        notes=("risk summaries and pathway review rollups",),
    ),
    LocalSourceDefinition(
        source_name="splits",
        category="metadata",
        candidate_roots=("data/splits",),
        load_hints=("preload",),
        notes=("split metadata and diagnostics",),
    ),
    LocalSourceDefinition(
        source_name="training_examples",
        category="derived_training",
        candidate_roots=("data/training_examples",),
        load_hints=("index",),
        likely_join_anchors=("P69905", "P31749"),
        notes=("assembled training-example layer",),
    ),
    LocalSourceDefinition(
        source_name="qa",
        category="metadata",
        candidate_roots=("data/qa",),
        load_hints=("preload",),
        notes=("scenario-test manifests and reports for quality assurance",),
    ),
    LocalSourceDefinition(
        source_name="packaged",
        category="release_artifact",
        candidate_roots=("data/packaged",),
        load_hints=("preload",),
        notes=("packaged catalogs and release-ready bundles",),
    ),
    LocalSourceDefinition(
        source_name="conformations",
        category="structure",
        candidate_roots=("data/conformations",),
        load_hints=("index", "lazy"),
        notes=("conformation state inventories and manifests",),
    ),
    LocalSourceDefinition(
        source_name="custom_training_sets",
        category="derived_training",
        candidate_roots=("data/custom_training_sets",),
        load_hints=("index",),
        notes=("run-specific custom training set bundles",),
    ),
    LocalSourceDefinition(
        source_name="demo",
        category="metadata",
        candidate_roots=("data/demo",),
        load_hints=("lazy",),
        notes=("demo scaffolding lane; empty unless explicitly populated",),
    ),
    LocalSourceDefinition(
        source_name="external",
        category="metadata",
        candidate_roots=("data/external",),
        load_hints=("lazy",),
        notes=("external handoff lane; keep joins empty unless a stable export appears",),
    ),
    LocalSourceDefinition(
        source_name="interim",
        category="metadata",
        candidate_roots=("data/interim",),
        load_hints=("lazy",),
        notes=("intermediate working lane; no stable join keys are implied",),
    ),
    LocalSourceDefinition(
        source_name="models",
        category="derived_training",
        candidate_roots=("data/models",),
        load_hints=("index", "lazy"),
        notes=("model artifacts and evaluation payloads across the workspace",),
    ),
    LocalSourceDefinition(
        source_name="prediction",
        category="derived_training",
        candidate_roots=("data/prediction",),
        load_hints=("index", "lazy"),
        notes=("prediction outputs such as ligand screening and peptide-binding runs",),
    ),
    LocalSourceDefinition(
        source_name="raw",
        category="metadata",
        candidate_roots=("data/raw",),
        load_hints=("index", "lazy"),
        notes=(
            "umbrella lane for raw mirrored payloads; prefer specific sub-sources for joins",
        ),
    ),
)


def build_bio_agent_lab_context_registry(
    storage_root: str | Path = DEFAULT_LOCAL_SOURCE_ROOT,
) -> LocalSourceRegistry:
    root = Path(storage_root)
    base_registry = build_default_local_source_registry(root)
    base_source_names = {entry.source_name.casefold() for entry in base_registry.entries}
    supplemental_definitions: list[LocalSourceDefinition] = []
    for definition in DEFAULT_CONTEXT_SOURCE_DEFINITIONS:
        if definition.source_name.casefold() in base_source_names:
            continue
        if not any(
            (root / candidate_root).exists() for candidate_root in definition.candidate_roots
        ):
            continue
        supplemental_definitions.append(definition)
    if not supplemental_definitions:
        return base_registry
    supplemental_registry = build_local_source_registry(
        root,
        tuple(supplemental_definitions),
        registry_id=base_registry.registry_id,
        notes=(
            "supplemental present bio-agent-lab/data context folders recognized by the importer",
        ),
    )
    return LocalSourceRegistry(
        registry_id=base_registry.registry_id,
        storage_root=base_registry.storage_root,
        entries=_dedupe_entries((*base_registry.entries, *supplemental_registry.entries)),
        notes=base_registry.notes
        + (
            "augmented with present bio-agent-lab/data context folders "
            "where that improves import coverage",
        ),
    )


def _root_fingerprint_payload(
    root: Path,
    *,
    kind: str,
    file_entries: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "fingerprint_version": "local-source-root:v1",
        "fingerprint_basis": "relative_path_and_size",
        "kind": kind,
        "files": list(file_entries),
    }


def _inventory_fingerprint_payload(
    source_name: str,
    *,
    category: str,
    status: str,
    root_summaries: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "fingerprint_version": "local-source-inventory:v1",
        "fingerprint_basis": "root_path_and_root_fingerprints",
        "source_name": source_name,
        "category": category,
        "status": status,
        "roots": [
            {
                "path": item["path"],
                "kind": item["kind"],
                "file_count": item["file_count"],
                "total_bytes": item["total_bytes"],
                "fingerprint": item["fingerprint"],
            }
            for item in root_summaries
        ],
    }


def summarize_local_root(root: str | Path, *, sample_limit: int = 8) -> dict[str, Any]:
    path = Path(root)
    exists = path.exists()
    summary: dict[str, Any] = {
        "path": str(path),
        "exists": exists,
        "kind": "missing",
        "file_count": 0,
        "total_bytes": 0,
        "sample_files": [],
        "latest_mtime": None,
        "fingerprint_version": "local-source-root:v1",
        "fingerprint_basis": "relative_path_and_size",
        "fingerprint": None,
    }
    if not exists:
        return summary

    if path.is_file():
        stat = path.stat()
        file_entries = [{"path": path.name, "size": stat.st_size}]
        return {
            "path": str(path),
            "exists": True,
            "kind": "file",
            "file_count": 1,
            "total_bytes": stat.st_size,
            "sample_files": [str(path.name)],
        "latest_mtime": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
        "fingerprint_version": "local-source-root:v1",
        "fingerprint_basis": "relative_path_and_size",
        "fingerprint": _sha256_hex(
            _stable_json_bytes(
                _root_fingerprint_payload(path, kind="file", file_entries=file_entries)
            )
        ),
    }

    file_count = 0
    total_bytes = 0
    latest_mtime = path.stat().st_mtime
    sample_files: list[str] = []
    file_entries: list[dict[str, Any]] = []
    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        relative_path = str(file_path.relative_to(path))
        stat = file_path.stat()
        file_count += 1
        total_bytes += stat.st_size
        latest_mtime = max(latest_mtime, stat.st_mtime)
        if len(sample_files) < max(1, sample_limit):
            sample_files.append(relative_path)
        file_entries.append({"path": relative_path, "size": stat.st_size})
    file_entries.sort(key=lambda item: item["path"])
    return {
        "path": str(path),
        "exists": True,
        "kind": "directory",
        "file_count": file_count,
        "total_bytes": total_bytes,
        "sample_files": sample_files,
        "latest_mtime": datetime.fromtimestamp(latest_mtime, tz=UTC).isoformat(),
        "fingerprint_version": "local-source-root:v1",
        "fingerprint_basis": "relative_path_and_size",
        "fingerprint": _sha256_hex(
            _stable_json_bytes(
                _root_fingerprint_payload(
                    path,
                    kind="directory",
                    file_entries=file_entries,
                )
            )
        ),
    }


def build_local_source_inventory(
    source: BioAgentLabImportSource,
    *,
    sample_limit: int = 8,
) -> dict[str, Any]:
    root_summaries = [
        summarize_local_root(root, sample_limit=sample_limit)
        for root in source.present_roots
    ]
    inventory_fingerprint_payload = _inventory_fingerprint_payload(
        source.source_name,
        category=source.category,
        status=source.status,
        root_summaries=root_summaries,
    )
    return {
        **source.to_dict(),
        "generated_at": _utc_now().isoformat(),
        "present_root_summaries": root_summaries,
        "present_file_count": sum(item["file_count"] for item in root_summaries),
        "present_total_bytes": sum(item["total_bytes"] for item in root_summaries),
        "large_payload": any(item["total_bytes"] >= 1_000_000_000 for item in root_summaries),
        "inventory_fingerprint_version": inventory_fingerprint_payload["fingerprint_version"],
        "inventory_fingerprint_basis": inventory_fingerprint_payload["fingerprint_basis"],
        "inventory_fingerprint": _sha256_hex(_stable_json_bytes(inventory_fingerprint_payload)),
    }


def _source_manifest(
    source: BioAgentLabImportSource,
    *,
    inventory_path: Path,
    release_version: str,
) -> dict[str, Any]:
    manifest = SourceReleaseManifest(
        source_name=f"bio-agent-lab/{source.source_name}",
        release_version=release_version,
        retrieval_mode="download",
        source_locator=(
            source.present_roots[0]
            if source.present_roots
            else source.candidate_roots[0]
        ),
        local_artifact_refs=tuple(source.present_roots) + (_path_ref(inventory_path),),
        provenance=(
            "local_source_mirror",
            "bio_agent_lab",
            source.category,
            source.status,
            *source.load_hints,
        ),
        reproducibility_metadata=(
            f"join_keys={','.join(source.join_keys)}" if source.join_keys else "join_keys=",
            f"missing_roots={len(source.missing_roots)}",
        ),
    )
    return manifest.to_dict()


def mirror_local_sources(
    *,
    storage_root: str | Path = DEFAULT_LOCAL_SOURCE_ROOT,
    raw_root: str | Path = DEFAULT_RAW_ROOT,
    source_names: Sequence[str] | None = None,
    include_missing: bool = False,
    dry_run: bool = False,
    sample_limit: int = 8,
    import_manifest: BioAgentLabImportManifest | None = None,
) -> dict[str, Any]:
    resolved_raw_root = Path(raw_root)
    resolved_storage_root = Path(storage_root)
    effective_registry = build_bio_agent_lab_context_registry(resolved_storage_root)
    manifest = import_manifest or build_bio_agent_lab_import_manifest(
        resolved_storage_root,
        registry=effective_registry,
        source_names=_normalize_source_names(source_names),
    )
    stamp = _timestamp_slug()
    release_version = _utc_now().date().isoformat()
    run_root = resolved_raw_root / "local_registry" / stamp
    summary: dict[str, Any] = {
        "generated_at": _utc_now().isoformat(),
        "storage_root": str(resolved_storage_root),
        "raw_root": str(resolved_raw_root),
        "registry_id": manifest.registry_id,
        "manifest_id": manifest.manifest_id,
        "stamp": stamp,
        "latest_update_policy": "full_authoritative_refresh_only",
        "authoritative_refresh": _is_authoritative_refresh(
            manifest,
            registry=effective_registry,
        ),
        "selected_source_count": len(manifest.sources),
        "imported_sources": [],
        "skipped_sources": [],
    }

    if not dry_run:
        resolved_raw_root.mkdir(parents=True, exist_ok=True)
        _write_json(run_root / "import_manifest.json", manifest.to_dict())

    for source in manifest.sources:
        if source.status == "missing" and not include_missing:
            summary["skipped_sources"].append(
                {
                    "source_name": source.source_name,
                    "status": source.status,
                    "reason": "missing_and_not_requested",
                }
            )
            continue

        source_dir = run_root / _safe_slug(source.source_name)
        inventory_path = source_dir / "inventory.json"
        inventory = build_local_source_inventory(source, sample_limit=sample_limit)
        source_manifest = _source_manifest(
            source,
            inventory_path=inventory_path,
            release_version=release_version,
        )
        source_result = {
            "source_name": source.source_name,
            "status": source.status,
            "category": source.category,
            "present_root_count": len(source.present_roots),
            "missing_root_count": len(source.missing_roots),
            "present_file_count": inventory["present_file_count"],
            "present_total_bytes": inventory["present_total_bytes"],
            "inventory_path": _path_ref(inventory_path),
            "manifest_path": _path_ref(source_dir / "manifest.json"),
            "load_hints": list(source.load_hints),
            "join_keys": list(source.join_keys),
            "inventory_fingerprint": inventory["inventory_fingerprint"],
            "inventory_fingerprint_version": inventory["inventory_fingerprint_version"],
        }
        summary["imported_sources"].append(source_result)
        if dry_run:
            continue
        _write_json(inventory_path, inventory)
        _write_json(source_dir / "manifest.json", source_manifest)

    summary["imported_source_count"] = len(summary["imported_sources"])
    summary["skipped_source_count"] = len(summary["skipped_sources"])
    summary_path = resolved_raw_root / "local_registry_runs" / f"{stamp}.json"
    latest_path = resolved_raw_root / "local_registry_runs" / "LATEST.json"
    summary["summary_path"] = _path_ref(summary_path)
    summary["latest_path"] = _path_ref(latest_path)
    summary["latest_updated"] = False
    summary["latest_update_reason"] = (
        "dry_run" if dry_run else "scoped_import_did_not_advance_latest"
    )
    if not dry_run:
        if summary["authoritative_refresh"]:
            summary["latest_updated"] = True
            summary["latest_update_reason"] = "authoritative_full_refresh"
        _write_json(summary_path, summary)
        if summary["authoritative_refresh"]:
            _write_json(latest_path, summary)
    return summary


__all__ = [
    "DEFAULT_RAW_ROOT",
    "build_local_source_inventory",
    "build_bio_agent_lab_context_registry",
    "mirror_local_sources",
    "summarize_local_root",
]
