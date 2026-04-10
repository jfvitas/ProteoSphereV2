from __future__ import annotations

import json

from evaluation.user_sim.scenario_harness import (
    DEFAULT_OPERATOR_LIBRARY_REGRESSION,
    DEFAULT_P20_PERSONAS,
    DEFAULT_PACKET_AUDIT,
    DEFAULT_PACKET_AUDIT_JSON,
    DEFAULT_RELEASE_PROGRAM,
    DEFAULT_SOURCE_JOIN_STRATEGIES,
    DEFAULT_SOURCE_STORAGE_STRATEGY,
    DEFAULT_USER_SIM_ACCEPTANCE_MATRIX,
    ScenarioArtifactRef,
    ScenarioPlaybackCase,
    ScenarioPlaybackHarness,
    build_phase20_playback_cases,
)


def test_default_phase20_playback_cases_cover_expected_workflows() -> None:
    harness = ScenarioPlaybackHarness()
    traces = harness.replay_many(build_phase20_playback_cases())

    assert tuple(trace.workflow for trace in traces) == (
        "recipe",
        "packet",
        "benchmark",
        "review",
    )
    assert tuple(trace.state for trace in traces) == (
        "weak",
        "weak",
        "weak",
        "blocked",
    )
    assert traces[0].artifact_checks[0].exists is True
    assert traces[3].artifact_checks[-1].exists is False
    assert "truth boundary preserved explicitly" in traces[0].rationale
    assert "missing required artifact(s)" in traces[3].rationale[0]
    assert json.dumps([trace.to_dict() for trace in traces])


def test_scenario_harness_supports_pass_weak_and_blocked_replays() -> None:
    harness = ScenarioPlaybackHarness()
    pass_case = ScenarioPlaybackCase(
        scenario_id="PASS-RECIPE",
        persona="Corpus Curator",
        workflow="recipe",
        expected_state="pass",
        artifacts=(
            ScenarioArtifactRef("persona brief", str(DEFAULT_P20_PERSONAS)),
            ScenarioArtifactRef("release program", str(DEFAULT_RELEASE_PROGRAM)),
            ScenarioArtifactRef("join strategies", str(DEFAULT_SOURCE_JOIN_STRATEGIES)),
            ScenarioArtifactRef("storage strategy", str(DEFAULT_SOURCE_STORAGE_STRATEGY)),
        ),
        evidence_refs=(str(DEFAULT_P20_PERSONAS), str(DEFAULT_RELEASE_PROGRAM)),
        pass_markers=("truth before throughput", "release definition"),
        truth_boundary=("selective expansion",),
        notes=("pass replay stays within the current planning boundary",),
    )
    weak_case = ScenarioPlaybackCase(
        scenario_id="WEAK-PACKET",
        persona="Packet Planner",
        workflow="packet",
        expected_state="weak",
        artifacts=(
            ScenarioArtifactRef("packet audit", str(DEFAULT_PACKET_AUDIT)),
            ScenarioArtifactRef("packet audit json", str(DEFAULT_PACKET_AUDIT_JSON)),
        ),
        evidence_refs=(str(DEFAULT_PACKET_AUDIT), str(DEFAULT_PACKET_AUDIT_JSON)),
        weak_markers=("partial", "prototype"),
        truth_boundary=("partial packets remain partial",),
    )
    blocked_case = ScenarioPlaybackCase(
        scenario_id="BLOCKED-REVIEW",
        persona="Operator Scientist",
        workflow="review",
        expected_state="blocked",
        artifacts=(
            ScenarioArtifactRef(
                "operator library regression",
                str(DEFAULT_OPERATOR_LIBRARY_REGRESSION),
            ),
            ScenarioArtifactRef(
                "user-sim acceptance matrix",
                str(DEFAULT_USER_SIM_ACCEPTANCE_MATRIX),
            ),
        ),
        evidence_refs=(str(DEFAULT_OPERATOR_LIBRARY_REGRESSION),),
        blocked_markers=("not yet", "blocked"),
        truth_boundary=("weeklong soak remains unproven",),
    )

    traces = harness.replay_many((pass_case, weak_case, blocked_case))

    assert tuple(trace.state for trace in traces) == ("pass", "weak", "blocked")
    assert traces[0].artifact_checks[0].exists is True
    assert traces[1].artifact_checks[0].exists is True
    assert traces[2].artifact_checks[1].exists is False
    assert "pass markers detected" in traces[0].rationale[0]
    assert "weak markers detected" in " | ".join(traces[1].rationale)
    assert "missing required artifact(s)" in traces[2].rationale[0]
    assert json.dumps([trace.to_dict() for trace in traces])
