from __future__ import annotations

from pathlib import Path

from execution.acquire.bio_agent_lab_imports import BioAgentLabImportSource
from execution.acquire.local_source_mirror import (
    build_local_source_inventory,
    mirror_local_sources,
    summarize_local_root,
)


def test_summarize_local_root_fingerprint_ignores_mtime_changes(tmp_path: Path) -> None:
    root = tmp_path / "source"
    nested = root / "nested"
    nested.mkdir(parents=True)
    alpha = root / "a.txt"
    beta = nested / "b.txt"
    alpha.write_text("abc", encoding="utf-8")
    beta.write_text("defgh", encoding="utf-8")

    original = summarize_local_root(root, sample_limit=2)
    alpha.touch()
    beta.touch()
    updated = summarize_local_root(root, sample_limit=2)

    assert original["fingerprint_version"] == "local-source-root:v1"
    assert original["fingerprint_basis"] == "relative_path_and_size"
    assert updated["fingerprint"] == original["fingerprint"]


def test_build_local_source_inventory_emits_stable_inventory_fingerprint(tmp_path: Path) -> None:
    source_root = tmp_path / "data_sources" / "uniprot"
    source_root.mkdir(parents=True)
    payload = source_root / "uniprot_sprot.dat.gz"
    payload.write_text("stub", encoding="utf-8")

    source = BioAgentLabImportSource(
        source_name="uniprot",
        category="sequence",
        status="present",
        candidate_roots=(str(payload),),
        present_roots=(str(payload),),
        missing_roots=(),
        join_keys=("P69905",),
        load_hints=("index",),
        provenance={"registry_id": "test", "storage_root": str(tmp_path)},
    )

    first = build_local_source_inventory(source, sample_limit=2)
    payload.touch()
    second = build_local_source_inventory(source, sample_limit=2)

    assert first["inventory_fingerprint_version"] == "local-source-inventory:v1"
    assert first["inventory_fingerprint_basis"] == "root_path_and_root_fingerprints"
    assert first["inventory_fingerprint"] == second["inventory_fingerprint"]
    assert (
        first["present_root_summaries"][0]["fingerprint"]
        == second["present_root_summaries"][0]["fingerprint"]
    )


def test_mirror_local_sources_surfaces_inventory_fingerprint_in_registry_summary(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    raw_root = tmp_path / "repo" / "data" / "raw"
    (storage_root / "data" / "catalog").mkdir(parents=True)
    (storage_root / "data" / "catalog" / "download_manifest.csv").write_text(
        "source\nuniprot\n",
        encoding="utf-8",
    )

    summary = mirror_local_sources(
        storage_root=storage_root,
        raw_root=raw_root,
        source_names=("catalog",),
        sample_limit=2,
    )

    source_summary = summary["imported_sources"][0]
    assert source_summary["source_name"] == "catalog"
    assert source_summary["inventory_fingerprint_version"] == "local-source-inventory:v1"
    assert len(source_summary["inventory_fingerprint"]) == 64
