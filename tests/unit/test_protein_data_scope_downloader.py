from __future__ import annotations

import importlib.util
import tarfile
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "protein_data_scope" / "download_all_sources.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("protein_data_scope_downloader", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_destination_root_stays_inside_repo() -> None:
    module = _load_module()

    destination = module.default_destination_root()

    assert destination == REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"


def test_source_tier_reads_policy_assignments() -> None:
    module = _load_module()
    policy = {
        "tiers": {
            "direct": {"source_ids": ["prosite"]},
            "resolver": {"source_ids": ["bindingdb"]},
        }
    }

    assert module.source_tier("prosite", policy) == "direct"
    assert module.source_tier("bindingdb", policy) == "resolver"
    assert module.source_tier("unknown_source", policy) == "unclassified"


def test_manual_sources_are_skipped_by_default() -> None:
    module = _load_module()

    skip, reason = module.should_skip_source(
        {"id": "bindingdb", "manual_review_required": True},
        allow_manual=False,
    )

    assert skip is True
    assert reason == "manual_review_required"


def test_html_placeholders_are_skipped_by_default() -> None:
    module = _load_module()

    skip, reason = module.should_skip_item(
        {"id": "interpro"},
        {"filename": "downloads_landing_page.html", "url": "https://example.org/downloads"},
        allow_html_placeholders=False,
    )

    assert skip is True
    assert reason == "html_placeholder"


def test_normalize_source_ids_can_filter_by_tier() -> None:
    module = _load_module()
    manifest = {
        "sources": [
            {"id": "prosite"},
            {"id": "bindingdb"},
            {"id": "reactome"},
        ]
    }
    policy = {
        "tiers": {
            "direct": {"source_ids": ["prosite", "reactome"]},
            "resolver": {"source_ids": ["bindingdb"]},
        }
    }

    filtered = module.normalize_source_ids(
        manifest,
        None,
        tiers=["direct"],
        policy=policy,
    )

    assert [item["id"] for item in filtered] == ["prosite", "reactome"]


def test_required_core_only_filters_source_files() -> None:
    module = _load_module()
    source = {
        "id": "uniprot",
        "top_level_files": [
            {"filename": "uniprot_sprot.dat.gz", "url": "https://example.org/dat"},
            {"filename": "uniprot_sprot.fasta.gz", "url": "https://example.org/fasta"},
            {"filename": "idmapping.dat.gz", "url": "https://example.org/idmapping"},
            {"filename": "uniprot_trembl.dat.gz", "url": "https://example.org/trembl"},
        ],
    }
    validation_policy = {
        "sources": {
            "uniprot": {
                "required_core_files": [
                    "uniprot_sprot.dat.gz",
                    "uniprot_sprot.fasta.gz",
                    "idmapping.dat.gz",
                ]
            }
        }
    }

    filtered = module.filter_top_level_files_for_required_core(
        source,
        validation_policy=validation_policy,
        required_core_only=True,
    )

    assert [item["filename"] for item in filtered] == [
        "uniprot_sprot.dat.gz",
        "uniprot_sprot.fasta.gz",
        "idmapping.dat.gz",
    ]


def test_selected_filenames_can_further_filter_source_files() -> None:
    module = _load_module()
    source = {
        "id": "biogrid",
        "top_level_files": [
            {"filename": "BIOGRID-ORGANISM-LATEST.mitab.zip", "url": "https://example.org/org"},
            {"filename": "BIOGRID-ALL-LATEST.mitab.zip", "url": "https://example.org/all"},
            {"filename": "BIOGRID-ORGANISM-LATEST.psi25.zip", "url": "https://example.org/psi25"},
        ],
    }

    filtered = module.filter_top_level_files_for_required_core(
        source,
        validation_policy={"sources": {}},
        required_core_only=False,
        selected_filenames={
            "BIOGRID-ORGANISM-LATEST.mitab.zip",
            "BIOGRID-ALL-LATEST.mitab.zip",
        },
    )

    assert [item["filename"] for item in filtered] == [
        "BIOGRID-ORGANISM-LATEST.mitab.zip",
        "BIOGRID-ALL-LATEST.mitab.zip",
    ]


def test_normalize_selected_filenames_splits_commas() -> None:
    module = _load_module()

    selected = module.normalize_selected_filenames(
        ["BIOGRID-ORGANISM-LATEST.mitab.zip,BIOGRID-ALL-LATEST.mitab.zip", " extra.txt "]
    )

    assert selected == {
        "BIOGRID-ORGANISM-LATEST.mitab.zip",
        "BIOGRID-ALL-LATEST.mitab.zip",
        "extra.txt",
    }


def test_safe_extract_zip_rejects_path_traversal(tmp_path: Path) -> None:
    module = _load_module()
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escape.txt", "bad")

    with zipfile.ZipFile(archive_path, "r") as archive:
        with pytest.raises(ValueError, match="unsafe archive path"):
            module._safe_extract_zip(archive, tmp_path / "out")


def test_safe_extract_tar_rejects_path_traversal(tmp_path: Path) -> None:
    module = _load_module()
    archive_path = tmp_path / "unsafe.tar"
    payload_path = tmp_path / "payload.txt"
    payload_path.write_text("bad", encoding="utf-8")

    with tarfile.open(archive_path, "w") as archive:
        archive.add(payload_path, arcname="../escape.txt")

    with tarfile.open(archive_path, "r") as archive:
        with pytest.raises(ValueError, match="unsafe archive path"):
            module._safe_extract_tar(archive, tmp_path / "out")


class _FakeResponse:
    def __init__(self, chunks: list[bytes], headers: dict[str, str] | None = None) -> None:
        self._chunks = list(chunks)
        self.headers = headers or {}

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def read(self, _chunk_size: int) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


def test_download_file_rejects_html_placeholder_responses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    fake_response = _FakeResponse(
        [b"<!DOCTYPE html><html><body>login</body></html>"],
        headers={"Content-Type": "text/html; charset=UTF-8"},
    )
    monkeypatch.setattr(module, "urlopen", lambda req, timeout=0: fake_response)

    ok, message = module.download_file(
        "https://example.org/archive.zip",
        tmp_path / "archive.zip",
        timeout=5,
        retries=1,
    )

    assert ok is False
    assert "html placeholder response" in message
    assert not (tmp_path / "archive.zip").exists()
    assert not (tmp_path / "archive.zip.part").exists()


def test_download_file_accepts_plain_text_payload_for_txt_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    fake_response = _FakeResponse(
        [b"field_a\tfield_b\nvalue_a\tvalue_b\n"],
        headers={"Content-Type": "text/plain; charset=UTF-8"},
    )
    monkeypatch.setattr(module, "urlopen", lambda req, timeout=0: fake_response)

    ok, message = module.download_file(
        "https://example.org/data.txt",
        tmp_path / "data.txt",
        timeout=5,
        retries=1,
    )

    assert ok is True
    assert message == "OK downloaded: data.txt"
    assert (tmp_path / "data.txt").read_text(encoding="utf-8") == (
        "field_a\tfield_b\nvalue_a\tvalue_b\n"
    )
