from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts import download_raw_data


def test_write_json_uses_temp_file_then_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_path = tmp_path / "data" / "raw" / "example.json"
    replace_calls: list[tuple[Path, Path]] = []
    real_replace = os.replace

    def recording_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        replace_calls.append((Path(src), Path(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(download_raw_data.os, "replace", recording_replace)

    download_raw_data._write_json(target_path, {"status": "ok", "count": 1})

    assert target_path.exists()
    assert json.loads(target_path.read_text(encoding="utf-8")) == {
        "status": "ok",
        "count": 1,
    }
    assert len(replace_calls) == 1
    temp_path, final_path = replace_calls[0]
    assert final_path == target_path
    assert temp_path.name.endswith(".tmp")
    assert temp_path != target_path
    assert not temp_path.exists()


def test_download_uniprot_writes_manifest_after_payload_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    release_dir = repo_root / "data" / "raw" / "uniprot" / "run-001"
    write_order: list[str] = []
    real_write_json = download_raw_data._write_json
    real_write_text = download_raw_data._write_text

    class FakeUniProtClient:
        def get_entry(self, accession: str, opener: object | None = None) -> dict[str, object]:
            return {"accession": accession}

        def get_fasta(self, accession: str, opener: object | None = None) -> str:
            return f">{accession}\nMKT\n"

        def get_text(self, accession: str, opener: object | None = None) -> str:
            return f"ID   {accession}"

    def recording_write_json(path: Path, payload: object) -> None:
        write_order.append(path.name)
        real_write_json(path, payload)

    def recording_write_text(path: Path, payload: str) -> None:
        write_order.append(path.name)
        real_write_text(path, payload)

    monkeypatch.setattr(download_raw_data, "UniProtClient", FakeUniProtClient)
    monkeypatch.setattr(download_raw_data, "ROOT", repo_root)
    monkeypatch.setattr(download_raw_data, "_write_json", recording_write_json)
    monkeypatch.setattr(download_raw_data, "_write_text", recording_write_text)

    result = download_raw_data._download_uniprot(
        accessions=("P12345",),
        release_dir=release_dir,
        opener=None,
        dry_run=False,
    )

    assert result["source"] == "uniprot"
    assert write_order[-1] == "manifest.json"
    assert write_order.index("P12345.json") < write_order.index("manifest.json")
    assert write_order.index("P12345.fasta") < write_order.index("manifest.json")
    assert write_order.index("P12345.txt") < write_order.index("manifest.json")
    assert (release_dir / "manifest.json").exists()


def test_run_bootstrap_does_not_promote_latest_when_required_source_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_root = tmp_path / "data" / "raw"

    monkeypatch.setattr(
        download_raw_data,
        "_download_uniprot",
        lambda **kwargs: {"source": "uniprot", "status": "ok", "downloaded_files": []},
    )
    monkeypatch.setattr(
        download_raw_data,
        "_download_alphafold",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    summary = download_raw_data.run_bootstrap(
        accessions=("P12345",),
        sources=("uniprot", "alphafold"),
        raw_root=raw_root,
        allow_insecure_ssl=False,
        dry_run=False,
        alphafold_assets=False,
        max_structures_per_accession=1,
        download_mmcif=False,
        psicquic_max_results=10,
    )

    assert summary["status"] == "failed"
    latest_path = raw_root / "bootstrap_runs" / "LATEST.json"
    assert latest_path.exists() is False
    summary_path = raw_root / "bootstrap_runs" / f"{summary['stamp']}.json"
    assert summary_path.exists()
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert any(result["status"] == "failed" for result in payload["results"])


def test_run_bootstrap_allows_manual_pdbbind_without_blocking_latest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_root = tmp_path / "data" / "raw"

    monkeypatch.setattr(
        download_raw_data,
        "_download_uniprot",
        lambda **kwargs: {"source": "uniprot", "status": "ok", "downloaded_files": []},
    )

    summary = download_raw_data.run_bootstrap(
        accessions=("P12345",),
        sources=("uniprot", "pdbbind"),
        raw_root=raw_root,
        allow_insecure_ssl=False,
        dry_run=False,
        alphafold_assets=False,
        max_structures_per_accession=1,
        download_mmcif=False,
        psicquic_max_results=10,
    )

    assert summary["status"] == "ok"
    latest_path = raw_root / "bootstrap_runs" / "LATEST.json"
    assert latest_path.exists()
    uniprot_result = next(
        result for result in summary["results"] if result["source"] == "uniprot"
    )
    pdbbind_result = next(
        result for result in summary["results"] if result["source"] == "pdbbind"
    )
    assert uniprot_result["write_complete"] is False
    assert uniprot_result["completion_metadata"]["completion_state"] == "incomplete"
    assert uniprot_result["snapshot_identity"]["identity_state"] == "empty"
    assert uniprot_result["snapshot_identity"]["manifest_sha256"] is None
    assert pdbbind_result["write_complete"] is True
    assert pdbbind_result["completion_metadata"]["completion_state"] == "materialized"
    assert pdbbind_result["completion_metadata"]["manifest_exists"] is True
    assert (
        pdbbind_result["snapshot_identity"]["identity_basis"]
        == "local_materialized_file_inventory"
    )
    assert pdbbind_result["snapshot_identity"]["identity_state"] == "materialized"
    assert pdbbind_result["snapshot_identity"]["manifest_sha256"] is not None
    assert pdbbind_result["snapshot_identity"]["artifact_inventory_sha256"] is not None
    assert pdbbind_result["snapshot_identity"]["materialized_file_count"] == 2


def test_run_bootstrap_writes_summary_before_latest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_root = tmp_path / "data" / "raw"
    write_order: list[Path] = []
    real_write_json = download_raw_data._write_json

    monkeypatch.setattr(
        download_raw_data,
        "_download_uniprot",
        lambda **kwargs: {"source": "uniprot", "status": "ok", "downloaded_files": []},
    )

    def recording_write_json(path: Path, payload: object) -> None:
        write_order.append(path)
        real_write_json(path, payload)

    monkeypatch.setattr(download_raw_data, "_write_json", recording_write_json)

    summary = download_raw_data.run_bootstrap(
        accessions=("P12345",),
        sources=("uniprot",),
        raw_root=raw_root,
        allow_insecure_ssl=False,
        dry_run=False,
        alphafold_assets=False,
        max_structures_per_accession=1,
        download_mmcif=False,
        psicquic_max_results=10,
    )

    summary_path = raw_root / "bootstrap_runs" / f"{summary['stamp']}.json"
    latest_path = raw_root / "bootstrap_runs" / "LATEST.json"
    assert summary_path in write_order
    assert latest_path in write_order
    assert write_order.index(summary_path) < write_order.index(latest_path)


def test_run_bootstrap_marks_failed_source_as_not_write_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_root = tmp_path / "data" / "raw"

    def failing_uniprot(**kwargs: object) -> dict[str, object]:
        release_dir = kwargs["release_dir"]
        assert isinstance(release_dir, Path)
        download_raw_data._write_text(release_dir / "partial.txt", "partial")
        raise RuntimeError("boom")

    monkeypatch.setattr(download_raw_data, "_download_uniprot", failing_uniprot)

    summary = download_raw_data.run_bootstrap(
        accessions=("P12345",),
        sources=("uniprot",),
        raw_root=raw_root,
        allow_insecure_ssl=False,
        dry_run=False,
        alphafold_assets=False,
        max_structures_per_accession=1,
        download_mmcif=False,
        psicquic_max_results=10,
    )

    result = summary["results"][0]
    assert result["status"] == "failed"
    assert result["write_complete"] is False
    assert result["completion_metadata"]["completion_state"] == "failed"
    assert result["completion_metadata"]["manifest_exists"] is False
    assert result["snapshot_identity"]["identity_state"] == "partial_materialization"
    assert result["snapshot_identity"]["manifest_sha256"] is None
    assert result["snapshot_identity"]["artifact_inventory_sha256"] is not None
    assert result["snapshot_identity"]["materialized_file_count"] == 1


def test_run_bootstrap_marks_dry_run_source_as_not_materialized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_root = tmp_path / "data" / "raw"

    monkeypatch.setattr(
        download_raw_data,
        "_download_uniprot",
        lambda **kwargs: {"source": "uniprot", "status": "ok", "downloaded_files": []},
    )

    summary = download_raw_data.run_bootstrap(
        accessions=("P12345",),
        sources=("uniprot",),
        raw_root=raw_root,
        allow_insecure_ssl=False,
        dry_run=True,
        alphafold_assets=False,
        max_structures_per_accession=1,
        download_mmcif=False,
        psicquic_max_results=10,
    )

    result = summary["results"][0]
    assert result["status"] == "ok"
    assert result["write_complete"] is False
    assert result["completion_metadata"]["completion_state"] == "dry_run"
    assert result["completion_metadata"]["manifest_exists"] is False
    assert result["snapshot_identity"]["identity_basis"] == "not_materialized"
    assert result["snapshot_identity"]["identity_state"] == "dry_run"
    assert result["snapshot_identity"]["manifest_sha256"] is None
    assert result["snapshot_identity"]["artifact_inventory_sha256"] is None
    assert result["snapshot_identity"]["materialized_file_count"] == 0
