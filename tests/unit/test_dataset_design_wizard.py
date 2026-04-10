from __future__ import annotations

from datasets.recipes.schema import (
    RecipeCompletenessPolicy,
    RecipeLeakagePolicy,
    RecipeSelectionRule,
    TrainingRecipeSchema,
)
from scripts.dataset_design_wizard import build_dataset_design_report, render_report_text


def test_dataset_design_wizard_real_truth_proposals() -> None:
    report = build_dataset_design_report()
    proposals = {proposal["accession"]: proposal for proposal in report["proposals"]}

    assert report["summary"]["proposal_count"] == 12
    assert report["summary"]["status_counts"]["supported"] == 1
    assert report["summary"]["status_counts"]["weak"] >= 1
    assert report["summary"]["status_counts"]["blocked"] >= 1
    assert report["summary"]["simulation"]["leakage_collisions"] == []

    p69905 = proposals["P69905"]
    assert p69905["status"] == "supported"
    assert p69905["completeness"]["status"] == "degraded"
    assert p69905["truth"]["scenario"]["scenario_id"] == "P20-G001-P69905"
    assert p69905["truth"]["scenario"]["state"] == "pass"

    p68871 = proposals["P68871"]
    assert p68871["status"] == "weak"
    assert p68871["completeness"]["mixed_evidence"] is True
    assert "probe-backed or mixed evidence stays weak" in p68871["notes"]

    p04637 = proposals["P04637"]
    assert p04637["status"] == "blocked"
    assert p04637["completeness"]["status"] == "blocked"
    assert len(p04637["completeness"]["missing_modalities"]) >= 3
    assert p04637["leakage"]["status"] == "ok"

    rendered = render_report_text(report)
    assert "Wizard: dataset-design-wizard" in rendered
    assert "supported" in rendered
    assert "weak" in rendered
    assert "blocked" in rendered


def test_dataset_design_wizard_diagnostics() -> None:
    recipe = TrainingRecipeSchema(
        recipe_id="recipe:synthetic",
        title="Synthetic design",
        goal="exercise diagnostics",
        requested_modalities=("sequence", "structure", "ligand"),
        target_splits={"train": 2, "val": 0, "test": 0},
        selection_rule=RecipeSelectionRule(
            field_name="record_type",
            operator="eq",
            value="protein",
        ),
        completeness_policy=RecipeCompletenessPolicy(
            requested_modalities=("sequence", "structure", "ligand"),
            max_missing_modalities=2,
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
    )

    report = build_dataset_design_report(
        recipe=recipe,
        rows=[
            {
                "accession": "A1",
                "canonical_id": "protein:A1",
                "split": "train",
                "leakage_key": "dup",
                "record_type": "protein",
                "bucket": "alpha_coverage",
                "grade": "weak",
                "evidence_mode": "direct_live_smoke",
                "validation_class": "direct_live_smoke",
                "lane_depth": 1,
                "present_modalities": ("sequence",),
                "missing_modalities": ("structure",),
                "source_lanes": ("UniProt",),
                "thin_coverage": False,
                "mixed_evidence": False,
                "packet_ready": False,
                "release_ready": False,
            },
            {
                "accession": "A2",
                "canonical_id": "protein:A2",
                "split": "train",
                "leakage_key": "dup",
                "record_type": "protein",
                "bucket": "zeta_coverage",
                "grade": "weak",
                "evidence_mode": "live_summary_library_probe",
                "validation_class": "probe_backed",
                "lane_depth": 2,
                "present_modalities": ("sequence", "ppi"),
                "missing_modalities": ("ligand",),
                "source_lanes": ("UniProt", "IntAct"),
                "thin_coverage": False,
                "mixed_evidence": True,
                "packet_ready": False,
                "release_ready": False,
            },
        ],
    )

    proposals = {proposal["accession"]: proposal for proposal in report["proposals"]}

    assert report["summary"]["status_counts"]["weak"] == 1
    assert report["summary"]["status_counts"]["blocked"] == 1
    assert report["summary"]["leakage_blocked_count"] == 1
    assert report["summary"]["completeness_blocked_count"] == 0

    a1 = proposals["A1"]
    assert a1["completeness"]["status"] == "degraded"
    assert a1["completeness"]["missing_modalities"] == ["structure"]

    a2 = proposals["A2"]
    assert a2["leakage"]["status"] == "blocked"
    assert "already assigned" in " ".join(a2["leakage"]["reasons"])
    assert a2["status"] == "blocked"
