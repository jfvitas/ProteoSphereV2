from __future__ import annotations

from scripts.export_procurement_space_recovery_safety_register_preview import (
    build_procurement_space_recovery_safety_register_preview,
)


def test_safety_register_preview_reports_duplicate_first_lane() -> None:
    payload = build_procurement_space_recovery_safety_register_preview(
        {
            "summary": {"ranked_candidate_count": 3},
            "rows": [
                {
                    "path": "D:/documents/ProteoSphereV2/data/raw/local_copies/biolip/BioLiP.txt",
                    "filename": "BioLiP.txt",
                    "reason": "duplicate_name_and_size_detected",
                    "safety_tier": "better_candidate",
                    "reclaim_gib_if_removed": 0.5,
                    "size_gib": 0.5,
                },
                {
                    "path": (
                        "D:/documents/ProteoSphereV2/data/raw/local_copies/biolip/"
                        "BioLiP_extracted/BioLiP.txt"
                    ),
                    "filename": "BioLiP.txt",
                    "reason": "duplicate_name_and_size_detected",
                    "safety_tier": "better_candidate",
                    "reclaim_gib_if_removed": 0.5,
                    "size_gib": 0.5,
                },
                {
                    "path": "D:/documents/ProteoSphereV2/data/raw/local_copies/chembl/chembl_36.db",
                    "filename": "chembl_36.db",
                    "reason": "duplicate_name_and_size_detected",
                    "safety_tier": "better_candidate",
                    "reclaim_gib_if_removed": 27.6,
                    "size_gib": 27.6,
                },
            ],
        }
    )

    assert payload["summary"]["safety_state"] == "duplicate_first_safety_lane_available"
    counts = payload["summary"]["safety_category_counts"]
    assert counts["archive_and_extracted_pair"] == 2
    assert counts["duplicate_name_and_size_detected"] == 1


def test_safety_register_preview_reports_review_required_lane() -> None:
    payload = build_procurement_space_recovery_safety_register_preview(
        {
            "summary": {"ranked_candidate_count": 1},
            "rows": [
                {
                    "path": "D:/documents/ProteoSphereV2/data/raw/local_copies/unique/archive.7z",
                    "filename": "archive.7z",
                    "reason": "large_local_copy_archive_or_db",
                    "safety_tier": "review_required",
                    "reclaim_gib_if_removed": 4.0,
                    "size_gib": 4.0,
                }
            ],
        }
    )

    assert payload["summary"]["safety_state"] == "review_required_lane_only"
    assert payload["summary"]["review_required_category_count"] == 1
