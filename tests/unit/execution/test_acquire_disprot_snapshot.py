from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.disprot_snapshot import (
    DEFAULT_DISPROT_API_BASE_URL,
    DISPROT_SMOKE_ENV_VAR,
    SnapshotSmokeDisabledError,
    acquire_disprot_snapshot,
    run_live_smoke_snapshot,
)


class _FakeResponse:
    def __init__(self, payload: bytes, *, headers: dict[str, str] | None = None):
        self._payload = payload
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def _fake_opener(payloads: dict[str, tuple[bytes, dict[str, str]] | Exception]):
    def opener(request, timeout=None):
        assert timeout == 30.0
        payload = payloads[request.full_url]
        if isinstance(payload, Exception):
            raise payload
        body, headers = payload
        assert request.headers["User-agent"] == "ProteoSphereV2-DisProtSnapshot/0.1"
        return _FakeResponse(body, headers=headers)

    return opener


def test_acquire_disprot_snapshot_records_disorder_regions_and_pinned_provenance() -> None:
    source_release = SourceReleaseManifest(
        source_name="DisProt",
        release_version="2025_12",
        retrieval_mode="download",
        source_locator="https://disprot.org/releases/DisProt%20release_2025_12.json",
    )
    manifest = {
        "source_release": source_release.to_dict(),
        "accessions": ["P49913"],
        "provenance": {"curation_batch": "2026Q1"},
    }
    payload = json.dumps(
        [
            {
                "acc": "P49913",
                "disprot_id": "DP00004",
                "sequence": "MKTQRDGHSLGRWSLVLLLLGLVMPLAIIAQVLSYKEAVL",
                "length": 40,
                "organism": "Homo sapiens",
                "ncbi_taxon_id": 9606,
                "name": "Cathelicidin antimicrobial peptide",
                "genes": [
                    {
                        "name": {"value": "CAMP"},
                        "synonyms": [{"value": "CAP18"}],
                        "orfNames": [{"value": "HSD26"}],
                    }
                ],
                "taxonomy": ["Eukaryota", "Metazoa"],
                "dataset": ["Curated disorder"],
                "UniParc": "UPI0000000A67",
                "uniref50": "UniRef50_P49913",
                "uniref90": "UniRef90_P49913",
                "uniref100": "UniRef100_P49913",
                "released": "2025_12",
                "date": "2025-12-20T12:00:00.000Z",
                "creator": "curator",
                "regions_counter": 1,
                "disorder_content": 0.25,
                "alphafold_very_low_content": 0.15,
                "disprot_consensus": {
                    "full": [{"start": 1, "end": 40, "type": "D"}],
                    "Structural state": [{"start": 1, "end": 40, "type": "D"}],
                },
                "regions": [
                    {
                        "region_id": "DP00004r001",
                        "start": 1,
                        "end": 40,
                        "version": 4,
                        "term_id": "IDPO:0000002",
                        "term_name": "disorder",
                        "term_namespace": "Structural state",
                        "term_ontology": "IDPO",
                        "disprot_namespace": "Structural state",
                        "ec_id": "ECO:0006206",
                        "ec_go": "EXP",
                        "ec_name": "near-UV circular dichroism evidence used in manual assertion",
                        "ec_ontology": "ECO",
                        "reference_id": "9452503",
                        "reference_source": "pmid",
                        "reference_html": "Example reference",
                        "curator_id": "esalladini",
                        "curator_name": "Edoardo Salladini",
                        "curator_orcid": "0000-0002-5152-5953",
                        "validated": {
                            "curator_id": "fquaglia",
                            "curator_name": "Federica Quaglia",
                        },
                        "date": "2025-12-19T08:00:00.000Z",
                        "released": "2025_12",
                        "uniprot_changed": True,
                        "cross_refs": [{"db": "PDB", "id": "1ABC"}],
                        "annotation_extensions": [{"name": "evidence"}],
                        "conditions": [{"name": "pH", "value": "7.0"}],
                        "construct_alterations": [{"type": "deletion"}],
                        "interaction_partner": [{"db": "UniProt", "id": "P07260"}],
                        "sample": [{"type": "cell"}],
                        "statement": [{"type": "Results", "text": "Example disorder span."}],
                    }
                ],
                "features": {"pfam": [{"id": "PF00000"}]},
            }
        ]
    ).encode("utf-8")

    result = acquire_disprot_snapshot(
        manifest,
        opener=_fake_opener(
            {
                "https://disprot.org/releases/DisProt%20release_2025_12.json": (
                    payload,
                    {"api-version": "8.0.1"},
                )
            }
        ),
        acquired_at="2026-03-22T12:00:00-05:00",
    )

    assert result.status == "ready"
    assert result.succeeded is True
    assert result.contract is not None
    assert result.contract.manifest_id == source_release.manifest_id
    assert result.snapshot is not None
    assert result.snapshot.provenance["record_count"] == 1
    assert result.snapshot.provenance["region_count"] == 1
    assert result.snapshot.provenance["api_version"] == "8.0.1"
    record = result.snapshot.records[0]
    assert record.accession == "P49913"
    assert record.disprot_id == "DP00004"
    assert record.gene_names == ("CAMP",)
    assert record.gene_synonyms == ("CAP18",)
    assert record.orf_names == ("HSD26",)
    assert record.disprot_consensus["full"][0].type == "D"
    assert record.regions[0].label_family == "Structural state"
    assert record.regions[0].cross_refs[0]["db"] == "PDB"
    assert result.provenance["requested_accessions"] == ["P49913"]
    assert result.provenance["source_name"] == "DisProt"
    assert result.to_dict()["contract"]["manifest_id"] == source_release.manifest_id
    assert result.to_dict()["snapshot"]["records"][0]["regions"][0]["term_id"] == "IDPO:0000002"


def test_acquire_disprot_snapshot_blocks_invalid_manifests_before_network() -> None:
    manifest = {
        "source_release": {
            "source_name": "UniProt",
            "release_version": "2025_12",
            "retrieval_mode": "download",
            "source_locator": "https://disprot.org/releases/DisProt%20release_2025_12.json",
        },
        "accessions": ["P49913"],
    }

    result = acquire_disprot_snapshot(manifest, opener=_unexpected_opener)

    assert result.status == "blocked"
    assert result.contract is None
    assert result.snapshot is None
    assert "DisProt" in result.blocker_reason


def test_acquire_disprot_snapshot_marks_missing_accessions_unavailable() -> None:
    manifest = {
        "source_release": {
            "source_name": "DisProt",
            "release_version": "2025_12",
            "retrieval_mode": "api",
            "source_locator": DEFAULT_DISPROT_API_BASE_URL,
        },
        "accessions": ["P49913"],
    }

    result = acquire_disprot_snapshot(
        manifest,
        opener=_fake_opener(
            {
                "https://disprot.org/api/search?query=P49913": (
                    json.dumps({"data": [], "size": 0}).encode("utf-8"),
                    {"api-version": "8.0.1"},
                )
            }
        ),
    )

    assert result.status == "unavailable"
    assert result.snapshot is None
    assert result.missing_accessions == ("P49913",)
    assert "did not resolve requested accession" in result.unavailable_reason


def test_acquire_disprot_snapshot_translates_network_failures_into_blockers() -> None:
    manifest = {
        "source_release": {
            "source_name": "DisProt",
            "release_version": "2025_12",
            "retrieval_mode": "api",
            "source_locator": DEFAULT_DISPROT_API_BASE_URL,
        },
        "accessions": ["P49913"],
    }

    result = acquire_disprot_snapshot(manifest, opener=_failing_opener)

    assert result.status == "blocked"
    assert result.snapshot is None
    assert "request failed" in result.blocker_reason


def test_run_live_smoke_snapshot_requires_explicit_opt_in(monkeypatch) -> None:
    monkeypatch.delenv(DISPROT_SMOKE_ENV_VAR, raising=False)

    with pytest.raises(SnapshotSmokeDisabledError):
        run_live_smoke_snapshot("P49913")


def _unexpected_opener(*args, **kwargs):
    raise AssertionError("network should not be called for blocked manifests")


def _failing_opener(request, timeout=None):
    raise URLError("network down")
