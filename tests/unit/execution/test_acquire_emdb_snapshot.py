from __future__ import annotations

from urllib.error import URLError

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.emdb_snapshot import EMDBSnapshotManifest, acquire_emdb_snapshot


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
        assert timeout == 30.0
        return _FakeResponse(payload)

    return opener


def test_acquire_emdb_snapshot_records_linkage_and_validation_metadata() -> None:
    source_release = SourceReleaseManifest(
        source_name="EMDB",
        release_version="2026_03",
        release_date="2026-03-20",
        source_locator="https://example.org/emdb-1234.json",
        provenance=("source:emdb", "source:empiar", "source:pdb"),
        reproducibility_metadata=("pinned-release",),
    )
    manifest = EMDBSnapshotManifest(
        source_release=source_release,
        accessions=("EMD-1234",),
        include_validation=True,
        metadata={"note": "unit-test"},
    )
    payload = b"""
    {
      "entries": [
        {
          "accession": "EMD-1234",
          "title": "Example cryo-EM map",
          "status": "REL",
          "schema_version": "1.0",
          "release_date": "2026-03-18",
          "deposition_date": "2026-01-01",
          "sample_type": "single particle",
          "organism": "Homo sapiens",
          "microscopy_method": "cryo-EM",
          "resolution": 2.4,
          "map_class": "single particle",
          "primary_map_ref": "EMD-1234.map",
          "map_file_refs": ["EMD-1234.map"],
          "auxiliary_file_refs": ["EMD-1234_half1.map", "EMD-1234_half2.map"],
          "linked_pdb_ids": ["7ABC"],
          "linked_empiar_ids": ["EMPIAR-12345"],
          "linked_uniprot_accessions": ["P69905"],
          "linked_alphafold_db_ids": ["AF-Q12345-F1"],
          "validation_summary": {
            "resolution": 2.4,
            "fsc": 0.143,
            "fit_to_model": "good"
          }
        }
      ]
    }
    """

    result = acquire_emdb_snapshot(
        manifest,
        opener=_fake_opener("https://example.org/emdb-1234.json", payload),
    )

    assert result.status == "ok"
    assert result.succeeded is True
    assert result.manifest is not None
    assert result.manifest.manifest_id == source_release.manifest_id
    assert result.snapshot is not None
    assert result.snapshot.provenance.source == "EMDB"
    assert result.snapshot.provenance.source_family == "map"
    assert result.snapshot.provenance.record_count == 1
    assert result.snapshot.provenance.linked_pdb_count == 1
    assert result.snapshot.provenance.linked_empiar_count == 1
    assert result.snapshot.provenance.linked_uniprot_count == 1
    assert result.snapshot.provenance.validation_record_count == 1
    record = result.snapshot.records[0]
    assert record.accession == "EMD-1234"
    assert record.title == "Example cryo-EM map"
    assert record.linked_pdb_ids == ("7ABC",)
    assert record.linked_empiar_ids == ("EMPIAR-12345",)
    assert record.linked_uniprot_accessions == ("P69905",)
    assert record.linked_alphafold_db_ids == ("AF-Q12345-F1",)
    assert record.validation_summary["resolution"] == 2.4
    assert record.validation_summary["fit_to_model"] == "good"
    assert record.provenance["source"] == "EMDB"
    assert result.raw_payload.lstrip().startswith("{")

    payload_dict = result.to_dict()
    assert payload_dict["manifest"]["manifest_id"] == source_release.manifest_id
    assert payload_dict["snapshot"]["records"][0]["linked_pdb_ids"] == ["7ABC"]
    assert payload_dict["provenance"]["linked_empiar_count"] == 1


def test_acquire_emdb_snapshot_blocks_when_manifest_lacks_locator() -> None:
    source_release = SourceReleaseManifest(
        source_name="EMDB",
        release_version="2026_03",
        release_date="2026-03-20",
        provenance=("source:emdb",),
    )
    manifest = EMDBSnapshotManifest(
        source_release=source_release,
        accessions=("EMD-1234",),
    )

    result = acquire_emdb_snapshot(manifest)

    assert result.status == "blocked"
    assert result.snapshot is None
    assert "source locator" in result.reason


def test_acquire_emdb_snapshot_blocks_invalid_accessions_before_fetch() -> None:
    source_release = SourceReleaseManifest(
        source_name="EMDB",
        release_version="2026_03",
        release_date="2026-03-20",
        source_locator="https://example.org/emdb-1234.json",
        provenance=("source:emdb",),
    )

    result = acquire_emdb_snapshot(
        {
            "source_release": source_release.to_dict(),
            "accessions": ["bad accession"],
        }
    )

    assert result.status == "blocked"
    assert result.snapshot is None
    assert "accessions must be valid" in result.reason


def test_acquire_emdb_snapshot_reports_unavailable_fetch_failures_honestly() -> None:
    source_release = SourceReleaseManifest(
        source_name="EMDB",
        release_version="2026_03",
        release_date="2026-03-20",
        source_locator="https://example.org/emdb-1234.json",
        provenance=("source:emdb",),
    )
    manifest = EMDBSnapshotManifest(
        source_release=source_release,
        accessions=("EMD-1234",),
    )

    def opener(request, timeout=None):
        raise URLError("network down")

    result = acquire_emdb_snapshot(manifest, opener=opener)

    assert result.status == "unavailable"
    assert result.snapshot is None
    assert "network down" in result.reason
