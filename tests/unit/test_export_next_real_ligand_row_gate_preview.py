from __future__ import annotations

from scripts.export_next_real_ligand_row_gate_preview import (
    build_next_real_ligand_row_gate_preview,
)


def test_build_next_real_ligand_row_gate_preview_preserves_blocked_order() -> None:
    payload = build_next_real_ligand_row_gate_preview(
        {
            "selected_accession": {
                "accession": "P09105",
                "fallback_accession_if_p09105_stays_blocked": "Q2TAC2",
            }
        },
        {
            "entries": [
                {"accession": "P09105", "classification": "structure_companion_only"},
                {"accession": "Q2TAC2", "classification": "structure_companion_only"},
            ]
        },
        {
            "entries": [
                {
                    "accession": "P09105",
                    "classification": "requires_extraction",
                    "best_next_action": "hold_for_ligand_acquisition",
                },
                {
                    "accession": "Q2TAC2",
                    "classification": "requires_extraction",
                    "best_next_action": "hold_for_ligand_acquisition",
                },
            ]
        },
        {"summary": {"grounded_accessions": ["P00387", "Q9NZD4"]}},
    )

    assert payload["selected_accession"] == "P09105"
    assert payload["selected_accession_gate_status"] == "blocked_pending_acquisition"
    assert payload["fallback_accession"] == "Q2TAC2"
    assert payload["fallback_accession_gate_status"] == "blocked_pending_acquisition"
    assert payload["current_grounded_accession_count"] == 2
    assert payload["current_grounded_accessions"] == ["P00387", "Q9NZD4"]
    assert payload["can_materialize_new_grounded_accession_now"] is False
    assert (
        payload["next_unlocked_stage"]
        == "record_selected_accession_blocker_then_recheck_fixed_fallback_accession"
    )
