from __future__ import annotations

from scripts.export_duplicate_cleanup_post_delete_verification_contract_preview import (
    build_duplicate_cleanup_post_delete_verification_contract_preview,
)


def test_build_duplicate_cleanup_post_delete_verification_contract_preview_emits_steps() -> None:
    payload = build_duplicate_cleanup_post_delete_verification_contract_preview(
        {
            "artifact_id": "duplicate_cleanup_delete_ready_manifest_preview",
            "action_count": 1,
            "delete_batch": {
                "keeper_path": "keeper",
                "removal_paths": ["remove"],
                "sha256": "abc",
            },
            "constraint_checks": {
                "keeper_path_exists": True,
                "removal_paths_present": True,
                "checksum_present": True,
                "no_partial_paths": True,
                "no_latest_json": True,
                "protected_path_hits": [],
                "all_constraints_satisfied_preview": True,
            },
        },
        {"validation": {"status": "passed"}},
    )

    assert payload["frozen_manifest_ref"] == "duplicate_cleanup_delete_ready_manifest_preview"
    assert len(payload["verification_steps"]) == 4
    assert payload["frozen_manifest_sha256"] == "abc"
    assert payload["delete_ready_action_count"] == 1
    assert payload["preflight_constraints"]["keeper_path_exists"] is True
    assert payload["preflight_constraints"]["all_constraints_satisfied_preview"] is True
    assert payload["truth_boundary"]["ready_for_post_delete_checklist"] is True
