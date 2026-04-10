from __future__ import annotations

import json
import re
from pathlib import Path

VALID_TASK_TYPES = {
    "coding",
    "data_analysis",
    "integration",
    "review_fix",
    "test_hardening",
    "docs_reporting",
}
VALID_STATUSES = {
    "pending",
    "ready",
    "dispatched",
    "running",
    "done",
    "blocked",
    "failed",
    "reviewed",
}


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "task"


def branch_name(task: dict) -> str:
    return f"codex/task/{task['id']}-{slugify(task['title'])}"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def normalize_task(task: dict) -> dict:
    normalized = dict(task)
    normalized.setdefault("dependencies", [])
    normalized.setdefault("status", "pending")
    normalized.setdefault("priority", "medium")
    normalized.setdefault("branch", branch_name(normalized))
    normalized.setdefault("notes", "")
    normalized["files"] = sorted(dict.fromkeys(normalized["files"]))
    normalized["success_criteria"] = list(normalized["success_criteria"])
    return normalized


def _visit(node: str, graph: dict[str, list[str]], visiting: set[str], visited: set[str]) -> bool:
    if node in visiting:
        return True
    if node in visited:
        return False
    visiting.add(node)
    for dep in graph.get(node, []):
        if _visit(dep, graph, visiting, visited):
            return True
    visiting.remove(node)
    visited.add(node)
    return False


def find_cycle(queue: list[dict]) -> bool:
    graph = {task["id"]: task.get("dependencies", []) for task in queue}
    visiting: set[str] = set()
    visited: set[str] = set()
    return any(_visit(node, graph, visiting, visited) for node in graph)


def validate_queue(queue: list[dict]) -> list[str]:
    errors: list[str] = []
    ids = [task.get("id") for task in queue]
    duplicate_ids = sorted({task_id for task_id in ids if ids.count(task_id) > 1})
    if duplicate_ids:
        errors.append(f"duplicate task ids: {', '.join(duplicate_ids)}")

    known_ids = set(ids)
    for task in queue:
        if task.get("type") not in VALID_TASK_TYPES:
            errors.append(f"{task.get('id')}: invalid type {task.get('type')}")
        if task.get("status") not in VALID_STATUSES:
            errors.append(f"{task.get('id')}: invalid status {task.get('status')}")
        if not task.get("files"):
            errors.append(f"{task.get('id')}: no file ownership declared")
        if not task.get("success_criteria"):
            errors.append(f"{task.get('id')}: no success criteria declared")
        for dep in task.get("dependencies", []):
            if dep not in known_ids:
                errors.append(f"{task.get('id')}: unknown dependency {dep}")
        if task.get("id") in task.get("dependencies", []):
            errors.append(f"{task.get('id')}: self dependency")
        branch = task.get("branch", "")
        if not branch.startswith("codex/task/"):
            errors.append(f"{task.get('id')}: branch must start with codex/task/")

    if find_cycle(queue):
        errors.append("dependency cycle detected")
    return errors


def dependencies_complete(task: dict, queue: list[dict]) -> bool:
    done = {item["id"] for item in queue if item.get("status") in {"done", "reviewed"}}
    return all(dep in done for dep in task.get("dependencies", []))


def path_overlaps(left: str, right: str) -> bool:
    left_parts = Path(left).parts
    right_parts = Path(right).parts
    length = min(len(left_parts), len(right_parts))
    return left_parts[:length] == right_parts[:length]


def conflicts(candidate: dict, active_tasks: list[dict]) -> list[str]:
    conflicts_with: list[str] = []
    for other in active_tasks:
        for candidate_path in candidate["files"]:
            for other_path in other["files"]:
                if (
                    path_overlaps(candidate_path, other_path)
                    or path_overlaps(other_path, candidate_path)
                ):
                    conflicts_with.append(other["id"])
                    break
            if conflicts_with and conflicts_with[-1] == other["id"]:
                break
    return conflicts_with


def task_counts(queue: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in queue:
        counts[task["status"]] = counts.get(task["status"], 0) + 1
    return counts
