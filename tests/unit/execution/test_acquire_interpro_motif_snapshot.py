from __future__ import annotations

from pathlib import Path

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.interpro_motif_snapshot import (
    InterProMotifSnapshot,
    InterProMotifSnapshotContract,
    InterProMotifSnapshotResult,
    acquire_interpro_motif_snapshot,
)


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def _fake_opener(expected_url: str, payload: bytes):
    def opener(request, timeout=None):
        assert request.full_url == expected_url
        assert request.headers["User-agent"] == "ProteoSphereV2-InterProMotifSnapshot/0.1"
        assert timeout == 30.0
        return _FakeResponse(payload)

    return opener


def test_acquire_interpro_motif_snapshot_uses_local_artifact_and_preserves_provenance(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "interpro-entry.html"
    source_file.write_text(
        "<html>\n<head><title>InterPro IPR000001</title></head>\n"
        "<body>Family annotation</body>\n</html>\n",
        encoding="utf-8",
    )

    manifest = SourceReleaseManifest(
        source_name="InterPro",
        release_version="108.0",
        release_date="2026-01-30",
        retrieval_mode="download",
        local_artifact_refs=(str(source_file),),
        provenance=("InterPro release archive", "InterPro entry page"),
        reproducibility_metadata=("sha256:seed",),
    )

    result = acquire_interpro_motif_snapshot(
        manifest,
        acquired_on="2026-03-22T00:00:00+00:00",
    )

    assert isinstance(result, InterProMotifSnapshotResult)
    assert result.status == "ok"
    assert result.reason == "interpro_motif_snapshot_acquired"
    assert result.succeeded is True
    assert isinstance(result.contract, InterProMotifSnapshotContract)
    assert isinstance(result.snapshot, InterProMotifSnapshot)
    assert result.contract.source_name == "InterPro"
    assert result.contract.target_id == "motif_interpro_entry"
    assert result.snapshot.content_source.startswith("local_artifact:")
    assert result.snapshot.source_family == "motif"
    assert result.snapshot.nonempty_line_count == 4
    assert result.provenance["source_name"] == "InterPro"
    assert result.provenance["requested_source_name"] == "InterPro"
    assert result.provenance["content_source"].startswith("local_artifact:")
    assert result.provenance["parser_version"] == "interpro-motif-text-v1"

    payload = result.to_dict()
    assert payload["manifest"]["release_version"] == "108.0"
    assert payload["snapshot"]["nonempty_line_count"] == 4


def test_acquire_interpro_motif_snapshot_accepts_prosite_remote_payload() -> None:
    manifest = SourceReleaseManifest(
        source_name="PROSITE",
        release_date="2026-03-01",
        retrieval_mode="scrape",
        source_locator="https://prosite.expasy.org/PS00001",
        provenance=("PROSITE pattern page",),
    )

    result = acquire_interpro_motif_snapshot(
        manifest,
        opener=_fake_opener(
            "https://prosite.expasy.org/PS00001",
            b"PROSITE detail page\npattern family\nmotif call\n",
        ),
        acquired_on="2026-03-22T00:00:00+00:00",
    )

    assert result.status == "ok"
    assert result.contract is not None
    assert result.contract.source_name == "PROSITE"
    assert result.contract.source_family == "motif"
    assert result.contract.target_id == "motif_prosite_details"
    assert result.snapshot is not None
    assert result.snapshot.content_source == "source_locator:https://prosite.expasy.org/PS00001"
    assert result.snapshot.line_count == 3
    assert result.snapshot.nonempty_line_count == 3
    assert result.snapshot.provenance["source_locator_prefix"] == "https://prosite.expasy.org/"


def test_acquire_interpro_motif_snapshot_reports_empty_payload_as_unavailable() -> None:
    manifest = SourceReleaseManifest(
        source_name="ELM",
        release_version="2026-03",
        retrieval_mode="scrape",
        source_locator="https://elm.eu.org/elms/elmPages/DOC_CYCLIN_RxL_1.html",
    )

    result = acquire_interpro_motif_snapshot(
        manifest,
        opener=_fake_opener(
            "https://elm.eu.org/elms/elmPages/DOC_CYCLIN_RxL_1.html",
            b"",
        ),
        acquired_on="2026-03-22T00:00:00+00:00",
    )

    assert result.status == "unavailable"
    assert result.reason == "interpro_motif_empty_payload"
    assert result.contract is not None
    assert result.snapshot is None
    assert result.provenance["availability"] == "unavailable"
    assert result.provenance["content_source"] == (
        "source_locator:https://elm.eu.org/elms/elmPages/DOC_CYCLIN_RxL_1.html"
    )


def test_acquire_interpro_motif_snapshot_blocks_unsupported_source() -> None:
    manifest = SourceReleaseManifest(
        source_name="Pfam",
        release_version="35.0",
        retrieval_mode="download",
        source_locator="https://www.ebi.ac.uk/interpro/entry/pfam/",
    )

    result = acquire_interpro_motif_snapshot(manifest)

    assert result.status == "blocked"
    assert result.reason == "interpro_motif_unsupported_source"
    assert result.contract is None
    assert result.snapshot is None
    assert result.provenance["availability"] == "blocked"
