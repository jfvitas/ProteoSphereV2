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
DEFAULT_SUPPORT_MANIFEST = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_support_manifest.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "ga_tagged_release_manifest.json"
)


class TagReleaseError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TagReleaseError(f"manifest must be a JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else REPO_ROOT / path


def _manifest_pin(
    *,
    pin_type: str,
    role: str,
    path: Path,
    required: bool = True,
) -> dict[str, Any]:
    present = path.exists()
    return {
        "pin_type": pin_type,
        "role": role,
        "path": str(path).replace("\\", "/"),
        "resolved_path": str(path.resolve()).replace("\\", "/"),
        "present": present,
        "required": required,
        "size_bytes": path.stat().st_size if present else 0,
        "sha256": _sha256(path) if present else None,
    }


def _artifact_pin(
    *,
    kind: str,
    role: str,
    path_value: str,
    required: bool,
) -> dict[str, Any]:
    resolved_path = _resolve_path(path_value)
    present = resolved_path.exists()
    return {
        "pin_type": kind,
        "role": role,
        "path": path_value,
        "resolved_path": str(resolved_path).replace("\\", "/"),
        "present": present,
        "required": required,
        "size_bytes": resolved_path.stat().st_size if present else 0,
        "sha256": _sha256(resolved_path) if present else None,
    }


def _validate_manifest_lineage(
    *,
    source_manifest: dict[str, Any],
    support_manifest: dict[str, Any],
    source_manifest_path: Path,
) -> None:
    support_source = support_manifest.get("source_manifest")
    if not isinstance(support_source, dict):
        raise TagReleaseError("support manifest is missing source_manifest lineage")

    source_sha = _sha256(source_manifest_path)
    if support_source.get("sha256") != source_sha:
        raise TagReleaseError("support manifest lineage does not match the source manifest")

    bundle_id = str(source_manifest.get("bundle_id") or "")
    if not bundle_id:
        raise TagReleaseError("source manifest is missing bundle_id")
    if str(support_manifest.get("bundle_id") or "") != bundle_id:
        raise TagReleaseError("support manifest bundle_id does not match the source manifest")

    release_status = str(source_manifest.get("status") or "")
    if str(support_manifest.get("release_status") or "") != release_status:
        raise TagReleaseError("support manifest release_status does not match the source manifest")

    if support_manifest.get("truth_boundary") != source_manifest.get("truth_boundary"):
        raise TagReleaseError("support manifest truth boundary does not match the source manifest")


def _collect_artifact_pins(source_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    artifact_pins: list[dict[str, Any]] = []
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
            pin = _artifact_pin(
                kind=kind,
                role=str(item.get("role") or "unknown"),
                path_value=path_value,
                required=bool(item.get("required", False)),
            )
            if pin["required"] and not pin["present"]:
                raise FileNotFoundError(
                    f"missing required release artifact: {pin['role']} ({pin['path']})"
                )
            artifact_pins.append(pin)
    return artifact_pins


def build_tagged_release(
    *,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
    support_manifest_path: Path = DEFAULT_SUPPORT_MANIFEST,
    output_path: Path = DEFAULT_OUTPUT,
    bundle_version: str | None = None,
    release_prefix: str = "ga-release",
    release_id: str | None = None,
) -> dict[str, Any]:
    if not source_manifest_path.exists():
        raise FileNotFoundError(f"missing release bundle manifest: {source_manifest_path}")
    if not support_manifest_path.exists():
        raise FileNotFoundError(f"missing release support manifest: {support_manifest_path}")

    source_manifest = _read_json(source_manifest_path)
    support_manifest = _read_json(support_manifest_path)
    _validate_manifest_lineage(
        source_manifest=source_manifest,
        support_manifest=support_manifest,
        source_manifest_path=source_manifest_path,
    )

    bundle_id = str(source_manifest["bundle_id"])
    version = (
        bundle_version
        or str(support_manifest.get("bundle_version") or "")
        or str(source_manifest.get("bundle_version") or "")
        or "v1"
    )
    pinned_release_id = release_id or f"{bundle_id}@{version}"
    pinned_release_tag = f"{release_prefix}:{pinned_release_id}"

    manifest_pins = [
        _manifest_pin(
            pin_type="source_manifest",
            role="release_bundle_manifest",
            path=source_manifest_path,
            required=True,
        ),
        _manifest_pin(
            pin_type="support_manifest",
            role="release_support_manifest",
            path=support_manifest_path,
            required=True,
        ),
    ]
    artifact_pins = _collect_artifact_pins(source_manifest)

    required_artifact_pins = [item for item in artifact_pins if item["required"]]
    pin_status = "aligned" if all(item["present"] for item in artifact_pins) else "attention"
    release_ready = False

    payload = {
        "artifact_id": "ga_tagged_release_manifest",
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "bundle_id": bundle_id,
        "bundle_version": version,
        "release_id": pinned_release_id,
        "release_tag": pinned_release_tag,
        "bundle_tag": pinned_release_tag,
        "release_status": source_manifest.get("status"),
        "release_ready": release_ready,
        "release_gate_status": source_manifest.get("status"),
        "release_posture": "tagged_with_blockers",
        "tag_status": "pinned_with_checksums",
        "pinning_status": pin_status,
        "source_manifest": {
            "path": str(source_manifest_path).replace("\\", "/"),
            "sha256": _sha256(source_manifest_path),
            "status": source_manifest.get("status"),
        },
        "support_manifest": {
            "path": str(support_manifest_path).replace("\\", "/"),
            "sha256": _sha256(support_manifest_path),
            "bundle_tag": support_manifest.get("bundle_tag"),
            "bundle_version": support_manifest.get("bundle_version"),
            "release_status": support_manifest.get("release_status"),
        },
        "manifest_pins": manifest_pins,
        "artifact_pins": artifact_pins,
        "pinned_required_artifacts": len(required_artifact_pins),
        "pin_summary": {
            "manifest_pin_count": len(manifest_pins),
            "artifact_pin_count": len(artifact_pins),
            "required_artifact_pin_count": len(required_artifact_pins),
            "present_artifact_pin_count": sum(1 for item in artifact_pins if item["present"]),
        },
        "source_release_profile": {
            "blocker_categories": list(source_manifest.get("blocker_categories", [])),
            "truth_boundary": source_manifest.get("truth_boundary", {}),
            "release_artifact_count": len(source_manifest.get("release_artifacts", [])),
            "supporting_artifact_count": len(source_manifest.get("supporting_artifacts", [])),
        },
        "truth_boundary": {
            "report_only": True,
            "fail_closed": True,
            "forbidden_overclaims": [
                "ga release readiness without evidence-backed pinning",
                "manifest tagging without pinned source/support lineage",
                "silent release-id drift",
                "silent version drift",
            ],
        },
        "validation_status": "passed",
        "validation_errors": [],
        "validation_warnings": [],
    }

    if not release_ready:
        payload["validation_warnings"].append("release_not_ready")

    _write_json(output_path, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a GA-tagged release manifest with pinned source and support lineage."
    )
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--support-manifest", type=Path, default=DEFAULT_SUPPORT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bundle-version", type=str, default=None)
    parser.add_argument("--release-prefix", type=str, default="ga-release")
    parser.add_argument("--release-id", type=str, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = build_tagged_release(
            source_manifest_path=args.source_manifest,
            support_manifest_path=args.support_manifest,
            output_path=args.output,
            bundle_version=args.bundle_version,
            release_prefix=args.release_prefix,
            release_id=args.release_id,
        )
    except (FileNotFoundError, TagReleaseError) as exc:
        failure_payload = {
            "artifact_id": "ga_tagged_release_manifest",
            "generated_at": datetime.now(UTC).isoformat(),
            "status": "blocked",
            "error": str(exc),
            "truth_boundary": {
                "report_only": True,
                "fail_closed": True,
            },
        }
        print(json.dumps(failure_payload, indent=2))
        raise SystemExit(1) from None

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
