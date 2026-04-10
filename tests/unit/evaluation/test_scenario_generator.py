from __future__ import annotations

import json

from evaluation.user_sim.scenario_generator import (
    build_phase20_scenario_suite,
    build_phase20_scenarios,
)
from evaluation.user_sim.scenario_harness import ScenarioPlaybackHarness


def test_phase20_scenario_generator_builds_real_truth_bound_suite() -> None:
    report = build_phase20_scenario_suite()
    harness = ScenarioPlaybackHarness()
    traces = harness.replay_many(report.scenarios)

    assert report.generator_id == "phase20-scenario-generator:v1"
    assert report.selected_accessions == (
        "P69905",
        "P68871",
        "P04637",
        "P31749",
        "Q9NZD4",
    )
    assert report.to_dict()["scenario_count"] == 6
    assert report.to_dict()["state_counts"] == {
        "pass": 1,
        "weak": 4,
        "blocked": 1,
    }
    assert report.to_dict()["workflow_counts"] == {
        "recipe": 1,
        "review": 2,
        "packet": 2,
        "benchmark": 1,
    }
    assert tuple(trace.state for trace in traces) == (
        "pass",
        "weak",
        "weak",
        "weak",
        "weak",
        "blocked",
    )
    assert traces[0].rationale[0] == (
        "pass markers detected: direct_live_smoke, direct_multilane, useful"
    )
    assert "missing required artifact(s): user-sim acceptance matrix" in traces[-1].rationale[0]
    assert traces[-1].state == "blocked"
    assert json.dumps(report.to_dict())


def test_phase20_scenario_generator_is_deterministic_and_reuses_cases() -> None:
    report_a = build_phase20_scenario_suite()
    report_b = build_phase20_scenario_suite()

    assert report_a.to_dict() == report_b.to_dict()
    assert build_phase20_scenarios() == report_a.scenarios
    assert report_a.source_files["acceptance_matrix"].endswith(
        "docs/reports/p20_user_sim_acceptance_matrix.md"
    )
