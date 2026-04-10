from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_MANIFEST = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "open_source_distribution_bundle"
)
DEFAULT_MANIFEST_NAME = "open_source_distribution_bundle_manifest.json"
DEFAULT_PUBLIC_SUPPORT_ROLES = (
    "run_manifest",
    "run_summary",
    "checkpoint_summary",
    "live_inputs",
    "summary",
    "full_results_readme",
    "cohort_manifest",
    "split_labels",
)


class PublishOpenSourceBundleError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PublishOpenSourceBundleError(f"manifest must be a JSON object: {path}")
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


def _stage_relative_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        try:
            return path.relative_to(REPO_ROOT)
        except ValueError:
            return Path(path.name)
    return path


def _artifact_tag(kind: str, role: str) -> str:
    return f"{kind}:{role}"


def _public_selection(
    source_manifest: dict[str, Any],
    *,
    public_support_roles: Sequence[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    skipped_support: list[dict[str, Any]] = []
    allowed_support_roles = set(public_support_roles)

    for section_name, visibility in (
        ("release_artifacts", "release"),
        ("supporting_artifacts", "support"),
    ):
        for item in source_manifest.get(section_name, []):
            if not isinstance(item, dict):
                continue
            path_value = str(item.get("path") or "")
            if not path_value:
                continue
            role = str(item.get("role") or "unknown")
            if visibility == "support" and role not in allowed_support_roles:
                skipped_support.append(
                    {
                        "role": role,
                        "path": path_value,
                        "reason": "not_public",
                    }
                )
                continue
            selected.append(
                {
                    "tag": _artifact_tag(f"{visibility}_artifact", role),
                    "kind": f"{visibility}_artifact",
                    "role": role,
                    "path": path_value,
                    "required": bool(item.get("required", False)) or True,
                    "visibility": visibility,
                }
            )
    return selected, skipped_support


def _stage_artifact(
    *,
    output_root: Path,
    entry: dict[str, Any],
) -> dict[str, Any]:
    source_path = _resolve_path(entry["path"])
    staged_path = output_root / "staged" / _stage_relative_path(entry["path"])
    staged_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, staged_path)
    return {
        "tag": entry["tag"],
        "kind": entry["kind"],
        "role": entry["role"],
        "visibility": entry["visibility"],
        "path": entry["path"],
        "resolved_source_path": str(source_path.resolve()).replace("\\", "/"),
        "staged_path": str(staged_path.resolve()).replace("\\", "/"),
        "present": True,
        "required": True,
        "size_bytes": staged_path.stat().st_size,
        "sha256": _sha256(staged_path),
    }


def build_open_source_bundle(
    *,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    bundle_version: str | None = None,
    distribution_prefix: str = "open-source-distribution",
    public_support_roles: Sequence[str] = DEFAULT_PUBLIC_SUPPORT_ROLES,
) -> dict[str, Any]:
    if not source_manifest_path.exists():
        raise FileNotFoundError(f"missing release bundle manifest: {source_manifest_path}")

    source_manifest = _read_json(source_manifest_path)
    source_manifest_checksum = _sha256(source_manifest_path)
    bundle_id = str(source_manifest.get("bundle_id") or source_manifest_path.stem)
    version = bundle_version or str(source_manifest.get("bundle_version") or "v1")
    distribution_tag = f"{distribution_prefix}:{bundle_id}@{version}"

    selected_artifacts, skipped_support = _public_selection(
        source_manifest, public_support_roles=public_support_roles
    )
    missing_selected: list[dict[str, Any]] = []
    for entry in selected_artifacts:
        resolved_path = _resolve_path(entry["path"])
        if not resolved_path.exists() or not bool(
            next(
                (
                    item.get("present", False)
                    for item in (
                        source_manifest.get("release_artifacts", [])
                        + source_manifest.get("supporting_artifacts", [])
                    )
                    if isinstance(item, dict)
                    and str(item.get("path") or "") == entry["path"]
                ),
                False,
            )
        ):
            missing_selected.append(
                {
                    "tag": entry["tag"],
                    "role": entry["role"],
                    "path": entry["path"],
                }
            )

    if missing_selected:
        details = ", ".join(
            f"{item['tag']} ({item['path']})" for item in missing_selected
        )
        raise FileNotFoundError(f"missing required public release artifacts: {details}")

    staged_artifacts = [
        _stage_artifact(output_root=output_root, entry=entry) for entry in selected_artifacts
    ]
    staged_index = {entry["tag"]: entry["sha256"] for entry in staged_artifacts}
    selected_release = [item for item in selected_artifacts if item["visibility"] == "release"]
    selected_support = [item for item in selected_artifacts if item["visibility"] == "support"]

    payload = {
        "artifact_id": "open_source_distribution_bundle_manifest",
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "bundle_id": bundle_id,
        "bundle_version": version,
        "distribution_tag": distribution_tag,
        "bundle_tag": distribution_tag,
        "bundle_status": "staged_with_checksums",
        "publication_posture": (
            "staged_with_blockers"
            if str(source_manifest.get("status") or "").endswith("with_blockers")
            else "staged"
        ),
        "release_status": source_manifest.get("status"),
        "release_ready": False,
        "source_manifest": {
            "path": str(source_manifest_path).replace("\\", "/"),
            "sha256": source_manifest_checksum,
        },
        "staging_root": str(output_root.resolve()).replace("\\", "/"),
        "staged_manifest_path": str(
            (output_root / DEFAULT_MANIFEST_NAME).resolve()
        ).replace("\\", "/"),
        "public_support_roles": list(public_support_roles),
        "staged_artifacts": staged_artifacts,
        "staged_artifact_sha256_index": staged_index,
        "selected_artifact_count": len(selected_artifacts),
        "staged_artifact_count": len(staged_artifacts),
        "selected_release_artifact_count": len(selected_release),
        "selected_support_artifact_count": len(selected_support),
        "excluded_support_artifacts": skipped_support,
        "missing_required_artifacts": [],
        "carry_through": {
            "blocker_categories": list(source_manifest.get("blocker_categories", [])),
            "release_status": source_manifest.get("status"),
        },
        "truth_boundary": {
            "report_only": True,
            "fail_closed": True,
            "forbidden_overclaims": [
                "release readiness without all public artifacts present",
                "silent inclusion of non-public support artifacts",
                "bundle publication without pinned source lineage",
                "bundle publication without staged artifact checksums",
            ],
        },
        "validation_status": "passed",
        "validation_errors": [],
        "validation_warnings": (
            ["release_not_ready"]
            if str(source_manifest.get("status") or "").endswith("with_blockers")
            else []
        ),
    }

    output_manifest_path = output_root / DEFAULT_MANIFEST_NAME
    _write_json(output_manifest_path, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage a public open-source distribution bundle from the release manifest."
    )
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--bundle-version", type=str, default=None)
    parser.add_argument(
        "--distribution-prefix",
        type=str,
        default="open-source-distribution",
    )
    parser.add_argument(
        "--public-support-role",
        action="append",
        dest="public_support_roles",
        type=str,
        help="Override or extend the default public support roles. Repeat for multiple roles.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    public_support_roles = args.public_support_roles or list(DEFAULT_PUBLIC_SUPPORT_ROLES)
    try:
        payload = build_open_source_bundle(
            source_manifest_path=args.source_manifest,
            output_root=args.output_root,
            bundle_version=args.bundle_version,
            distribution_prefix=args.distribution_prefix,
            public_support_roles=public_support_roles,
        )
    except FileNotFoundError as exc:
        failure_payload = {
            "artifact_id": "open_source_distribution_bundle_manifest",
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
