from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_MANIFEST = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "runs"
    / "real_data_benchmark"
    / "full_results"
    / "versioned_release_bundle_manifest.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


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


def _artifact_tag(kind: str, role: str) -> str:
    return f"{kind}:{role}"


def _tagged_manifest_entry(
    *,
    kind: str,
    role: str,
    path_value: str,
    present: bool,
    required: bool,
) -> dict[str, Any]:
    resolved_path = _resolve_path(path_value)
    exists = resolved_path.exists()
    checksum = _sha256(resolved_path) if present and exists else None
    size_bytes = resolved_path.stat().st_size if present and exists else 0
    return {
        "tag": _artifact_tag(kind, role),
        "kind": kind,
        "role": role,
        "path": path_value,
        "resolved_path": str(resolved_path).replace("\\", "/"),
        "present": present and exists,
        "required": required,
        "size_bytes": size_bytes,
        "sha256": checksum,
    }


def build_release_bundle(
    *,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
    output_path: Path = DEFAULT_OUTPUT,
    bundle_version: str | None = None,
    bundle_tag_prefix: str = "release-bundle",
) -> dict[str, Any]:
    source_manifest = _read_json(source_manifest_path)
    source_manifest_checksum = _sha256(source_manifest_path)
    bundle_id = str(source_manifest.get("bundle_id") or source_manifest_path.stem)
    version = bundle_version or str(source_manifest.get("bundle_version") or "v1")
    bundle_tag = f"{bundle_tag_prefix}:{bundle_id}@{version}"

    tagged_manifests: list[dict[str, Any]] = [
        {
            "tag": _artifact_tag("source_manifest", "release_bundle_manifest"),
            "kind": "source_manifest",
            "role": "release_bundle_manifest",
            "path": str(source_manifest_path).replace("\\", "/"),
            "resolved_path": str(source_manifest_path.resolve()).replace("\\", "/"),
            "present": True,
            "required": True,
            "size_bytes": source_manifest_path.stat().st_size,
            "sha256": source_manifest_checksum,
        }
    ]
    checksum_index = {
        tagged_manifests[0]["tag"]: source_manifest_checksum,
    }

    missing_required: list[dict[str, Any]] = []
    for section_name, kind in (
        ("release_artifacts", "release_artifact"),
        ("supporting_artifacts", "supporting_artifact"),
    ):
        for item in source_manifest.get(section_name, []):
            if not isinstance(item, dict):
                continue
            path_value = str(item.get("path") or "")
            if not path_value:
                continue
            present = bool(item.get("present", False))
            required = bool(item.get("required", False))
            entry = _tagged_manifest_entry(
                kind=kind,
                role=str(item.get("role") or "unknown"),
                path_value=path_value,
                present=present,
                required=required,
            )
            tagged_manifests.append(entry)
            if entry["sha256"] is not None:
                checksum_index[entry["tag"]] = entry["sha256"]
            if entry["required"] and not entry["present"]:
                missing_required.append(
                    {
                        "tag": entry["tag"],
                        "role": entry["role"],
                        "path": entry["path"],
                    }
                )

    if missing_required:
        details = ", ".join(
            f"{item['tag']} ({item['path']})" for item in missing_required
        )
        raise FileNotFoundError(f"missing required release artifacts: {details}")

    payload = dict(source_manifest)
    payload.update(
        {
            "bundle_version": version,
            "bundle_tag": bundle_tag,
            "bundle_status": "assembled_with_checksums",
            "generated_at": datetime.now(UTC).isoformat(),
            "source_manifest": {
                "path": str(source_manifest_path).replace("\\", "/"),
                "sha256": source_manifest_checksum,
            },
            "tagged_manifests": tagged_manifests,
            "checksums": {
                "source_manifest_sha256": source_manifest_checksum,
                "artifact_sha256_index": checksum_index,
            },
            "missing_required_artifacts": [],
            "validation_status": "passed",
            "validation_errors": [],
        }
    )

    _write_json(output_path, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a versioned release bundle manifest with tagged artifacts and checksums."
        )
    )
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bundle-version", type=str, default=None)
    parser.add_argument("--bundle-tag-prefix", type=str, default="release-bundle")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_release_bundle(
        source_manifest_path=args.source_manifest,
        output_path=args.output,
        bundle_version=args.bundle_version,
        bundle_tag_prefix=args.bundle_tag_prefix,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
