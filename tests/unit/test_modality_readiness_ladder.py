from __future__ import annotations

from scripts.modality_readiness_ladder import classify_ligand_readiness


def test_classify_ligand_readiness_orders_governing_before_preview_before_support() -> None:
    assert (
        classify_ligand_readiness(
            "P00387",
            grounded_accessions={"P00387"},
            candidate_only_accessions={"Q9NZD4"},
            support_accessions={"P00387", "P09105"},
            bundle_ligands_included=True,
        )
        == "grounded governing"
    )
    assert (
        classify_ligand_readiness(
            "P00387",
            grounded_accessions={"P00387"},
            candidate_only_accessions={"Q9NZD4"},
            support_accessions={"P00387", "P09105"},
            bundle_ligands_included=False,
        )
        == "grounded preview-safe"
    )
    assert (
        classify_ligand_readiness(
            "Q9NZD4",
            grounded_accessions={"P00387"},
            candidate_only_accessions={"Q9NZD4"},
            support_accessions={"P00387", "P09105"},
        )
        == "candidate-only non-governing"
    )
    assert (
        classify_ligand_readiness(
            "P09105",
            grounded_accessions={"P00387"},
            candidate_only_accessions={"Q9NZD4"},
            support_accessions={"P00387", "P09105"},
        )
        == "support-only"
    )
    assert (
        classify_ligand_readiness(
            "Q9UCM0",
            grounded_accessions={"P00387"},
            candidate_only_accessions={"Q9NZD4"},
            support_accessions={"P00387", "P09105"},
            packet_status="partial",
            packet_missing_modalities=["ligand"],
        )
        == "absent"
    )
