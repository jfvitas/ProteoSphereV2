from __future__ import annotations

from datasets.recipes.schema import (
    RecipeCompletenessPolicy,
    RecipeEvaluationContext,
    RecipeLeakagePolicy,
    RecipeRuleGroup,
    RecipeSelectionRule,
    TrainingRecipeSchema,
)


def test_training_recipe_schema_round_trips_with_nested_rule_group() -> None:
    recipe = TrainingRecipeSchema(
        recipe_id="recipe:multilane-direct",
        title="Multilane direct anchors",
        goal="Select direct or bridge-upgrade proteins with strong coverage.",
        requested_modalities=("sequence", "structure", "ligand"),
        target_splits={"train": 8, "val": 2, "test": 2},
        selection_rule=RecipeRuleGroup(
            mode="all",
            description="top-level inclusion rules",
            rules=(
                RecipeSelectionRule(
                    field_name="bucket",
                    operator="in",
                    value=("rich_coverage", "moderate_coverage"),
                    description="bucket must be selected",
                ),
                RecipeRuleGroup(
                    mode="any",
                    description="evidence depth path",
                    rules=(
                        RecipeSelectionRule(
                            field_name="evidence_mode",
                            operator="eq",
                            value="direct_live_smoke",
                            description="direct live smoke",
                        ),
                        RecipeSelectionRule(
                            field_name="source_lanes",
                            operator="contains",
                            value=("AlphaFold DB",),
                            description="structure bridge available",
                        ),
                    ),
                ),
            ),
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
        tags=("release", "science"),
        notes=("multilane-only recipe",),
    )

    restored = TrainingRecipeSchema.from_dict(recipe.to_dict())

    assert restored == recipe
    assert restored.target_splits == {"train": 8, "val": 2, "test": 2}


def test_recipe_schema_rejects_candidate_for_leakage_and_incomplete_modalities() -> None:
    recipe = TrainingRecipeSchema(
        recipe_id="recipe:strict",
        title="Strict release recipe",
        goal="Require complete modalities with no leakage.",
        selection_rule=RecipeSelectionRule(
            field_name="validation_class",
            operator="eq",
            value="direct_live_smoke",
            description="direct evidence only",
        ),
        completeness_policy=RecipeCompletenessPolicy(
            requested_modalities=("sequence", "structure", "ligand", "ppi"),
            max_missing_modalities=0,
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

    candidate = {
        "accession": "P31749",
        "leakage_key": "P31749",
        "validation_class": "direct_live_smoke",
        "missing_modalities": ("sequence", "structure"),
        "lane_depth": 1,
        "thin_coverage": True,
        "mixed_evidence": False,
        "packet_ready": False,
    }

    evaluation = recipe.evaluate_candidate(
        candidate,
        context=RecipeEvaluationContext(occupied_leakage_keys=("P31749",)),
    )

    assert evaluation.accepted is False
    assert "missing_modalities=2 exceeds 0" in evaluation.reasons
    assert "lane_depth=1 below 2" in evaluation.reasons
    assert "thin_coverage is not allowed" in evaluation.reasons
    assert "packet_ready is required" in evaluation.reasons
    assert "leakage key 'P31749' already assigned" in evaluation.reasons


def test_recipe_schema_accepts_candidate_when_constraints_are_met() -> None:
    recipe = TrainingRecipeSchema(
        recipe_id="recipe:balanced",
        title="Balanced benchmark recipe",
        goal="Allow one missing modality while preserving leakage safety.",
        selection_rule=RecipeRuleGroup(
            mode="all",
            description="balanced rules",
            rules=(
                RecipeSelectionRule(
                    field_name="split",
                    operator="eq",
                    value="train",
                    description="train rows only",
                ),
                RecipeSelectionRule(
                    field_name="source_lanes",
                    operator="contains",
                    value=("Reactome", "AlphaFold DB"),
                    description="pathway and structure depth",
                ),
            ),
        ),
        completeness_policy=RecipeCompletenessPolicy(
            requested_modalities=("sequence", "structure", "ligand"),
            max_missing_modalities=1,
            min_lane_depth=3,
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

    candidate = {
        "accession": "P69905",
        "canonical_id": "protein:P69905",
        "leakage_key": "P69905",
        "split": "train",
        "source_lanes": (
            "UniProt",
            "Reactome",
            "AlphaFold DB",
            "Evolutionary / MSA",
        ),
        "missing_modalities": ("ligand",),
        "lane_depth": 5,
        "thin_coverage": False,
        "mixed_evidence": False,
        "packet_ready": True,
    }

    evaluation = recipe.evaluate_candidate(
        candidate,
        context=RecipeEvaluationContext(occupied_leakage_keys=("P31749",)),
    )

    assert evaluation.accepted is True
    assert evaluation.reasons == ()
    assert "balanced rules" in evaluation.matched_rules
