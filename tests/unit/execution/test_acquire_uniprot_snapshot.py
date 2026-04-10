from __future__ import annotations

from connectors.uniprot.client import UniProtClientError
from execution.acquire.supplemental_scrape_registry import (
    DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY,
)
from execution.acquire.uniprot_snapshot import acquire_uniprot_snapshot


class _FakeClient:
    def __init__(
        self,
        entries: dict[str, dict[str, object]] | None = None,
        *,
        error: Exception | None = None,
    ):
        self.entries = entries or {}
        self.error = error
        self.requests: list[tuple[str, object]] = []

    def get_entry(self, accession: str, opener=None):
        self.requests.append((accession, opener))
        if self.error is not None:
            raise self.error
        return self.entries[accession]


def test_acquire_uniprot_snapshot_records_release_proteome_and_provenance() -> None:
    client = _FakeClient(
        {
            "P12345": {
                "primaryAccession": "P12345",
                "uniProtkbId": "ABC_HUMAN",
                "entryType": "UniProtKB reviewed (Swiss-Prot)",
                "proteinDescription": {
                    "recommendedName": {"fullName": {"value": "Example protein"}},
                },
                "genes": [
                    {
                        "geneName": {"value": "ABC"},
                    }
                ],
                "organism": {"scientificName": "Homo sapiens"},
                "sequence": {"value": "MEEPQSDPSV", "length": 10},
            }
        }
    )
    manifest = {
        "source": "UniProt",
        "release": "2026_02",
        "release_date": "2026-03-01",
        "proteome_id": "UP000005640",
        "proteome_name": "Homo sapiens",
        "proteome_reference": True,
        "proteome_taxon_id": 9606,
        "accessions": ["P12345"],
        "manifest_id": "uniprot:identity:human",
        "provenance": {
            "source_ids": ["raw/uniprot/2026_02/human.json"],
            "acquired_at": "2026-03-22T12:00:00+00:00",
            "parser_version": "1.0",
        },
    }

    result = acquire_uniprot_snapshot(manifest, client=client)

    assert result.status == "ready"
    assert result.contract is not None
    assert result.contract.release == "2026_02"
    assert result.contract.proteome_id == "UP000005640"
    assert result.contract.accessions == ("P12345",)
    assert result.snapshot is not None
    assert result.snapshot.source_release["manifest_id"] == "uniprot:identity:human"
    assert result.snapshot.proteome["proteome_reference"] is True
    assert result.snapshot.provenance["record_count"] == 1
    assert result.snapshot.provenance["supplemental_lane_count"] == 0
    assert result.snapshot.records[0].sequence.accession == "P12345"
    assert result.snapshot.records[0].sequence.protein_name == "Example protein"
    assert result.snapshot.records[0].provenance["proteome_id"] == "UP000005640"
    assert result.snapshot.records[0].supplemental_lanes == ()
    assert result.provenance["source_ids"] == ("raw/uniprot/2026_02/human.json",)
    assert client.requests == [("P12345", None)]

    payload = result.to_dict()
    assert payload["status"] == "ready"
    assert payload["snapshot"]["records"][0]["sequence"]["accession"] == "P12345"
    assert payload["snapshot"]["source_release"]["release"] == "2026_02"


def test_acquire_uniprot_snapshot_blocks_when_manifest_lacks_required_metadata() -> None:
    client = _FakeClient()
    manifest = {
        "source": "UniProt",
        "provenance": {"source_ids": ["raw/uniprot/missing-release.json"]},
    }

    result = acquire_uniprot_snapshot(manifest, client=client)

    assert result.status == "blocked"
    assert result.contract is None
    assert result.snapshot is None
    assert result.missing_fields == ("release", "release_date", "proteome_id", "accessions")
    assert "missing required fields" in result.blocker_reason
    assert client.requests == []


def test_acquire_uniprot_snapshot_reports_unavailable_client_failures_honestly() -> None:
    client = _FakeClient(error=UniProtClientError("UniProt request could not be completed"))
    manifest = {
        "source": "UniProt",
        "release": "2026_02",
        "release_date": "2026-03-01",
        "proteome_id": "UP000005640",
        "accessions": ["P12345"],
        "provenance": {"source_ids": ["raw/uniprot/2026_02/human.json"]},
    }

    result = acquire_uniprot_snapshot(manifest, client=client)

    assert result.status == "unavailable"
    assert result.contract is not None
    assert result.snapshot is None
    assert "unavailable" in result.unavailable_reason
    assert "UniProt request could not be completed" in result.unavailable_reason
    assert client.requests == [("P12345", None)]


def test_acquire_uniprot_snapshot_blocks_invalid_accessions_before_fetch() -> None:
    client = _FakeClient()
    manifest = {
        "source": "UniProt",
        "release": "2026_02",
        "release_date": "2026-03-01",
        "proteome_id": "UP000005640",
        "accessions": ["bad id"],
        "provenance": {"source_ids": ["raw/uniprot/2026_02/human.json"]},
    }

    result = acquire_uniprot_snapshot(manifest, client=client)

    assert result.status == "blocked"
    assert result.invalid_accessions == ("BAD ID",)
    assert "invalid accessions" in result.blocker_reason
    assert client.requests == []


def test_acquire_uniprot_snapshot_attaches_supplemental_lanes_for_verified_rows() -> None:
    client = _FakeClient(
        {
            "P09105": {
                "primaryAccession": "P09105",
                "uniProtkbId": "Q9UCM0_HUMAN",
                "entryType": "UniProtKB reviewed (Swiss-Prot)",
                "proteinDescription": {
                    "recommendedName": {"fullName": {"value": "Supplemental protein 1"}},
                },
                "genes": [
                    {
                        "geneName": {"value": "SUP1"},
                    }
                ],
                "organism": {"scientificName": "Homo sapiens"},
                "sequence": {"value": "MEEPQSDPSV", "length": 10},
            },
            "Q9UCM0": {
                "primaryAccession": "Q9UCM0",
                "uniProtkbId": "Q9UCM0_HUMAN",
                "entryType": "UniProtKB reviewed (Swiss-Prot)",
                "proteinDescription": {
                    "recommendedName": {"fullName": {"value": "Supplemental protein 2"}},
                },
                "genes": [
                    {
                        "geneName": {"value": "SUP2"},
                    }
                ],
                "organism": {"scientificName": "Homo sapiens"},
                "sequence": {"value": "MEEPQSDPSV", "length": 10},
            },
        }
    )
    manifest = {
        "source": "UniProt",
        "release": "2026_02",
        "release_date": "2026-03-01",
        "proteome_id": "UP000005640",
        "proteome_name": "Homo sapiens",
        "proteome_reference": True,
        "proteome_taxon_id": 9606,
        "accessions": ["P09105", "Q9UCM0"],
        "supplemental_requests": {
            "P09105": [
                {
                    "target_id": "motif_interpro_entry",
                    "extraction_mode": "html_document",
                    "scope": "P09105",
                    "source_release": {
                        "source_name": "InterPro",
                        "release_version": "108.0",
                        "release_date": "2026-01-01",
                        "retrieval_mode": "download",
                        "source_locator": "https://www.ebi.ac.uk/interpro/download/",
                    },
                }
            ],
            "Q9UCM0": [
                {
                    "target_id": "pathway_reactome_pathway",
                    "extraction_mode": "html_document",
                    "scope": "Q9UCM0",
                    "source_release": {
                        "source_name": "Reactome",
                        "release_version": "95",
                        "release_date": "2025-12-09",
                        "retrieval_mode": "download",
                        "source_locator": "https://reactome.org/download-data",
                    },
                },
                {
                    "target_id": "browser_walk",
                    "extraction_mode": "html_document",
                    "scope": "Q9UCM0",
                    "source_release": {
                        "source_name": "Reactome",
                        "release_version": "95",
                        "release_date": "2025-12-09",
                        "retrieval_mode": "download",
                        "source_locator": "https://reactome.org/download-data",
                    },
                },
            ],
        },
        "provenance": {"source_ids": ["raw/uniprot/2026_02/human.json"]},
    }

    result = acquire_uniprot_snapshot(
        manifest,
        client=client,
        supplemental_registry=DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY,
    )

    assert result.status == "ready"
    assert result.snapshot is not None
    assert result.snapshot.provenance["supplemental_lane_count"] == 3
    assert result.snapshot.provenance["supplemental_lane_approved_count"] == 2
    assert result.snapshot.provenance["supplemental_lane_blocked_count"] == 1

    first_record, second_record = result.snapshot.records
    assert first_record.accession == "P09105"
    assert len(first_record.supplemental_lanes) == 1
    assert first_record.supplemental_lanes[0]["status"] == "approved"
    assert first_record.supplemental_lanes[0]["target"]["target_id"] == (
        "motif_interpro_entry"
    )
    assert first_record.provenance["supplemental_lane_count"] == 1
    assert first_record.provenance["supplemental_lane_approved_count"] == 1
    assert first_record.provenance["supplemental_lane_blocked_count"] == 0

    assert second_record.accession == "Q9UCM0"
    assert [lane["status"] for lane in second_record.supplemental_lanes] == [
        "approved",
        "blocked",
    ]
    assert second_record.supplemental_lanes[0]["request"]["scope"] == "Q9UCM0"
    assert second_record.supplemental_lanes[1]["blocker"]["code"] == "target_not_registered"
    assert second_record.provenance["supplemental_lane_count"] == 2
    assert second_record.provenance["supplemental_lane_approved_count"] == 1
    assert second_record.provenance["supplemental_lane_blocked_count"] == 1
