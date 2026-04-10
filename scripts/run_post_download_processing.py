from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEQUENCE_ARTIFACT = REPO_ROOT / "artifacts" / "status" / "p32_processing_sequence.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "p32_processing_run_manifest.json"
DEFAULT_STATUS_OUTPUT = (
    REPO_ROOT / "artifacts" / "status" / "p32_post_download_processing_status.json"
)
DEFAULT_READINESS_OUTPUT = REPO_ROOT / "artifacts" / "status" / "p32_processing_readiness.json"
DEFAULT_STATUS_ARTIFACT_CANDIDATES = (
    REPO_ROOT / "artifacts" / "status" / "p32_post_download_processing_status.json",
    REPO_ROOT / "artifacts" / "status" / "post_download_processing_status.json",
)
SCHEMA_ID = "proteosphere-p32-processing-run-manifest-2026-03-30"
STATUS_SCHEMA_ID = "proteosphere-p32-post-download-status-2026-03-30"
READINESS_SCHEMA_ID = "proteosphere-p32-processing-readiness-2026-03-30"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _tail_text(text: str, *, max_lines: int = 20) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[-max_lines:])


def _is_placeholder_path(text: str) -> bool:
    cleaned = _clean_text(text)
    return "<" in cleaned and ">" in cleaned


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _string_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        text = _clean_text(values)
        return [text] if text else []
    if isinstance(values, Mapping):
        iterable: Any = values.values()
    else:
        iterable = values
    try:
        items = list(iterable)
    except TypeError:
        items = [iterable]
    result: list[str] = []
    for item in items:
        text = _clean_text(item)
        if text:
            result.append(text)
    return result


def _require_mapping(payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError(f"{label} must be a JSON object")
    return dict(payload)


def _stage_name(stage: Mapping[str, Any]) -> str:
    return _clean_text(stage.get("stage"))


def _stage_rank(stage: Mapping[str, Any]) -> int:
    return int(stage.get("rank") or 0)


def _matches_stage_selector(stage: Mapping[str, Any], selector: str) -> bool:
    selector_text = _clean_text(selector)
    if not selector_text:
        return False
    stage_name = _stage_name(stage)
    if selector_text == stage_name:
        return True
    if selector_text.isdigit() and int(selector_text) == _stage_rank(stage):
        return True
    return False


def _stage_manifest(stage: Mapping[str, Any]) -> dict[str, Any]:
    commands = _string_list(stage.get("commands"))
    inputs = _string_list(stage.get("inputs"))
    outputs = _string_list(stage.get("expected_outputs") or stage.get("outputs"))
    gates = _string_list(stage.get("gates"))
    stage_manifest: dict[str, Any] = {
        "rank": int(stage.get("rank") or 0),
        "stage": _clean_text(stage.get("stage")),
        "title": _clean_text(stage.get("title")),
        "commands": commands,
        "inputs": inputs,
        "outputs": outputs,
        "gates": gates,
    }
    sample_output = stage.get("sample_output")
    if isinstance(sample_output, Mapping):
        stage_manifest["sample_output"] = dict(sample_output)
    return stage_manifest


def _stage_input_paths(stage: Mapping[str, Any]) -> tuple[str, ...]:
    inputs = _string_list(stage.get("inputs"))
    return tuple(path for path in inputs if path and not _is_placeholder_path(path))


def _selected_stages(
    stages_payload: list[Any],
    *,
    stage_selectors: tuple[str, ...] = (),
    resume_from_stage: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    available_stages: list[dict[str, Any]] = []
    for index, stage in enumerate(stages_payload, start=1):
        if not isinstance(stage, Mapping):
            raise TypeError(f"processing_sequence[{index - 1}] must be a JSON object")
        stage_manifest = _stage_manifest(stage)
        stage_manifest["sequence_index"] = index
        available_stages.append(stage_manifest)

    stage_names = [stage["stage"] for stage in available_stages]
    resume_stage_text = _clean_text(resume_from_stage)
    if resume_stage_text:
        resume_index = next(
            (
                index
                for index, stage in enumerate(available_stages)
                if _matches_stage_selector(stage, resume_stage_text)
            ),
            None,
        )
        if resume_index is None:
            raise ValueError(
                "resume-from-stage did not match any processing stage: "
                f"{resume_stage_text}. Available stages: {', '.join(stage_names)}"
            )
        candidate_stages = available_stages[resume_index:]
    else:
        candidate_stages = available_stages

    requested_selectors = tuple(
        selector
        for selector in (_clean_text(selector) for selector in stage_selectors)
        if selector
    )
    if requested_selectors:
        selected = [
            stage
            for stage in candidate_stages
            if any(_matches_stage_selector(stage, selector) for selector in requested_selectors)
        ]
        if not selected:
            raise ValueError(
                "stage selection produced no runnable stages. "
                f"Requested selectors: {', '.join(requested_selectors)}. "
                f"Available stages: {', '.join(stage_names)}"
            )
        selection_mode = "stage_filter"
        if resume_stage_text:
            selection_mode = "stage_filter+resume"
    else:
        selected = list(candidate_stages)
        selection_mode = "resume" if resume_stage_text else "all"

    selected_stage_names = [stage["stage"] for stage in selected]
    selected_stage_ranks = [stage["rank"] for stage in selected]
    selection = {
        "mode": selection_mode,
        "requested_stage_selectors": list(requested_selectors),
        "resume_from_stage": resume_stage_text,
        "selected_stage_names": selected_stage_names,
        "selected_stage_ranks": selected_stage_ranks,
        "selected_stage_count": len(selected),
        "selected_command_count": sum(len(stage["commands"]) for stage in selected),
    }
    return selected, selection


def _build_wave_context(sequence_payload: Mapping[str, Any]) -> dict[str, Any]:
    wave_context: dict[str, Any] = {}
    for key in ("basis", "current_state"):
        value = sequence_payload.get(key)
        if isinstance(value, Mapping):
            wave_context[key] = dict(value)
    return wave_context


def _artifact_exists(relative_path: str) -> bool:
    if not relative_path:
        return False
    return (REPO_ROOT / Path(relative_path)).exists()


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = _require_mapping(_read_json(path), str(path))
    return payload


def _resolve_status_artifact_path(explicit_path: Path | None = None) -> Path | None:
    if explicit_path is not None:
        if explicit_path.exists():
            return explicit_path
        raise FileNotFoundError(f"status artifact not found: {explicit_path}")
    for candidate in DEFAULT_STATUS_ARTIFACT_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _status_stage_map(status_artifact: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    stage_map: dict[str, dict[str, Any]] = {}
    if not isinstance(status_artifact, Mapping):
        return stage_map
    stages = status_artifact.get("stage_statuses")
    if not isinstance(stages, list):
        return stage_map
    for stage in stages:
        if not isinstance(stage, Mapping):
            continue
        name = _clean_text(stage.get("stage"))
        if name:
            stage_map[name] = dict(stage)
    return stage_map


def _readiness_requirement_paths(
    stage_name: str,
    sequence_payload: Mapping[str, Any],
) -> tuple[str, ...]:
    basis = sequence_payload.get("basis")
    basis_raw_mirrors: tuple[str, ...] = ()
    if isinstance(basis, Mapping):
        basis_raw_mirrors = tuple(
            path
            for path in _string_list(basis.get("raw_mirror_dirs"))
            if path and not _is_placeholder_path(path)
        )
    stage_name = _clean_text(stage_name)
    if stage_name == "validation":
        return (
            *basis_raw_mirrors,
            "data/raw/bootstrap_runs/LATEST.json",
            "data/raw/local_registry_runs/LATEST.json",
            "artifacts/status/reactome_local_summary_library.json",
            "artifacts/status/intact_local_summary_library.json",
            "data/packages/LATEST.json",
        )
    if stage_name == "local_imports":
        return basis_raw_mirrors
    if stage_name == "canonical_rebuild":
        return (
            *basis_raw_mirrors,
            "data/raw/bootstrap_runs/LATEST.json",
            "data/raw/local_registry_runs/LATEST.json",
        )
    if stage_name == "summary_rebuilds":
        return (
            "data/canonical/LATEST.json",
            "artifacts/status/release_cohort_registry.json",
            "artifacts/status/reactome_local_summary_library.json",
            "artifacts/status/intact_local_summary_library.json",
            "runs/real_data_benchmark/full_results/p15_upgraded_cohort_slice.json",
        )
    if stage_name == "packet_rematerialization":
        return (
            "runs/real_data_benchmark/full_results/balanced_dataset_plan.json",
            "data/canonical/LATEST.json",
            "data/packages/LATEST.json",
            "artifacts/status/protein_summary_library.json",
        )
    if stage_name == "postrun_validation":
        return (
            "data/packages/LATEST.json",
            "artifacts/status/selected_cohort_materialization.current.json",
            "artifacts/status/packet_deficit_dashboard.json",
        )
    return ()


def _build_source_artifact(
    sequence_artifact_path: Path,
    sequence_payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "path": str(sequence_artifact_path).replace("\\", "/"),
        "sha256": _file_sha256(sequence_artifact_path),
        "schema_id": _clean_text(sequence_payload.get("schema_id")),
        "generated_at": _clean_text(sequence_payload.get("generated_at")),
    }


def _build_stage_and_command_rows(
    selected_stages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int, int]:
    ordered_stages: list[dict[str, Any]] = []
    ordered_commands: list[dict[str, Any]] = []
    input_count = 0
    output_count = 0
    gate_count = 0

    for stage_index, stage_manifest in enumerate(selected_stages, start=1):
        ordered_stages.append(stage_manifest)
        input_count += len(stage_manifest["inputs"])
        output_count += len(stage_manifest["outputs"])
        gate_count += len(stage_manifest["gates"])

        for command_index, command in enumerate(stage_manifest["commands"], start=1):
            ordered_commands.append(
                {
                    "sequence_index": len(ordered_commands) + 1,
                    "stage_sequence_index": stage_index,
                    "rank": stage_manifest["rank"],
                    "stage": stage_manifest["stage"],
                    "command_index": command_index,
                    "command": command,
                }
            )

    return ordered_stages, ordered_commands, input_count, output_count, gate_count


def _stage_ref(stage: Mapping[str, Any], *, include_status: bool = False) -> dict[str, Any]:
    ref = {
        "sequence_index": int(stage.get("sequence_index") or 0),
        "rank": int(stage.get("rank") or 0),
        "stage": _clean_text(stage.get("stage")),
        "title": _clean_text(stage.get("title")),
    }
    if include_status:
        ref["status"] = _clean_text(stage.get("status"))
    return ref


def _planned_stage_status(stage: Mapping[str, Any]) -> dict[str, Any]:
    row = _stage_ref(stage, include_status=True)
    row.update(
        {
            "command_count": len(_string_list(stage.get("commands"))),
            "completed_command_count": 0,
            "status": "planned",
            "returncode": None,
        }
    )
    return row


def _blocked_stage_status(stage: Mapping[str, Any], reason: str) -> dict[str, Any]:
    row = _planned_stage_status(stage)
    row.update({"status": "blocked", "reason": reason})
    return row


def build_readiness_view(
    manifest_or_path: Path | Mapping[str, Any],
    *,
    status_artifact: Path | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    sequence_artifact_path = DEFAULT_SEQUENCE_ARTIFACT
    if isinstance(manifest_or_path, Path):
        sequence_artifact_path = manifest_or_path
    else:
        source_artifact = manifest_or_path.get("source_artifact")
        if isinstance(source_artifact, Mapping):
            source_path_text = _clean_text(source_artifact.get("path"))
            if source_path_text:
                candidate_path = Path(source_path_text)
                if not candidate_path.is_absolute():
                    candidate_path = REPO_ROOT / candidate_path
                sequence_artifact_path = candidate_path
    if not sequence_artifact_path.exists():
        sequence_artifact_path = DEFAULT_SEQUENCE_ARTIFACT
    sequence_payload = _require_mapping(
        _read_json(sequence_artifact_path),
        "sequence artifact",
    )
    manifest = build_run_manifest(sequence_artifact_path)
    stage_rows = manifest.get("ordered_stages")
    if not isinstance(stage_rows, list):
        raise TypeError("run manifest is missing ordered_stages")

    resolved_status_path: Path | None = None
    status_payload: dict[str, Any] | None
    if isinstance(status_artifact, Path):
        resolved_status_path = _resolve_status_artifact_path(status_artifact)
        status_payload = (
            _load_json_if_exists(resolved_status_path) if resolved_status_path else None
        )
    elif isinstance(status_artifact, Mapping):
        status_payload = dict(status_artifact)
    else:
        resolved_status_path = _resolve_status_artifact_path()
        status_payload = (
            _load_json_if_exists(resolved_status_path) if resolved_status_path else None
        )

    stage_status_map = _status_stage_map(status_payload)
    stage_readiness: list[dict[str, Any]] = []
    previous_stage_passed = True
    previous_stage_name = ""

    for stage in stage_rows:
        stage_name = _clean_text(stage.get("stage"))
        explicit_status = _clean_text(stage_status_map.get(stage_name, {}).get("status"))
        required_artifacts = _readiness_requirement_paths(stage_name, sequence_payload)
        present_artifacts = [path for path in required_artifacts if _artifact_exists(path)]
        missing_artifacts = [path for path in required_artifacts if path not in present_artifacts]
        blockers: list[str] = []

        if not previous_stage_passed and previous_stage_name:
            blockers.append(f"previous stage not passed: {previous_stage_name}")
        for path in missing_artifacts:
            blockers.append(f"missing artifact: {path}")
        if explicit_status in {"failed", "blocked"}:
            blockers.append(f"explicit status is {explicit_status}")
        if not explicit_status and stage_name != "validation" and previous_stage_name:
            blockers.append("explicit status missing")

        safe_to_run = previous_stage_passed and not missing_artifacts and explicit_status not in {
            "failed",
            "blocked",
            "passed",
        }
        state = "ready" if safe_to_run else "blocked"
        if explicit_status == "passed":
            state = "complete"

        stage_row = {
            "rank": int(stage.get("rank") or 0),
            "stage": stage_name,
            "title": _clean_text(stage.get("title")),
            "explicit_status": explicit_status or None,
            "state": state,
            "safe_to_run": safe_to_run,
            "required_artifacts": list(required_artifacts),
            "required_artifacts_present": present_artifacts,
            "required_artifacts_missing": missing_artifacts,
            "blockers": blockers,
        }
        stage_readiness.append(stage_row)
        previous_stage_passed = explicit_status == "passed"
        previous_stage_name = stage_name

    next_safe_stage = next((stage for stage in stage_readiness if stage["safe_to_run"]), None)
    complete_stage_count = sum(1 for stage in stage_readiness if stage["state"] == "complete")
    ready_stage_count = sum(1 for stage in stage_readiness if stage["state"] == "ready")
    blocked_stage_count = sum(1 for stage in stage_readiness if stage["state"] == "blocked")
    status_summary = {
        "path": None if resolved_status_path is None else _repo_relative(resolved_status_path),
        "exists": status_payload is not None,
        "execution_status": _clean_text((status_payload or {}).get("execution", {}).get("status")),
        "latest_completed_stage": (status_payload or {}).get("latest_completed_stage"),
    }
    return {
        "schema_id": READINESS_SCHEMA_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_artifact": manifest["source_artifact"],
        "status_artifact": status_summary,
        "summary": {
            "stage_count": len(stage_readiness),
            "complete_stage_count": complete_stage_count,
            "ready_stage_count": ready_stage_count,
            "blocked_stage_count": blocked_stage_count,
        },
        "next_safe_stage": next_safe_stage,
        "stages": stage_readiness,
    }


def _execution_stage_status(
    stage: Mapping[str, Any],
    *,
    started_at: str,
    finished_at: str,
    command_results: list[subprocess.CompletedProcess[str]],
    status: str,
    failed_command_index: int | None = None,
    failed_command: str | None = None,
) -> dict[str, Any]:
    row = _stage_ref(stage, include_status=True)
    last_result = command_results[-1] if command_results else None
    row.update(
        {
            "command_count": len(_string_list(stage.get("commands"))),
            "completed_command_count": len(command_results),
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "returncode": None if last_result is None else last_result.returncode,
            "failed_command_index": failed_command_index,
            "failed_command": failed_command,
            "stdout_tail": _tail_text(last_result.stdout) if last_result else "",
            "stderr_tail": _tail_text(last_result.stderr) if last_result else "",
        }
    )
    return row


def _run_shell_command(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )


def build_run_manifest(
    sequence_artifact_path: Path,
    *,
    stage_selectors: tuple[str, ...] = (),
    resume_from_stage: str | None = None,
) -> dict[str, Any]:
    sequence_payload = _require_mapping(_read_json(sequence_artifact_path), "sequence artifact")
    stages_payload = sequence_payload.get("processing_sequence")
    if not isinstance(stages_payload, list):
        raise TypeError("sequence artifact is missing processing_sequence")

    selected_stages, selection = _selected_stages(
        stages_payload,
        stage_selectors=stage_selectors,
        resume_from_stage=resume_from_stage,
    )
    ordered_stages, ordered_commands, input_count, output_count, gate_count = (
        _build_stage_and_command_rows(selected_stages)
    )
    source_artifact = _build_source_artifact(sequence_artifact_path, sequence_payload)
    wave_context = _build_wave_context(sequence_payload)

    return {
        "schema_id": SCHEMA_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_artifact": source_artifact,
        "selection": selection,
        "summary": {
            "stage_count": len(ordered_stages),
            "command_count": len(ordered_commands),
            "input_count": input_count,
            "output_count": output_count,
            "gate_count": gate_count,
        },
        "wave_context": wave_context,
        "ordered_stages": ordered_stages,
        "ordered_commands": ordered_commands,
    }


def build_status_artifact(
    manifest_or_path: Path | Mapping[str, Any],
    *,
    execution_mode: str = "dry-run",
    execution_status: str | None = None,
    stage_statuses: list[dict[str, Any]] | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    manifest = (
        build_run_manifest(manifest_or_path)
        if isinstance(manifest_or_path, Path)
        else dict(manifest_or_path)
    )
    selected_stages = manifest.get("ordered_stages")
    if not isinstance(selected_stages, list):
        raise TypeError("run manifest is missing ordered_stages")
    if stage_statuses is None:
        stage_statuses = [_planned_stage_status(stage) for stage in selected_stages]
    execution_status = execution_status or ("planned" if execution_mode == "dry-run" else "running")
    completed_stage_count = sum(
        1 for stage in stage_statuses if _clean_text(stage.get("status")) in {"passed", "failed"}
    )
    failed_stage_count = sum(
        1 for stage in stage_statuses if _clean_text(stage.get("status")) == "failed"
    )
    blocked_stage_count = sum(
        1 for stage in stage_statuses if _clean_text(stage.get("status")) == "blocked"
    )
    planned_stage_count = sum(
        1 for stage in stage_statuses if _clean_text(stage.get("status")) == "planned"
    )
    latest_completed_stage = next(
        (
            _stage_ref(stage, include_status=True)
            for stage in reversed(stage_statuses)
            if _clean_text(stage.get("status")) in {"passed", "failed"}
        ),
        None,
    )
    next_stage = next(
        (
            _stage_ref(stage, include_status=True)
            for stage in stage_statuses
            if _clean_text(stage.get("status")) in {"planned", "blocked"}
        ),
        None,
    )
    return {
        "schema_id": STATUS_SCHEMA_ID,
        "generated_at": manifest["generated_at"],
        "source_artifact": manifest["source_artifact"],
        "selection": manifest["selection"],
        "execution": {
            "mode": execution_mode,
            "status": execution_status,
            "started_at": started_at,
            "completed_at": completed_at,
            "completed_stage_count": completed_stage_count,
            "failed_stage_count": failed_stage_count,
            "blocked_stage_count": blocked_stage_count,
            "planned_stage_count": planned_stage_count,
        },
        "summary": manifest["summary"],
        "wave_context": manifest["wave_context"],
        "latest_completed_stage": latest_completed_stage,
        "next_stage": next_stage,
        "stage_statuses": stage_statuses,
    }


def _set_remaining_blocked(
    stage_statuses: list[dict[str, Any]],
    selected_stages: list[dict[str, Any]],
    start_index: int,
    reason: str,
) -> None:
    for offset, stage in enumerate(selected_stages[start_index:], start=start_index):
        stage_statuses[offset] = _blocked_stage_status(stage, reason)


def process_post_download_run(
    sequence_artifact_path: Path,
    *,
    output_path: Path = DEFAULT_OUTPUT,
    status_output_path: Path = DEFAULT_STATUS_OUTPUT,
    readiness_output_path: Path = DEFAULT_READINESS_OUTPUT,
    stage_selectors: tuple[str, ...] = (),
    resume_from_stage: str | None = None,
    execute: bool = False,
    command_runner: Callable[[str], subprocess.CompletedProcess[str]] | None = None,
    status_artifact_path: Path | None = None,
) -> dict[str, Any]:
    manifest = build_run_manifest(
        sequence_artifact_path,
        stage_selectors=stage_selectors,
        resume_from_stage=resume_from_stage,
    )
    ordered_stages = manifest["ordered_stages"]
    run_started_at = datetime.now(UTC).isoformat()
    command_runner = command_runner or _run_shell_command

    def _write_snapshots(status_payload: dict[str, Any]) -> dict[str, Any]:
        readiness_payload = build_readiness_view(
            sequence_artifact_path,
            status_artifact=status_payload
            if execute
            else (status_artifact_path or status_payload),
        )
        _write_json(status_output_path, status_payload)
        _write_json(readiness_output_path, readiness_payload)
        return readiness_payload

    if not execute:
        stage_statuses = [_planned_stage_status(stage) for stage in ordered_stages]
        status_artifact = build_status_artifact(
            manifest,
            execution_mode="dry-run",
            execution_status="planned",
            stage_statuses=stage_statuses,
            started_at=run_started_at,
        )
        _write_json(output_path, manifest)
        readiness_artifact = _write_snapshots(status_artifact)
        return {
            "manifest": manifest,
            "status": status_artifact,
            "readiness": readiness_artifact,
        }

    stage_statuses = [_planned_stage_status(stage) for stage in ordered_stages]
    execution_status = "passed"
    completed_at: str | None = None

    for stage_index, stage in enumerate(ordered_stages):
        stage_started_at = datetime.now(UTC).isoformat()
        command_results: list[subprocess.CompletedProcess[str]] = []
        failure_command_index: int | None = None
        failure_command: str | None = None
        stage_status = "passed"
        for command_index, command in enumerate(stage["commands"], start=1):
            completed = command_runner(command)
            command_results.append(completed)
            if completed.returncode != 0:
                stage_status = "failed"
                failure_command_index = command_index
                failure_command = command
                break
        stage_statuses[stage_index] = _execution_stage_status(
            stage,
            started_at=stage_started_at,
            finished_at=datetime.now(UTC).isoformat(),
            command_results=command_results,
            status=stage_status,
            failed_command_index=failure_command_index,
            failed_command=failure_command,
        )
        if stage_status == "failed":
            execution_status = "failed"
            _set_remaining_blocked(
                stage_statuses,
                ordered_stages,
                stage_index + 1,
                f"previous stage failed: {stage_statuses[stage_index]['stage']}",
            )
            completed_at = datetime.now(UTC).isoformat()
            status_artifact = build_status_artifact(
                manifest,
                execution_mode="execute",
                execution_status=execution_status,
                stage_statuses=stage_statuses,
                started_at=run_started_at,
                completed_at=completed_at,
            )
            readiness_artifact = _write_snapshots(status_artifact)
            _write_json(output_path, manifest)
            return {
                "manifest": manifest,
                "status": status_artifact,
                "readiness": readiness_artifact,
            }

        status_artifact = build_status_artifact(
            manifest,
            execution_mode="execute",
            execution_status="running",
            stage_statuses=stage_statuses,
            started_at=run_started_at,
        )
        _write_snapshots(status_artifact)

    completed_at = datetime.now(UTC).isoformat()
    status_artifact = build_status_artifact(
        manifest,
        execution_mode="execute",
        execution_status=execution_status,
        stage_statuses=stage_statuses,
        started_at=run_started_at,
        completed_at=completed_at,
    )
    _write_json(output_path, manifest)
    readiness_artifact = _write_snapshots(status_artifact)
    return {
        "manifest": manifest,
        "status": status_artifact,
        "readiness": readiness_artifact,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit a machine-readable run manifest from p32_processing_sequence.json."
    )
    parser.add_argument("--sequence-artifact", type=Path, default=DEFAULT_SEQUENCE_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--status-output", type=Path, default=DEFAULT_STATUS_OUTPUT)
    parser.add_argument("--readiness-output", type=Path, default=DEFAULT_READINESS_OUTPUT)
    parser.add_argument(
        "--status-artifact",
        type=Path,
        default=None,
        help="Optional explicit status artifact to use when building readiness.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the selected stages instead of only planning them.",
    )
    parser.add_argument(
        "--stage",
        dest="stage_selectors",
        action="append",
        default=None,
        help="Select one or more stages by rank or name. May be repeated.",
    )
    parser.add_argument(
        "--resume-from-stage",
        default=None,
        help="Resume from the named or ranked stage, inclusive.",
    )
    parser.add_argument(
        "--no-stdout",
        action="store_true",
        help="Write the run manifest to --output without echoing JSON to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    stage_selectors = tuple(args.stage_selectors or ())
    result = process_post_download_run(
        args.sequence_artifact,
        output_path=args.output,
        status_output_path=args.status_output,
        readiness_output_path=args.readiness_output,
        stage_selectors=stage_selectors,
        resume_from_stage=args.resume_from_stage,
        execute=args.execute,
        status_artifact_path=args.status_artifact,
    )
    manifest = result["manifest"]
    if not args.no_stdout:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
