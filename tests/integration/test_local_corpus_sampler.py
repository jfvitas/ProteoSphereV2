from __future__ import annotations

from execution.acquire.local_corpus_sampler import fingerprint_local_source_registry
from execution.acquire.local_source_registry import DEFAULT_LOCAL_SOURCE_REGISTRY


def test_local_corpus_sampler_fingerprints_real_mirrors_conservatively() -> None:
    report = fingerprint_local_source_registry(DEFAULT_LOCAL_SOURCE_REGISTRY)

    assert report.entry_count == 39
    assert report.present_entry_count == 29
    assert report.partial_entry_count == 2
    assert report.missing_entry_count == 8
    assert report.sampled_file_count >= 100

    by_name = {entry.source_name: entry for entry in report.entries}

    assert by_name["uniprot"].coverage_status == "partial"
    assert by_name["uniprot"].sampled_file_count == 1
    assert by_name["reactome"].coverage_status == "present"
    assert by_name["reactome"].sampled_file_count >= 3
    assert by_name["biolip"].coverage_status == "present"
    assert by_name["pdbbind_pp"].coverage_status == "present"
    assert by_name["pdbbind_pl"].coverage_status == "partial"
    assert by_name["biogrid"].coverage_status == "missing"
    assert by_name["biogrid"].sampled_file_count == 0

    assert any("uniprot_sprot.dat.gz" in path for path in by_name["uniprot"].sampled_paths)
    assert any(
        "UniProt2Reactome_All_Levels.txt" in path
        for path in by_name["reactome"].sampled_paths
    )
    assert any("BioLiP.txt" in path for path in by_name["biolip"].sampled_paths)
