from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = REPO_ROOT
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "runtime" / "recovered_release_state"
DEFAULT_REPORT_NAME = "rollback_release_report.json"
RELEASE_BUNDLE_MANIFEST_PATH = (
    Path("runs") / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)
VERSIONED_RELEASE_BUNDLE_MANIFEST_PATH = (
    Path("runs")
    / "real_data_benchmark"
    / "full_results"
    / "versioned_release_bundle_manifest.json"
)


class RollbackReleaseError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class RollbackItem:
    role: str
    section: str
    source_path: Path
    destination_path: Path
    required: bool
    present: bool


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RollbackReleaseError(f"manifest must be a JSON object: {path}")
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


def _resolve_path(root: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else root / path


def _copy_item(item: RollbackItem, output_root: Path) -> dict[str, Any]:
    destination_path = output_root / item.destination_path
    entry = {
        "role": item.role,
        "section": item.section,
        "required": item.required,
        "present": item.present,
        "source_path": str(item.source_path).replace("\\", "/"),
        "destination_path": str(destination_path).replace("\\", "/"),
        "copied": False,
        "sha256": None,
    }
    if item.present and item.source_path.exists():
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item.source_path, destination_path)
        entry["copied"] = True
        entry["sha256"] = _sha256(destination_path)
    return entry


def _collect_release_items(
    source_root: Path,
    release_manifest: dict[str, Any],
) -> list[RollbackItem]:
    items: list[RollbackItem] = [
        RollbackItem(
            role="release_bundle_manifest",
            section="manifest",
            source_path=source_root / RELEASE_BUNDLE_MANIFEST_PATH,
            destination_path=RELEASE_BUNDLE_MANIFEST_PATH,
            required=True,
            present=True,
        ),
        RollbackItem(
            role="versioned_release_bundle_manifest",
            section="manifest",
            source_path=source_root / VERSIONED_RELEASE_BUNDLE_MANIFEST_PATH,
            destination_path=VERSIONED_RELEASE_BUNDLE_MANIFEST_PATH,
            required=True,
            present=(source_root / VERSIONED_RELEASE_BUNDLE_MANIFEST_PATH).exists(),
        ),
    ]

    for section_name in ("release_artifacts", "supporting_artifacts"):
        for entry in release_manifest.get(section_name, []):
            if not isinstance(entry, dict):
                continue
            raw_path = entry.get("path")
            if not raw_path:
                continue
            items.append(
                RollbackItem(
                    role=str(entry.get("role") or "artifact"),
                    section=section_name,
                    source_path=_resolve_path(source_root, raw_path),
                    destination_path=Path(str(raw_path)),
                    required=bool(entry.get("required", False)),
                    present=bool(entry.get("present", True)),
                )
            )
    return items


def _versioned_manifest_lineage_ok(
    source_manifest_path: Path,
    versioned_manifest: dict[str, Any],
) -> bool:
    source_sha = _sha256(source_manifest_path)
    versioned_source = versioned_manifest.get("source_manifest", {})
    if not isinstance(versioned_source, dict):
        return False
    if versioned_source.get("sha256") != source_sha:
        return False
    checksums = versioned_manifest.get("checksums", {})
    if not isinstance(checksums, dict):
        return False
    return checksums.get("source_manifest_sha256") == source_sha


def _build_report(
    *,
    source_root: Path,
    output_root: Path,
    allow_partial: bool,
) -> tuple[dict[str, Any], bool]:
    source_manifest_path = source_root / RELEASE_BUNDLE_MANIFEST_PATH
    versioned_manifest_path = source_root / VERSIONED_RELEASE_BUNDLE_MANIFEST_PATH

    if not source_manifest_path.exists():
        raise RollbackReleaseError(f"release bundle manifest missing: {source_manifest_path}")
    if not versioned_manifest_path.exists():
        raise RollbackReleaseError(
            f"versioned release bundle manifest missing: {versioned_manifest_path}"
        )

    source_manifest = _read_json(source_manifest_path)
    versioned_manifest = _read_json(versioned_manifest_path)
    lineage_ok = _versioned_manifest_lineage_ok(source_manifest_path, versioned_manifest)

    items = _collect_release_items(source_root, source_manifest)
    missing_required: list[dict[str, Any]] = []
    missing_optional: list[dict[str, Any]] = []
    for item in items:
        present = item.present and item.source_path.exists()
        if not present:
            record = {
                "role": item.role,
                "section": item.section,
                "required": item.required,
                "present": False,
                "source_path": str(item.source_path).replace("\\", "/"),
                "destination_path": str(output_root / item.destination_path).replace(
                    "\\", "/"
                ),
            }
            if item.required:
                missing_required.append(record)
            else:
                missing_optional.append(record)

    if not lineage_ok:
        missing_required.append(
            {
                "role": "versioned_release_bundle_manifest",
                "section": "manifest",
                "required": True,
                "present": False,
                "source_path": str(versioned_manifest_path).replace("\\", "/"),
                "destination_path": str(
                    output_root / VERSIONED_RELEASE_BUNDLE_MANIFEST_PATH
                ).replace("\\", "/"),
                "reason": "versioned manifest lineage does not match the current release bundle",
            }
        )

    missing_count = len(missing_required) + len(missing_optional)
    if missing_required and not allow_partial:
        if output_root.exists():
            shutil.rmtree(output_root)
        raise RollbackReleaseError(
            "unsafe rollback conditions: "
            + ", ".join(item["role"] for item in missing_required)
        )

    copied_artifacts: list[dict[str, Any]] = []
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for item in items:
        copied_artifacts.append(_copy_item(item, output_root))

    report = {
        "task_id": "P23-T004",
        "generated_at": _utc_now(),
        "source_root": str(source_root).replace("\\", "/"),
        "output_root": str(output_root).replace("\\", "/"),
        "status": "partial_restore" if missing_required or missing_optional else "restored",
        "rollback": {
            "performed": bool(missing_required),
            "reason": (
                None
                if (allow_partial or not missing_required)
                else "unsafe rollback conditions"
            ),
        },
        "source_manifest": {
            "path": str(source_manifest_path).replace("\\", "/"),
            "sha256": _sha256(source_manifest_path),
            "bundle_id": source_manifest.get("bundle_id"),
            "status": source_manifest.get("status"),
        },
        "versioned_manifest": {
            "path": str(versioned_manifest_path).replace("\\", "/"),
            "bundle_id": versioned_manifest.get("bundle_id"),
            "bundle_tag": versioned_manifest.get("bundle_tag"),
            "bundle_version": versioned_manifest.get("bundle_version"),
            "bundle_status": versioned_manifest.get("bundle_status"),
            "lineage_ok": lineage_ok,
        },
        "artifacts": {
            "copied_artifacts": copied_artifacts,
            "missing_artifacts": missing_required + missing_optional,
            "missing_count": missing_count,
            "required_missing_count": len(missing_required),
        },
        "truth_boundary": {
            "report_only": True,
            "non_mutating": True,
            "orphaning_prevented": True,
            "allow_partial": allow_partial,
            "unsafe_conditions_blocked": True,
        },
    }

    report_path = output_root / DEFAULT_REPORT_NAME
    _write_json(report_path, report)
    return report, bool(missing_required)


def rollback_release_state(
    *,
    source_root: str | Path | None = None,
    output_root: str | Path | None = None,
    allow_partial: bool = False,
) -> dict[str, Any]:
    resolved_source_root = Path(source_root or DEFAULT_SOURCE_ROOT).resolve()
    resolved_output_root = Path(output_root or DEFAULT_OUTPUT_ROOT).resolve()
    report, has_required_missing = _build_report(
        source_root=resolved_source_root,
        output_root=resolved_output_root,
        allow_partial=allow_partial,
    )
    if has_required_missing and not allow_partial:
        report["status"] = "blocked"
    return report


def recover_release_state(
    *,
    source_root: str | Path | None = None,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    return rollback_release_state(
        source_root=source_root,
        output_root=output_root,
        allow_partial=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rollback or recover release state from a paired bundle manifest."
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Allow partial recovery when optional artifacts are missing.",
    )
    parser.add_argument(
        "--report-json",
        action="store_true",
        help="Emit the rollback report as JSON (default behavior is also JSON).",
    )
    return parser.parse_args()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rollback or recover release state from a paired bundle manifest."
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Allow partial recovery when optional artifacts are missing.",
    )
    parser.add_argument(
        "--report-json",
        action="store_true",
        help="Emit the rollback report as JSON (default behavior is also JSON).",
    )
    args = parser.parse_args(argv)

    try:
        report = rollback_release_state(
            source_root=args.source_root,
            output_root=args.output_root,
            allow_partial=args.allow_partial,
        )
    except RollbackReleaseError as exc:
        failure_report = {
            "task_id": "P23-T004",
            "generated_at": _utc_now(),
            "status": "blocked",
            "error": str(exc),
            "truth_boundary": {
                "report_only": True,
                "non_mutating": True,
                "orphaning_prevented": True,
                "unsafe_conditions_blocked": True,
            },
        }
        print(json.dumps(failure_report, indent=2))
        return 1

    print(json.dumps(report, indent=2) if args.report_json else json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
