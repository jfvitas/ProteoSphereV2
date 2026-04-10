from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else dict(default or {})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


@dataclass(frozen=True, slots=True)
class StepSpec:
    step_id: str
    description: str
    kind: str = "python"
    command: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    source: str | None = None
    destination: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _expected_outputs_present(step: StepSpec) -> bool:
    if step.kind == "move":
        if not step.destination:
            return False
        return Path(step.destination).exists()
    if not step.expected_outputs:
        return True
    return all((REPO_ROOT / relative_path).exists() for relative_path in step.expected_outputs)


def _step_state_entry(state: dict[str, Any], step_id: str) -> dict[str, Any]:
    steps = state.setdefault("steps", {})
    entry = steps.get(step_id)
    if isinstance(entry, dict):
        return entry
    steps[step_id] = {}
    return steps[step_id]


def initialize_state(
    *,
    runner_name: str,
    steps: list[StepSpec],
    state_path: Path,
) -> dict[str, Any]:
    state = read_json(
        state_path,
        default={
            "runner_name": runner_name,
            "created_at": utc_now(),
            "steps": {},
        },
    )
    state["runner_name"] = runner_name
    state["updated_at"] = utc_now()
    state["step_order"] = [step.step_id for step in steps]
    return state


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now()
    write_json(state_path, state)


def run_python_command(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    return completed.returncode, combined.strip()


def _execute_step(step: StepSpec) -> tuple[int, str]:
    if step.kind == "move":
        if not step.source or not step.destination:
            return 1, "move step is missing source or destination"
        source = Path(step.source)
        destination = Path(step.destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if source.exists():
                source_size = source.stat().st_size
                destination_size = destination.stat().st_size
                if source_size != destination_size:
                    return 1, (
                        "destination already exists with different size: "
                        f"{destination_size} != {source_size}"
                    )
                source.unlink()
                return 0, f"destination already existed; removed duplicate source {source}"
            return 0, f"destination already present at {destination}"
        if not source.exists():
            return 1, f"missing source file: {source}"
        shutil.move(str(source), str(destination))
        return 0, f"moved {source} -> {destination}"

    if step.kind != "python":
        return 1, f"unsupported step kind: {step.kind}"
    if not step.command:
        return 1, "python step is missing command"
    return run_python_command(list(step.command))


def run_steps(
    *,
    runner_name: str,
    steps: list[StepSpec],
    state_path: Path,
    ledger_path: Path,
    resume: bool,
) -> tuple[dict[str, Any], bool]:
    state = initialize_state(runner_name=runner_name, steps=steps, state_path=state_path)
    save_state(state_path, state)
    all_successful = True

    for index, step in enumerate(steps, start=1):
        entry = _step_state_entry(state, step.step_id)
        already_successful = (
            resume
            and entry.get("status") == "completed"
            and _expected_outputs_present(step)
        )
        if already_successful:
            append_jsonl(
                ledger_path,
                {
                    "timestamp": utc_now(),
                    "runner_name": runner_name,
                    "step_id": step.step_id,
                    "status": "skipped_existing",
                    "execution_order": index,
                },
            )
            continue

        state["current_step"] = step.step_id
        state["current_step_description"] = step.description
        save_state(state_path, state)
        started_at = utc_now()
        returncode, output_excerpt = _execute_step(step)
        status = "completed" if returncode == 0 and _expected_outputs_present(step) else "failed"
        entry.update(
            {
                "description": step.description,
                "kind": step.kind,
                "status": status,
                "started_at": started_at,
                "completed_at": utc_now(),
                "returncode": returncode,
                "expected_outputs": list(step.expected_outputs),
                "source": step.source,
                "destination": step.destination,
                "metadata": dict(step.metadata),
                "output_excerpt": output_excerpt[-4000:],
            }
        )
        if status == "completed":
            state["last_successful_step"] = step.step_id
        else:
            state["last_failed_step"] = step.step_id
            state["restart_hint"] = f"Resume with --resume after fixing step '{step.step_id}'."
            all_successful = False
        save_state(state_path, state)
        append_jsonl(
            ledger_path,
            {
                "timestamp": utc_now(),
                "runner_name": runner_name,
                "step_id": step.step_id,
                "status": status,
                "returncode": returncode,
                "execution_order": index,
            },
        )
        if status != "completed":
            break

    if all_successful:
        state["current_step"] = None
        state["current_step_description"] = None
        state["last_failed_step"] = None
        state["restart_hint"] = "No restart needed; all post-tail steps completed."
        save_state(state_path, state)
    return state, all_successful


def python_step(
    step_id: str,
    description: str,
    script_relative_path: str,
    *,
    args: list[str] | None = None,
    expected_outputs: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> StepSpec:
    command = [sys.executable, str(REPO_ROOT / script_relative_path)]
    if args:
        command.extend(args)
    return StepSpec(
        step_id=step_id,
        description=description,
        kind="python",
        command=tuple(command),
        expected_outputs=tuple(expected_outputs or []),
        metadata=dict(metadata or {}),
    )


def move_step(
    step_id: str,
    description: str,
    *,
    source: str,
    destination: str,
    metadata: dict[str, Any] | None = None,
) -> StepSpec:
    return StepSpec(
        step_id=step_id,
        description=description,
        kind="move",
        source=source,
        destination=destination,
        metadata=dict(metadata or {}),
    )
