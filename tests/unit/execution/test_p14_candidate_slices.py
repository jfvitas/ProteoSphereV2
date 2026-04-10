from __future__ import annotations

from execution.analysis.p14_candidate_slices import (
    build_curated_ppi_candidate_slice,
    build_protein_depth_candidate_slice,
)


def test_build_curated_ppi_candidate_slice_keeps_direct_vs_breadth_explicit() -> None:
    usefulness = {
        "example_reviews": [
            {
                "accession": "P04637",
                "canonical_id": "protein:P04637",
                "split": "train",
                "bucket": "rich_coverage",
                "judgment": "weak",
                "evidence_mode": "direct_live_smoke",
                "validation_class": "direct_live_smoke",
                "lane_depth": 1,
                "mixed_evidence": False,
                "thin_coverage": True,
                "source_lanes": ["IntAct"],
            },
            {
                "accession": "P31749",
                "canonical_id": "protein:P31749",
                "split": "train",
                "bucket": "rich_coverage",
                "judgment": "weak",
                "evidence_mode": "direct_live_smoke",
                "validation_class": "direct_live_smoke",
                "lane_depth": 1,
                "mixed_evidence": False,
                "thin_coverage": True,
                "source_lanes": ["BindingDB"],
            },
        ]
    }
    audit = {"packets": []}
    intact = {
        "P04637": {
            "state": "direct_hit",
            "pair_count": 1,
            "pair_records": [
                {
                    "source_record_ids": ["EBI-12345"],
                    "pair_key": "pair:protein:P04637|protein:P69905",
                }
            ],
            "probe_reason": "direct curated pair evidence located",
        },
        "P31749": {
            "state": "reachable_empty",
            "pair_count": 0,
            "pair_records": [],
            "probe_reason": "IntAct probe succeeded but returned no curated IntAct pairs",
        },
    }
    biogrid = {
        "source_name": "BioGRID",
        "probe_state": "surface_reachable",
        "next_step": "pin a release export",
        "notes": ["surface only"],
    }

    payload = build_curated_ppi_candidate_slice(usefulness, audit, intact, biogrid)

    assert payload["summary"]["direct_evidence_count"] == 1
    assert payload["summary"]["breadth_only_count"] == 2
    assert payload["summary"]["empty_hit_count"] == 1
    assert payload["direct_evidence"][0]["accession"] == "P04637"
    assert payload["breadth_only_evidence"][0]["evidence_kind"] == "breadth_surface_only"
    assert payload["empty_hits"][0]["accession"] == "P31749"


def test_build_protein_depth_candidate_slice_keeps_bridge_and_empty_hits_separate() -> None:
    usefulness = {
        "example_reviews": [
            {
                "accession": "P04637",
                "canonical_id": "protein:P04637",
                "split": "train",
                "bucket": "rich_coverage",
                "judgment": "weak",
                "evidence_mode": "direct_live_smoke",
                "validation_class": "direct_live_smoke",
                "lane_depth": 1,
                "mixed_evidence": False,
                "thin_coverage": True,
                "source_lanes": ["IntAct"],
                "coverage_notes": ["single-lane coverage"],
            }
        ]
    }
    audit = {
        "packets": [
            {
                "accession": "P04637",
                "present_modalities": ["ppi"],
                "missing_modalities": ["sequence", "structure"],
            }
        ]
    }
    disprot = {
        "records": [
            {
                "accession": "P04637",
                "status": "positive_hit",
                "probe_url": "https://disprot.org/api/search?acc=P04637",
                "matched_record_count": 1,
                "matched_disprot_ids": ["DP00086"],
                "returned_record_count": 1,
            },
            {
                "accession": "P69905",
                "status": "reachable_empty",
                "probe_url": "https://disprot.org/api/search?acc=P69905",
                "matched_record_count": 0,
                "matched_disprot_ids": [],
                "returned_record_count": 0,
            },
        ]
    }
    structure = {
        "records": [
            {
                "accession": "P04637",
                "canonical_id": "protein:P04637",
                "source_name": "RCSB/PDBe bridge",
                "pdb_id": "9R2Q",
                "bridge_state": "positive_hit",
                "bridge_kind": "bridge_only",
                "matched_uniprot_ids": ["P04637"],
                "chain_ids": ["K"],
                "evidence_refs": ["https://data.rcsb.org/rest/v1/core/entry/9r2q"],
                "notes": ["bridge_only_evidence"],
            },
            {
                "accession": "P69905",
                "canonical_id": "protein:P69905",
                "source_name": "RCSB/PDBe bridge",
                "pdb_id": "1HHB",
                "bridge_state": "reachable_empty",
                "bridge_kind": "bridge_only",
                "matched_uniprot_ids": [],
                "chain_ids": [],
                "evidence_refs": ["https://data.rcsb.org/rest/v1/core/entry/1hhb"],
                "notes": ["bridge_lookup_reachable_but_accession_not_linked"],
            },
        ]
    }
    sabiork = {
        "source_name": "SABIO-RK",
        "probe_state": "reachable_no_target_data",
        "expected_join_anchors": ["P31749"],
        "next_step": "choose a better anchor",
        "notes": ["official endpoint reachable but target empty"],
    }

    payload = build_protein_depth_candidate_slice(usefulness, audit, disprot, structure, sabiork)

    assert payload["summary"]["direct_evidence_count"] == 1
    assert payload["summary"]["disprot_positive_count"] == 1
    assert payload["summary"]["bridge_glue_count"] == 1
    assert payload["summary"]["empty_hit_count"] == 3
    assert payload["breadth_only_evidence"][0]["accession"] == "P04637"
    assert payload["bridge_glue"][0]["pdb_id"] == "9R2Q"
