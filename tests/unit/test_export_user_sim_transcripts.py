from __future__ import annotations

import json

from scripts.export_user_sim_transcripts import export_user_sim_transcripts, main


def test_export_user_sim_transcripts_emits_json_and_markdown(tmp_path) -> None:
    artifact_one = tmp_path / "artifact-one.md"
    artifact_one.write_text(
        "prototype boundary evidence artifact with checkpoint trace and provenance language.",
        encoding="utf-8",
    )
    missing_artifact = tmp_path / "missing-artifact.md"
    payload = {
        "scenarios": [
            {
                "scenario_id": "S-001",
                "persona": "Corpus Curator",
                "workflow": "recipe",
                "expected_state": "pass",
                "artifacts": [
                    {
                        "label": "evidence note",
                        "path": str(artifact_one),
                    }
                ],
                "evidence_refs": [str(artifact_one)],
                "pass_markers": [
                    "truth before throughput",
                    "prototype boundary",
                ],
                "truth_boundary": ["selective expansion"],
                "notes": ["pass scenario"],
            },
            {
                "scenario_id": "S-002",
                "persona": "Operator Scientist",
                "workflow": "review",
                "expected_state": "blocked",
                "artifacts": [
                    {
                        "label": "missing report",
                        "path": str(missing_artifact),
                    }
                ],
                "evidence_refs": [str(missing_artifact)],
                "blocked_markers": ["blocked"],
                "truth_boundary": ["weeklong soak remains unproven"],
                "notes": ["blocked scenario"],
            },
        ],
        "rubric_scenarios": [
            {
                "scenario_id": "S-001",
                "persona": "Corpus Curator",
                "judgment": "pass",
                "evidence_mode": "rich",
                "evidence_depth": 5,
                "evidence_refs": [str(artifact_one)],
                "action_items": ["retain explicit citations"],
                "claims": ["selective expansion"],
            },
            {
                "scenario_id": "S-002",
                "persona": "Operator Scientist",
                "judgment": "blocked",
                "evidence_mode": "blocked",
                "evidence_depth": 0,
                "evidence_refs": [str(missing_artifact)],
                "action_items": ["stop", "request missing artifact"],
                "blocker_reason": "required artifact missing",
            },
        ],
    }
    input_path = tmp_path / "user_sim_bundle.json"
    input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    json_output = tmp_path / "transcript.json"
    text_output = tmp_path / "transcript.md"

    transcript = export_user_sim_transcripts(
        input_path=input_path,
        json_output=json_output,
        text_output=text_output,
    )

    assert json_output.exists()
    assert text_output.exists()
    assert transcript["scenario_count"] == 2
    assert transcript["summary"]["trace_states"] == {"blocked": 1, "pass": 1, "weak": 0}
    assert transcript["summary"]["rubric_judgments"] == {"blocked": 1, "pass": 1, "weak": 0}
    assert transcript["summary"]["plausibility_judgments"] == {
        "conservative": 1,
        "weak_usable": 0,
        "unsupported": 1,
    }

    persisted = json.loads(json_output.read_text(encoding="utf-8"))
    assert persisted == transcript
    assert persisted["entries"][0]["trace"]["state"] == "pass"
    assert persisted["entries"][1]["trace"]["state"] == "blocked"
    assert persisted["entries"][0]["plausibility"]["judgment"] == "conservative"
    assert persisted["entries"][1]["plausibility"]["judgment"] == "unsupported"
    assert str(artifact_one) in text_output.read_text(encoding="utf-8")
    assert "Truth boundary notes" in text_output.read_text(encoding="utf-8")
    assert "missing required artifact" in text_output.read_text(encoding="utf-8")


def test_export_user_sim_transcripts_cli_uses_default_outputs(tmp_path) -> None:
    artifact_one = tmp_path / "artifact-one.md"
    artifact_one.write_text(
        "prototype boundary evidence artifact with checkpoint trace and provenance language.",
        encoding="utf-8",
    )
    bundle = {
        "scenarios": [
            {
                "scenario_id": "S-CLI",
                "persona": "Evidence Reviewer",
                "workflow": "review",
                "expected_state": "pass",
                "artifacts": [
                    {
                        "label": "evidence note",
                        "path": str(artifact_one),
                    }
                ],
                "evidence_refs": [str(artifact_one)],
                "pass_markers": ["prototype boundary"],
                "truth_boundary": ["truth before throughput"],
            }
        ],
        "rubric_scenarios": [
            {
                "scenario_id": "S-CLI",
                "persona": "Evidence Reviewer",
                "judgment": "pass",
                "evidence_mode": "rich",
                "evidence_depth": 4,
                "evidence_refs": [str(artifact_one)],
                "action_items": ["trace evidence"],
                "claims": ["truth before throughput"],
            }
        ],
    }
    input_path = tmp_path / "bundle.json"
    input_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    json_output = tmp_path / "export.json"
    text_output = tmp_path / "export.md"

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--json-output",
            str(json_output),
            "--text-output",
            str(text_output),
        ]
    )

    assert exit_code == 0
    assert json_output.exists()
    assert text_output.exists()
    assert "S-CLI" in text_output.read_text(encoding="utf-8")
