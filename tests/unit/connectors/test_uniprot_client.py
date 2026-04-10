from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from connectors.uniprot.client import UniProtClient, UniProtClientError


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


def test_get_entry_uses_uniprot_rest_api():
    client = UniProtClient()
    payload = json.dumps(
        {
            "primaryAccession": "P12345",
            "sequence": {"value": "MEEPQSDPSV"},
        }
    ).encode("utf-8")

    data = client.get_entry(
        "p12345",
        opener=_fake_opener(
            "https://rest.uniprot.org/uniprotkb/P12345.json",
            payload,
        ),
    )

    assert data["primaryAccession"] == "P12345"
    assert data["sequence"]["value"] == "MEEPQSDPSV"


def test_get_fasta_and_text_normalize_accession():
    client = UniProtClient()
    fasta = client.get_fasta(
        "a0a024rbg1",
        opener=_fake_opener(
            "https://rest.uniprot.org/uniprotkb/A0A024RBG1.fasta",
            b">sp|A0A024RBG1| Example protein\nMEEPQSDPSV\n",
        ),
    )
    text = client.get_text(
        "A0A024RBG1",
        opener=_fake_opener(
            "https://rest.uniprot.org/uniprotkb/A0A024RBG1.txt",
            b"ID   Example protein\n",
        ),
    )

    assert "A0A024RBG1" in fasta
    assert "Example protein" in text


def test_invalid_accession_is_rejected():
    client = UniProtClient()

    with pytest.raises(ValueError):
        client.get_entry("bad id")


def test_http_error_is_wrapped():
    class _ErrorResponse:
        def __call__(self, request, timeout=None):
            raise URLError("network down")

    client = UniProtClient()

    with pytest.raises(UniProtClientError):
        client.get_entry("P12345", opener=_ErrorResponse())


def test_json_parse_error_is_wrapped():
    client = UniProtClient()

    with pytest.raises(UniProtClientError):
        client.get_entry(
            "P12345",
            opener=_fake_opener("https://rest.uniprot.org/uniprotkb/P12345.json", b"not-json"),
        )
