from __future__ import annotations

from scripts.export_duplicate_cleanup_dry_run_plan import (
    build_duplicate_cleanup_dry_run_plan,
    render_duplicate_cleanup_dry_run_plan_markdown,
)


def test_build_duplicate_cleanup_dry_run_plan_selects_safe_first_groups() -> None:
    inventory = {
        "generated_at": "2026-04-01T15:41:41+00:00",
        "duplicate_groups": [
            {
                "duplicate_class": "exact_duplicate_same_release",
                "reclaimable": True,
                "reclaimable_bytes": 200,
                "sha256": "abc",
                "files": [
                    {"relative_path": "data\\raw\\local_copies\\raw\\rcsb\\1ABC.json"},
                    {"relative_path": "data\\raw\\local_copies\\raw_rcsb\\1ABC.json"},
                ],
            },
            {
                "duplicate_class": "unsafe_near_duplicate",
                "reclaimable": True,
                "reclaimable_bytes": 999,
                "sha256": "bad",
                "files": [
                    {"relative_path": "data\\packages\\LATEST.json"},
                    {"relative_path": "data\\packages\\latest_copy.json"},
                ],
            },
        ],
    }
    status_payload = {
        "safe_first_cleanup_cohorts": [
            {"cohort_name": "same_release_local_copy_duplicates"},
        ]
    }

    payload = build_duplicate_cleanup_dry_run_plan(inventory, status_payload, max_actions=10)

    assert payload["action_count"] == 1
    assert payload["planned_reclaimable_bytes"] == 200
    assert payload["actions"][0]["cohort_name"] == "same_release_local_copy_duplicates"
    assert payload["actions"][0]["keeper_path"].endswith("1ABC.json")


def test_render_duplicate_cleanup_dry_run_plan_markdown_has_action_summary() -> None:
    payload = {
        "generated_at": "2026-04-01T15:41:41+00:00",
        "allowed_cohorts": ["same_release_local_copy_duplicates"],
        "action_count": 1,
        "planned_reclaimable_bytes": 200,
        "actions": [
            {
                "cohort_name": "same_release_local_copy_duplicates",
                "duplicate_class": "exact_duplicate_same_release",
                "keeper_path": "data\\raw\\local_copies\\raw\\rcsb\\1ABC.json",
                "removal_paths": ["data\\raw\\local_copies\\raw_rcsb\\1ABC.json"],
                "reclaimable_bytes": 200,
            }
        ],
    }

    markdown = render_duplicate_cleanup_dry_run_plan_markdown(payload)

    assert "# Duplicate Cleanup Dry-Run Plan" in markdown
    assert "same_release_local_copy_duplicates" in markdown
    assert "1ABC.json" in markdown
