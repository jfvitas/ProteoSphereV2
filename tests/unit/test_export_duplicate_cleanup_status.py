from __future__ import annotations

from scripts.export_duplicate_cleanup_status import (
    build_duplicate_cleanup_status,
    render_duplicate_cleanup_status_markdown,
)


def test_build_duplicate_cleanup_status_summarizes_inventory() -> None:
    inventory = {
        "generated_at": "2026-04-01T15:41:41+00:00",
        "summary": {
            "scanned_root_count": 5,
            "scanned_file_count": 20,
            "duplicate_group_count": 3,
            "duplicate_file_count": 7,
            "reclaimable_file_count": 4,
            "reclaimable_bytes": 600,
            "partial_file_count": 1,
            "protected_file_count": 2,
        },
        "duplicate_groups": [
            {
                "duplicate_class": "equivalent_archive_copy",
                "reclaimable": True,
                "reclaimable_bytes": 400,
                "files": [
                    {
                        "relative_path": "data\\raw\\local_copies\\alphafold_db\\a.tar",
                    },
                    {
                        "relative_path": "data\\raw\\protein_data_scope_seed\\alphafold_db\\a.tar",
                    },
                ],
            },
            {
                "duplicate_class": "exact_duplicate_same_release",
                "reclaimable": True,
                "reclaimable_bytes": 200,
                "files": [
                    {
                        "relative_path": "data\\raw\\local_copies\\raw\\rcsb\\1ABC.json",
                    },
                    {
                        "relative_path": "data\\raw\\local_copies\\raw_rcsb\\1ABC.json",
                    },
                ],
            },
            {
                "duplicate_class": "unsafe_near_duplicate",
                "reclaimable": False,
                "reclaimable_bytes": 999,
                "files": [
                    {
                        "relative_path": "data\\packages\\LATEST.json",
                    }
                ],
            },
        ],
    }

    status = build_duplicate_cleanup_status(inventory, top_n=5)

    assert status["inventory_summary"]["scanned_file_count"] == 20
    assert status["top_duplicate_classes"][0]["duplicate_class"] == "equivalent_archive_copy"
    assert status["top_root_prefixes"][0]["root_prefix"].startswith("data\\raw\\local_copies")
    cohort_names = [entry["cohort_name"] for entry in status["safe_first_cleanup_cohorts"]]
    assert "local_archive_equivalents" in cohort_names
    assert "same_release_local_copy_duplicates" in cohort_names


def test_render_duplicate_cleanup_status_markdown_includes_core_sections() -> None:
    payload = {
        "generated_at": "2026-04-01T15:41:41+00:00",
        "inventory_summary": {
            "scanned_file_count": 20,
            "duplicate_group_count": 3,
            "reclaimable_file_count": 4,
            "reclaimable_bytes": 600,
            "protected_file_count": 2,
            "partial_file_count": 1,
        },
        "top_duplicate_classes": [
            {
                "duplicate_class": "equivalent_archive_copy",
                "group_count": 1,
                "reclaimable_bytes": 400,
            }
        ],
        "top_root_prefixes": [
            {
                "root_prefix": "data\\raw\\local_copies\\alphafold_db",
                "group_count": 1,
                "reclaimable_bytes": 400,
            }
        ],
        "safe_first_cleanup_cohorts": [
            {
                "cohort_name": "local_archive_equivalents",
                "group_count": 1,
                "reclaimable_bytes": 400,
                "example_paths": [
                    "data\\raw\\local_copies\\alphafold_db\\a.tar",
                ],
            }
        ],
    }

    markdown = render_duplicate_cleanup_status_markdown(payload)

    assert "# Duplicate Cleanup Status" in markdown
    assert "Top Duplicate Classes" in markdown
    assert "Top Root Prefixes" in markdown
    assert "Safe-First Cleanup Cohorts" in markdown
    assert "local_archive_equivalents" in markdown
