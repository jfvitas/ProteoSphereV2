from __future__ import annotations

import json
from urllib.error import URLError
from urllib.parse import quote

from execution.acquire.disprot_candidate_probe import (
    DEFAULT_DISPROT_API_BASE_URL,
    DisProtCandidateProbeManifest,
    build_disprot_candidate_probe_manifest,
    probe_disprot_candidate,
    probe_disprot_candidates,
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
        assert request.headers["User-agent"] == "ProteoSphereV2-DisProtCandidateProbe/0.1"
        payload = payloads[request.full_url]
        if isinstance(payload, Exception):
            raise payload
        return _FakeResponse(payload)

    return opener


def _probe_url(accession: str, api_base_url: str = DEFAULT_DISPROT_API_BASE_URL) -> str:
    return f"{api_base_url.rstrip('/')}/search?acc={quote(accession)}"


def test_manifest_normalizes_accessions_and_preserves_metadata() -> None:
    manifest = build_disprot_candidate_probe_manifest(
        [" p69905 ", "P69905", "p04637"],
        metadata={"lane": "cohort"},
    )

    assert isinstance(manifest, DisProtCandidateProbeManifest)
    assert manifest.accessions == ("P69905", "P04637")
    assert manifest.metadata["lane"] == "cohort"
    assert manifest.to_dict()["source_name"] == "DisProt"


def test_probe_distinguishes_positive_hits_from_reachable_empty() -> None:
    manifest = build_disprot_candidate_probe_manifest(["P69905", "P04637"])
    payloads = {
        _probe_url("P69905"): _json(
            {
                "data": [
                    {
                        "acc": "P69905",
                        "disprot_id": "DP00001",
                        "sequence": "MGLSDGEWQLVLNVWGKVEADIPGHGQEVLIRLFKG",
                    }
                ],
                "size": 1,
            }
        ),
        _probe_url("P04637"): _json({"data": [], "size": 0}),
    }

    result = probe_disprot_candidates(manifest, opener=_fake_opener(payloads))

    assert result.positive_accessions == ("P69905",)
    assert result.reachable_empty_accessions == ("P04637",)
    assert result.blocked_accessions == ()
    assert result.records[0].status == "positive_hit"
    assert result.records[0].returned_record_count == 1
    assert result.records[0].matched_record_count == 1
    assert result.records[0].matched_disprot_ids == ("DP00001",)
    assert result.records[0].matched_accessions == ("P69905",)
    assert result.records[1].status == "reachable_empty"
    assert result.records[1].returned_record_count == 0
    assert result.records[1].matched_record_count == 0
    assert result.records[1].blocker_reason == ""

    summary = result.to_dict()["summary"]
    assert summary["positive_count"] == 1
    assert summary["reachable_empty_count"] == 1
    assert summary["blocked_count"] == 0


def test_probe_marks_network_failure_blocked_without_negative_labeling() -> None:
    manifest = build_disprot_candidate_probe_manifest(["P69905"])
    result = probe_disprot_candidate(
        "P69905",
        opener=_fake_opener({_probe_url("P69905"): URLError("network down")}),
    )

    assert result.blocked_accessions == ("P69905",)
    assert result.positive_accessions == ()
    assert result.reachable_empty_accessions == ()

    record = result.records[0]
    assert record.status == "blocked"
    assert record.returned_record_count == 0
    assert record.matched_record_count == 0
    assert "request failed" in record.blocker_reason
    assert manifest.accessions == ("P69905",)
