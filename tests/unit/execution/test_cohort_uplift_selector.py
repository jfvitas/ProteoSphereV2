from __future__ import annotations

from execution.analysis.cohort_uplift_selector import (
    build_cohort_uplift_selection,
)


def _review(
    accession: str,
    *,
    split: str,
    judgment: str,
    evidence_mode: str,
    validation_class: str,
    lane_depth: int,
    mixed_evidence: bool,
    thin_coverage: bool,
) -> dict:
    return {
        "accession": accession,
        "canonical_id": f"protein:{accession}",
        "split": split,
        "judgment": judgment,
        "evidence_mode": evidence_mode,
        "validation_class": validation_class,
        "lane_depth": lane_depth,
        "mixed_evidence": mixed_evidence,
        "thin_coverage": thin_coverage,
        "source_lanes": ["UniProt"],
    }


def _packet(
    accession: str,
    *,
    present_modalities: list[str],
    missing_modalities: list[str],
) -> dict:
    return {
        "accession": accession,
        "planning_index_ref": f"planning/{accession}",
        "present_modalities": present_modalities,
        "missing_modalities": missing_modalities,
    }


def test_selector_prioritizes_mixed_upgrade_before_thin_and_anchor_rows() -> None:
    usefulness_review = {
        "example_reviews": [
            _review(
                "P69905",
                split="train",
                judgment="useful",
                evidence_mode="direct_live_smoke",
                validation_class="direct_live_smoke",
                lane_depth=5,
                mixed_evidence=False,
                thin_coverage=False,
            ),
            _review(
                "P68871",
                split="train",
                judgment="weak",
                evidence_mode="live_summary_library_probe",
                validation_class="probe_backed",
                lane_depth=2,
                mixed_evidence=True,
                thin_coverage=False,
            ),
            _review(
                "P04637",
                split="train",
                judgment="weak",
                evidence_mode="direct_live_smoke",
                validation_class="direct_live_smoke",
                lane_depth=1,
                mixed_evidence=False,
                thin_coverage=True,
            ),
        ]
    }
    training_packet_audit = {
        "packets": [
            _packet(
                "P69905",
                present_modalities=["sequence", "structure"],
                missing_modalities=["ligand", "ppi"],
            ),
            _packet(
                "P68871",
                present_modalities=["sequence", "ppi"],
                missing_modalities=["structure", "ligand"],
            ),
            _packet(
                "P04637",
                present_modalities=["ppi"],
                missing_modalities=["sequence", "structure", "ligand"],
            ),
        ]
    }

    selection = build_cohort_uplift_selection(usefulness_review, training_packet_audit)

    assert selection.top_accessions == ("P68871", "P04637", "P69905")
    assert selection.candidates[0].priority_class == "mixed_upgrade"
    assert selection.candidates[1].priority_class == "single_lane_direct_anchor"
    assert selection.candidates[2].priority_class == "reference_anchor"


def test_selector_prefers_accession_clean_train_rows_over_controls() -> None:
    usefulness_review = {
        "example_reviews": [
            _review(
                "Q9NZD4",
                split="train",
                judgment="weak",
                evidence_mode="in_tree_live_snapshot",
                validation_class="snapshot_backed",
                lane_depth=1,
                mixed_evidence=False,
                thin_coverage=True,
            ),
            _review(
                "P69892",
                split="val",
                judgment="weak",
                evidence_mode="in_tree_live_snapshot",
                validation_class="snapshot_backed",
                lane_depth=1,
                mixed_evidence=False,
                thin_coverage=True,
            ),
            _review(
                "P09105",
                split="test",
                judgment="weak",
                evidence_mode="live_verified_accession",
                validation_class="verified_accession",
                lane_depth=1,
                mixed_evidence=False,
                thin_coverage=True,
            ),
        ]
    }
    training_packet_audit = {
        "packets": [
            _packet(
                "Q9NZD4",
                present_modalities=["sequence"],
                missing_modalities=["structure", "ligand", "ppi"],
            ),
            _packet(
                "P69892",
                present_modalities=["sequence"],
                missing_modalities=["structure", "ligand", "ppi"],
            ),
            _packet(
                "P09105",
                present_modalities=["sequence"],
                missing_modalities=["structure", "ligand", "ppi"],
            ),
        ]
    }

    selection = build_cohort_uplift_selection(usefulness_review, training_packet_audit)

    assert selection.top_accessions == ("Q9NZD4", "P69892", "P09105")
    assert selection.candidates[0].priority_class == "accession_clean_train"
    assert selection.candidates[1].priority_class == "control_snapshot"
    assert selection.candidates[2].priority_class == "verified_control"
