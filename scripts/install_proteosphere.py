from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.tasklib import save_json

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "install_bootstrap_state.json"

BOOTSTRAP_DIRECTORIES = (
    "tasks",
    "logs",
    "artifacts/status",
    "artifacts/reports",
    "artifacts/blockers",
    "artifacts/reviews",
    "artifacts/planner",
    "artifacts/dispatch",
    "docs/reports",
)

REQUIRED_FILES = (
    "scripts/bootstrap_repo.py",
    "scripts/orchestrator.py",
    "scripts/monitor.py",
    "scripts/tasklib.py",
    "scripts/validate_operator_state.py",
    "scripts/powershell_interface.ps1",
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_repo_root(repo_root: Path | str | None) -> Path:
    if repo_root is None:
        return REPO_ROOT
    return Path(repo_root).resolve()


def _bootstrap_repo_state(repo_root: Path) -> dict[str, Any]:
    created_directories: list[str] = []
    for relative_path in BOOTSTRAP_DIRECTORIES:
        directory = repo_root / relative_path
        if not directory.exists():
            created_directories.append(relative_path)
        directory.mkdir(parents=True, exist_ok=True)

    queue_path = repo_root / "tasks" / "task_queue.json"
    queue_created = not queue_path.exists()
    if queue_created:
        queue_path.write_text("[]\n", encoding="utf-8")

    orchestrator_state_path = repo_root / "artifacts" / "status" / "orchestrator_state.json"
    orchestrator_created = not orchestrator_state_path.exists()
    if orchestrator_created:
        save_json(
            orchestrator_state_path,
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

    return {
        "bootstrap_status": "ready",
        "created_directories": created_directories,
        "queue_created": queue_created,
        "orchestrator_state_created": orchestrator_created,
        "queue_path": str(queue_path).replace("\\", "/"),
        "orchestrator_state_path": str(orchestrator_state_path).replace("\\", "/"),
    }


def _dependency_checks(repo_root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    missing_paths: list[str] = []

    python_ok = sys.version_info >= (3, 11)
    checks.append(
        {
            "name": "python",
            "status": "ready" if python_ok else "blocked",
            "details": platform.python_version(),
        }
    )

    executable_ok = Path(sys.executable).exists()
    checks.append(
        {
            "name": "python_executable",
            "status": "ready" if executable_ok else "blocked",
            "details": sys.executable,
        }
    )

    for relative_path in REQUIRED_FILES:
        path = repo_root / relative_path
        exists = path.exists()
        checks.append(
            {
                "name": relative_path,
                "status": "ready" if exists else "blocked",
                "details": str(path).replace("\\", "/"),
            }
        )
        if not exists:
            missing_paths.append(relative_path)

    status = "ready" if python_ok and executable_ok and not missing_paths else "blocked"
    return {
        "status": status,
        "checks": checks,
        "missing_paths": missing_paths,
    }


def _bootstrap_state(repo_root: Path) -> dict[str, Any]:
    queue_path = repo_root / "tasks" / "task_queue.json"
    orchestrator_state_path = repo_root / "artifacts" / "status" / "orchestrator_state.json"

    queue_missing = not queue_path.exists()
    orchestrator_missing = not orchestrator_state_path.exists()
    queue_valid = False
    orchestrator_valid = False
    queue_value: Any = None
    orchestrator_value: Any = None

    if not queue_missing:
        try:
            queue_value = _read_json(queue_path)
            queue_valid = isinstance(queue_value, list)
        except json.JSONDecodeError:
            queue_valid = False

    if not orchestrator_missing:
        try:
            orchestrator_value = _read_json(orchestrator_state_path)
            orchestrator_valid = isinstance(orchestrator_value, dict)
        except json.JSONDecodeError:
            orchestrator_valid = False

    bootstrap_status = "ready"
    if queue_missing or orchestrator_missing:
        bootstrap_status = "missing"
    elif not queue_valid or not orchestrator_valid:
        bootstrap_status = "invalid"

    missing_paths = []
    if queue_missing:
        missing_paths.append("tasks/task_queue.json")
    if orchestrator_missing:
        missing_paths.append("artifacts/status/orchestrator_state.json")

    return {
        "status": bootstrap_status,
        "queue": {
            "path": str(queue_path).replace("\\", "/"),
            "present": not queue_missing,
            "valid": queue_valid,
            "value_type": type(queue_value).__name__ if queue_value is not None else None,
        },
        "orchestrator_state": {
            "path": str(orchestrator_state_path).replace("\\", "/"),
            "present": not orchestrator_missing,
            "valid": orchestrator_valid,
            "value_type": (
                type(orchestrator_value).__name__
                if orchestrator_value is not None
                else None
            ),
        },
        "missing_paths": missing_paths,
    }


def install_proteosphere(
    *,
    repo_root: Path | str | None = None,
    output_path: Path | str | None = None,
    bootstrap: bool = True,
) -> dict[str, Any]:
    resolved_repo_root = _resolve_repo_root(repo_root)
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT

    bootstrap_result: dict[str, Any] = {
        "bootstrap_status": "skipped",
        "created_directories": [],
        "queue_created": False,
        "orchestrator_state_created": False,
        "queue_path": str(resolved_repo_root / "tasks" / "task_queue.json").replace("\\", "/"),
        "orchestrator_state_path": str(
            resolved_repo_root / "artifacts" / "status" / "orchestrator_state.json"
        ).replace("\\", "/"),
    }
    if bootstrap:
        bootstrap_result = _bootstrap_repo_state(resolved_repo_root)

    dependency_report = _dependency_checks(resolved_repo_root)
    bootstrap_report = _bootstrap_state(resolved_repo_root)

    status = "ready"
    if dependency_report["status"] != "ready" or bootstrap_report["status"] != "ready":
        status = "blocked"

    payload: dict[str, Any] = {
        "status": status,
        "repo_root": str(resolved_repo_root).replace("\\", "/"),
        "environment": {
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "status": dependency_report["status"],
        },
        "dependency_report": dependency_report,
        "bootstrap_report": bootstrap_report,
        "bootstrap_action": bootstrap_result,
        "missing_dependencies": dependency_report["missing_paths"],
        "missing_bootstrap_paths": bootstrap_report["missing_paths"],
        "bootstrap_verified": bootstrap_report["status"] == "ready",
        "dependency_verified": dependency_report["status"] == "ready",
    }

    _write_json(resolved_output_path, payload)
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap ProteoSphere state and verify the local installation dependencies."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--no-bootstrap",
        action="store_true",
        help="Verify only; do not seed missing bootstrap state.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    payload = install_proteosphere(
        repo_root=args.repo_root,
        output_path=args.output,
        bootstrap=not args.no_bootstrap,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
