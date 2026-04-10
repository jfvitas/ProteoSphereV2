from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_compact_family_policy_matrix_labels_and_consolidation() -> None:
    matrix_path = REPO_ROOT / "artifacts" / "status" / "p91_compact_family_policy_matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))

    assert matrix["status"] == "report_only"
    assert matrix["policy_labels_supported"] == [
        "report_only_non_governing",
        "preview_bundle_safe_non_governing",
        "grounded_and_governing",
    ]
    assert matrix["summary"]["family_count"] == 3
    assert matrix["summary"]["grounded_and_governing_family_count"] == 0
    assert matrix["summary"]["preview_bundle_safe_non_governing_family_count"] == 1
    assert matrix["summary"]["report_only_non_governing_family_count"] == 2

    families = {family["family_name"]: family for family in matrix["family_policies"]}
    assert families["motif_domain_compact_preview_family"]["bundle_policy_label"] == (
        "preview_bundle_safe_non_governing"
    )
    assert families["motif_domain_compact_preview_family"]["operator_policy_label"] == (
        "report_only_non_governing"
    )
    assert families["interaction_similarity_compact_family"]["operator_policy_label"] == (
        "report_only_non_governing"
    )
    assert families["kinetics_support_compact_family"]["operator_policy_label"] == (
        "report_only_non_governing"
    )
    assert families["kinetics_support_compact_family"]["family_aliases"] == [
        "sabio_rk_support_preview",
        "kinetics_enzyme_support_preview",
    ]

    sabio_path = REPO_ROOT / "artifacts" / "status" / "sabio_rk_support_preview.json"
    kinetics_path = REPO_ROOT / "artifacts" / "status" / "kinetics_enzyme_support_preview.json"
    interaction_path = (
        REPO_ROOT / "artifacts" / "status" / "interaction_similarity_signature_preview.json"
    )
    motif_path = REPO_ROOT / "artifacts" / "status" / "p89_motif_domain_compact_preview_family.json"
    control_path = (
        REPO_ROOT / "artifacts" / "status" / "p90_motif_domain_compact_control_plane_boundary.json"
    )

    sabio = json.loads(sabio_path.read_text(encoding="utf-8"))
    kinetics = json.loads(kinetics_path.read_text(encoding="utf-8"))
    interaction = json.loads(interaction_path.read_text(encoding="utf-8"))
    motif = json.loads(motif_path.read_text(encoding="utf-8"))
    control = json.loads(control_path.read_text(encoding="utf-8"))

    assert sabio["policy_family"] == "kinetics_support_compact_family"
    assert sabio["policy_label"] == "report_only_non_governing"
    assert kinetics["policy_family"] == "kinetics_support_compact_family"
    assert kinetics["policy_label"] == "report_only_non_governing"
    assert interaction["policy_family"] == "interaction_similarity_compact_family"
    assert interaction["policy_label"] == "report_only_non_governing"
    assert motif["policy_family"] == "motif_domain_compact_family"
    assert motif["bundle_policy_label"] == "preview_bundle_safe_non_governing"
    assert control["policy_family"] == "motif_domain_compact_family"
    assert control["bundle_policy_label"] == "report_only_non_governing"
