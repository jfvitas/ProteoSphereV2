from __future__ import annotations

from core.library.entity_card import (
    EntityCardEvidenceSummary,
    ProteinEntityCard,
    ProteinLigandEntityCard,
    ProteinProteinEntityCard,
)
from execution.library.interaction_trace_explainer import (
    explain_ligand_trace,
    explain_pair_trace,
)


def _protein_card(protein_ref: str, title: str) -> ProteinEntityCard:
    accession = protein_ref.split(":", 1)[1]
    return ProteinEntityCard(
        card_id=f"card:{protein_ref}",
        entity_kind="protein",
        canonical_id=protein_ref,
        title=title,
        accession=accession,
        evidence_summary=EntityCardEvidenceSummary(
            coverage_state="blocked",
            evidence_depth="direct",
            evidence_lanes=("UniProt", "IntAct"),
            blocker_ids=("packet_not_materialized",),
            provenance_refs=(f"ledger:{protein_ref}",),
        ),
    )


def test_pair_trace_explains_pair_back_to_source_proteins() -> None:
    pair_card = ProteinProteinEntityCard(
        card_id="pair-card-1",
        entity_kind="protein_protein",
        canonical_id="pair:protein:P31749|protein:Q92831",
        title="AKT1 - Q92831",
        protein_a_ref="protein:P31749",
        protein_b_ref="protein:Q92831",
        interaction_refs=("intact:EBI-123",),
        evidence_summary=EntityCardEvidenceSummary(
            coverage_state="partial",
            evidence_depth="direct",
            evidence_lanes=("IntAct",),
            provenance_refs=("intact:EBI-123",),
        ),
    )

    explanation = explain_pair_trace(
        pair_card,
        {
            "protein:P31749": _protein_card("protein:P31749", "AKT1"),
            "protein:Q92831": _protein_card("protein:Q92831", "KAT2B"),
        },
    )

    assert explanation.trace_state == "resolved"
    assert [anchor.title for anchor in explanation.anchors] == ["AKT1", "KAT2B"]
    assert explanation.supporting_refs == ("intact:EBI-123",)
    assert explanation.provenance_refs == ("intact:EBI-123",)


def test_ligand_trace_preserves_blocked_state_when_anchor_exists() -> None:
    ligand_card = ProteinLigandEntityCard(
        card_id="ligand-card-1",
        entity_kind="protein_ligand",
        canonical_id="association:protein:P31749|ligand:CHEBI:15377",
        title="AKT1 - water",
        protein_ref="protein:P31749",
        ligand_ref="ligand:CHEBI:15377",
        assay_refs=("bindingdb:assay-1",),
        structure_refs=("7NH5",),
        evidence_summary=EntityCardEvidenceSummary(
            coverage_state="blocked",
            evidence_depth="direct",
            evidence_lanes=("BindingDB",),
            blocker_ids=("thin_coverage", "modalities_incomplete"),
            provenance_refs=("bindingdb:assay-1",),
        ),
    )

    explanation = explain_ligand_trace(
        ligand_card,
        {"protein:P31749": _protein_card("protein:P31749", "AKT1")},
    )

    assert explanation.trace_state == "partial"
    assert explanation.anchors[0].canonical_id == "protein:P31749"
    assert explanation.supporting_refs == ("bindingdb:assay-1", "7NH5")
    assert "thin_coverage" in explanation.blocker_ids


def test_unresolved_trace_state_survives_missing_anchor() -> None:
    pair_card = ProteinProteinEntityCard(
        card_id="pair-card-2",
        entity_kind="protein_protein",
        canonical_id="pair:protein:P09105|protein:Q9UCM0",
        title="GAP pair",
        protein_a_ref="protein:P09105",
        protein_b_ref="protein:Q9UCM0",
        evidence_summary=EntityCardEvidenceSummary(
            coverage_state="blocked",
            evidence_depth="thin",
            evidence_lanes=("IntAct",),
            blocker_ids=("ppi_gap",),
            provenance_refs=("release-ppi-wave:gap",),
        ),
    )

    explanation = explain_pair_trace(
        pair_card,
        {"protein:P09105": _protein_card("protein:P09105", "HBBP1")},
    )

    assert explanation.trace_state == "unresolved"
    assert explanation.missing_anchor_refs == ("protein:Q9UCM0",)
    assert "missing_anchor:protein:Q9UCM0" in explanation.blocker_ids
