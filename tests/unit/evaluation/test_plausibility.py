from __future__ import annotations

from evaluation.user_sim.plausibility import PlausibilityCase, score_plausibility


def test_conservative_plausibility_scoring_is_boundary_aware() -> None:
    result = score_plausibility(
        PlausibilityCase(
            scenario_id="sim-conservative",
            persona="Evidence Reviewer",
            artifact_kind="evidence_review",
            output_text=(
                "The conclusion stays inside the prototype boundary: P69905 is useful "
                "for the current benchmark, but the packet remains partial and not "
                "release-ready. The assessment is evidence-backed and conservative."
            ),
            evidence_mode="direct_live_smoke",
            truth_boundary={
                "prototype_runtime": True,
                "partial_packet": True,
                "thin_evidence": True,
            },
            evidence_refs=(
                "docs/reports/live_source_smoke_2026_03_22.md",
                "runs/real_data_benchmark/full_results/source_coverage.json",
            ),
        )
    )

    assert result.judgment == "conservative"
    assert result.score >= 70
    assert "boundary-aware language detected" in result.reasons
    assert "prototype_boundary" in result.supported_signals
    assert "release_ready_claim" not in result.unsupported_signals


def test_weak_plausibility_scoring_stays_usable_but_not_conservative() -> None:
    result = score_plausibility(
        {
            "scenario_id": "sim-weak",
            "persona": "Packet Planner",
            "artifact_kind": "packet_review",
            "output_text": (
                "This probe-backed example is useful for planning, but it stays weak "
                "because the packet is partial and the evidence remains mixed."
            ),
            "evidence_mode": "probe_backed",
            "truth_boundary": {
                "partial_packet": True,
                "mixed_evidence": True,
            },
            "claims": ("This example is useful for planning",),
        }
    )

    assert result.judgment == "weak_usable"
    assert 35 <= result.score < 70
    assert "partiality_acknowledged" in result.supported_signals
    assert "evidence_language" in result.supported_signals
    assert result.unsupported_signals == ()


def test_unsupported_plausibility_scoring_fails_closed_on_overclaim() -> None:
    result = score_plausibility(
        PlausibilityCase(
            scenario_id="sim-unsupported",
            persona="Training Operator",
            artifact_kind="training_interpretation",
            output_text=(
                "This is release-ready, fully validated, complete corpus coverage, and "
                "the weeklong soak is done."
            ),
            evidence_mode="snapshot_backed",
            truth_boundary={
                "prototype_runtime": True,
                "partial_packet": True,
            },
        )
    )

    assert result.judgment == "unsupported"
    assert result.score == 0
    assert "release_ready_claim" in result.unsupported_signals
    assert "fully_validated_claim" in result.unsupported_signals
    assert "weeklong_soak_claim" in result.unsupported_signals
