from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from connectors.bindingdb.client import BindingDBClient, BindingDBClientError


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


def test_get_ligands_by_pdbs_builds_json_request():
    client = BindingDBClient()
    payload = json.dumps(
        [
            {
                "pdb": "1ABC",
                "monomerID": 123,
            }
        ]
    ).encode("utf-8")

    data = client.get_ligands_by_pdbs(
        ["1abc", "2xyz"],
        cutoff=100,
        identity=92,
        opener=_fake_opener(
            "https://www.bindingdb.org/rest/getLigandsByPDBs?pdb=1ABC%2C2XYZ&response=application%2Fjson&cutoff=100&identity=92",
            payload,
        ),
    )

    assert data[0]["pdb"] == "1ABC"
    assert data[0]["monomerID"] == 123


def test_get_ligands_by_uniprot_uses_semicolon_cutoff():
    client = BindingDBClient()
    payload = json.dumps({"records": []}).encode("utf-8")

    data = client.get_ligands_by_uniprot(
        "p35355",
        cutoff=100,
        opener=_fake_opener(
            "https://www.bindingdb.org/rest/getLigandsByUniprot?uniprot=P35355%3B100&response=application%2Fjson",
            payload,
        ),
    )

    assert data == {"records": []}


def test_get_target_by_compound_returns_empty_string_for_blank_response():
    client = BindingDBClient()

    data = client.get_target_by_compound(
        "CCO",
        opener=_fake_opener(
            "https://www.bindingdb.org/rest/getTargetByCompound?smiles=CCO&response=application%2Fjson",
            b"",
        ),
    )

    assert data == ""


def test_invalid_identifier_is_rejected():
    client = BindingDBClient()

    with pytest.raises(ValueError):
        client.get_ligands_by_pdbs("too-long")


def test_network_failure_is_wrapped():
    class _ErrorOpener:
        def __call__(self, request, timeout=None):
            raise URLError("network down")

    client = BindingDBClient()

    with pytest.raises(BindingDBClientError):
        client.get_ligands_by_uniprots("P00176", opener=_ErrorOpener())
