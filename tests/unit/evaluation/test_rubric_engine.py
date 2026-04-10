from __future__ import annotations

import json

from evaluation.user_sim.rubric_engine import (
    DEFAULT_TRUTH_BOUNDARY,
    WorkflowRubricEngine,
    WorkflowRubricScenario,
    score_workflow_scenarios,
)


def test_workflow_rubric_preserves_pass_weak_and_blocked_judgments() -> None:
    engine = WorkflowRubricEngine()

    pass_score = engine.score_scenario(
        WorkflowRubricScenario(
            scenario_id="curator-pass",
            persona="Corpus Curator",
            judgment="pass",
            evidence_mode="rich",
            evidence_depth=5,
            evidence_refs=(
                "source_coverage.json",
                "data_inventory_audit.json",
                "p19_model_portfolio_benchmark.json",
            ),
            action_items=("select cohort",),
            claims=("selective cohort",),
        )
    )
    weak_score = engine.score_scenario(
        {
            "scenario_id": "review-weak",
            "persona": "Evidence Reviewer",
            "judgment": "weak",
            "evidence_mode": "mixed",
            "evidence_depth": 2,
            "evidence_refs": (
                "runs/real_data_benchmark/full_results/usefulness_review.json",
                "runs/real_data_benchmark/full_results/training_packet_audit.json",
            ),
            "action_items": ("flag thin lane", "retain provenance"),
            "claims": ("mixed evidence remains weak",),
        }
    )
    blocked_score = engine.score_scenario(
        WorkflowRubricScenario(
            scenario_id="operator-blocked",
            persona="Training Operator",
            judgment="blocked",
            evidence_mode="blocked",
            evidence_depth=0,
            evidence_refs=("docs/reports/p19_training_envelopes.md",),
            action_items=("stop", "request direct evidence"),
            blocker_reason="prototype boundary remains active",
        )
    )

    assert pass_score.judgment == "pass"
    assert weak_score.judgment == "weak"
    assert blocked_score.judgment == "blocked"

    assert pass_score.total_score > weak_score.total_score > blocked_score.total_score
    assert pass_score.utility_score > weak_score.utility_score > blocked_score.utility_score
    assert blocked_score.trust_score > weak_score.trust_score
    assert blocked_score.actionability_score > 0
    assert "boundary_hits=none" in pass_score.rationale
    assert "weak judgment preserved" in " ".join(weak_score.rationale)
    assert "blocked judgment preserved" in " ".join(blocked_score.rationale)
    assert json.dumps(blocked_score.to_dict())


def test_workflow_rubric_flags_truth_boundary_overclaims() -> None:
    engine = WorkflowRubricEngine()

    blocked_score = engine.score_scenario(
        WorkflowRubricScenario(
            scenario_id="soak-overclaim",
            persona="Training Operator",
            judgment="blocked",
            evidence_mode="blocked",
            evidence_depth=0,
            truth_boundary=DEFAULT_TRUTH_BOUNDARY,
            claims=("release-grade validation", "weeklong soak complete"),
            evidence_refs=("docs/reports/p22_weeklong_soak.md",),
            action_items=("stop", "wait for real soak evidence"),
            blocker_reason="weeklong soak remains outside the current truth boundary",
        )
    )

    assert blocked_score.judgment == "blocked"
    assert blocked_score.boundary_hits == (
        "release-grade claim outside prototype boundary",
        "weeklong soak claim outside phase 20",
    )
    assert blocked_score.trust_score < 70
    assert blocked_score.utility_score < 10
    assert blocked_score.actionability_score < 40
    assert "boundary_hit=release-grade claim outside prototype boundary" in blocked_score.rationale


def test_workflow_rubric_batches_scores_into_a_report() -> None:
    report = score_workflow_scenarios(
        (
            WorkflowRubricScenario(
                scenario_id="curator-pass",
                persona="Corpus Curator",
                judgment="pass",
                evidence_mode="rich",
                evidence_depth=5,
                evidence_refs=("source_coverage.json", "data_inventory_audit.json"),
                action_items=("select cohort",),
                claims=("selective cohort",),
            ),
            {
                "scenario_id": "review-weak",
                "persona": "Evidence Reviewer",
                "judgment": "weak",
                "evidence_mode": "mixed",
                "evidence_depth": 2,
                "evidence_refs": ("usefulness_review.json",),
                "action_items": ("flag thin lane",),
                "claims": ("mixed evidence remains weak",),
            },
            {
                "scenario_id": "operator-blocked",
                "persona": "Training Operator",
                "judgment": "blocked",
                "evidence_mode": "blocked",
                "evidence_depth": 0,
                "evidence_refs": ("p19_training_envelopes.md",),
                "action_items": ("stop", "request direct evidence"),
                "blocker_reason": "prototype boundary remains active",
            },
        )
    )

    payload = report.to_dict()
    assert report.scenario_count == 3
    assert payload["judgment_counts"] == {"pass": 1, "weak": 1, "blocked": 1}
    assert payload["scenario_count"] == 3
    assert payload["utility_mean"] > payload["actionability_mean"] / 2
    assert json.dumps(payload)
