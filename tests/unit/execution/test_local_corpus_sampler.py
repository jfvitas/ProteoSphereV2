from __future__ import annotations

import hashlib
from pathlib import Path

from execution.acquire.local_corpus_sampler import (
    LocalCorpusFingerprintReport,
    fingerprint_local_corpus_entry,
    fingerprint_local_source_registry,
)
from execution.acquire.local_source_registry import (
    LocalSourceDefinition,
    build_local_source_registry,
)


def test_fingerprint_local_source_registry_reports_present_partial_missing(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    present_file = storage_root / "data_sources" / "uniprot" / "uniprot_sprot.dat.gz"
    present_file.parent.mkdir(parents=True, exist_ok=True)
    present_file.write_bytes(b"alpha\nbeta\n")

    present_dir = storage_root / "data" / "catalog"
    present_dir.mkdir(parents=True, exist_ok=True)
    first_dir_file = present_dir / "a.json"
    second_dir_file = present_dir / "b.json"
    first_dir_file.write_bytes(b'{"id": 1}\n')
    second_dir_file.write_bytes(b'{"id": 2}\n')

    registry = build_local_source_registry(
        storage_root,
        (
            LocalSourceDefinition(
                source_name="uniprot",
                category="sequence",
                candidate_roots=("data_sources/uniprot/uniprot_sprot.dat.gz",),
                load_hints=("index",),
            ),
            LocalSourceDefinition(
                source_name="catalog",
                category="metadata",
                candidate_roots=("data/catalog", "data/catalog/missing.json"),
                load_hints=("preload",),
            ),
            LocalSourceDefinition(
                source_name="missing_source",
                category="metadata",
                candidate_roots=("data/missing/source.json",),
                load_hints=("lazy",),
            ),
        ),
        registry_id="temp-registry",
    )

    report = fingerprint_local_source_registry(registry, sample_limit=2)
    payload = report.to_dict()
    by_name = {entry["source_name"]: entry for entry in payload["entries"]}

    assert isinstance(report, LocalCorpusFingerprintReport)
    assert payload["report_id"] == "local-corpus-fingerprint-report:v1"
    assert payload["entry_count"] == 3
    assert payload["present_entry_count"] == 1
    assert payload["partial_entry_count"] == 1
    assert payload["missing_entry_count"] == 1
    assert payload["missing_sources"] == ["missing_source"]

    uniprot = by_name["uniprot"]
    assert uniprot["coverage_status"] == "present"
    assert uniprot["sampled_file_count"] == 1
    assert uniprot["sampled_paths"] == [str(present_file).replace("\\", "/")]
    assert uniprot["sampled_files"][0]["sha256"] == hashlib.sha256(
        b"alpha\nbeta\n"
    ).hexdigest()

    catalog = by_name["catalog"]
    assert catalog["coverage_status"] == "partial"
    assert catalog["sampled_file_count"] == 2
    assert catalog["missing_roots"] == [
        str(storage_root / "data" / "catalog" / "missing.json")
    ]
    assert set(catalog["sampled_paths"]) == {
        str(first_dir_file).replace("\\", "/"),
        str(second_dir_file).replace("\\", "/"),
    }

    missing = by_name["missing_source"]
    assert missing["coverage_status"] == "missing"
    assert missing["sampled_file_count"] == 0
    assert missing["sampled_paths"] == []
    assert missing["fingerprint"]


def test_fingerprint_local_corpus_entry_uses_actual_file_metadata(tmp_path: Path) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    storage_root.mkdir(parents=True)
    file_path = storage_root / "data" / "reports" / "summary.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b'{"status": "ok"}\n')

    registry = build_local_source_registry(
        storage_root,
        (
            LocalSourceDefinition(
                source_name="reports",
                category="metadata",
                candidate_roots=("data/reports/summary.json",),
                load_hints=("preload",),
                notes=("report slice",),
            ),
        ),
    )
    entry = registry.get("reports")
    assert entry is not None

    fingerprint = fingerprint_local_corpus_entry(entry)

    assert fingerprint.coverage_status == "present"
    assert fingerprint.sampled_file_count == 1
    assert fingerprint.sampled_files[0].path == str(file_path).replace("\\", "/")
    assert fingerprint.sampled_files[0].hash_mode == "full"
    assert fingerprint.sampled_files[0].size_bytes == file_path.stat().st_size
    assert fingerprint.sampled_files[0].modified_ns == file_path.stat().st_mtime_ns
    assert fingerprint.notes == ("report slice",)
