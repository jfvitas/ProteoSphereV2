from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts import run_post_download_processing as runner


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_sequence_artifact() -> dict[str, object]:
    return {
        "schema_id": "proteosphere-p32-processing-sequence-2026-03-30",
        "generated_at": "2026-03-30T16:48:53.2240981-05:00",
        "basis": {
            "raw_mirror_dirs": ["data/raw/uniprot", "data/raw/intact"],
            "canonical_artifact": "data/canonical/LATEST.json",
            "summary_artifacts": [
                "artifacts/status/reactome_local_summary_library.json",
                "artifacts/status/intact_local_summary_library.json",
            ],
        },
        "current_state": {
            "registry_summary": {"present": 29, "partial": 2, "missing": 8},
            "packet_state": {
                "selected_count": 12,
                "complete_count": 7,
                "partial_count": 5,
                "unresolved_count": 0,
            },
        },
        "processing_sequence": [
            {
                "rank": 1,
                "stage": "validation",
                "title": "Preflight the wave and registry",
                "commands": [
                    (
                        "python scripts\\export_source_coverage_matrix.py --output "
                        "artifacts\\status\\source_coverage_matrix.json"
                    ),
                    "python scripts\\validate_operator_state.py",
                ],
                "inputs": ["data/raw/bootstrap_runs/LATEST.json"],
                "expected_outputs": [
                    "artifacts/status/source_coverage_matrix.json",
                    "docs/reports/source_coverage_matrix.md",
                ],
                "gates": ["Do not move to import refresh until validation passes."],
                "sample_output": {"source_coverage_summary": {"present": 29}},
            },
            {
                "rank": 2,
                "stage": "local_imports",
                "title": "Refresh local mirrors and registry state",
                "commands": ["python scripts\\import_local_sources.py --include-missing"],
                "inputs": ["data/raw/local_registry_runs/LATEST.json"],
                "expected_outputs": ["data/raw/local_registry_runs/LATEST.json"],
                "gates": ["Missing source lanes should stay visible."],
            },
            {
                "rank": 3,
                "stage": "canonical_rebuild",
                "title": "Rebuild the canonical store",
                "commands": ["python scripts\\materialize_canonical_store.py"],
                "inputs": ["data/raw/bootstrap_runs/LATEST.json"],
                "expected_outputs": ["data/canonical/LATEST.json"],
                "gates": ["Canonical rebuild waits for the import refresh."],
            },
            {
                "rank": 4,
                "stage": "summary_rebuilds",
                "title": "Refresh source summaries",
                "commands": [
                    (
                        "python scripts\\materialize_protein_summary_library.py --output "
                        "artifacts\\status\\protein_summary_library.json"
                    )
                ],
                "inputs": ["data/canonical/LATEST.json"],
                "expected_outputs": ["artifacts/status/protein_summary_library.json"],
                "gates": ["Summary rebuild waits for canonical refresh."],
            },
            {
                "rank": 5,
                "stage": "packet_rematerialization",
                "title": "Regenerate available payloads and rematerialize packets",
                "commands": [
                    "python scripts\\materialize_selected_packet_cohort.py --run-id test-wave"
                ],
                "inputs": ["artifacts/status/protein_summary_library.json"],
                "expected_outputs": ["data/packages/LATEST.json"],
                "gates": ["Packet rematerialization waits for summary refresh."],
            },
            {
                "rank": 6,
                "stage": "postrun_validation",
                "title": "Final validation",
                "commands": ["python scripts\\validate_operator_state.py"],
                "inputs": ["data/packages/LATEST.json"],
                "expected_outputs": ["artifacts/status/p32_post_download_processing_status.json"],
                "gates": ["Only run after packet rematerialization completes."],
            },
        ],
    }


def _completed_process(
    command: str,
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=command,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _stage_status_rows(
    manifest: dict[str, object],
    *,
    passed_stages: set[str] | None = None,
) -> list[dict[str, object]]:
    passed_stages = passed_stages or set()
    rows: list[dict[str, object]] = []
    for stage in manifest["ordered_stages"]:
        assert isinstance(stage, dict)
        stage_name = str(stage["stage"])
        passed = stage_name in passed_stages
        rows.append(
            {
                "sequence_index": stage["sequence_index"],
                "rank": stage["rank"],
                "stage": stage_name,
                "title": stage["title"],
                "command_count": len(stage["commands"]),
                "completed_command_count": len(stage["commands"]) if passed else 0,
                "status": "passed" if passed else "planned",
                "returncode": 0 if passed else None,
            }
        )
    return rows


def test_build_run_manifest_orders_stages_and_commands(tmp_path: Path) -> None:
    sequence_artifact = tmp_path / "artifacts" / "status" / "p32_processing_sequence.json"
    _write_json(sequence_artifact, _sample_sequence_artifact())

    manifest = runner.build_run_manifest(sequence_artifact)

    assert manifest["schema_id"] == "proteosphere-p32-processing-run-manifest-2026-03-30"
    assert manifest["selection"]["mode"] == "all"
    assert manifest["summary"] == {
        "stage_count": 6,
        "command_count": 7,
        "input_count": 6,
        "output_count": 7,
        "gate_count": 6,
    }
    assert [stage["stage"] for stage in manifest["ordered_stages"]] == [
        "validation",
        "local_imports",
        "canonical_rebuild",
        "summary_rebuilds",
        "packet_rematerialization",
        "postrun_validation",
    ]
    assert [command["stage"] for command in manifest["ordered_commands"]] == [
        "validation",
        "validation",
        "local_imports",
        "canonical_rebuild",
        "summary_rebuilds",
        "packet_rematerialization",
        "postrun_validation",
    ]


def test_build_readiness_view_reports_next_safe_stage_from_explicit_status(
    tmp_path: Path,
) -> None:
    sequence_artifact = tmp_path / "artifacts" / "status" / "p32_processing_sequence.json"
    _write_json(sequence_artifact, _sample_sequence_artifact())
    manifest = runner.build_run_manifest(sequence_artifact)
    status_payload = runner.build_status_artifact(
        manifest,
        execution_mode="execute",
        execution_status="passed",
        stage_statuses=_stage_status_rows(manifest, passed_stages={"validation"}),
        started_at="2026-03-30T22:00:00+00:00",
        completed_at="2026-03-30T22:01:00+00:00",
    )

    readiness = runner.build_readiness_view(
        sequence_artifact,
        status_artifact=status_payload,
    )

    assert readiness["status_artifact"]["execution_status"] == "passed"
    assert readiness["summary"] == {
        "stage_count": 6,
        "complete_stage_count": 1,
        "ready_stage_count": 1,
        "blocked_stage_count": 4,
    }
    assert readiness["next_safe_stage"]["stage"] == "local_imports"
    assert [stage["state"] for stage in readiness["stages"]] == [
        "complete",
        "ready",
        "blocked",
        "blocked",
        "blocked",
        "blocked",
    ]
    assert readiness["stages"][2]["blockers"][0].startswith("previous stage not passed")


def test_process_post_download_run_dry_run_writes_planned_status(tmp_path: Path) -> None:
    sequence_artifact = tmp_path / "artifacts" / "status" / "p32_processing_sequence.json"
    output_path = tmp_path / "artifacts" / "status" / "p32_processing_run_manifest.json"
    status_output = tmp_path / "artifacts" / "status" / "p32_post_download_processing_status.json"
    readiness_output = tmp_path / "artifacts" / "status" / "p32_processing_readiness.json"
    upstream_status = tmp_path / "artifacts" / "status" / "post_download_processing_status.json"
    _write_json(sequence_artifact, _sample_sequence_artifact())
    manifest = runner.build_run_manifest(sequence_artifact)
    _write_json(
        upstream_status,
        runner.build_status_artifact(
            manifest,
            execution_mode="execute",
            execution_status="passed",
            stage_statuses=_stage_status_rows(manifest, passed_stages={"validation"}),
            started_at="2026-03-30T22:00:00+00:00",
            completed_at="2026-03-30T22:01:00+00:00",
        ),
    )

    result = runner.process_post_download_run(
        sequence_artifact,
        output_path=output_path,
        status_output_path=status_output,
        readiness_output_path=readiness_output,
        stage_selectors=("summary_rebuilds", "packet_rematerialization"),
        resume_from_stage="canonical_rebuild",
        execute=False,
        status_artifact_path=upstream_status,
    )

    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    status_payload = json.loads(status_output.read_text(encoding="utf-8"))
    readiness_payload = json.loads(readiness_output.read_text(encoding="utf-8"))
    assert result["manifest"] == manifest
    assert status_payload["execution"]["mode"] == "dry-run"
    assert status_payload["execution"]["status"] == "planned"
    assert status_payload["execution"]["planned_stage_count"] == 2
    assert status_payload["latest_completed_stage"] is None
    assert readiness_payload["next_safe_stage"]["stage"] == "local_imports"
    assert [row["status"] for row in status_payload["stage_statuses"]] == [
        "planned",
        "planned",
    ]
    assert readiness_payload["stages"][0]["state"] == "complete"
    assert readiness_payload["stages"][1]["state"] == "ready"


def test_process_post_download_run_execute_streams_stage_updates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    sequence_artifact = tmp_path / "artifacts" / "status" / "p32_processing_sequence.json"
    output_path = tmp_path / "artifacts" / "status" / "p32_processing_run_manifest.json"
    status_output = tmp_path / "artifacts" / "status" / "p32_post_download_processing_status.json"
    readiness_output = tmp_path / "artifacts" / "status" / "p32_processing_readiness.json"
    _write_json(sequence_artifact, _sample_sequence_artifact())

    writes: list[dict[str, object]] = []
    real_write_json = runner._write_json

    def _spy_write_json(path: Path, payload: dict[str, object]) -> None:
        if path == status_output:
            writes.append(json.loads(json.dumps(payload)))
        real_write_json(path, payload)

    def _fake_command_runner(command: str) -> subprocess.CompletedProcess[str]:
        if "materialize_protein_summary_library.py" in command:
            return _completed_process(command, returncode=1, stderr="summary failed\n")
        return _completed_process(command, stdout="ok\n")

    monkeypatch.setattr(runner, "_write_json", _spy_write_json)

    result = runner.process_post_download_run(
        sequence_artifact,
        output_path=output_path,
        status_output_path=status_output,
        readiness_output_path=readiness_output,
        stage_selectors=("canonical_rebuild", "summary_rebuilds", "packet_rematerialization"),
        resume_from_stage="canonical_rebuild",
        execute=True,
        command_runner=_fake_command_runner,
    )

    status_payload = json.loads(status_output.read_text(encoding="utf-8"))
    readiness_payload = json.loads(readiness_output.read_text(encoding="utf-8"))
    assert len(writes) >= 2
    assert writes[0]["execution"]["status"] == "running"
    assert writes[0]["latest_completed_stage"]["stage"] == "canonical_rebuild"
    assert status_payload["execution"]["status"] == "failed"
    assert status_payload["execution"]["failed_stage_count"] == 1
    assert status_payload["execution"]["blocked_stage_count"] == 1
    assert [row["status"] for row in status_payload["stage_statuses"]] == [
        "passed",
        "failed",
        "blocked",
    ]
    assert status_payload["latest_completed_stage"]["stage"] == "summary_rebuilds"
    assert status_payload["next_stage"]["stage"] == "packet_rematerialization"
    assert readiness_payload["next_safe_stage"]["stage"] == "validation"
    assert readiness_payload["stages"][1]["state"] == "blocked"
    assert result["manifest"] == json.loads(output_path.read_text(encoding="utf-8"))


def test_main_execute_writes_outputs_with_monkeypatched_runner(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    sequence_artifact = tmp_path / "artifacts" / "status" / "p32_processing_sequence.json"
    output_path = tmp_path / "artifacts" / "status" / "p32_processing_run_manifest.json"
    status_output = tmp_path / "artifacts" / "status" / "p32_post_download_processing_status.json"
    readiness_output = tmp_path / "artifacts" / "status" / "p32_processing_readiness.json"
    _write_json(sequence_artifact, _sample_sequence_artifact())

    monkeypatch.setattr(
        runner,
        "_run_shell_command",
        lambda command: _completed_process(command, stdout="ok\n"),
    )

    exit_code = runner.main(
        [
            "--sequence-artifact",
            str(sequence_artifact),
            "--output",
            str(output_path),
            "--status-output",
            str(status_output),
            "--readiness-output",
            str(readiness_output),
            "--execute",
            "--stage",
            "validation",
        ]
    )

    stdout_payload = json.loads(capsys.readouterr().out)
    status_payload = json.loads(status_output.read_text(encoding="utf-8"))
    readiness_payload = json.loads(readiness_output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert stdout_payload == json.loads(output_path.read_text(encoding="utf-8"))
    assert stdout_payload["selection"]["selected_stage_names"] == ["validation"]
    assert status_payload["execution"]["mode"] == "execute"
    assert status_payload["execution"]["status"] == "passed"
    assert status_payload["stage_statuses"][0]["status"] == "passed"
    assert status_payload["latest_completed_stage"]["stage"] == "validation"
    assert readiness_payload["next_safe_stage"]["stage"] == "local_imports"
