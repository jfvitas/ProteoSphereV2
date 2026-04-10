from __future__ import annotations

from datasets.recipes.balanced_cohort_scorer import rank_candidates, score_candidate


def test_score_candidate_favors_complete_direct_packet_ready_candidate() -> None:
    strong = score_candidate(
        {
            "canonical_id": "protein:P69905",
            "leakage_key": "P69905",
            "present_modalities": ("sequence", "structure", "ppi"),
            "missing_modalities": (),
            "source_lanes": ("UniProt", "AlphaFold DB", "Reactome"),
            "lane_depth": 5,
            "evidence_mode": "direct_live_smoke",
            "validation_class": "direct_live_smoke",
            "bucket": "rich_coverage",
            "packet_ready": True,
            "thin_coverage": False,
            "mixed_evidence": False,
        },
        requested_modalities=("sequence", "structure", "ppi"),
    )
    weak = score_candidate(
        {
            "canonical_id": "protein:P04637",
            "leakage_key": "P04637",
            "present_modalities": ("ppi",),
            "missing_modalities": ("sequence", "structure"),
            "source_lanes": ("IntAct",),
            "lane_depth": 1,
            "evidence_mode": "in_tree_live_snapshot",
            "validation_class": "thin_probe",
            "bucket": "thin_coverage",
            "packet_ready": False,
            "thin_coverage": True,
            "mixed_evidence": False,
        },
        requested_modalities=("sequence", "structure", "ppi"),
    )

    assert strong.accepted is True
    assert weak.accepted is True
    assert strong.total_score > weak.total_score
    assert strong.component_scores["completeness"] == 1.0
    assert weak.component_scores["completeness"] < 0.5


def test_rank_candidates_blocks_duplicate_leakage_keys_after_first_selection() -> None:
    ranking = rank_candidates(
        (
            {
                "canonical_id": "protein:P69905",
                "leakage_key": "P69905",
                "present_modalities": ("sequence", "structure"),
                "missing_modalities": (),
                "source_lanes": ("UniProt", "AlphaFold DB"),
                "lane_depth": 4,
                "evidence_mode": "direct_live_smoke",
                "validation_class": "direct_live_smoke",
                "bucket": "rich_coverage",
                "packet_ready": True,
            },
            {
                "canonical_id": "protein:P69905-duplicate",
                "leakage_key": "P69905",
                "present_modalities": ("sequence",),
                "missing_modalities": ("structure",),
                "source_lanes": ("UniProt",),
                "lane_depth": 2,
                "evidence_mode": "live_verified_accession",
                "validation_class": "verified",
                "bucket": "moderate_coverage",
                "packet_ready": False,
            },
        ),
        requested_modalities=("sequence", "structure"),
    )

    assert [item.canonical_id for item in ranking.accepted] == ["protein:P69905"]
    assert ranking.rejected[0].canonical_id == "protein:P69905-duplicate"
    assert "leakage_key=P69905 already selected" in ranking.rejected[0].reasons


def test_rank_candidates_rewards_diverse_follow_on_selection() -> None:
    ranking = rank_candidates(
        (
            {
                "canonical_id": "protein:P69905",
                "leakage_key": "P69905",
                "present_modalities": ("sequence", "structure"),
                "missing_modalities": (),
                "source_lanes": ("UniProt", "AlphaFold DB"),
                "lane_depth": 5,
                "evidence_mode": "direct_live_smoke",
                "validation_class": "direct_live_smoke",
                "bucket": "rich_coverage",
                "packet_ready": True,
            },
            {
                "canonical_id": "protein:P31749",
                "leakage_key": "P31749",
                "present_modalities": ("sequence", "ligand"),
                "missing_modalities": ("structure",),
                "source_lanes": ("UniProt", "BindingDB"),
                "lane_depth": 4,
                "evidence_mode": "live_summary_library_probe",
                "validation_class": "ligand_anchor",
                "bucket": "moderate_coverage",
                "packet_ready": True,
            },
            {
                "canonical_id": "protein:P31749-similar",
                "leakage_key": "Q00000",
                "present_modalities": ("sequence", "ligand"),
                "missing_modalities": ("structure",),
                "source_lanes": ("UniProt", "AlphaFold DB"),
                "lane_depth": 4,
                "evidence_mode": "direct_live_smoke",
                "validation_class": "direct_live_smoke",
                "bucket": "rich_coverage",
                "packet_ready": True,
            },
        ),
        requested_modalities=("sequence", "structure", "ligand"),
        limit=2,
    )

    assert [item.canonical_id for item in ranking.accepted] == [
        "protein:P69905",
        "protein:P31749",
    ]
    assert ranking.accepted[1].component_scores["diversity"] > 0.1
    assert ranking.rejected[0].canonical_id == "protein:P31749-similar"
    assert "selection_limit_reached" in ranking.rejected[0].reasons
