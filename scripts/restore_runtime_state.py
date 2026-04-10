from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = ROOT
DEFAULT_OUTPUT_ROOT = ROOT / "artifacts" / "runtime" / "restored_runtime_state"
DEFAULT_REPORT_NAME = "runtime_state_restore.json"
QUEUE_PATH = Path("tasks") / "task_queue.json"
ORCHESTRATOR_STATE_PATH = Path("artifacts") / "status" / "orchestrator_state.json"
RELEASE_BUNDLE_MANIFEST_PATH = (
    Path("runs") / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)
RELEASE_RESULTS_ROOT = Path("runs") / "real_data_benchmark" / "full_results"


@dataclass(frozen=True)
class RestoreItem:
    role: str
    source_path: Path
    destination_path: Path
    required: bool
    present: bool
    section: str


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _resolve_path(root: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else root / path


def _queue_summary(
    queue_payload: Any,
    source_path: Path,
    destination_path: Path,
) -> dict[str, Any]:
    is_valid_queue_payload = isinstance(queue_payload, list) or (
        isinstance(queue_payload, dict) and isinstance(queue_payload.get("value"), list)
    )
    if isinstance(queue_payload, list):
        task_list = queue_payload
    elif isinstance(queue_payload, dict) and isinstance(queue_payload.get("value"), list):
        task_list = queue_payload["value"]
    else:
        task_list = []
    counts: dict[str, int] = {}
    for task in task_list:
        if not isinstance(task, dict):
            continue
        status = str(task.get("status") or "unknown").strip() or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return {
        "source_path": str(source_path),
        "destination_path": str(destination_path),
        "task_count": len(task_list),
        "status_counts": counts,
        "is_valid_queue_payload": is_valid_queue_payload,
    }


def _orchestrator_summary(
    orchestrator_payload: dict[str, Any],
    source_path: Path,
    destination_path: Path,
) -> dict[str, Any]:
    return {
        "source_path": str(source_path),
        "destination_path": str(destination_path),
        "done_count": int(orchestrator_payload.get("done_count", 0)),
        "blocked_count": int(orchestrator_payload.get("blocked_count", 0)),
        "pending_count": int(orchestrator_payload.get("queue_counts", {}).get("pending", 0)),
        "active_worker_count": int(orchestrator_payload.get("active_worker_count", 0)),
        "dispatch_queue_count": int(orchestrator_payload.get("dispatch_queue_count", 0)),
        "review_queue_count": int(orchestrator_payload.get("review_queue_count", 0)),
        "resume_cause": orchestrator_payload.get("resume_cause"),
        "last_tick_completed_at": orchestrator_payload.get("last_tick_completed_at"),
    }


def _release_item_specs(source_root: Path, release_manifest: dict[str, Any]) -> list[RestoreItem]:
    items: list[RestoreItem] = [
        RestoreItem(
            role="bundle_manifest",
            source_path=source_root / RELEASE_BUNDLE_MANIFEST_PATH,
            destination_path=RELEASE_BUNDLE_MANIFEST_PATH,
            required=True,
            present=True,
            section="manifest",
        )
    ]
    for section_name in ("release_artifacts", "supporting_artifacts"):
        for entry in release_manifest.get(section_name, []):
            if not isinstance(entry, dict):
                continue
            raw_path = entry.get("path")
            if not raw_path:
                continue
            items.append(
                RestoreItem(
                    role=str(entry.get("role") or "artifact"),
                    source_path=_resolve_path(source_root, raw_path),
                    destination_path=Path(str(raw_path)),
                    required=bool(entry.get("required")),
                    present=bool(entry.get("present", True)),
                    section=section_name,
                )
            )
    return items


def _copy_item(item: RestoreItem, output_root: Path) -> dict[str, Any]:
    source_exists = item.source_path.exists() and item.present
    destination_path = output_root / item.destination_path
    entry = {
        "role": item.role,
        "section": item.section,
        "required": item.required,
        "present": item.present,
        "source_path": str(item.source_path),
        "destination_path": str(destination_path),
        "copied": False,
    }
    if source_exists:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item.source_path, destination_path)
        entry["copied"] = True
    return entry


def _build_restore_report(
    *,
    source_root: Path,
    output_root: Path,
    allow_partial: bool,
) -> tuple[dict[str, Any], bool]:
    queue_source = source_root / QUEUE_PATH
    orchestrator_source = source_root / ORCHESTRATOR_STATE_PATH
    release_manifest_source = source_root / RELEASE_BUNDLE_MANIFEST_PATH
    queue_missing: list[dict[str, Any]] = []
    queue_copied: list[dict[str, Any]] = []
    release_missing: list[dict[str, Any]] = []
    release_copied: list[dict[str, Any]] = []

    if not queue_source.exists():
        queue_missing.append(
            {
                "role": "task_queue",
                "source_path": str(queue_source),
                "required": True,
                "section": "queue",
            }
        )
    else:
        queue_copied.append(
            _copy_item(
                RestoreItem(
                    role="task_queue",
                    source_path=queue_source,
                    destination_path=QUEUE_PATH,
                    required=True,
                    present=True,
                    section="queue",
                ),
                output_root,
            )
        )

    if not orchestrator_source.exists():
        queue_missing.append(
            {
                "role": "orchestrator_state",
                "source_path": str(orchestrator_source),
                "required": True,
                "section": "queue",
            }
        )
    else:
        queue_copied.append(
            _copy_item(
                RestoreItem(
                    role="orchestrator_state",
                    source_path=orchestrator_source,
                    destination_path=ORCHESTRATOR_STATE_PATH,
                    required=True,
                    present=True,
                    section="queue",
                ),
                output_root,
            )
        )

    if not release_manifest_source.exists():
        queue_and_release_missing = queue_missing + release_missing
        report = {
            "task_id": "P22-T006",
            "generated_at": _utc_now(),
            "source_root": str(source_root),
            "output_root": str(output_root),
            "status": "blocked" if not allow_partial else "partial_restore",
            "rollback": {
                "performed": not allow_partial,
                "reason": None if allow_partial else "release bundle manifest missing",
            },
            "queue": {
                "task_queue": None,
                "orchestrator_state": None,
                "missing_artifacts": queue_missing,
                "copied_artifacts": queue_copied,
            },
            "release": {
                "bundle_manifest": None,
                "artifacts": [],
                "missing_artifacts": release_missing,
                "copied_artifacts": release_copied,
            },
            "missing_count": len(queue_and_release_missing),
            "required_missing_count": len(queue_and_release_missing),
        }
        return report, False

    release_manifest = _read_json(release_manifest_source)
    release_items = _release_item_specs(source_root, release_manifest)
    for item in release_items:
        copied_entry = _copy_item(item, output_root)
        if copied_entry["copied"]:
            release_copied.append(copied_entry)
        else:
            release_missing.append(
                {
                    "role": item.role,
                    "section": item.section,
                    "required": item.required,
                    "present": item.present,
                    "source_path": str(item.source_path),
                    "destination_path": str(output_root / item.destination_path),
                }
            )

    queue_payload = _read_json(queue_source) if queue_source.exists() else {}
    orchestrator_payload = _read_json(orchestrator_source) if orchestrator_source.exists() else {}
    queue_summary = _queue_summary(queue_payload, queue_source, output_root / QUEUE_PATH)
    orchestrator_summary = _orchestrator_summary(
        orchestrator_payload,
        orchestrator_source,
        output_root / ORCHESTRATOR_STATE_PATH,
    )

    missing = queue_missing + release_missing
    required_missing = [item for item in missing if item.get("required")]
    status = "restored"
    if missing:
        status = "partial_restore" if allow_partial else "blocked"

    report = {
        "task_id": "P22-T006",
        "generated_at": _utc_now(),
        "source_root": str(source_root),
        "output_root": str(output_root),
        "status": status,
        "rollback": {
            "performed": bool(missing and not allow_partial),
            "reason": None if (not missing or allow_partial) else "restore artifact missing",
        },
        "queue": {
            "task_queue": queue_summary,
            "orchestrator_state": orchestrator_summary,
            "missing_artifacts": queue_missing,
            "copied_artifacts": queue_copied,
        },
        "release": {
            "bundle_manifest": {
                "bundle_id": release_manifest.get("bundle_id"),
                "task_id": release_manifest.get("task_id"),
                "status": release_manifest.get("status"),
                "generated_at": release_manifest.get("generated_at"),
                "blocker_categories": list(release_manifest.get("blocker_categories", [])),
                "summary": dict(release_manifest.get("bundle_summary", {})),
                "truth_boundary": dict(release_manifest.get("truth_boundary", {})),
            },
            "artifacts": release_copied,
            "missing_artifacts": release_missing,
            "missing_count": len(missing),
            "required_missing_count": len(required_missing),
        },
    }
    return report, bool(missing)


def restore_runtime_state(
    *,
    source_root: Path | str = DEFAULT_SOURCE_ROOT,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    allow_partial: bool = False,
) -> dict[str, Any]:
    source_root = Path(source_root)
    output_root = Path(output_root)
    staging_root = output_root.parent / f".{output_root.name}.restore-{uuid4().hex}"
    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True, exist_ok=False)

    try:
        report, blocked = _build_restore_report(
            source_root=source_root,
            output_root=staging_root,
            allow_partial=allow_partial,
        )
        if blocked and not allow_partial:
            shutil.rmtree(staging_root, ignore_errors=True)
            report["output_root"] = str(output_root)
            report["restore_report_path"] = None
            return report

        if output_root.exists():
            shutil.rmtree(output_root)
        output_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging_root), str(output_root))
        report["output_root"] = str(output_root)
        report["restore_report_path"] = str(output_root / DEFAULT_REPORT_NAME)
        _write_json(output_root / DEFAULT_REPORT_NAME, report)
        return report
    except Exception:
        shutil.rmtree(staging_root, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Restore runtime state from pinned benchmark snapshots, "
            "including queue and release artifacts."
        )
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DEFAULT_SOURCE_ROOT,
        help="Root containing the pinned queue and benchmark snapshot artifacts.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Destination root for the restored runtime-state tree.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Keep available artifacts and report a partial restore instead of rolling back.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = restore_runtime_state(
        source_root=args.source_root,
        output_root=args.output_root,
        allow_partial=args.allow_partial,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
