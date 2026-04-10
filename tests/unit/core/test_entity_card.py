from __future__ import annotations

import pytest

from core.library.entity_card import (
    EntityCardEvidenceSummary,
    ProteinEntityCard,
    ProteinLigandEntityCard,
    ProteinProteinEntityCard,
    entity_card_from_dict,
)


def test_protein_entity_card_round_trips_with_evidence_summary_and_notes() -> None:
    card = ProteinEntityCard(
        card_id="protein-card-1",
        entity_kind="protein",
        canonical_id="protein:P69905",
        title="Hemoglobin subunit alpha",
        subtitle="Reference anchor",
        summary_record_ref="summary:protein:P69905",
        evidence_summary=EntityCardEvidenceSummary(
            coverage_state="blocked",
            evidence_depth="multilane_direct",
            evidence_lanes=("UniProt", "Reactome", "AlphaFold DB"),
            coverage_notes=("multilane anchor",),
            blocker_ids=("packet_not_materialized",),
            provenance_refs=("ledger:protein:P69905",),
            packet_ready=False,
            release_score=69,
            confidence=0.97,
        ),
        related_entity_refs=("pair:protein:P69905|protein:P09105",),
        trace_refs=("release-ledger:protein:P69905",),
        tags=("train", "useful"),
        notes=("blocked but evidence-rich",),
        accession="P69905",
        organism_name="Homo sapiens",
        gene_names=("HBA1", "HBA2"),
        pathway_refs=("reactome:R-HSA-5693567",),
        motif_refs=("interpro:IPR002337",),
    )

    restored = entity_card_from_dict(card.to_dict())

    assert isinstance(restored, ProteinEntityCard)
    assert restored == card
    assert restored.evidence_summary.evidence_depth == "multilane_direct"
    assert restored.pathway_refs == ("reactome:R-HSA-5693567",)


def test_pair_entity_card_preserves_related_entities_and_blockers() -> None:
    card = ProteinProteinEntityCard(
        card_id="pair-card-1",
        entity_kind="protein_protein",
        canonical_id="pair:protein:P31749|protein:Q92831",
        title="AKT1 - Q92831",
        summary_record_ref="summary:pair:P31749:Q92831",
        evidence_summary=EntityCardEvidenceSummary(
            coverage_state="partial",
            evidence_depth="direct",
            evidence_lanes=("IntAct",),
            coverage_notes=("curated direct pair evidence",),
            provenance_refs=("intact:EBI-123",),
            packet_ready=None,
            release_score=55,
        ),
        related_entity_refs=("protein:P31749", "protein:Q92831"),
        trace_refs=("curated-ppi-candidate-slice:P14-I006",),
        protein_a_ref="protein:P31749",
        protein_b_ref="protein:Q92831",
        interaction_refs=("intact:EBI-123",),
        curated_direct=True,
    )

    restored = entity_card_from_dict(card.to_dict())

    assert isinstance(restored, ProteinProteinEntityCard)
    assert restored == card
    assert restored.curated_direct is True

    with pytest.raises(ValueError, match="must be different"):
        ProteinProteinEntityCard(
            card_id="pair-card-2",
            entity_kind="protein_protein",
            canonical_id="pair:protein:P31749|protein:P31749",
            title="bad pair",
            protein_a_ref="protein:P31749",
            protein_b_ref="protein:P31749",
        )


def test_ligand_entity_card_requires_protein_and_ligand_refs() -> None:
    card = ProteinLigandEntityCard(
        card_id="ligand-card-1",
        entity_kind="protein_ligand",
        canonical_id="association:protein:P31749|ligand:CHEBI:15377",
        title="AKT1 - water",
        summary_record_ref="summary:ligand:P31749:CHEBI15377",
        evidence_summary=EntityCardEvidenceSummary(
            coverage_state="blocked",
            evidence_depth="direct",
            evidence_lanes=("BindingDB",),
            coverage_notes=("assay linked but thin",),
            blocker_ids=("thin_coverage", "modalities_incomplete"),
            provenance_refs=("bindingdb:row-1",),
            packet_ready=False,
            release_score=46,
        ),
        related_entity_refs=("protein:P31749", "ligand:CHEBI:15377"),
        trace_refs=("release-ligand-wave:v1",),
        protein_ref="protein:P31749",
        ligand_ref="ligand:CHEBI:15377",
        assay_refs=("bindingdb:assay-1",),
        structure_refs=("7NH5",),
    )

    restored = entity_card_from_dict(card.to_dict())

    assert isinstance(restored, ProteinLigandEntityCard)
    assert restored == card
    assert restored.structure_refs == ("7NH5",)

    with pytest.raises(ValueError, match="ligand_ref must not be empty"):
        ProteinLigandEntityCard(
            card_id="ligand-card-2",
            entity_kind="protein_ligand",
            canonical_id="association:protein:P31749|ligand:missing",
            title="bad ligand card",
            protein_ref="protein:P31749",
        )
