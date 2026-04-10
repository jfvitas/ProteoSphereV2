from __future__ import annotations

from training.multimodal.curriculum import (
    CurriculumExample,
    HardNegativeCandidate,
    build_curriculum_schedule,
)


def test_curriculum_scheduler_progresses_from_anchor_to_mixed_and_blocks_unresolved_rows() -> None:
    schedule = build_curriculum_schedule(
        [
            CurriculumExample(
                example_id="anchor-1",
                evidence_depth=5,
                thin_coverage=False,
                mixed_evidence=False,
                status="ready",
                present_modalities=("sequence", "structure"),
                source_lanes=("UniProt", "AlphaFold DB"),
            ),
            CurriculumExample(
                example_id="progressive-1",
                evidence_depth=3,
                thin_coverage=False,
                mixed_evidence=False,
                status="ready",
                present_modalities=("sequence", "ppi"),
                source_lanes=("UniProt", "IntAct"),
            ),
            CurriculumExample(
                example_id="thin-1",
                evidence_depth=1,
                thin_coverage=True,
                mixed_evidence=False,
                status="ready",
                present_modalities=("ligand",),
                source_lanes=("BindingDB",),
            ),
            CurriculumExample(
                example_id="mixed-1",
                evidence_depth=2,
                thin_coverage=False,
                mixed_evidence=True,
                status="partial",
                present_modalities=("sequence", "ppi"),
                source_lanes=("UniProt", "protein-protein summary library"),
            ),
            CurriculumExample(
                example_id="blocked-1",
                evidence_depth=4,
                thin_coverage=False,
                mixed_evidence=False,
                status="unresolved",
                present_modalities=("sequence",),
                source_lanes=("UniProt",),
            ),
        ],
        notes=("curriculum",),
    )

    assert schedule.stage == "mixed_transition"
    assert schedule.ordered_example_ids == (
        "anchor-1",
        "progressive-1",
        "thin-1",
        "mixed-1",
        "blocked-1",
    )
    assert schedule.examples[0].curriculum_state == "anchor"
    assert schedule.examples[1].curriculum_state == "progressive"
    assert schedule.examples[2].curriculum_state == "thin"
    assert schedule.examples[3].curriculum_state == "mixed"
    assert schedule.examples[4].curriculum_state == "blocked"
    assert schedule.to_dict()["stage"] == "mixed_transition"


def test_hard_negative_selection_blocks_incomplete_candidates_fail_closed() -> None:
    schedule = build_curriculum_schedule(
        [
            CurriculumExample(
                example_id="anchor-1",
                evidence_depth=5,
                thin_coverage=False,
                mixed_evidence=False,
                status="ready",
                present_modalities=("sequence", "structure"),
                source_lanes=("UniProt", "AlphaFold DB"),
            ),
        ],
        hard_negative_candidates=[
            HardNegativeCandidate(
                candidate_id="neg-good",
                evidence_depth=4,
                thin_coverage=False,
                mixed_evidence=False,
                status="ready",
                source_lanes=("UniProt",),
            ),
            HardNegativeCandidate(
                candidate_id="neg-missing-depth",
                evidence_depth=None,
                thin_coverage=False,
                mixed_evidence=False,
                status="ready",
                source_lanes=("UniProt",),
            ),
            HardNegativeCandidate(
                candidate_id="neg-unresolved",
                evidence_depth=3,
                thin_coverage=False,
                mixed_evidence=False,
                status="unresolved",
                source_lanes=("UniProt",),
                unresolved_reason="missing evidence metadata",
            ),
        ],
        hard_negative_limit=1,
    )

    assert schedule.hard_negatives.selected_candidate_ids == ("neg-good",)
    assert set(schedule.hard_negatives.blocked_candidate_ids) == {
        "neg-missing-depth",
        "neg-unresolved",
    }
    blocked_reasons = {
        decision.candidate_id: decision.reason
        for decision in schedule.hard_negatives.decisions
        if decision.decision == "blocked"
    }
    assert "missing required evidence metadata" in blocked_reasons["neg-missing-depth"]
    assert "missing evidence metadata" in blocked_reasons["neg-unresolved"]
