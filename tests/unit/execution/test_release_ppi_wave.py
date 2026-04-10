from __future__ import annotations

import json

from execution.acquire.release_ppi_wave import build_release_ppi_wave_plan


def _sample_manifest() -> dict[str, object]:
    return {
        "manifest_id": "benchmark-cohort-manifest-2026-03-22",
        "cohort": [
            {
                "accession": "P04637",
                "split": "train",
                "bucket": "rich_coverage",
                "evidence_mode": "direct_live_smoke",
                "source_lanes": ["IntAct"],
                "evidence_refs": ["docs/reports/ppi_live_smoke_2026_03_22.md"],
            },
            {
                "accession": "P68871",
                "split": "train",
                "bucket": "rich_coverage",
                "evidence_mode": "live_summary_library_probe",
                "source_lanes": ["UniProt", "protein-protein summary library"],
                "evidence_refs": ["runs/real_data_benchmark/results/live_inputs.json"],
            },
            {
                "accession": "QBREATH",
                "split": "val",
                "bucket": "sparse_or_control",
                "evidence_mode": "direct_live_smoke",
                "source_lanes": ["STRING"],
                "evidence_refs": ["docs/reports/ppi_live_smoke_2026_03_22.md"],
            },
            {
                "accession": "QMULTI",
                "split": "test",
                "bucket": "sparse_or_control",
                "evidence_mode": "direct_live_smoke",
                "source_lanes": ["STRING", "BioGRID", "IntAct"],
                "evidence_refs": ["docs/reports/ppi_live_smoke_2026_03_22.md"],
            },
        ],
    }


def test_release_ppi_wave_plan_ranks_direct_and_breadth_sources() -> None:
    plan = build_release_ppi_wave_plan(_sample_manifest())

    assert plan.manifest_id == "benchmark-cohort-manifest-2026-03-22"
    assert plan.plan_id.startswith("release-ppi-wave-")
    assert [spec.source_name for spec in plan.source_ranking] == [
        "IntAct",
        "BioGRID",
        "STRING",
    ]
    assert [spec.source_tier for spec in plan.source_ranking] == [
        "direct",
        "direct",
        "breadth",
    ]

    direct_record = next(record for record in plan.records if record.accession == "P04637")
    assert direct_record.case_kind == "direct_single_source"
    assert direct_record.observed_sources == ("IntAct",)
    assert direct_record.next_sources == ("BioGRID", "STRING")
    assert direct_record.source_decisions[0].status == "observed"
    assert [decision.status for decision in direct_record.source_decisions] == [
        "observed",
        "missing",
        "missing",
    ]

    breadth_record = next(record for record in plan.records if record.accession == "QBREATH")
    assert breadth_record.case_kind == "breadth_only"
    assert breadth_record.observed_sources == ("STRING",)
    assert breadth_record.primary_observed_source == "STRING"
    assert breadth_record.next_sources == ("IntAct", "BioGRID")

    multi_record = next(record for record in plan.records if record.accession == "QMULTI")
    assert multi_record.case_kind == "multi_source"
    assert multi_record.multi_source is True
    assert multi_record.observed_sources == ("IntAct", "BioGRID", "STRING")
    assert multi_record.next_sources == ()
    assert multi_record.source_decisions[0].status == "observed"
    assert multi_record.source_decisions[1].status == "observed"
    assert multi_record.source_decisions[2].status == "observed"


def test_release_ppi_wave_plan_keeps_unresolved_and_unsupported_cases_explicit() -> None:
    plan = build_release_ppi_wave_plan(_sample_manifest())

    unresolved_record = next(record for record in plan.records if record.accession == "P68871")
    assert unresolved_record.case_kind == "unresolved"
    assert unresolved_record.observed_sources == ()
    assert unresolved_record.next_sources == ("IntAct", "BioGRID", "STRING")
    assert unresolved_record.unsupported_lanes == (
        "UniProt",
        "protein-protein summary library",
    )
    assert "ppi_sources_unresolved" in unresolved_record.notes
    assert "unsupported_lanes_preserved" in unresolved_record.notes

    assert plan.summary == {
        "total_accessions": 4,
        "direct_covered_accessions": 2,
        "breadth_covered_accessions": 2,
        "multi_source_accessions": 1,
        "unresolved_accessions": 1,
        "unsupported_lane_accessions": 1,
    }


def test_release_ppi_wave_plan_loads_from_json_path(tmp_path) -> None:
    manifest_path = tmp_path / "cohort_manifest.json"
    manifest_path.write_text(json.dumps(_sample_manifest()), encoding="utf-8")

    plan = build_release_ppi_wave_plan(manifest_path)

    assert plan.manifest_id == "benchmark-cohort-manifest-2026-03-22"
    assert len(plan.records) == 4
    assert any(record.accession == "QMULTI" for record in plan.records)
