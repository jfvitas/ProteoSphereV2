from __future__ import annotations

import json
from pathlib import Path

from datasets.recipes.schema import (
    RecipeCompletenessPolicy,
    RecipeLeakagePolicy,
    RecipeRuleGroup,
    RecipeSelectionRule,
    TrainingRecipeSchema,
)
from datasets.recipes.split_simulator import (
    SplitSimulationCandidate,
    simulate_recipe_splits,
)

ROOT = Path(__file__).resolve().parents[2]
COHORT_MANIFEST_PATH = ROOT / "runs" / "real_data_benchmark" / "cohort" / "cohort_manifest.json"
LEDGER_PATH = (
    ROOT
    / "runs"
    / "real_data_benchmark"
    / "full_results"
    / "release_corpus_evidence_ledger.json"
)


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_replay_inputs() -> tuple[dict[str, object], list[dict[str, object]]]:
    cohort_manifest = _load_json(COHORT_MANIFEST_PATH)
    ledger = _load_json(LEDGER_PATH)
    ledger_by_accession = {
        str(row["metadata"]["accession"]): row for row in ledger["rows"]  # type: ignore[index]
    }

    merged_rows: list[dict[str, object]] = []
    for row in cohort_manifest["cohort"]:  # type: ignore[index]
        accession = str(row["accession"])
        ledger_row = ledger_by_accession[accession]
        merged_row = dict(ledger_row)
        merged_row.update(row)
        metadata = dict(ledger_row["metadata"])  # type: ignore[index]
        merged_row.setdefault("record_type", ledger_row.get("record_type", "protein"))
        merged_row.setdefault("missing_modalities", metadata.get("missing_modalities", ()))
        merged_row.setdefault("present_modalities", metadata.get("present_modalities", ()))
        merged_row.setdefault("packet_ready", ledger_row.get("packet_ready"))
        merged_row.setdefault("thin_coverage", metadata.get("thin_coverage", False))
        merged_row.setdefault("mixed_evidence", metadata.get("mixed_evidence", False))
        merged_row.setdefault("lane_depth", metadata.get("lane_depth", 0))
        merged_row.setdefault("blocker_ids", ledger_row.get("blocker_ids", ()))
        merged_rows.append(merged_row)

    return cohort_manifest, merged_rows


def _build_replay_recipe() -> TrainingRecipeSchema:
    return TrainingRecipeSchema(
        recipe_id="recipe:frozen-benchmark-replay",
        title="Frozen benchmark replay",
        goal="Replay the pinned 12-accession benchmark cohort and split decisions.",
        requested_modalities=("sequence", "structure", "ligand", "ppi"),
        target_splits={"train": 8, "val": 2, "test": 2},
        selection_rule=RecipeRuleGroup(
            mode="all",
            description="frozen benchmark cohort",
            rules=(
                RecipeSelectionRule(
                    field_name="freeze_state",
                    operator="eq",
                    value="frozen",
                    description="freeze state must be frozen",
                ),
                RecipeSelectionRule(
                    field_name="inclusion_status",
                    operator="eq",
                    value="included",
                    description="cohort rows must be included",
                ),
                RecipeSelectionRule(
                    field_name="record_type",
                    operator="eq",
                    value="protein",
                    description="protein records only",
                ),
            ),
        ),
        completeness_policy=RecipeCompletenessPolicy(
            requested_modalities=("sequence", "structure", "ligand", "ppi"),
            max_missing_modalities=3,
            min_lane_depth=1,
            allow_thin_coverage=True,
            allow_mixed_evidence=True,
            require_packet_ready=False,
        ),
        leakage_policy=RecipeLeakagePolicy(
            scope="accession",
            key_field="leakage_key",
            forbid_cross_split=True,
        ),
        tags=("benchmark", "replay"),
        notes=("pinned benchmark slice",),
    )


def _build_candidates(rows: list[dict[str, object]]) -> list[SplitSimulationCandidate]:
    return [SplitSimulationCandidate.from_dict(row) for row in rows]


def test_recipe_replay_is_deterministic_and_preserves_pinned_splits() -> None:
    cohort_manifest, rows = _build_replay_inputs()
    recipe = _build_replay_recipe()
    restored = TrainingRecipeSchema.from_dict(recipe.to_dict())
    candidates = _build_candidates(rows)
    replay = simulate_recipe_splits(restored, candidates)
    replay_again = simulate_recipe_splits(restored, reversed(candidates))

    assert restored == recipe
    assert replay == replay_again
    assert replay.recipe_id == "recipe:frozen-benchmark-replay"
    assert replay.target_counts == {"train": 8, "val": 2, "test": 2}
    assert replay.split_counts == {"train": 8, "val": 2, "test": 2}
    assert replay.leakage_collisions == ()
    assert replay.rejected == ()
    assert replay.notes == ()

    expected_pairs = {
        (f"protein:{row['accession']}", row["split"]) for row in cohort_manifest["cohort"]  # type: ignore[index]
    }
    actual_pairs = {
        (assignment.canonical_id, assignment.split_name) for assignment in replay.assignments
    }
    assert actual_pairs == expected_pairs

    per_accession_split = {
        assignment.canonical_id: assignment.split_name for assignment in replay.assignments
    }
    assert per_accession_split["protein:P69905"] == "train"
    assert per_accession_split["protein:P02100"] == "val"
    assert per_accession_split["protein:P09105"] == "test"

    p68871 = next(row for row in rows if row["canonical_id"] == "protein:P68871")
    assert p68871["blocker_ids"] == [
        "packet_not_materialized",
        "modalities_incomplete",
        "mixed_evidence",
    ]
    assert p68871["packet_ready"] is False


def test_recipe_replay_keeps_leakage_boundaries_explicit() -> None:
    _, rows = _build_replay_inputs()
    mutated_rows = [dict(row) for row in rows]
    mutated_rows[1]["leakage_key"] = mutated_rows[0]["leakage_key"]

    recipe = _build_replay_recipe()
    replay = simulate_recipe_splits(recipe, _build_candidates(mutated_rows))

    assert replay.rejected
    assert replay.leakage_collisions == ()
    assert any(
        rejection.canonical_id == "protein:P68871"
        and "already assigned" in " ".join(rejection.reasons)
        for rejection in replay.rejected
    )
    assert replay.split_counts["train"] == 7
    assert replay.notes == ("simulated split counts do not exactly match requested targets",)
