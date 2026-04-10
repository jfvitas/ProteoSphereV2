from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DELETE_READY_MANIFEST = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_delete_ready_manifest_preview.json"
)
DEFAULT_EXECUTOR_STATUS = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_executor_status.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "duplicate_cleanup_post_delete_verification_contract_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "duplicate_cleanup_post_delete_verification_contract_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_duplicate_cleanup_post_delete_verification_contract_preview(
    delete_ready_manifest: dict[str, Any],
    executor_status: dict[str, Any],
) -> dict[str, Any]:
    delete_batch = delete_ready_manifest.get("delete_batch") or {}
    constraint_checks = delete_ready_manifest.get("constraint_checks") or {}
    action_count = int(delete_ready_manifest.get("action_count") or 0)
    return {
        "artifact_id": "duplicate_cleanup_post_delete_verification_contract_preview",
        "schema_id": (
            "proteosphere-duplicate-cleanup-post-delete-verification-contract-preview-"
            "2026-04-02"
        ),
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "verification_steps": [
            "surviving canonical keeper path still exists",
            "surviving keeper checksum still matches the frozen manifest checksum",
            "removed path is outside protected and latest surfaces",
            "duplicate cleanup status and executor surfaces show reclaim delta",
        ],
        "frozen_manifest_ref": delete_ready_manifest.get("artifact_id"),
        "executor_validation_status": executor_status.get("validation", {}).get("status"),
        "delete_ready_action_count": action_count,
        "keeper_path": delete_batch.get("keeper_path"),
        "removal_paths": delete_batch.get("removal_paths") or [],
        "frozen_manifest_sha256": delete_batch.get("sha256"),
        "preflight_constraints": {
            "keeper_path_exists": constraint_checks.get("keeper_path_exists"),
            "removal_paths_present": constraint_checks.get("removal_paths_present"),
            "checksum_present": constraint_checks.get("checksum_present"),
            "no_partial_paths": constraint_checks.get("no_partial_paths"),
            "no_latest_json": constraint_checks.get("no_latest_json"),
            "protected_path_hits": constraint_checks.get("protected_path_hits") or [],
            "all_constraints_satisfied_preview": constraint_checks.get(
                "all_constraints_satisfied_preview"
            ),
        },
        "truth_boundary": {
            "report_only": True,
            "delete_enabled": False,
            "mutation_allowed": False,
            "ready_for_post_delete_checklist": action_count > 0,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Duplicate Cleanup Post-Delete Verification Contract Preview",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Frozen manifest ref: `{payload['frozen_manifest_ref']}`",
        "",
        "## Verification Steps",
        "",
    ]
    lines.extend(f"- {step}" for step in payload["verification_steps"])
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only post-delete verification contract preview."
    )
    parser.add_argument(
        "--delete-ready-manifest",
        type=Path,
        default=DEFAULT_DELETE_READY_MANIFEST,
    )
    parser.add_argument("--executor-status", type=Path, default=DEFAULT_EXECUTOR_STATUS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_duplicate_cleanup_post_delete_verification_contract_preview(
        _read_json(args.delete_ready_manifest),
        _read_json(args.executor_status),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
