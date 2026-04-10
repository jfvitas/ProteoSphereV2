from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "artifacts" / "status" / "summary_library_inventory.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "summary_library_inventory.schema_v2.json"
CURRENT_SCHEMA_VERSION = 2


class SchemaMigrationError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


MigrationStep = Callable[[dict[str, Any]], dict[str, Any]]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SchemaMigrationError(f"schema artifact must be a JSON object: {path}")
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


def _resolved_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _validate_schema_version(payload: dict[str, Any], *, label: str) -> int:
    raw_version = payload.get("schema_version")
    if not isinstance(raw_version, int):
        raise SchemaMigrationError(f"{label} schema_version must be an integer")
    if raw_version < 1:
        raise SchemaMigrationError(f"{label} schema_version must be >= 1")
    return raw_version


def _assert_additive_top_level_migration(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    allowed_changed_keys: set[str],
) -> None:
    removed_keys = [
        key
        for key in before
        if key not in after and key not in allowed_changed_keys
    ]
    if removed_keys:
        raise SchemaMigrationError(
            "schema migration must not remove top-level keys: "
            + ", ".join(sorted(removed_keys))
        )

    changed_keys = [
        key
        for key in before
        if key in after and before[key] != after[key] and key not in allowed_changed_keys
    ]
    if changed_keys:
        raise SchemaMigrationError(
            "schema migration must be additive for pinned artifacts; unexpected changes: "
            + ", ".join(sorted(changed_keys))
        )


def _upgrade_schema_v1_to_v2(payload: dict[str, Any]) -> dict[str, Any]:
    upgraded = copy.deepcopy(payload)
    upgraded["schema_version"] = 2
    upgraded["schema_version_history"] = [1, 2]
    upgraded["schema_migration"] = {
        "status": "upgraded",
        "upgrade_policy": "forward_only",
        "safe_upgrade": True,
        "source_schema_version": 1,
        "target_schema_version": 2,
        "applied_migrations": ["schema_version 1 -> 2"],
        "preserved_truth_boundary": True,
    }
    return upgraded


MIGRATIONS: dict[int, MigrationStep] = {
    1: _upgrade_schema_v1_to_v2,
}


def migrate_schema_payload(
    payload: dict[str, Any],
    *,
    target_schema_version: int = CURRENT_SCHEMA_VERSION,
) -> tuple[dict[str, Any], dict[str, Any]]:
    working = copy.deepcopy(payload)
    source_schema_version = _validate_schema_version(working, label="source artifact")

    if target_schema_version > CURRENT_SCHEMA_VERSION:
        raise SchemaMigrationError(
            f"unsupported target schema_version {target_schema_version}; "
            f"latest supported version is {CURRENT_SCHEMA_VERSION}"
        )
    if source_schema_version > target_schema_version:
        raise SchemaMigrationError(
            "downgrades are not supported by the schema migration framework"
        )

    applied: list[str] = []
    if source_schema_version < target_schema_version:
        for version in range(source_schema_version, target_schema_version):
            step = MIGRATIONS.get(version)
            if step is None:
                raise SchemaMigrationError(
                    f"no forward migration registered for schema_version {version}"
                )
            before = copy.deepcopy(working)
            working = step(working)
            _validate_schema_version(working, label="migrated artifact")
            _assert_additive_top_level_migration(
                before,
                working,
                allowed_changed_keys={
                    "schema_version",
                    "schema_version_history",
                    "schema_migration",
                },
            )
            applied.append(f"schema_version {version} -> {version + 1}")

    migration_report = {
        "status": "upgraded" if applied else "current",
        "safe_upgrade": True,
        "upgrade_policy": "forward_only",
        "source_schema_version": source_schema_version,
        "target_schema_version": target_schema_version,
        "applied_migrations": applied,
        "current_schema_version": working["schema_version"],
        "schema_version_history": working.get("schema_version_history", [source_schema_version]),
    }
    return working, migration_report


def migrate_schema_file(
    input_path: Path,
    output_path: Path,
    *,
    target_schema_version: int = CURRENT_SCHEMA_VERSION,
) -> dict[str, Any]:
    source_payload = _read_json(input_path)
    migrated_payload, report = migrate_schema_payload(
        source_payload,
        target_schema_version=target_schema_version,
    )
    report = dict(report)
    report.update(
        {
            "input_path": str(input_path).replace("\\", "/"),
            "output_path": str(output_path).replace("\\", "/"),
            "input_sha256": _sha256(input_path),
        }
    )
    _write_json(output_path, migrated_payload)
    report["output_sha256"] = _sha256(output_path)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upgrade pinned artifact schema versions safely and forward-only."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--target-schema-version",
        type=int,
        default=CURRENT_SCHEMA_VERSION,
    )
    parser.add_argument(
        "--report-json",
        action="store_true",
        help="Emit the migration report as JSON instead of the upgraded payload.",
    )
    return parser.parse_args()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Upgrade pinned artifact schema versions safely and forward-only."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--target-schema-version",
        type=int,
        default=CURRENT_SCHEMA_VERSION,
    )
    parser.add_argument(
        "--report-json",
        action="store_true",
        help="Emit the migration report as JSON instead of the upgraded payload.",
    )
    args = parser.parse_args(argv)

    report = migrate_schema_file(
        _resolved_path(args.input),
        _resolved_path(args.output),
        target_schema_version=args.target_schema_version,
    )
    if args.report_json:
        print(json.dumps(report, indent=2))
    else:
        print(json.dumps(_read_json(_resolved_path(args.output)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
