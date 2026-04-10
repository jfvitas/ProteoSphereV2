from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.storage.canonical_store import CanonicalStore  # noqa: E402
from core.storage.package_manifest import PackageManifest  # noqa: E402
from execution.materialization.packet_checksum_audit import (  # noqa: E402
    PacketChecksumAuditResult,
    audit_packet_checksum_payload,
    audit_packet_checksums,
)
from execution.materialization.selective_materializer import (  # noqa: E402
    SelectiveMaterializationResult,
    materialize_selected_examples,
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _load_package_manifest(path: Path) -> PackageManifest:
    return PackageManifest.from_dict(_read_json(path))


def _load_available_artifacts(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise TypeError("available artifacts payload must be a JSON object")
    candidate = payload.get("available_artifacts")
    if isinstance(candidate, dict):
        return dict(candidate)
    candidate = payload.get("artifacts")
    if isinstance(candidate, dict):
        return dict(candidate)
    return dict(payload)


def _load_canonical_store(path: Path | None) -> CanonicalStore | None:
    if path is None:
        return None
    return CanonicalStore.from_dict(_read_json(path))


def _read_reference_audit(path: Path | None) -> PacketChecksumAuditResult | None:
    if path is None:
        return None
    return audit_packet_checksum_payload(_read_json(path))


def _issue_summary(
    selective_result: SelectiveMaterializationResult,
    checksum_audit: PacketChecksumAuditResult,
) -> dict[str, Any]:
    checksum_summary = dict(checksum_audit.summary)
    return {
        "materialization_issue_count": len(selective_result.issues),
        "checksum_issue_count": sum(len(entry.issues) for entry in checksum_audit.entries),
        "missing_artifact_issue_count": sum(
            1 for issue in selective_result.issues if issue.kind == "missing_artifact_payload"
        ),
        "missing_canonical_issue_count": sum(
            1 for issue in selective_result.issues if issue.kind == "missing_canonical_record"
        ),
        "invalid_artifact_issue_count": sum(
            1 for issue in selective_result.issues if issue.kind == "invalid_artifact_payload"
        ),
        "missing_artifact_pointer_count": int(checksum_summary.get("missing_artifact_count") or 0),
        "partial_packet_count": int(checksum_summary.get("partial_count") or 0),
        "unavailable_packet_count": int(checksum_summary.get("unavailable_count") or 0),
        "drifted_count": int(checksum_summary.get("drifted_count") or 0),
    }


def build_rehydration_report(
    package_manifest: PackageManifest,
    available_artifacts: dict[str, Any],
    *,
    canonical_store: CanonicalStore | None = None,
    reference_audit: PacketChecksumAuditResult | None = None,
    materialization_run_id: str | None = None,
    materialized_at: str | None = None,
    allow_partial: bool = False,
) -> tuple[dict[str, Any], int]:
    selective_result = materialize_selected_examples(
        package_manifest,
        available_artifacts=available_artifacts,
        canonical_store=canonical_store,
        materialization_run_id=materialization_run_id,
        materialized_at=materialized_at,
    )
    checksum_audit = audit_packet_checksums(
        package_manifest,
        selective_result,
        reference_audit=reference_audit,
    )

    clean_rebuild = (
        selective_result.status == "materialized" and checksum_audit.status == "consistent"
    )
    if clean_rebuild:
        status = "materialized"
        exit_code = 0
    elif allow_partial and selective_result.status == "partial":
        status = "partial_rehydration"
        exit_code = 0
    else:
        status = (
            "unresolved_rehydration"
            if selective_result.materialized_example_count == 0
            else "blocked_rehydration"
        )
        exit_code = 1

    report = {
        "task_id": "P18-T006",
        "status": status,
        "package_id": package_manifest.package_id,
        "package_manifest_id": package_manifest.manifest_id,
        "selected_example_count": package_manifest.selected_example_count,
        "materialized_example_count": selective_result.materialized_example_count,
        "materialization_status": selective_result.status,
        "checksum_audit_status": checksum_audit.status,
        "allow_partial": allow_partial,
        "reference_audit_id": checksum_audit.reference_audit_id,
        "issue_summary": _issue_summary(selective_result, checksum_audit),
        "materialization": selective_result.to_dict(),
        "checksum_audit": checksum_audit.to_dict(),
    }
    return report, exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rehydrate a selected training packet from a pinned package manifest."
    )
    parser.add_argument(
        "--package-manifest",
        type=Path,
        required=True,
        help="Path to the package manifest JSON.",
    )
    parser.add_argument(
        "--available-artifacts",
        type=Path,
        required=True,
        help="Path to the JSON mapping of pinned artifact pointers to available payloads.",
    )
    parser.add_argument(
        "--canonical-store",
        type=Path,
        default=None,
        help="Optional canonical store JSON used to validate selected canonical ids.",
    )
    parser.add_argument(
        "--reference-audit",
        type=Path,
        default=None,
        help="Optional prior checksum audit JSON to compare packet identity drift.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Target JSON path for the rehydration report.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Return success for partial rebuilds while preserving the partial status in output.",
    )
    parser.add_argument(
        "--materialization-run-id",
        type=str,
        default=None,
        help="Optional explicit materialization run id to embed in the report.",
    )
    parser.add_argument(
        "--materialized-at",
        type=str,
        default=None,
        help="Optional explicit materialized-at timestamp to embed in the report.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    package_manifest = _load_package_manifest(args.package_manifest)
    available_artifacts = _load_available_artifacts(args.available_artifacts)
    canonical_store = _load_canonical_store(args.canonical_store)
    reference_audit = _read_reference_audit(args.reference_audit)
    report, exit_code = build_rehydration_report(
        package_manifest,
        available_artifacts,
        canonical_store=canonical_store,
        reference_audit=reference_audit,
        materialization_run_id=args.materialization_run_id,
        materialized_at=args.materialized_at,
        allow_partial=args.allow_partial,
    )
    _write_json(args.output, report)
    print(json.dumps(report, indent=2))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
