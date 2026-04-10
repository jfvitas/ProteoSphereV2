from __future__ import annotations

import json
from pathlib import Path

from execution.acquire.release_ligand_wave import (
    DEFAULT_WAVE_ID,
    build_release_ligand_wave_plan,
    build_release_ligand_wave_plan_from_artifacts,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"
PROBE_MATRIX_PATH = REPO_ROOT / "artifacts" / "status" / "p13_missing_source_probe_matrix.json"


def test_release_ligand_wave_plan_ranks_assay_and_structure_candidates() -> None:
    plan = build_release_ligand_wave_plan_from_artifacts(
        results_dir=RESULTS_DIR,
        probe_matrix_path=PROBE_MATRIX_PATH,
    )
    by_accession = {candidate.accession: candidate for candidate in plan.candidates}

    assert plan.wave_id == DEFAULT_WAVE_ID
    assert plan.candidate_count == 12
    assert plan.assay_linked_count == 1
    assert plan.structure_linked_count == 2
    assert plan.held_sparse_gap_count == 9
    assert plan.deep_lane_count == 2
    assert plan.sparse_lane_count == 10
    assert plan.top_accessions[:3] == ("P31749", "P68871", "P69905")

    p31749 = by_accession["P31749"]
    p68871 = by_accession["P68871"]
    p69905 = by_accession["P69905"]
    p04637 = by_accession["P04637"]

    assert p31749.ligand_lane_class == "assay_linked"
    assert p31749.lane_profile == "sparse"
    assert "SABIO-RK returned no target data for this anchor" in p31749.probe_notes

    assert p68871.ligand_lane_class == "structure_linked"
    assert p68871.lane_profile == "deep"
    assert "4HHB" in "".join(p68871.structure_refs)
    assert p68871.status == "ranked"

    assert p69905.ligand_lane_class == "structure_linked"
    assert p69905.lane_profile == "deep"
    assert p69905.status == "ranked"

    assert p04637.ligand_lane_class == "held_sparse_gap"
    assert p04637.status == "held"
    assert p04637.unresolved_reason is not None

    payload = plan.to_dict()
    assert payload["wave_id"] == DEFAULT_WAVE_ID
    assert payload["candidate_count"] == 12
    assert payload["probe_summary"]["empty_target_probe_sources"]
    assert "RCSB/PDBe bridge" in payload["probe_summary"]["structured_probe_sources"]


def test_release_ligand_wave_plan_is_machine_readable() -> None:
    plan = build_release_ligand_wave_plan_from_artifacts(
        results_dir=RESULTS_DIR,
        probe_matrix_path=PROBE_MATRIX_PATH,
    )

    payload = json.loads(json.dumps(plan.to_dict()))

    assert payload["wave_id"] == DEFAULT_WAVE_ID
    assert payload["top_accessions"] == list(plan.top_accessions)
    assert payload["candidates"][0]["selector_rank"] == 3
    assert payload["candidates"][0]["ligand_lane_class"] == "assay_linked"
    assert payload["candidates"][1]["ligand_lane_class"] == "structure_linked"
    assert payload["candidates"][3]["status"] == "held"


def test_release_ligand_wave_plan_does_not_upgrade_chembl_planning_signal_to_assay_linked() -> None:
    usefulness_review_payload = {
        "example_reviews": [
            {"accession": "P00387", "usefulness_score": 0.1, "status": "weak"},
        ]
    }
    training_packet_audit_payload = {
        "packets": [
            {
                "accession": "P00387",
                "canonical_id": "protein:P00387",
                "split": "train",
                "bucket": "moderate_coverage",
                "present_modalities": ["sequence"],
                "missing_modalities": ["ligand", "structure", "ppi"],
                "lane_depth": 1,
                "thin_coverage": True,
                "mixed_evidence": False,
                "evidence_mode": "planning_only",
                "validation_class": "planning_only",
            }
        ]
    }
    source_coverage_payload = {
        "coverage_matrix": [
            {
                "accession": "P00387",
                "canonical_id": "protein:P00387",
                "split": "train",
                "bucket": "moderate_coverage",
                "present_modalities": ["sequence"],
                "missing_modalities": ["ligand", "structure", "ppi"],
                "source_lanes": ["UniProt", "ChEMBL"],
                "evidence_refs": ["artifacts/status/local_ligand_source_map.json"],
                "lane_depth": 1,
                "thin_coverage": True,
                "mixed_evidence": False,
                "evidence_mode": "planning_only",
                "validation_class": "planning_only",
            },
            {
                "accession": "P69905",
                "canonical_id": "protein:P69905",
                "split": "train",
                "bucket": "rich_coverage",
                "present_modalities": ["sequence"],
                "missing_modalities": ["ligand", "ppi"],
                "source_lanes": ["UniProt", "BioLiP"],
                "evidence_refs": ["artifacts/status/local_ligand_source_map.json"],
                "lane_depth": 1,
                "thin_coverage": True,
                "mixed_evidence": False,
                "evidence_mode": "planning_only",
                "validation_class": "planning_only",
            },
        ]
    }

    plan = build_release_ligand_wave_plan(
        usefulness_review_payload=usefulness_review_payload,
        training_packet_audit_payload=training_packet_audit_payload,
        source_coverage_payload=source_coverage_payload,
    )
    by_accession = {candidate.accession: candidate for candidate in plan.candidates}

    assert by_accession["P00387"].ligand_lane_class == "held_sparse_gap"
    assert by_accession["P00387"].status == "held"
    assert by_accession["P69905"].ligand_lane_class == "structure_linked"
