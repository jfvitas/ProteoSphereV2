from __future__ import annotations

from scripts.export_archive_cleanup_keeper_rules_preview import (
    build_archive_cleanup_keeper_rules_preview,
)


def test_build_archive_cleanup_keeper_rules_preview_stays_blocked() -> None:
    payload = build_archive_cleanup_keeper_rules_preview(
        {
            "top_root_prefixes": [
                {
                    "root_prefix": "data\\raw\\local_copies\\chembl",
                    "reclaimable_bytes": 100,
                },
                {
                    "root_prefix": "data\\raw\\local_copies\\pdbbind",
                    "reclaimable_bytes": 200,
                },
                {
                    "root_prefix": "data\\raw\\local_copies\\alphafold_db",
                    "reclaimable_bytes": 300,
                },
            ]
        }
    )

    assert payload["status"] == "report_only"
    assert payload["row_count"] == 3
    assert payload["summary"]["delete_ready_now_count"] == 0
    assert payload["rows"][0]["family_id"] == "chembl_archive_vs_extracted"
    assert payload["rows"][1]["observed_layout"] == "archive_plus_extracted"
    assert payload["rows"][2]["preferred_keeper_kind"] == "protein_data_scope_seed_archive"
    assert payload["truth_boundary"]["archive_cleanup_executed"] is False
