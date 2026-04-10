from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from connectors.rcsb.client import RCSBClient, RCSBClientError


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


def test_get_entry_uses_rcsb_data_api():
    client = RCSBClient()
    payload = json.dumps(
        {
            "entry": {
                "id": "1abc",
                "struct": {"title": "Example entry"},
            }
        }
    ).encode("utf-8")
    opener = _fake_opener(
        "https://data.rcsb.org/rest/v1/core/entry/1abc",
        payload,
    )

    data = client.get_entry("1ABC", opener=opener)

    assert data["entry"]["id"] == "1abc"
    assert data["entry"]["struct"]["title"] == "Example entry"


def test_get_entity_and_assembly_normalize_identifiers():
    client = RCSBClient()
    entity_payload = json.dumps({"entity": {"id": "2"}}).encode("utf-8")
    assembly_payload = json.dumps({"assembly": {"id": "1"}}).encode("utf-8")

    entity = client.get_entity(
        "2xyz",
        2,
        opener=_fake_opener(
            "https://data.rcsb.org/rest/v1/core/polymer_entity/2xyz/2",
            entity_payload,
        ),
    )
    assembly = client.get_assembly(
        "2xyz",
        "1",
        opener=_fake_opener(
            "https://data.rcsb.org/rest/v1/core/assembly/2xyz/1",
            assembly_payload,
        ),
    )

    assert entity["entity"]["id"] == "2"
    assert assembly["assembly"]["id"] == "1"


def test_get_mmcif_fetches_archive_text():
    client = RCSBClient()
    opener = _fake_opener(
        "https://files.rcsb.org/download/3def.cif",
        b"data_3def\n#\n",
    )

    text = client.get_mmcif("3DEF", opener=opener)

    assert "data_3def" in text


def test_invalid_identifier_is_rejected():
    client = RCSBClient()

    with pytest.raises(ValueError):
        client.get_entry("too-long")


def test_http_error_is_wrapped():
    class _ErrorResponse:
        def __call__(self, request, timeout=None):
            raise URLError("network down")

    client = RCSBClient()

    with pytest.raises(RCSBClientError):
        client.get_entry("4ghi", opener=_ErrorResponse())
