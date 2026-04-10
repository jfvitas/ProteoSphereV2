from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from connectors.rcsb.client import RCSBClient
from execution.acquire.rcsb_pdbe_snapshot import (
    LIVE_SMOKE_ENV_VAR,
    SnapshotAcquisitionResult,
    SnapshotBlockerCode,
    SnapshotManifest,
    SnapshotSmokeDisabledError,
    SnapshotStatus,
    acquire_rcsb_pdbe_snapshot,
    build_accession_enrichment_manifest,
    build_snapshot_manifest,
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


def _json(payload: dict[str, object]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _fake_opener(payloads: dict[str, bytes | Exception]):
    def opener(request, timeout=None):
        assert timeout == 30.0
        payload = payloads[request.full_url]
        if isinstance(payload, Exception):
            raise payload
        return _FakeResponse(payload)

    return opener


def test_snapshot_manifest_supports_release_and_snapshot_mapping():
    manifest = SnapshotManifest.from_mapping(
        {
            "release": "2026-03-18",
            "snapshot": "weekly-2026-03-18",
            "entries": ["1abc", "1ABC"],
            "resources": ["UNIPROT_MAPPING", "chains"],
            "metadata": {
                "validation_url_template": "https://example.org/{pdb_id}.xml",
            },
        }
    )

    assert manifest.release_id == "2026-03-18"
    assert manifest.snapshot_id == "weekly-2026-03-18"
    assert manifest.pdb_ids == ("1ABC",)
    assert manifest.pdbe_resources == ("uniprot_mapping", "chains")
    assert manifest.metadata["validation_url_template"] == "https://example.org/{pdb_id}.xml"


def test_acquire_snapshot_returns_structured_results():
    manifest = build_snapshot_manifest(
        ["1abc"],
        release_id="2026-03-18",
        pdbe_resources=("uniprot_mapping",),
    )
    payloads = {
        "https://data.rcsb.org/rest/v1/core/entry/1abc": _json(
            {
                "rcsb_id": "1abc",
                "struct": {"title": "Example structure"},
                "rcsb_entry_info": {"experimental_method": ["X-RAY DIFFRACTION"]},
                "rcsb_accession_info": {"initial_release_date": "2026-03-01"},
                "rcsb_entry_container_identifiers": {
                    "assembly_ids": ["1"],
                    "polymer_entity_ids": ["1"],
                    "nonpolymer_entity_ids": [],
                },
            }
        ),
        "https://data.rcsb.org/rest/v1/core/polymer_entity/1abc/1": _json(
            {
                "rcsb_id": "1abc",
                "entity": {"id": "1", "pdbx_description": "Example protein"},
                "entity_poly": {
                    "type": "polypeptide(L)",
                    "pdbx_seq_one_letter_code_can": "MKT",
                    "rcsb_sample_sequence_length": 3,
                },
                "rcsb_polymer_entity_container_identifiers": {
                    "entity_id": "1",
                    "auth_asym_ids": ["A"],
                    "uniprot_ids": ["P12345"],
                },
                "rcsb_entity_source_organism": [
                    {"scientific_name": "Homo sapiens", "ncbi_taxonomy_id": 9606}
                ],
            }
        ),
        "https://data.rcsb.org/rest/v1/core/assembly/1abc/1": _json(
            {
                "rcsb_id": "1abc",
                "id": "1",
                "details": "Biological assembly 1",
                "rcsb_assembly_container_identifiers": {
                    "assembly_id": "1",
                    "polymer_entity_ids": ["1"],
                    "auth_asym_ids": ["A"],
                },
            }
        ),
        "https://www.ebi.ac.uk/pdbe/api/pdb/entry/uniprot_mapping/1abc/1": _json(
            {"1abc": {"1": {"mappings": []}}}
        ),
    }
    result = acquire_rcsb_pdbe_snapshot(
        manifest,
        client=RCSBClient(),
        opener=_fake_opener(payloads),
    )

    assert isinstance(result, SnapshotAcquisitionResult)
    assert result.status == SnapshotStatus.COMPLETE
    assert result.succeeded
    assert result.blockers == ()
    assert len(result.structure_bundles) == 1
    bundle = result.structure_bundles[0]
    assert bundle.entry.title == "Example structure"
    assert bundle.entities[0].chain_ids == ("A",)
    assert [asset.resource for asset in result.assets] == [
        "entry",
        "polymer_entity",
        "assembly",
        "uniprot_mapping",
    ]
    assert result.assets[-1].identifier == "1ABC:1:uniprot_mapping"


def test_accession_enrichment_manifest_materializes_only_explicit_structures():
    manifest = build_accession_enrichment_manifest(
        ["P69905", "Q9NZD4"],
        accession_pdb_ids={
            "P69905": ["4hhb"],
            "Q9NZD4": [],
        },
        release_id="2026-03-22",
        metadata={"lane": "thin_cohort"},
    )

    assert manifest.pdb_ids == ("4HHB",)
    assert manifest.metadata["accessions"] == ["P69905", "Q9NZD4"]
    assert manifest.metadata["unresolved_accessions"] == ["Q9NZD4"]
    assert manifest.metadata["resolved_accession_count"] == 1
    assert manifest.metadata["lane"] == "thin_cohort"


def test_accession_enrichment_manifest_acquires_explicitly_mapped_structure():
    manifest = build_accession_enrichment_manifest(
        ["P69905", "Q9NZD4"],
        accession_pdb_ids={
            "P69905": ["4hhb"],
            "Q9NZD4": [],
        },
        release_id="2026-03-22",
    )
    payloads = {
        "https://data.rcsb.org/rest/v1/core/entry/4hhb": _json(
            {
                "rcsb_id": "4hhb",
                "struct": {"title": "Hemoglobin"},
                "rcsb_entry_info": {"experimental_method": ["X-RAY DIFFRACTION"]},
                "rcsb_accession_info": {"initial_release_date": "1998-01-01"},
                "rcsb_entry_container_identifiers": {
                    "assembly_ids": ["1"],
                    "polymer_entity_ids": ["1", "2"],
                    "nonpolymer_entity_ids": [],
                },
            }
        ),
        "https://data.rcsb.org/rest/v1/core/polymer_entity/4hhb/1": _json(
            {
                "rcsb_id": "4hhb",
                "entity": {"id": "1", "pdbx_description": "Alpha chain"},
                "entity_poly": {
                    "type": "polypeptide(L)",
                    "pdbx_seq_one_letter_code_can": "MKT",
                    "rcsb_sample_sequence_length": 3,
                },
                "rcsb_polymer_entity_container_identifiers": {
                    "entry_id": "4HHB",
                    "entity_id": "1",
                    "auth_asym_ids": ["A"],
                    "uniprot_ids": ["P69905"],
                },
            }
        ),
        "https://data.rcsb.org/rest/v1/core/polymer_entity/4hhb/2": _json(
            {
                "rcsb_id": "4hhb",
                "entity": {"id": "2", "pdbx_description": "Beta chain"},
                "entity_poly": {
                    "type": "polypeptide(L)",
                    "pdbx_seq_one_letter_code_can": "MKT",
                    "rcsb_sample_sequence_length": 3,
                },
                "rcsb_polymer_entity_container_identifiers": {
                    "entry_id": "4HHB",
                    "entity_id": "2",
                    "auth_asym_ids": ["B"],
                    "uniprot_ids": ["P68871"],
                },
            }
        ),
        "https://data.rcsb.org/rest/v1/core/assembly/4hhb/1": _json(
            {
                "rcsb_id": "4hhb",
                "id": "1",
                "rcsb_assembly_container_identifiers": {
                    "entry_id": "4HHB",
                    "assembly_id": "1",
                    "auth_asym_ids": ["A", "B"],
                    "polymer_entity_ids": ["1", "2"],
                },
            }
        ),
        "https://www.ebi.ac.uk/pdbe/api/pdb/entry/uniprot_mapping/4hhb/1": _json(
            {"4hhb": {"1": {"mappings": []}}}
        ),
        "https://www.ebi.ac.uk/pdbe/api/pdb/entry/uniprot_mapping/4hhb/2": _json(
            {"4hhb": {"2": {"mappings": []}}}
        ),
        "https://www.ebi.ac.uk/pdbe/api/pdb/entry/chains/4hhb/1": _json(
            {"4hhb": {"1": [{"chain_id": "A"}]}}
        ),
        "https://www.ebi.ac.uk/pdbe/api/pdb/entry/chains/4hhb/2": _json(
            {"4hhb": {"2": [{"chain_id": "B"}]}}
        ),
    }

    result = acquire_rcsb_pdbe_snapshot(
        manifest,
        client=RCSBClient(),
        opener=_fake_opener(payloads),
    )

    assert result.status == SnapshotStatus.COMPLETE
    assert result.blockers == ()
    assert len(result.structure_bundles) == 1
    assert result.structure_bundles[0].pdb_id == "4HHB"
    assert result.structure_bundles[0].entry.title == "Hemoglobin"
    assert [asset.resource for asset in result.assets] == [
        "entry",
        "polymer_entity",
        "polymer_entity",
        "assembly",
        "uniprot_mapping",
        "chains",
        "uniprot_mapping",
        "chains",
    ]


def test_acquire_snapshot_blocks_on_network_failure():
    manifest = build_snapshot_manifest(["1abc"], release_id="2026-03-18")
    result = acquire_rcsb_pdbe_snapshot(
        manifest,
        client=RCSBClient(),
        opener=_fake_opener(
            {
                "https://data.rcsb.org/rest/v1/core/entry/1abc": URLError("network down"),
            }
        ),
    )

    assert result.status == SnapshotStatus.BLOCKED
    assert result.structure_bundles == ()
    assert result.assets == ()
    assert len(result.blockers) == 1
    assert result.blockers[0].code == SnapshotBlockerCode.NETWORK
    assert result.blockers[0].retryable is True


def test_acquire_snapshot_blocks_on_unpinned_manifest():
    manifest = SnapshotManifest(release_id=None, snapshot_id=None, pdb_ids=("1ABC",))

    result = acquire_rcsb_pdbe_snapshot(manifest)

    assert result.status == SnapshotStatus.BLOCKED
    assert result.blockers[0].code == SnapshotBlockerCode.MANIFEST_UNPINNED
    assert result.structure_bundles == ()
    assert result.assets == ()


def test_live_smoke_snapshot_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv(LIVE_SMOKE_ENV_VAR, raising=False)

    with pytest.raises(SnapshotSmokeDisabledError):
        run_live_smoke_snapshot("1ABC")


def test_live_smoke_snapshot_delegates_when_opted_in(monkeypatch):
    monkeypatch.setenv(LIVE_SMOKE_ENV_VAR, "1")
    payloads = {
        "https://data.rcsb.org/rest/v1/core/entry/1abc": _json(
            {
                "rcsb_id": "1abc",
                "struct": {"title": "Smoke structure"},
                "rcsb_entry_info": {"experimental_method": ["X-RAY DIFFRACTION"]},
                "rcsb_entry_container_identifiers": {
                    "assembly_ids": ["1"],
                    "polymer_entity_ids": ["1"],
                },
            }
        ),
        "https://data.rcsb.org/rest/v1/core/polymer_entity/1abc/1": _json(
            {
                "rcsb_id": "1abc",
                "entity": {"id": "1", "pdbx_description": "Smoke protein"},
                "entity_poly": {"type": "polypeptide(L)", "pdbx_seq_one_letter_code_can": "M"},
                "rcsb_polymer_entity_container_identifiers": {
                    "entity_id": "1",
                    "auth_asym_ids": ["A"],
                },
            }
        ),
        "https://data.rcsb.org/rest/v1/core/assembly/1abc/1": _json(
            {
                "rcsb_id": "1abc",
                "id": "1",
                "rcsb_assembly_container_identifiers": {
                    "assembly_id": "1",
                    "auth_asym_ids": ["A"],
                },
            }
        ),
        "https://www.ebi.ac.uk/pdbe/api/pdb/entry/uniprot_mapping/1abc/1": _json(
            {"1abc": {"1": {"mappings": []}}}
        ),
    }

    result = run_live_smoke_snapshot(
        "1abc",
        client=RCSBClient(),
        opener=_fake_opener(payloads),
        pdbe_opener=_fake_opener(payloads),
    )

    assert result.status == SnapshotStatus.COMPLETE
    assert result.blockers == ()
