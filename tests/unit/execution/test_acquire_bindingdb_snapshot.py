from __future__ import annotations

import json
from urllib.error import URLError

from execution.acquire.bindingdb_snapshot import (
    BindingDBSnapshotManifest,
    acquire_bindingdb_snapshot,
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
        assert request.headers["User-agent"] == "ProteoSphereV2-BindingDBClient/0.1"
        assert timeout == 30.0
        return _FakeResponse(payload)

    return opener


def test_acquire_bindingdb_snapshot_uses_manifest_and_preserves_provenance():
    manifest = BindingDBSnapshotManifest(
        snapshot_id="bindingdb-pinned-2026q1",
        query_kind="pdbs",
        query_values=("1abc", "2xyz"),
        release_pin="2026Q1",
        source_url="https://www.bindingdb.org/rwd/bind/info.jsp",
        archive_url="https://www.bindingdb.org/rwd/bind/chemsearch/marvin/Download.jsp",
        cutoff=100,
        identity=92,
    )
    payload = json.dumps(
        [
            {
                "BindingDB Reactant_set_id": "RS123",
                "BindingDB MonomerID": " 120095 ",
                "Ligand SMILES": " CCO ",
                "Ligand InChI Key": "InChIKey=ABCDEF",
                "Target Name": "Mitogen-activated protein kinase 1",
                "UniProtKB/SwissProt": "p28482;Q9XYZ1",
                "PDB": "1abc|2xyz",
                "Affinity Type": "Ki",
                "affinity_value_nM": "2.18E+4 nM",
                "Assay Description": "Competitive inhibition by fluorescence",
                "Publication Date": "2022-03-25",
                "BindingDB Curation Date": "2022-04-01",
            }
        ]
    ).encode("utf-8")

    result = acquire_bindingdb_snapshot(
        manifest,
        opener=_fake_opener(
            "https://www.bindingdb.org/rest/getLigandsByPDBs?pdb=1ABC%2C2XYZ&response=application%2Fjson&cutoff=100&identity=92",
            payload,
        ),
        acquired_on="2026-03-22",
    )

    assert result.status == "ok"
    assert result.reason == "bindingdb_snapshot_acquired"
    assert result.succeeded is True
    assert result.manifest.snapshot_id == "bindingdb-pinned-2026q1"
    assert result.provenance.source == "BindingDB"
    assert result.provenance.source_family == "assay"
    assert result.provenance.release_pin == "2026Q1"
    assert result.provenance.query_kind == "pdbs"
    assert result.provenance.query_values == ("1ABC", "2XYZ")
    assert result.provenance.endpoint == "getLigandsByPDBs"
    assert result.provenance.record_count == 1
    assert result.provenance.acquired_on == "2026-03-22"
    assert len(result.records) == 1
    assert result.records[0].reactant_set_id == "RS123"
    assert result.records[0].target_uniprot_ids == ("P28482", "Q9XYZ1")
    assert result.records[0].source == "getLigandsByPDBs"
    assert result.to_dict()["provenance"]["snapshot_id"] == "bindingdb-pinned-2026q1"


def test_acquire_bindingdb_snapshot_reports_manifest_blockers_without_network():
    manifest = {
        "snapshot_id": "bindingdb-pinned-2026q1",
        "query_kind": "uniprots",
        "uniprot_ids": ["P28482"],
        "availability": "blocked",
        "blocked_reason": "quarterly archive not published yet",
        "release_pin": "2026Q1",
    }

    result = acquire_bindingdb_snapshot(
        manifest,
        opener=_unexpected_opener,
        acquired_on="2026-03-22",
    )

    assert result.status == "blocked"
    assert result.reason == "quarterly archive not published yet"
    assert result.records == ()
    assert result.provenance.availability == "blocked"
    assert result.provenance.blocker_reason == "quarterly archive not published yet"
    assert result.provenance.record_count == 0


def test_acquire_bindingdb_snapshot_marks_empty_source_as_unavailable():
    manifest = {
        "snapshot_id": "bindingdb-pinned-2026q1",
        "query_kind": "uniprot",
        "uniprot_id": "P35355",
        "release_pin": "2026Q1",
    }

    result = acquire_bindingdb_snapshot(
        manifest,
        opener=_fake_opener(
            "https://www.bindingdb.org/rest/getLigandsByUniprot?uniprot=P35355&response=application%2Fjson",
            b"",
        ),
        acquired_on="2026-03-22",
    )

    assert result.status == "unavailable"
    assert result.reason == "bindingdb_no_assay_records"
    assert result.records == ()
    assert result.provenance.availability == "unavailable"
    assert result.provenance.record_count == 0


def test_acquire_bindingdb_snapshot_translates_request_failures_into_blockers():
    manifest = {
        "snapshot_id": "bindingdb-pinned-2026q1",
        "query_kind": "pdbs",
        "pdb_ids": ["1abc"],
        "release_pin": "2026Q1",
    }

    result = acquire_bindingdb_snapshot(
        manifest,
        opener=_failing_opener,
        acquired_on="2026-03-22",
    )

    assert result.status == "blocked"
    assert result.reason == "bindingdb_request_failed"
    assert result.records == ()
    assert "could not be completed" in result.provenance.error
    assert result.provenance.availability == "blocked"


def _unexpected_opener(*args, **kwargs):
    raise AssertionError("network should not be called for blocked manifests")


def _failing_opener(request, timeout=None):
    raise URLError("network down")
