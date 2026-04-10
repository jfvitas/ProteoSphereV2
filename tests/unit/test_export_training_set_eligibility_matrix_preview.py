from __future__ import annotations

from scripts.export_training_set_eligibility_matrix_preview import (
    build_training_set_eligibility_matrix_preview,
)


def test_build_training_set_eligibility_matrix_preview_classifies_accessions() -> None:
    packet_deficit = {
        "packets": [
            {
                "accession": "P00387",
                "status": "partial",
                "present_modalities": ["sequence", "structure", "ppi"],
                "missing_modalities": ["ligand"],
            },
            {
                "accession": "P04637",
                "status": "complete",
                "present_modalities": ["sequence", "structure", "ligand", "ppi"],
                "missing_modalities": [],
            },
            {
                "accession": "Q9UCM0",
                "status": "partial",
                "present_modalities": ["sequence"],
                "missing_modalities": ["structure", "ligand", "ppi"],
            },
        ]
    }
    accession_matrix = {
        "rows": [
            {
                "accession": "P00387",
                "protein_ref": "protein:P00387",
                "protein_name": "Protein 387",
                "protein_summary_present": True,
                "variant_count": 0,
                "structure_unit_count": 0,
            },
            {
                "accession": "P04637",
                "protein_ref": "protein:P04637",
                "protein_name": "Protein 4637",
                "protein_summary_present": True,
                "variant_count": 2,
                "structure_unit_count": 0,
            },
        ]
    }
    support_readiness = {
        "summary": {
            "support_accessions": ["P00387", "P09105", "Q2TAC2", "Q9NZD4"],
            "deferred_accessions": ["Q9UCM0"],
            "bundle_ligands_included": False,
        }
    }
    ligand_row_preview = {
        "summary": {
            "grounded_accessions": ["P00387"],
            "candidate_only_accessions": ["Q9NZD4"],
        }
    }

    payload = build_training_set_eligibility_matrix_preview(
        packet_deficit,
        accession_matrix,
        ligand_row_preview,
        support_readiness,
    )

    assert payload["summary"]["accession_count"] == 6
    rows = {row["accession"]: row for row in payload["rows"]}

    assert rows["P00387"]["task_eligibility"]["grounded_ligand_similarity_preview"]["status"] == (
        "eligible_for_task"
    )
    assert rows["P00387"]["ligand_readiness_ladder"] == "grounded preview-safe"
    assert rows["P00387"]["task_eligibility"]["full_packet_current_latest"]["status"] == (
        "blocked_pending_acquisition"
    )
    assert rows["P04637"]["task_eligibility"]["full_packet_current_latest"]["status"] == (
        "eligible_for_task"
    )
    assert rows["P04637"]["task_eligibility"]["grounded_ligand_similarity_preview"]["status"] == (
        "library_only"
    )
    assert rows["P04637"]["ligand_readiness_ladder"] == "support-only"
    assert rows["P04637"]["modality_readiness"]["structure"] == "support-only"
    assert rows["P09105"]["ligand_readiness_ladder"] == "support-only"
    assert rows["Q2TAC2"]["ligand_readiness_ladder"] == "support-only"
    assert rows["Q9UCM0"]["task_eligibility"]["protein_reference"]["status"] == "audit_only"
    assert rows["Q9UCM0"]["task_eligibility"]["structure_conditioned_current_latest"]["status"] == (
        "blocked_pending_acquisition"
    )
    assert rows["Q9UCM0"]["ligand_readiness_ladder"] == "absent"
    assert rows["Q9NZD4"]["task_eligibility"]["grounded_ligand_similarity_preview"]["status"] == (
        "candidate_only_non_governing"
    )
    assert rows["Q9NZD4"]["ligand_readiness_ladder"] == "candidate-only non-governing"
    assert payload["summary"]["ligand_readiness_ladder_counts"] == {
        "absent": 1,
        "support-only": 3,
        "candidate-only non-governing": 1,
        "grounded preview-safe": 1,
    }
    assert payload["summary"]["modality_readiness_counts"]["structure"]["support-only"] == 2
