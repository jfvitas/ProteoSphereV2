from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIRST_BATCH_MANIFEST = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "p86_duplicate_cleanup_first_execution_batch_manifest_preview.json"
)
DEFAULT_REAL_EXECUTION_BLOCKER = (
    REPO_ROOT / "artifacts" / "status" / "p87_duplicate_cleanup_real_execution_blocker.json"
)
DEFAULT_POST_DELETE_VERIFICATION_CONTRACT = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "p64_duplicate_cleanup_post_mutation_verification_contract.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "p90_duplicate_cleanup_delete_ready_first_batch_manifest.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "p90_duplicate_cleanup_delete_ready_first_batch_manifest.md"
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError(f"{path} must contain a JSON object")
    return dict(payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _extract_action_signature(action: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "duplicate_class": action.get("duplicate_class"),
        "sha256": action.get("sha256"),
        "keeper_path": action.get("keeper_path"),
        "removal_path": action.get("removal_path"),
        "reclaimable_bytes": int(action.get("reclaimable_bytes") or 0),
    }


def _verification_scaffold(
    verification_contract: Mapping[str, Any],
) -> dict[str, Any]:
    contract = verification_contract.get("post_mutation_verification_contract") or {}
    if not isinstance(contract, Mapping):
        contract = {}
    acceptance_standard = verification_contract.get("acceptance_standard") or {}
    if not isinstance(acceptance_standard, Mapping):
        acceptance_standard = {}
    minimum_checks = [
        item
        for item in (contract.get("minimum_checks") or ())
        if isinstance(item, Mapping)
    ]
    return {
        "scaffold_status": "report_only_scaffold",
        "source_contract_path": str(DEFAULT_POST_DELETE_VERIFICATION_CONTRACT).replace("\\", "/"),
        "minimum_checks": minimum_checks,
        "acceptance_standard": {
            "status": acceptance_standard.get("status"),
            "summary": acceptance_standard.get("summary"),
            "what_success_requires": list(acceptance_standard.get("what_success_requires") or ()),
        },
        "minimum_audit_fields": [
            "approval_id",
            "executor_id",
            "source_hashes",
            "before_after_path_delta",
        ],
        "required_post_delete_artifacts": [
            "refreshed inventory snapshot",
            "observed removal count reconciliation",
            "reclaimed bytes reconciliation",
            "rollback or recovery note if partial",
        ],
        "operator_consumption": {
            "surface_targets": [
                "operator_dashboard",
                "duplicate_cleanup_validation",
            ],
            "ready_for_future_delete_run": False,
        },
    }


def build_duplicate_cleanup_delete_ready_first_batch_manifest(
    first_batch_manifest: Mapping[str, Any],
    real_execution_blocker: Mapping[str, Any],
    verification_contract: Mapping[str, Any],
) -> dict[str, Any]:
    batch_identity = first_batch_manifest.get("batch_identity") or {}
    if not isinstance(batch_identity, Mapping):
        batch_identity = {}
    frozen_action = first_batch_manifest.get("frozen_action") or {}
    if not isinstance(frozen_action, Mapping):
        frozen_action = {}

    blocker_answer = real_execution_blocker.get("answer") or {}
    if not isinstance(blocker_answer, Mapping):
        blocker_answer = {}
    current_first_batch = real_execution_blocker.get("current_first_batch") or {}
    if not isinstance(current_first_batch, Mapping):
        current_first_batch = {}
    unmet_conditions = [
        item for item in (real_execution_blocker.get("unmet_conditions") or ()) if isinstance(item, Mapping)
    ]

    current_signature = _extract_action_signature(current_first_batch)
    frozen_signature = _extract_action_signature(frozen_action)
    first_action_matches_blocker = current_signature == frozen_signature

    delete_ready_manifest = {
        "manifest_state": "delete_ready_preview_non_destructive",
        "delete_enabled": False,
        "safe_to_execute_today": bool(blocker_answer.get("safe_to_execute_today")) is True,
        "batch_size_limit": int(batch_identity.get("batch_size_limit") or 0),
        "batch_shape": batch_identity.get("batch_shape"),
        "cohort_name": batch_identity.get("cohort_name"),
        "plan_id": batch_identity.get("plan_id"),
        "plan_action_index": int(batch_identity.get("plan_action_index") or 0),
        "action_count": int(batch_identity.get("action_count") or 0),
        "duplicate_class": frozen_action.get("duplicate_class"),
        "sha256": frozen_action.get("sha256"),
        "keeper_path": frozen_action.get("keeper_path"),
        "removal_path": frozen_action.get("removal_path"),
        "reclaimable_bytes": int(frozen_action.get("reclaimable_bytes") or 0),
        "validation_gates": list(frozen_action.get("validation_gates") or ()),
        "ready_for_operator_preview": True,
        "ready_for_delete": False,
        "delete_ready_manifest_emitted": True,
    }

    validation_checks = [
        {
            "check_id": "first_action_matches_p87_blocker",
            "status": "passed" if first_action_matches_blocker else "failed",
            "detail": "the refreshed manifest matches the frozen first-action blocker exemplar"
            if first_action_matches_blocker
            else "the refreshed manifest diverges from the blocker exemplar",
        },
        {
            "check_id": "batch_locked_to_single_action",
            "status": "passed" if int(batch_identity.get("batch_size_limit") or 0) == 1 else "failed",
            "detail": "the batch remains a one-action boundary",
        },
        {
            "check_id": "blocker_remains_not_safe_today",
            "status": "passed" if blocker_answer.get("safe_to_execute_today") is False else "failed",
            "detail": "the real execution blocker still says the batch is not safely executable today",
        },
        {
            "check_id": "verification_scaffold_present",
            "status": "passed"
            if len(_verification_scaffold(verification_contract)["minimum_checks"]) > 0
            else "failed",
            "detail": "the post-delete verification contract scaffold is present and populated",
        },
        {
            "check_id": "cohort_lock_preserved",
            "status": "passed"
            if batch_identity.get("cohort_name") == "same_release_local_copy_duplicates"
            else "failed",
            "detail": "the batch remains locked to same_release_local_copy_duplicates",
        },
    ]
    validation_errors = [
        item["check_id"] for item in validation_checks if item["status"] == "failed"
    ]
    validation_status = "failed" if validation_errors else "passed"

    payload = {
        "artifact_id": "p90_duplicate_cleanup_delete_ready_first_batch_manifest",
        "schema_id": (
            "proteosphere-p90-duplicate-cleanup-delete-ready-first-batch-manifest-2026-04-02"
        ),
        "report_type": "duplicate_cleanup_delete_ready_first_batch_manifest",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "basis_artifacts": {
            "first_batch_manifest_preview": str(DEFAULT_FIRST_BATCH_MANIFEST).replace("\\", "/"),
            "real_execution_blocker": str(DEFAULT_REAL_EXECUTION_BLOCKER).replace("\\", "/"),
            "post_delete_verification_contract": str(DEFAULT_POST_DELETE_VERIFICATION_CONTRACT).replace(
                "\\", "/"
            ),
        },
        "surface_state": {
            "preview_kind": "delete_ready_manifest_surface",
            "report_only": True,
            "delete_enabled": False,
            "safe_to_execute_today": bool(blocker_answer.get("safe_to_execute_today")),
            "ready_for_operator_preview": True,
            "ready_for_future_delete_run": False,
        },
        "delete_ready_manifest": delete_ready_manifest,
        "real_execution_blocker_alignment": {
            "safe_to_execute_today": bool(blocker_answer.get("safe_to_execute_today")),
            "delete_ready_manifest_emitted": bool(
                blocker_answer.get("delete_ready_manifest_emitted")
            ),
            "current_first_batch": {
                "duplicate_class": current_first_batch.get("duplicate_class"),
                "sha256": current_first_batch.get("sha256"),
                "keeper_path": current_first_batch.get("keeper_path"),
                "removal_path": current_first_batch.get("removal_path"),
                "reclaimable_bytes": int(current_first_batch.get("reclaimable_bytes") or 0),
                "validation_gates": list(current_first_batch.get("validation_gates") or ()),
            },
            "unmet_conditions": unmet_conditions,
        },
        "post_delete_verification_contract_scaffold": _verification_scaffold(
            verification_contract
        ),
        "validation": {
            "status": validation_status,
            "checks": validation_checks,
            "errors": validation_errors,
        },
        "truth_boundary": {
            "report_only": True,
            "delete_enabled": False,
            "latest_surfaces_mutated": False,
            "mutation_allowed": False,
            "ready_for_operator_preview": True,
            "next_required_state": "mutation_authorization_and_frozen_batch_approval",
        },
    }
    return payload


def render_markdown(payload: Mapping[str, Any]) -> str:
    delete_ready = payload["delete_ready_manifest"]
    blocker = payload["real_execution_blocker_alignment"]
    verification_scaffold = payload["post_delete_verification_contract_scaffold"]
    lines = [
        "# Duplicate Cleanup Delete-Ready First Batch Manifest",
        "",
        f"- Status: `{payload['status']}`",
        f"- Surface state: `{payload['surface_state']['preview_kind']}`",
        f"- Safe to execute today: `{payload['surface_state']['safe_to_execute_today']}`",
        f"- Delete-ready manifest emitted: `{delete_ready['delete_ready_manifest_emitted']}`",
        f"- Batch size limit: `{delete_ready['batch_size_limit']}`",
        f"- Cohort: `{delete_ready['cohort_name']}`",
        f"- Action count in frozen plan: `{delete_ready['action_count']}`",
        "",
        "## Delete-Ready Manifest",
        "",
        f"- Keeper: `{delete_ready['keeper_path']}`",
        f"- Removal: `{delete_ready['removal_path']}`",
        f"- SHA-256: `{delete_ready['sha256']}`",
        f"- Reclaimable bytes: `{delete_ready['reclaimable_bytes']}`",
        f"- Validation gates: `{', '.join(delete_ready['validation_gates'])}`",
        "",
        "## Real Execution Blocker Alignment",
        "",
        f"- Blocker safe to execute today: `{blocker['safe_to_execute_today']}`",
        f"- Blocker delete-ready manifest emitted: `{blocker['delete_ready_manifest_emitted']}`",
        f"- Blocker unmet conditions: `{len(blocker['unmet_conditions'])}`",
        "",
        "## Post-Delete Verification Scaffold",
        "",
        f"- Scaffold status: `{verification_scaffold['scaffold_status']}`",
        f"- Source contract: `{verification_scaffold['source_contract_path']}`",
    ]
    for check in verification_scaffold["minimum_checks"]:
        lines.append(f"- `{check['check']}`")
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- Report only: `{payload['truth_boundary']['report_only']}`",
            f"- Delete enabled: `{payload['truth_boundary']['delete_enabled']}`",
            f"- Latest surfaces mutated: `{payload['truth_boundary']['latest_surfaces_mutated']}`",
            f"- Mutation allowed: `{payload['truth_boundary']['mutation_allowed']}`",
            f"- Next required state: `{payload['truth_boundary']['next_required_state']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a report-only delete-ready first-batch manifest and verification "
            "scaffold for duplicate cleanup."
        )
    )
    parser.add_argument("--first-batch-manifest", type=Path, default=DEFAULT_FIRST_BATCH_MANIFEST)
    parser.add_argument("--real-execution-blocker", type=Path, default=DEFAULT_REAL_EXECUTION_BLOCKER)
    parser.add_argument(
        "--post-delete-verification-contract",
        type=Path,
        default=DEFAULT_POST_DELETE_VERIFICATION_CONTRACT,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    first_batch_manifest = _load_json(args.first_batch_manifest)
    real_execution_blocker = _load_json(args.real_execution_blocker)
    verification_contract = _load_json(args.post_delete_verification_contract)

    payload = build_duplicate_cleanup_delete_ready_first_batch_manifest(
        first_batch_manifest,
        real_execution_blocker,
        verification_contract,
    )
    _write_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
