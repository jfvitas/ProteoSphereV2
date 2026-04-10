from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_MANIFESTS = (
    REPO_ROOT / "data" / "raw" / "local_registry" / "20260330T222435Z" / "demo" / "manifest.json",
    REPO_ROOT
    / "data"
    / "raw"
    / "local_registry"
    / "20260330T222435Z"
    / "training_examples"
    / "manifest.json",
)
DEFAULT_TUTORIAL_DOCS = (
    REPO_ROOT / "docs" / "reports" / "training_set_candidate_package_manifest_preview.md",
    REPO_ROOT / "docs" / "reports" / "package_readiness_preview.md",
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "sample_project_tutorial_package_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "sample_project_tutorial_package_preview.md"
DEFAULT_PACKAGE_ID = "sample-projects-and-tutorials"
DEFAULT_PACKAGE_VERSION = "v1"
DEFAULT_PACKAGE_TAG_PREFIX = "release-user-sample-package"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _iso_timestamp(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


def _latest_mtime(path: Path) -> float | None:
    if not path.exists():
        return None
    if path.is_file():
        return path.stat().st_mtime
    latest: float | None = path.stat().st_mtime
    for child in path.rglob("*"):
        if child.is_file():
            latest = child.stat().st_mtime if latest is None else max(latest, child.stat().st_mtime)
    return latest


def _directory_fingerprint(path: Path) -> str | None:
    if not path.exists() or not path.is_dir():
        return None
    digest = hashlib.sha256()
    for child in sorted(path.rglob("*")):
        if not child.is_file():
            continue
        relative = child.relative_to(path).as_posix()
        stat = child.stat()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _path_snapshot(path: Path, *, required: bool = True) -> dict[str, Any]:
    exists = path.exists()
    kind = "missing"
    if exists:
        kind = "directory" if path.is_dir() else "file"
    file_count = 0
    size_bytes = 0
    sha256 = None
    fingerprint = None
    if exists and path.is_file():
        size_bytes = path.stat().st_size
        file_count = 1
        sha256 = _sha256(path)
    elif exists and path.is_dir():
        files = [child for child in path.rglob("*") if child.is_file()]
        file_count = len(files)
        size_bytes = sum(child.stat().st_size for child in files)
        fingerprint = _directory_fingerprint(path)
    latest_mtime = _latest_mtime(path)
    resolved_path = path.resolve() if exists else path
    return {
        "path": str(path).replace("\\", "/"),
        "resolved_path": str(resolved_path).replace("\\", "/"),
        "required": required,
        "present": exists,
        "kind": kind,
        "size_bytes": size_bytes,
        "file_count": file_count,
        "latest_mtime": _iso_timestamp(latest_mtime),
        "sha256": sha256,
        "fingerprint": fingerprint,
    }


def _manifest_component(path: Path) -> dict[str, Any]:
    manifest = _read_json(path)
    local_refs = [
        str(item)
        for item in manifest.get("local_artifact_refs") or []
        if str(item).strip()
    ]
    manifest_snapshot = _path_snapshot(path)
    ref_snapshots = [_path_snapshot(_resolve_path(ref)) for ref in local_refs]
    missing_refs = [snapshot for snapshot in ref_snapshots if not snapshot["present"]]
    freshness_candidates = [path.stat().st_mtime]
    freshness_candidates.extend(
        _latest_mtime(_resolve_path(ref)) or 0 for ref in local_refs
    )
    freshness_anchor = max(freshness_candidates)
    return {
        "component_kind": "sample_project",
        "manifest_path": manifest_snapshot["path"],
        "manifest": {
            "manifest_id": str(manifest.get("manifest_id") or path.stem),
            "source_name": str(manifest.get("source_name") or path.parent.name),
            "release_version": str(manifest.get("release_version") or ""),
            "release_date": manifest.get("release_date"),
            "retrieval_mode": manifest.get("retrieval_mode"),
            "source_locator": manifest.get("source_locator"),
            "local_artifact_refs": local_refs,
            "provenance": list(manifest.get("provenance") or []),
            "reproducibility_metadata": list(manifest.get("reproducibility_metadata") or []),
            "snapshot_fingerprint": manifest.get("snapshot_fingerprint"),
        },
        "manifest_snapshot": manifest_snapshot,
        "local_artifact_refs": ref_snapshots,
        "missing_local_artifact_refs": missing_refs,
        "freshness_anchor": _iso_timestamp(freshness_anchor),
        "freshness_anchor_epoch": freshness_anchor,
    }


def _doc_snapshot(path: Path, *, freshness_anchor_epoch: float) -> dict[str, Any]:
    snapshot = _path_snapshot(path)
    if not snapshot["present"]:
        return snapshot
    latest_mtime = _latest_mtime(path)
    stale = bool(latest_mtime is not None and latest_mtime < freshness_anchor_epoch)
    return {
        **snapshot,
        "component_kind": "tutorial_doc",
        "stale": stale,
        "freshness_anchor": _iso_timestamp(freshness_anchor_epoch),
        "doc_title": path.stem.replace("_", " "),
    }


def _truth_boundary() -> dict[str, Any]:
    return {
        "summary": (
            "This package preview is report-only. It packages sample projects and tutorials "
            "for release users, but it does not authorize release, mutate inputs, or "
            "silently accept missing artifacts or stale docs."
        ),
        "report_only": True,
        "non_mutating": True,
        "package_not_authorized": True,
        "missing_artifacts_block_package": True,
        "stale_docs_block_package": True,
    }


def build_sample_project_package(
    *,
    source_manifest_paths: tuple[Path, ...] = DEFAULT_SOURCE_MANIFESTS,
    tutorial_doc_paths: tuple[Path, ...] = DEFAULT_TUTORIAL_DOCS,
    output_json: Path = DEFAULT_OUTPUT_JSON,
    output_md: Path = DEFAULT_OUTPUT_MD,
    package_id: str = DEFAULT_PACKAGE_ID,
    package_version: str = DEFAULT_PACKAGE_VERSION,
    package_tag_prefix: str = DEFAULT_PACKAGE_TAG_PREFIX,
) -> dict[str, Any]:
    source_components: list[dict[str, Any]] = []
    missing_artifacts: list[dict[str, Any]] = []
    for manifest_path in source_manifest_paths:
        resolved_manifest = _resolve_path(manifest_path)
        if not resolved_manifest.exists():
            missing_artifacts.append(
                {
                    "kind": "source_manifest",
                    "path": str(resolved_manifest).replace("\\", "/"),
                }
            )
            continue
        component = _manifest_component(resolved_manifest)
        source_components.append(component)
        missing_artifacts.extend(
            {
                "kind": "sample_project_artifact",
                "source_name": component["manifest"]["source_name"],
                "manifest_id": component["manifest"]["manifest_id"],
                "path": item["path"],
            }
            for item in component["missing_local_artifact_refs"]
        )

    if missing_artifacts:
        details = ", ".join(
            f"{item.get('kind')}:{item.get('path')}" for item in missing_artifacts
        )
        raise FileNotFoundError(f"missing required sample project artifacts: {details}")

    if not source_components:
        raise FileNotFoundError("no sample project manifests were found")

    freshness_anchor_epoch = max(
        component["freshness_anchor_epoch"] for component in source_components
    )
    tutorial_components: list[dict[str, Any]] = []
    stale_docs: list[dict[str, Any]] = []
    for tutorial_path in tutorial_doc_paths:
        resolved_tutorial = _resolve_path(tutorial_path)
        snapshot = _doc_snapshot(
            resolved_tutorial,
            freshness_anchor_epoch=freshness_anchor_epoch,
        )
        if not snapshot["present"]:
            raise FileNotFoundError(
                f"missing required tutorial doc: {snapshot['path']}"
            )
        tutorial_components.append(snapshot)
        if snapshot.get("stale"):
            stale_docs.append(snapshot)

    if stale_docs:
        details = ", ".join(item["path"] for item in stale_docs)
        raise ValueError(f"stale tutorial docs block release packaging: {details}")

    package_tag = f"{package_tag_prefix}:{package_id}@{package_version}"
    generated_at = datetime.now(UTC).isoformat()

    tutorial_latest_mtime = max(
        (datetime.fromisoformat(item["latest_mtime"]).timestamp() for item in tutorial_components),
        default=freshness_anchor_epoch,
    )
    payload = {
        "artifact_id": "sample_project_tutorial_package_preview",
        "schema_id": "proteosphere-sample-project-tutorial-package-preview-2026-04-03",
        "status": "report_only",
        "generated_at": generated_at,
        "package_identity": {
            "package_kind": "sample_project_tutorial_release_package",
            "package_id": package_id,
            "package_version": package_version,
            "package_tag": package_tag,
            "release_user_ready": True,
            "package_authorization_required": True,
        },
        "source_artifacts": {
            "sample_project_manifests": [
                component["manifest_path"] for component in source_components
            ],
            "tutorial_docs": [component["path"] for component in tutorial_components],
        },
        "summary": {
            "sample_project_count": len(source_components),
            "tutorial_doc_count": len(tutorial_components),
            "sample_project_names": [
                component["manifest"]["source_name"] for component in source_components
            ],
            "missing_artifact_count": 0,
            "stale_doc_count": 0,
            "freshness_anchor": _iso_timestamp(freshness_anchor_epoch),
            "newest_tutorial_doc_mtime": _iso_timestamp(tutorial_latest_mtime),
            "release_user_ready": True,
        },
        "sample_projects": source_components,
        "tutorial_docs": tutorial_components,
        "truth_boundary": _truth_boundary(),
    }
    _write_json(output_json, payload)
    _write_text(output_md, render_markdown(payload))
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Sample Project and Tutorial Package Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Package tag: `{payload.get('package_identity', {}).get('package_tag')}`",
        f"- Release-user ready: `{summary.get('release_user_ready')}`",
        f"- Sample project count: `{summary.get('sample_project_count')}`",
        f"- Tutorial doc count: `{summary.get('tutorial_doc_count')}`",
        "",
        "## Sample Projects",
        "",
        "| Source | Manifest | Release version | Local refs |",
        "| --- | --- | --- | --- |",
    ]
    for component in payload.get("sample_projects") or []:
        manifest = component.get("manifest") or {}
        lines.append(
            "| "
            + f"`{manifest.get('source_name')}` | "
            + f"`{manifest.get('manifest_id')}` | "
            + f"{manifest.get('release_version')} | "
            + f"{len(component.get('local_artifact_refs') or [])} |"
        )
    lines.extend(
        [
            "",
            "## Tutorials",
            "",
            "| Doc | Freshness | Mtime |",
            "| --- | --- | --- |",
        ]
    )
    for doc in payload.get("tutorial_docs") or []:
        lines.append(
            "| "
            + f"`{doc.get('doc_title')}` | "
            + f"{'stale' if doc.get('stale') else 'fresh'} | "
            + f"{doc.get('latest_mtime')} |"
        )
    truth_boundary = payload.get("truth_boundary") or {}
    if truth_boundary.get("summary"):
        lines.extend(["", "## Truth Boundary", "", f"- {truth_boundary['summary']}"])
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package sample projects and tutorial docs for release users."
    )
    parser.add_argument(
        "--source-manifest",
        type=Path,
        action="append",
        dest="source_manifests",
        default=None,
    )
    parser.add_argument(
        "--tutorial-doc",
        type=Path,
        action="append",
        dest="tutorial_docs",
        default=None,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--package-id", type=str, default=DEFAULT_PACKAGE_ID)
    parser.add_argument("--package-version", type=str, default=DEFAULT_PACKAGE_VERSION)
    parser.add_argument("--package-tag-prefix", type=str, default=DEFAULT_PACKAGE_TAG_PREFIX)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_manifests = tuple(args.source_manifests or DEFAULT_SOURCE_MANIFESTS)
    tutorial_docs = tuple(args.tutorial_docs or DEFAULT_TUTORIAL_DOCS)
    payload = build_sample_project_package(
        source_manifest_paths=source_manifests,
        tutorial_doc_paths=tutorial_docs,
        output_json=args.output_json,
        output_md=args.output_md,
        package_id=args.package_id,
        package_version=args.package_version,
        package_tag_prefix=args.package_tag_prefix,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
