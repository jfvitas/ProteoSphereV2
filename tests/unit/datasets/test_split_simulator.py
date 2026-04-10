from __future__ import annotations

from datasets.recipes.schema import (
    RecipeCompletenessPolicy,
    RecipeLeakagePolicy,
    RecipeSelectionRule,
    TrainingRecipeSchema,
)
from datasets.recipes.split_simulator import simulate_recipe_splits


def test_split_simulator_rejects_thin_lane_candidates_under_strict_recipe() -> None:
    recipe = TrainingRecipeSchema(
        recipe_id="recipe:strict-sim",
        title="Strict simulator recipe",
        goal="Reject thin incomplete rows.",
        target_splits={"train": 1, "val": 0, "test": 0},
        selection_rule=RecipeSelectionRule(
            field_name="record_type",
            operator="eq",
            value="protein",
        ),
        completeness_policy=RecipeCompletenessPolicy(
            requested_modalities=("sequence", "structure", "ligand"),
            max_missing_modalities=1,
            min_lane_depth=2,
            allow_thin_coverage=False,
            allow_mixed_evidence=False,
            require_packet_ready=True,
        ),
        leakage_policy=RecipeLeakagePolicy(
            scope="accession",
            key_field="leakage_key",
            forbid_cross_split=True,
        ),
    )

    result = simulate_recipe_splits(
        recipe,
        (
            {
                "canonical_id": "protein:P04637",
                "record_type": "protein",
                "leakage_key": "P04637",
                "split": "train",
                "metadata": {
                    "lane_depth": 1,
                },
                "missing_modalities": ("sequence", "structure", "ligand"),
                "thin_coverage": True,
                "mixed_evidence": False,
                "packet_ready": False,
            },
        ),
    )

    assert result.assignments == ()
    assert result.rejected[0].canonical_id == "protein:P04637"
    assert "lane_depth=1 below 2" in result.rejected[0].reasons
    assert "packet_ready is required" in result.rejected[0].reasons


def test_split_simulator_keeps_pair_linked_candidates_in_same_split() -> None:
    recipe = TrainingRecipeSchema(
        recipe_id="recipe:pair-linked",
        title="Pair-linked simulator recipe",
        goal="Keep linked pair evidence together while balancing splits.",
        target_splits={"train": 2, "val": 1, "test": 0},
        selection_rule=RecipeSelectionRule(
            field_name="record_type",
            operator="eq",
            value="protein",
        ),
        completeness_policy=RecipeCompletenessPolicy(
            requested_modalities=("sequence",),
            max_missing_modalities=3,
            min_lane_depth=1,
            allow_thin_coverage=True,
            allow_mixed_evidence=True,
            require_packet_ready=False,
        ),
    )

    result = simulate_recipe_splits(
        recipe,
        (
            {
                "canonical_id": "protein:P31749",
                "record_type": "protein",
                "leakage_key": "P31749",
                "split": "train",
                "linked_group_id": "pair-group:akt1-axis",
                "metadata": {"lane_depth": 3},
                "packet_ready": False,
            },
            {
                "canonical_id": "protein:Q92831",
                "record_type": "protein",
                "leakage_key": "Q92831",
                "split": "val",
                "linked_group_id": "pair-group:akt1-axis",
                "metadata": {"lane_depth": 2},
                "packet_ready": False,
            },
            {
                "canonical_id": "protein:P69905",
                "record_type": "protein",
                "leakage_key": "P69905",
                "split": "val",
                "metadata": {"lane_depth": 5},
                "packet_ready": False,
            },
        ),
    )

    assignment_by_id = {item.canonical_id: item for item in result.assignments}

    assert (
        assignment_by_id["protein:P31749"].split_name
        == assignment_by_id["protein:Q92831"].split_name
    )
    assert result.linked_group_count == 2
    assert result.split_counts["train"] == 2
    assert result.split_counts["val"] == 1
    assert result.lane_depth_by_split["train"]["avg_lane_depth"] >= 2.0
