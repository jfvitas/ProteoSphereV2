from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKLIST = (
    REPO_ROOT / "artifacts" / "status" / "p76_duplicate_cleanup_first_execution_checklist.json"
)
DEFAULT_DELETE_READY_MANIFEST = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_delete_ready_manifest_preview.json"
)
DEFAULT_EXECUTOR_STATUS = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_executor_status.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_first_execution_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "duplicate_cleanup_first_execution_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_from_delete_ready_manifest(
    delete_ready_manifest: dict[str, Any],
    executor_status: dict[str, Any],
    legacy_checklist: dict[str, Any] | None = None,
) -> dict[str, Any]:
    delete_batch = (
        delete_ready_manifest.get("delete_batch")
        if isinstance(delete_ready_manifest.get("delete_batch"), dict)
        else {}
    )
    truth = (
        delete_ready_manifest.get("truth_boundary")
        if isinstance(delete_ready_manifest.get("truth_boundary"), dict)
        else {}
    )
    action_count = int(delete_ready_manifest.get("action_count") or 0)
    removal_paths = [
        str(path)
        for path in (delete_batch.get("removal_paths") or [])
        if str(path).strip()
    ]
    batch_size_limit = 1
    batch_shape = "one exact-match removal action from same_release_local_copy_duplicates"
    if legacy_checklist is not None:
        shape = (
            legacy_checklist.get("first_authorized_execution_shape")
            if isinstance(legacy_checklist.get("first_authorized_execution_shape"), dict)
            else {}
        )
        batch_size_limit = int(shape.get("batch_size_limit") or 1)
        batch_shape = str(shape.get("batch_shape") or batch_shape)

    if action_count > 0 and removal_paths:
        batch_size_limit = max(batch_size_limit, len(removal_paths))

    refresh_required = action_count <= 0
    preview_manifest_status = str(
        delete_ready_manifest.get("preview_manifest_status") or "report_only"
    )
    execution_status = (
        "refresh_required_after_consumed_preview_batch"
        if refresh_required
        else preview_manifest_status
    )

    return {
        "artifact_id": "duplicate_cleanup_first_execution_preview",
        "schema_id": "proteosphere-duplicate-cleanup-first-execution-preview-2026-04-02",
        "status": "complete",
        "execution_status": execution_status,
        "preview_manifest_status": preview_manifest_status,
        "batch_size_limit": batch_size_limit,
        "batch_shape": batch_shape,
        "duplicate_class": str(delete_batch.get("duplicate_class") or ""),
        "keeper_path": str(delete_batch.get("keeper_path") or ""),
        "removal_path": removal_paths[0] if removal_paths else "",
        "reclaimable_bytes": int(delete_batch.get("reclaimable_bytes") or 0),
        "delete_ready_action_count": action_count,
        "refresh_required": refresh_required,
        "executor_validation_status": executor_status.get("validation", {}).get("status"),
        "truth_boundary": {
            "summary": (
                "This is a report-only summary of the current first duplicate-cleanup "
                "execution boundary. It mirrors the live delete-ready manifest and "
                "stays non-destructive when the staged batch has already been consumed."
            ),
            "report_only": True,
            "delete_enabled": False,
            "latest_surfaces_mutated": False,
            "ready_for_operator_preview": True,
            "requires_plan_refresh_when_consumed": truth.get(
                "requires_plan_refresh_when_consumed",
                True,
            ),
        },
    }


def _build_from_legacy_checklist(
    checklist: dict[str, Any],
    executor_status: dict[str, Any],
) -> dict[str, Any]:
    shape = checklist["first_authorized_execution_shape"]
    exemplar = shape["current_plan_exemplar"]
    operator_summary = checklist["operator_summary"]
    truth = checklist["current_boundary"]["truth_boundary"]

    return {
        "artifact_id": "duplicate_cleanup_first_execution_preview",
        "schema_id": "proteosphere-duplicate-cleanup-first-execution-preview-2026-04-01",
        "status": "complete",
        "execution_status": operator_summary["status"],
        "preview_manifest_status": "legacy_checklist_preview",
        "batch_size_limit": shape["batch_size_limit"],
        "batch_shape": shape["batch_shape"],
        "duplicate_class": exemplar["duplicate_class"],
        "keeper_path": exemplar["keeper_path"],
        "removal_path": exemplar["removal_path"],
        "reclaimable_bytes": exemplar["reclaimable_bytes"],
        "delete_ready_action_count": 1,
        "refresh_required": False,
        "executor_validation_status": executor_status["validation"]["status"],
        "truth_boundary": {
            "summary": (
                "This is a preview of the first authorized duplicate-cleanup execution "
                "boundary. It remains report-only and does not authorize or perform deletion."
            ),
            "report_only": checklist["report_only"],
            "delete_enabled": truth["delete_enabled"],
            "latest_surfaces_mutated": truth["latest_surfaces_mutated"],
            "ready_for_operator_preview": True,
            "requires_plan_refresh_when_consumed": True,
        },
    }


def build_duplicate_cleanup_first_execution_preview(
    primary: dict[str, Any],
    executor_status: dict[str, Any],
    legacy_checklist: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if primary.get("artifact_id") == "duplicate_cleanup_delete_ready_manifest_preview":
        return _build_from_delete_ready_manifest(
            primary,
            executor_status,
            legacy_checklist=legacy_checklist,
        )
    return _build_from_legacy_checklist(primary, executor_status)


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Duplicate Cleanup First Execution Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Execution status: `{payload['execution_status']}`",
        f"- Preview manifest status: `{payload['preview_manifest_status']}`",
        f"- Batch size limit: `{payload['batch_size_limit']}`",
        f"- Duplicate class: `{payload['duplicate_class']}`",
        f"- Reclaimable bytes: `{payload['reclaimable_bytes']}`",
        f"- Refresh required: `{payload['refresh_required']}`",
        "",
        "## Exemplar",
        "",
        f"- Keeper: `{payload['keeper_path']}`",
        f"- Removal: `{payload['removal_path']}`",
        "",
        "## Truth Boundary",
        "",
        f"- {payload['truth_boundary']['summary']}",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the first duplicate-cleanup execution preview."
    )
    parser.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
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
    checklist = _read_json(args.checklist) if args.checklist.exists() else None
    if args.delete_ready_manifest.exists():
        payload = build_duplicate_cleanup_first_execution_preview(
            _read_json(args.delete_ready_manifest),
            _read_json(args.executor_status),
            legacy_checklist=checklist,
        )
    else:
        if checklist is None:
            raise FileNotFoundError(
                "neither delete-ready manifest nor legacy checklist is available"
            )
        payload = build_duplicate_cleanup_first_execution_preview(
            checklist,
            _read_json(args.executor_status),
        )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
