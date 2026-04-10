from __future__ import annotations

from scripts.export_next_real_ligand_row_decision_preview import (
    build_next_real_ligand_row_decision_preview,
)


def test_build_next_real_ligand_row_decision_preview_keeps_blocked_selection_and_fixed_fallback(
) -> None:
    payload = build_next_real_ligand_row_decision_preview(
        {
            "selected_accession": "P09105",
            "selected_accession_gate_status": "blocked_pending_acquisition",
            "fallback_accession": "Q2TAC2",
            "fallback_accession_gate_status": "blocked_pending_acquisition",
            "current_grounded_accessions": ["P00387"],
        },
        {
            "entries": [
                {
                    "accession": "P09105",
                    "classification": "structure_companion_only",
                    "recommended_next_action": "hold_for_ligand_acquisition",
                },
                {
                    "accession": "Q2TAC2",
                    "classification": "structure_companion_only",
                    "recommended_next_action": "hold_for_ligand_acquisition",
                },
            ]
        },
        {
            "entries": [
                {
                    "accession": "P09105",
                    "classification": "requires_extraction",
                    "best_next_action": "hold_for_ligand_acquisition",
                    "best_next_source": "local_structure_companion",
                },
                {
                    "accession": "Q2TAC2",
                    "classification": "requires_extraction",
                    "best_next_action": "hold_for_ligand_acquisition",
                    "best_next_source": "local_structure_companion",
                },
            ]
        },
    )

    assert payload["selected_accession"] == "P09105"
    assert payload["selected_accession_gate_status"] == "blocked_pending_acquisition"
    assert payload["selected_accession_probe_criteria"]["source_classification"] == (
        "structure_companion_only"
    )
    assert payload["selected_accession_probe_criteria"]["gap_probe_classification"] == (
        "requires_extraction"
    )
    assert payload["fallback_accession"] == "Q2TAC2"
    assert payload["fallback_accession_gate_status"] == "blocked_pending_acquisition"
    assert "P09105" in payload["fallback_trigger_rule"]
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["grounded_ligand_rows_mutated"] is False
