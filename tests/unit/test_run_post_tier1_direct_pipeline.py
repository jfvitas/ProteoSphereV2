from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import run_post_tier1_direct_pipeline as pipeline


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_run_post_tier1_pipeline_requires_promoted_artifact(tmp_path: Path) -> None:
    promotion_path = tmp_path / "promotion.json"
    _write_json(promotion_path, {"status": "held"})

    with pytest.raises(ValueError, match="not promoted"):
        pipeline.run_post_tier1_pipeline(
            promotion_path=promotion_path,
            status_path=tmp_path / "status.json",
            markdown_path=tmp_path / "report.md",
        )


def test_run_post_tier1_pipeline_runs_steps_in_order(monkeypatch, tmp_path: Path) -> None:
    promotion_path = tmp_path / "promotion.json"
    _write_json(
        promotion_path,
        {
            "status": "promoted",
            "promotion_id": "promotion-001",
        },
    )
    commands: list[tuple[str, ...]] = []

    class Result:
        def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    monkeypatch.setattr(
        pipeline,
        "DEFAULT_PACKAGES_ROOT",
        tmp_path / "packages",
    )
    monkeypatch.setattr(
        pipeline,
        "DEFAULT_BASELINE_PACKET_SUMMARY_PATH",
        tmp_path / "packages" / "LATEST.json",
    )
    _write_json(
        tmp_path / "packages" / "LATEST.json",
        {
            "packet_count": 1,
            "complete_count": 1,
            "partial_count": 0,
            "unresolved_count": 0,
            "packets": [
                {
                    "accession": "P68871",
                    "status": "complete",
                    "missing_modalities": [],
                }
            ],
        },
    )

    def fake_run(command: tuple[str, ...]) -> Result:
        commands.append(command)
        command_text = " ".join(command)
        if "materialize_selected_packet_cohort.py" in command_text:
            output_index = command.index("--output") + 1
            output_root_index = command.index("--output-root") + 1
            _write_json(
                Path(command[output_index]),
                {
                    "materialization": {
                        "packet_count": 1,
                        "complete_count": 1,
                        "partial_count": 0,
                        "unresolved_count": 0,
                        "packets": [
                            {
                                "accession": "P68871",
                                "status": "complete",
                                "missing_modalities": [],
                            }
                        ],
                    }
                },
            )
            _write_json(Path(command[output_root_index]) / "LATEST.json", {"status": "ready"})
        elif "materialize_canonical_store.py" in command_text:
            canonical_root = Path(command[command.index("--canonical-root") + 1])
            _write_json(
                canonical_root / "LATEST.json",
                {
                    "status": "ready",
                    "bindingdb_selection": {
                        "selected_summary_path": "data/raw/bindingdb_dump_local/LATEST.json",
                        "selection_mode": "local_summary",
                        "local_row_count": 1,
                    },
                },
            )
        elif "export_source_coverage_matrix.py" in command_text:
            _write_json(Path(command[command.index("--output") + 1]), {"status": "ok"})
            Path(command[command.index("--markdown-output") + 1]).write_text(
                "# source coverage\n",
                encoding="utf-8",
            )
        elif "generate_available_payload_registry.py" in command_text:
            _write_json(Path(command[command.index("--output") + 1]), {"status": "ok"})
        elif "export_packet_deficit_dashboard.py" in command_text:
            _write_json(Path(command[command.index("--output") + 1]), {"status": "ok"})
            Path(command[command.index("--markdown-output") + 1]).write_text(
                "# packet deficit\n",
                encoding="utf-8",
            )
        return Result(returncode=0, stdout="ok")

    monkeypatch.setattr(pipeline, "_run_command", fake_run)

    payload = pipeline.run_post_tier1_pipeline(
        promotion_path=promotion_path,
        status_path=tmp_path / "status.json",
        markdown_path=tmp_path / "report.md",
    )

    assert payload["status"] == "passed"
    assert (
        payload["canonical_traceability"]["bindingdb_selection"]["selected_summary_path"]
        == "data/raw/bindingdb_dump_local/LATEST.json"
    )
    assert payload["packet_regression_gate"]["status"] == "passed"
    assert (
        payload["packet_regression_gate"]["baseline_selection"][
            "current_latest_matches_strongest"
        ]
        is True
    )
    assert [step["step_id"] for step in payload["steps"]] == [
        "canonical",
        "source_coverage_matrix",
        "available_payload_registry",
        "selected_packet_materialization",
        "packet_deficit_dashboard",
    ]
    assert commands[0][:2] == ("python", "scripts\\materialize_canonical_store.py")
    assert "--canonical-root" in commands[0]
    assert commands[-1][:2] == ("python", "scripts\\export_packet_deficit_dashboard.py")
    assert "--packages-root" in commands[-1]
    assert payload["scope_root"].startswith("runs/tier1_direct_validation/")


def test_render_post_tier1_pipeline_markdown_includes_steps() -> None:
    payload = {
        "status": "passed",
        "generated_at": "2026-03-23T00:00:00+00:00",
        "promotion_path": "data/raw/protein_data_scope_seed/promotions/LATEST.json",
        "promotion_id": "promotion-001",
        "run_id": "20260323T000000Z",
        "scope_root": "runs/tier1_direct_validation/20260323T000000Z",
        "canonical_traceability": {
            "canonical_latest_path": (
                "runs/tier1_direct_validation/20260323T000000Z/"
                "canonical/LATEST.json"
            ),
            "bindingdb_selection": {
                "selected_summary_path": (
                    "data/raw/bindingdb_dump_local/"
                    "bindingdb-local-20260323/summary.json"
                ),
                "selection_mode": "local_summary",
                "local_row_count": 5138,
            },
        },
        "packet_regression_gate": {
            "status": "passed",
            "baseline_path": "data/packages/LATEST.json",
            "candidate_path": (
                "runs/tier1_direct_validation/20260323T000000Z/"
                "selected_cohort_materialization.json"
            ),
            "baseline_selection": {
                "selection_notes": ["baseline_selector=strongest_materialization_summary"],
                "current_latest_path": "data/packages/LATEST.json",
                "current_latest_matches_strongest": False,
            },
            "baseline_metrics": {
                "complete_count": 7,
                "partial_count": 5,
                "unresolved_count": 0,
                "packet_deficit_count": 5,
                "total_missing_modality_count": 7,
            },
            "candidate_metrics": {
                "complete_count": 7,
                "partial_count": 5,
                "unresolved_count": 0,
                "packet_deficit_count": 5,
                "total_missing_modality_count": 7,
            },
            "regressions": [],
            "improvements": [],
        },
        "steps": [
            {
                "step_id": "canonical",
                "label": "Canonical materialization",
                "status": "passed",
                "returncode": 0,
                "command": ["python", "scripts\\materialize_canonical_store.py"],
            }
        ],
    }

    markdown = pipeline.render_post_tier1_pipeline_markdown(payload)

    assert "# Post Tier1 Direct Pipeline" in markdown
    assert "## Canonical Traceability" in markdown
    assert "BindingDB selection path" in markdown
    assert "## Packet Regression Gate" in markdown
    assert "Current latest matches strongest baseline" in markdown
    assert "## canonical" in markdown
    assert "Scope root" in markdown


def test_run_post_tier1_pipeline_marks_regressive_packet_state_failed(
    monkeypatch,
    tmp_path: Path,
) -> None:
    promotion_path = tmp_path / "promotion.json"
    _write_json(
        promotion_path,
        {
            "status": "promoted",
            "promotion_id": "promotion-001",
        },
    )
    monkeypatch.setattr(
        pipeline,
        "DEFAULT_PACKAGES_ROOT",
        tmp_path / "packages",
    )
    monkeypatch.setattr(
        pipeline,
        "DEFAULT_BASELINE_PACKET_SUMMARY_PATH",
        tmp_path / "packages" / "LATEST.json",
    )
    _write_json(
        tmp_path / "packages" / "LATEST.json",
        {
            "packet_count": 2,
            "complete_count": 1,
            "partial_count": 1,
            "unresolved_count": 0,
            "packets": [
                {
                    "accession": "P69905",
                    "status": "partial",
                    "missing_modalities": ["ligand"],
                },
                {"accession": "P04637", "status": "complete", "missing_modalities": []},
            ],
        },
    )
    _write_json(
        tmp_path
        / "packages"
        / "selected-cohort-strict-20260323T1648Z"
        / "materialization_summary.json",
        {
            "packet_count": 2,
            "complete_count": 2,
            "partial_count": 0,
            "unresolved_count": 0,
            "packets": [
                {"accession": "P69905", "status": "complete", "missing_modalities": []},
                {"accession": "P04637", "status": "complete", "missing_modalities": []},
            ],
        },
    )

    class Result:
        def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command: tuple[str, ...]) -> Result:
        command_text = " ".join(command)
        if "materialize_selected_packet_cohort.py" in command_text:
            output_index = command.index("--output") + 1
            selected_output = Path(command[output_index])
            _write_json(
                selected_output,
                {
                    "materialization": {
                        "packet_count": 2,
                        "complete_count": 1,
                        "partial_count": 1,
                        "unresolved_count": 0,
                        "packets": [
                            {
                                "accession": "P69905",
                                "status": "partial",
                                "missing_modalities": ["ligand"],
                            },
                            {
                                "accession": "P04637",
                                "status": "complete",
                                "missing_modalities": [],
                            },
                        ],
                    }
                },
            )
            latest_scope = Path(command[command.index("--output-root") + 1]) / "LATEST.json"
            _write_json(latest_scope, {"status": "partial"})
        elif "export_packet_deficit_dashboard.py" in command_text:
            output_index = command.index("--output") + 1
            markdown_index = command.index("--markdown-output") + 1
            _write_json(Path(command[output_index]), {"status": "ok"})
            Path(command[markdown_index]).parent.mkdir(parents=True, exist_ok=True)
            Path(command[markdown_index]).write_text("# deficit\n", encoding="utf-8")
        else:
            if "--canonical-root" in command:
                canonical_latest = (
                    Path(command[command.index("--canonical-root") + 1]) / "LATEST.json"
                )
                _write_json(canonical_latest, {"status": "ready"})
            if "--output" in command:
                output_path = Path(command[command.index("--output") + 1])
                if output_path.suffix == ".json" and not output_path.exists():
                    _write_json(output_path, {"status": "ok"})
                elif output_path.suffix == ".md":
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text("# ok\n", encoding="utf-8")
        return Result(returncode=0, stdout="ok")

    monkeypatch.setattr(pipeline, "_run_command", fake_run)

    payload = pipeline.run_post_tier1_pipeline(
        promotion_path=promotion_path,
        status_path=tmp_path / "status.json",
        markdown_path=tmp_path / "report.md",
    )

    assert payload["status"] == "failed"
    assert payload["packet_regression_gate"]["status"] == "failed"
    assert (
        payload["packet_regression_gate"]["baseline_selection"][
            "current_latest_matches_strongest"
        ]
        is False
    )
    assert "complete_count:2->1" in payload["packet_regression_gate"]["regressions"]
    assert "ligand_deficit_count:0->1" in payload["packet_regression_gate"]["regressions"]
