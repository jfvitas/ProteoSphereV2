from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.tasklib import dependencies_complete, normalize_task, save_json, validate_queue

QUEUE_PATH = Path("tasks/task_queue.json")
STATE_PATH = Path("artifacts/status/orchestrator_state.json")
DISPATCH_DIR = Path("artifacts/dispatch")
REPORT_PATH = Path("artifacts/status/overnight_queue_repair_report.json")


@dataclass(frozen=True)
class SeedTask:
    id: str
    title: str
    task_type: str
    phase: int
    files: list[str]
    success_criteria: list[str]
    priority: str = "high"
    dependencies: list[str] | None = None
    notes: str = "overnight_wave_seed"

    def as_task(self) -> dict[str, Any]:
        return normalize_task(
            {
                "id": self.id,
                "title": self.title,
                "type": self.task_type,
                "phase": self.phase,
                "files": self.files,
                "dependencies": self.dependencies or [],
                "status": "pending",
                "success_criteria": self.success_criteria,
                "priority": self.priority,
                "notes": self.notes,
            }
        )


SEED_TASKS: tuple[SeedTask, ...] = (
    SeedTask(
        id="OVR-T001",
        title="Export binding measurement suspect row audit preview",
        task_type="coding",
        phase=0,
        files=[
            "scripts/export_binding_measurement_suspect_rows_preview.py",
            "artifacts/status/binding_measurement_suspect_rows_preview.json",
            "tests/unit/test_export_binding_measurement_suspect_rows_preview.py",
        ],
        success_criteria=[
            "suspect affinity rows are summarized with reasons",
            "preview output remains non-governing",
            "unit tests cover normalization edge cases",
        ],
    ),
    SeedTask(
        id="OVR-T002",
        title="Export cross-source duplicate measurement audit preview",
        task_type="coding",
        phase=0,
        files=[
            "scripts/export_cross_source_duplicate_measurement_audit_preview.py",
            "artifacts/status/cross_source_duplicate_measurement_audit_preview.json",
            "tests/unit/test_export_cross_source_duplicate_measurement_audit_preview.py",
        ],
        success_criteria=[
            "duplicate measurement families are surfaced without silent dedupe",
            "source-specific provenance is preserved",
            "unit tests cover duplicate grouping rules",
        ],
    ),
    SeedTask(
        id="OVR-T003",
        title="Export structure affinity best evidence preview",
        task_type="coding",
        phase=0,
        files=[
            "scripts/export_structure_affinity_best_evidence_preview.py",
            "artifacts/status/structure_affinity_best_evidence_preview.json",
            "tests/unit/test_export_structure_affinity_best_evidence_preview.py",
        ],
        success_criteria=[
            "best available affinity evidence is summarized per structure",
            "complex type remains explicit",
            "unit tests cover exact-vs-derived ranking",
        ],
    ),
    SeedTask(
        id="OVR-T004",
        title="Export interaction STRING merge impact preview",
        task_type="coding",
        phase=0,
        files=[
            "scripts/export_interaction_string_merge_impact_preview.py",
            "artifacts/status/interaction_string_merge_impact_preview.json",
            "tests/unit/test_export_interaction_string_merge_impact_preview.py",
        ],
        success_criteria=[
            "current interaction surfaces flag likely post-tail changes",
            "STRING remains report-only and non-governing",
            "unit tests cover source separation",
        ],
    ),
    SeedTask(
        id="OVR-T005",
        title="Export targeted page scrape execution preview",
        task_type="coding",
        phase=0,
        files=[
            "scripts/export_targeted_page_scrape_execution_preview.py",
            "artifacts/status/targeted_page_scrape_execution_preview.json",
            "tests/unit/test_export_targeted_page_scrape_execution_preview.py",
        ],
        success_criteria=[
            "targeted page scrape backlog is converted into concrete execution slices",
            "page scrape policy remains candidate-only non-governing",
            "unit tests cover priority ordering",
        ],
    ),
    SeedTask(
        id="OVR-T006",
        title="Implement external dataset sample manifest fixtures",
        task_type="coding",
        phase=0,
        files=[
            "tests/fixtures/external_dataset/sample_dataset_manifest.json",
            "tests/fixtures/external_dataset/sample_folder_package_manifest.json",
            "tests/unit/test_external_dataset_assessment_fixtures.py",
        ],
        success_criteria=[
            "json and folder-package intake shapes have realistic fixtures",
            "fixtures exercise fail-closed validation paths",
            "unit tests validate fixture completeness",
        ],
    ),
    SeedTask(
        id="OVR-T007",
        title="Export training set candidate package manifest preview",
        task_type="coding",
        phase=0,
        files=[
            "scripts/export_training_set_candidate_package_manifest_preview.py",
            "artifacts/status/training_set_candidate_package_manifest_preview.json",
            "tests/unit/test_export_training_set_candidate_package_manifest_preview.py",
        ],
        success_criteria=[
            "candidate package planning is visible without mutating protected manifests",
            "blocked reasons remain explicit",
            "unit tests cover preview-only behavior",
        ],
    ),
    SeedTask(
        id="OVR-A008",
        title="Analyze overnight scrape backlog operational wave",
        task_type="data_analysis",
        phase=0,
        files=[
            "scripts/analyze_overnight_scrape_backlog.py",
            "artifacts/status/overnight_scrape_wave_analysis.json",
            "tests/unit/test_analyze_overnight_scrape_backlog.py",
        ],
        success_criteria=[
            "next scrape/acquire/export wave is prioritized concretely",
            "blocked-by-tail work is separated from harvestable work",
            "unit tests cover priority banding",
        ],
        priority="medium",
    ),
)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    import json

    return json.loads(path.read_text(encoding="utf-8-sig"))


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _stale_dispatch_ids(
    queue: list[dict[str, Any]],
    dispatch_dir: Path,
    stale_after: timedelta,
    now: datetime,
) -> list[str]:
    stale_ids: list[str] = []
    queue_lookup = {task["id"]: task for task in queue}

    for manifest in sorted(dispatch_dir.glob("*.json")):
        task_id = manifest.stem
        task = queue_lookup.get(task_id)
        if not task or task.get("status") not in {"dispatched", "running"}:
            continue
        age = now - datetime.fromtimestamp(manifest.stat().st_mtime, tz=UTC)
        if age >= stale_after:
            stale_ids.append(task_id)
    return stale_ids


def _append_seed_tasks(queue: list[dict[str, Any]]) -> list[str]:
    existing = {task["id"] for task in queue}
    added: list[str] = []
    for seed in SEED_TASKS:
        if seed.id in existing:
            continue
        queue.append(seed.as_task())
        added.append(seed.id)
    return added


def repair_queue(
    queue_path: Path = QUEUE_PATH,
    state_path: Path = STATE_PATH,
    dispatch_dir: Path = DISPATCH_DIR,
    report_path: Path = REPORT_PATH,
    stale_after_hours: int = 6,
    seed_tasks: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or _utc_now()
    queue = [normalize_task(task) for task in load_json(queue_path, [])]
    state = load_json(
        state_path,
        {
            "active_workers": [],
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_tasks": [],
            "review_queue": [],
            "dispatch_queue": [],
            "last_task_generation_ts": None,
        },
    )
    stale_after = timedelta(hours=stale_after_hours)
    stale_ids = _stale_dispatch_ids(queue, dispatch_dir, stale_after, now)

    queue_by_id = {task["id"]: task for task in queue}
    demoted: list[str] = []
    deleted_manifests: list[str] = []
    for task_id in stale_ids:
        task = queue_by_id[task_id]
        task["status"] = "pending"
        demoted.append(task_id)
        manifest = dispatch_dir / f"{task_id}.json"
        if manifest.exists():
            manifest.unlink()
            deleted_manifests.append(task_id)

    state["active_workers"] = [
        worker
        for worker in state.get("active_workers", [])
        if worker.get("task_id") not in stale_ids
    ]
    state["dispatch_queue"] = [
        task_id for task_id in state.get("dispatch_queue", []) if task_id not in stale_ids
    ]

    added_tasks = _append_seed_tasks(queue) if seed_tasks else []

    for task in queue:
        if task["status"] == "pending" and dependencies_complete(task, queue):
            task["status"] = "ready"

    state["completed_tasks"] = sorted(
        task["id"] for task in queue if task.get("status") in {"done", "reviewed"}
    )
    state["blocked_tasks"] = sorted(
        task["id"] for task in queue if task.get("status") == "blocked"
    )
    state["last_queue_repair_at"] = now.isoformat()

    errors = validate_queue(queue)
    if errors:
        raise SystemExit(f"queue validation failed after repair: {errors}")

    save_json(queue_path, queue)
    save_json(state_path, state)

    counts: dict[str, int] = {}
    for task in queue:
        counts[task["status"]] = counts.get(task["status"], 0) + 1

    report = {
        "repaired_at": now.isoformat(),
        "stale_after_hours": stale_after_hours,
        "demoted_stale_dispatches": demoted,
        "deleted_dispatch_manifests": deleted_manifests,
        "seeded_task_ids": added_tasks,
        "queue_counts": counts,
        "active_worker_ids": [worker["task_id"] for worker in state.get("active_workers", [])],
    }
    save_json(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stale-after-hours", type=int, default=6)
    parser.add_argument("--no-seed-tasks", action="store_true")
    args = parser.parse_args()

    report = repair_queue(
        stale_after_hours=args.stale_after_hours,
        seed_tasks=not args.no_seed_tasks,
    )
    import json

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
