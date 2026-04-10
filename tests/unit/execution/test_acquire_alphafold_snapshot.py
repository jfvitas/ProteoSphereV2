from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)
from execution.acquire.alphafold_snapshot import (
    ALPHAFOLD_API_BASE_URL,
    ALPHAFOLD_SMOKE_ENV_VAR,
    AlphaFoldSnapshotManifest,
    AlphaFoldSnapshotStatus,
    SnapshotSmokeDisabledError,
    acquire_alphafold_snapshot,
    build_accession_snapshot_manifest,
    build_alphafold_snapshot_manifest,
    run_live_smoke_snapshot,
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


def _json(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _fake_opener(payloads: dict[str, bytes | Exception]):
    def opener(request, timeout=None):
        assert timeout == 30.0
        payload = payloads[request.full_url]
        if isinstance(payload, Exception):
            raise payload
        return _FakeResponse(payload)

    return opener


def _release_manifest() -> SourceReleaseManifest:
    return SourceReleaseManifest(
        source_name="AlphaFold DB",
        release_version="2026_03",
        retrieval_mode="api",
        source_locator="https://alphafold.ebi.ac.uk/api/openapi.json",
    )


def test_manifest_supports_source_release_and_qualifiers() -> None:
    manifest = AlphaFoldSnapshotManifest.from_mapping(
        {
            "source_release": {
                "source_name": "AlphaFold DB",
                "release_version": "2026_03",
                "retrieval_mode": "api",
                "source_locator": "https://alphafold.ebi.ac.uk/api/openapi.json",
            },
            "qualifiers": [" p12345 ", "P12345"],
            "include_complexes": True,
            "asset_types": ["bcif", "plddt_doc"],
            "metadata": {"notes": "planning snapshot"},
        }
    )

    assert manifest.manifest_id.startswith("AlphaFold DB:2026_03:api:")
    assert manifest.qualifiers == ("P12345",)
    assert manifest.include_complexes is True
    assert manifest.coordinate_asset_types == ("bcif", "plddt_doc")
    assert manifest.metadata["notes"] == "planning snapshot"


def test_accession_snapshot_manifest_keeps_accession_first_inputs() -> None:
    manifest = build_accession_snapshot_manifest(
        ["q9nzd4"],
        source_release=_release_manifest(),
        metadata={"lane": "thin_cohort"},
    )

    assert manifest.qualifiers == ("Q9NZD4",)
    assert manifest.metadata["accessions"] == ["Q9NZD4"]
    assert manifest.metadata["lane"] == "thin_cohort"
    assert manifest.manifest_id.startswith("AlphaFold DB:2026_03:api:")


def test_acquire_snapshot_returns_prediction_and_complex_metadata() -> None:
    manifest = build_alphafold_snapshot_manifest(
        ["P12345"],
        source_release=_release_manifest(),
        include_complexes=True,
    )
    payloads = {
        f"{ALPHAFOLD_API_BASE_URL}/prediction/P12345": _json(
            [
                {
                    "uniprotAccession": ["P12345"],
                    "uniprotId": ["TEST_HUMAN"],
                    "modelEntityId": "AF-P12345-F1",
                    "entryId": "AF-P12345-F1",
                    "sequenceChecksum": "ABC123",
                    "latestVersion": 5,
                    "allVersions": [4, 5],
                    "toolUsed": "AlphaFold2",
                    "providerId": "Google Deepmind",
                    "entityType": "protein",
                    "isUniProt": True,
                    "isUniProtReviewed": True,
                    "isUniProtReferenceProteome": True,
                    "gene": ["TEST"],
                    "taxId": [9606],
                    "organismScientificName": ["Homo sapiens"],
                    "sequenceStart": 1,
                    "sequenceEnd": 100,
                    "sequence": "MKT",
                    "uniprotStart": 10,
                    "uniprotEnd": 110,
                    "uniprotSequence": "MKT",
                    "globalMetricValue": 91.2,
                    "fractionVeryHigh": 0.8,
                    "bcifUrl": "https://files.example.org/model.bcif",
                    "pdbUrl": "https://files.example.org/model.pdb",
                }
            ]
        ),
        f"{ALPHAFOLD_API_BASE_URL}/complex/P12345": _json(
            [
                {
                    "uniprotAccession": ["P12345", "Q9TEST"],
                    "modelEntityId": "AF-P12345-PARTNER",
                    "providerId": "NVIDIA",
                    "assemblyType": "Hetero",
                    "oligomericState": "dimer",
                    "complexName": "Example complex",
                    "complexComposition": [
                        {
                            "identifier": "P12345",
                            "identifierType": "uniprotAccession",
                            "stoichiometry": 1,
                        },
                        {
                            "identifier": "Q9TEST",
                            "identifierType": "uniprotAccession",
                            "stoichiometry": 2,
                        },
                    ],
                    "globalMetricValue": 86.0,
                    "complexPredictionAccuracy_ipTM": 0.88,
                    "complexPredictionAccuracy_pDockQ2": 0.55,
                }
            ]
        ),
    }

    result = acquire_alphafold_snapshot(
        manifest,
        opener=_fake_opener(payloads),
    )

    assert result.status == AlphaFoldSnapshotStatus.READY
    assert result.succeeded
    assert result.blocker_reason == ""
    assert len(result.records) == 2

    prediction, complex_record = result.records
    assert prediction.structure_kind == "prediction"
    assert prediction.confidence.global_metric_value == 91.2
    assert prediction.confidence.confidence_fractions["fractionVeryHigh"] == 0.8
    assert prediction.asset_urls["bcif"] == "https://files.example.org/model.bcif"
    assert prediction.provenance.manifest_id.startswith("AlphaFold DB:2026_03:api:")
    assert complex_record.structure_kind == "complex"
    assert complex_record.assembly_type == "Hetero"
    assert complex_record.complex_name == "Example complex"
    assert complex_record.confidence.complex_metrics["complexPredictionAccuracy_ipTM"] == 0.88
    assert complex_record.complex_composition[1].stoichiometry == 2


def test_acquire_snapshot_materializes_selected_assets() -> None:
    manifest = build_alphafold_snapshot_manifest(
        ["P12345"],
        source_release=_release_manifest(),
        coordinate_asset_types=("bcif", "plddt_doc"),
    )
    payloads = {
        f"{ALPHAFOLD_API_BASE_URL}/prediction/P12345": _json(
            [
                {
                    "uniprotAccession": ["P12345"],
                    "modelEntityId": "AF-P12345-F1",
                    "bcifUrl": "https://files.example.org/model.bcif",
                    "plddtDocUrl": "https://files.example.org/model_plddt.json",
                }
            ]
        ),
        "https://files.example.org/model.bcif": b"BCIF",
        "https://files.example.org/model_plddt.json": _json({"plddt": [91.2, 88.1]}),
    }

    result = acquire_alphafold_snapshot(manifest, opener=_fake_opener(payloads))

    assert result.status == AlphaFoldSnapshotStatus.READY
    assert [asset.asset_type for asset in result.assets] == ["bcif", "plddt_doc"]
    assert result.assets[0].payload == b"BCIF"
    assert result.assets[1].payload == {"plddt": [91.2, 88.1]}


def test_acquire_snapshot_blocks_on_network_failure() -> None:
    manifest = build_alphafold_snapshot_manifest(
        ["P12345"],
        source_release=_release_manifest(),
    )
    result = acquire_alphafold_snapshot(
        manifest,
        opener=_fake_opener(
            {
                f"{ALPHAFOLD_API_BASE_URL}/prediction/P12345": URLError("network down"),
            }
        ),
    )

    assert result.status == AlphaFoldSnapshotStatus.BLOCKED
    assert result.blocker_reason.startswith("AlphaFold request failed")
    assert result.invalid_qualifiers == ("P12345",)


def test_acquire_snapshot_is_unavailable_for_empty_payload() -> None:
    manifest = build_alphafold_snapshot_manifest(
        ["P12345"],
        source_release=_release_manifest(),
    )
    result = acquire_alphafold_snapshot(
        manifest,
        opener=_fake_opener(
            {
                f"{ALPHAFOLD_API_BASE_URL}/prediction/P12345": _json([]),
            }
        ),
    )

    assert result.status == AlphaFoldSnapshotStatus.UNAVAILABLE
    assert result.records == ()
    assert "no prediction or complex records" in result.unavailable_reason


def test_acquire_snapshot_preserves_invalid_manifest_request_identity() -> None:
    result = acquire_alphafold_snapshot(
        {
            "source_release": {
                "source_name": "AlphaFold DB",
                "release_version": "2026_03",
                "retrieval_mode": "screen-scrape",
                "source_locator": "https://alphafold.ebi.ac.uk/api/openapi.json",
            },
            "qualifiers": ["Q9TEST"],
        }
    )

    assert result.status == AlphaFoldSnapshotStatus.BLOCKED
    assert result.manifest.qualifiers == ("Q9TEST",)
    assert result.manifest.source_release.source_name == "AlphaFold DB"
    assert result.manifest.source_release.release_version == "2026_03"
    assert result.manifest.source_release.retrieval_mode == "api"
    assert result.manifest.manifest_id.startswith("AlphaFold DB:2026_03:api:")
    assert result.manifest.metadata["requested_invalid_retrieval_mode"] == "screen-scrape"
    round_tripped = validate_source_release_manifest_payload(
        result.manifest.to_dict()["source_release"]
    )
    assert round_tripped.retrieval_mode == "api"
    assert result.invalid_qualifiers == ()
    assert "unsupported retrieval_mode" in result.blocker_reason
    assert "P69905" not in result.manifest.manifest_id


def test_live_smoke_snapshot_requires_explicit_opt_in(monkeypatch) -> None:
    monkeypatch.delenv(ALPHAFOLD_SMOKE_ENV_VAR, raising=False)

    with pytest.raises(SnapshotSmokeDisabledError):
        run_live_smoke_snapshot("P12345")


def test_live_smoke_snapshot_delegates_when_opted_in(monkeypatch) -> None:
    monkeypatch.setenv(ALPHAFOLD_SMOKE_ENV_VAR, "1")
    payloads = {
        f"{ALPHAFOLD_API_BASE_URL}/prediction/P12345": _json(
            [
                {
                    "uniprotAccession": ["P12345"],
                    "modelEntityId": "AF-P12345-F1",
                    "globalMetricValue": 92.1,
                }
            ]
        ),
    }

    result = run_live_smoke_snapshot("P12345", opener=_fake_opener(payloads))

    assert result.status == AlphaFoldSnapshotStatus.READY
    assert len(result.records) == 1
