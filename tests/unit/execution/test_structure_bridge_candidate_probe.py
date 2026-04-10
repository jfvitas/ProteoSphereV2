from __future__ import annotations

import json
from urllib.error import URLError

from execution.acquire.structure_bridge_candidate_probe import (
    PROBE_KIND,
    SOURCE_NAME,
    StructureBridgeCandidateProbeManifest,
    build_structure_bridge_candidate_probe_manifest,
    probe_structure_bridge_candidates,
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


def test_build_manifest_normalizes_accession_targets() -> None:
    manifest = build_structure_bridge_candidate_probe_manifest(
        {
            "p68871": ["4hhb", "4HHB"],
            "P04637": ["1tsr", "1TSR"],
        },
        notes=("bridge-only",),
    )

    assert manifest.source_name == SOURCE_NAME
    assert manifest.notes == ("bridge-only",)
    assert manifest.candidate_accessions == ("P68871", "P04637")
    assert manifest.candidates[0].pdb_ids == ("4HHB",)
    assert manifest.candidates[1].pdb_ids == ("1TSR",)
    assert manifest.manifest_id.startswith("structure-bridge-candidate-probe:")
    assert len(manifest.manifest_id.split(":")) == 2


def test_probe_reports_bridge_only_positive_and_empty_hits() -> None:
    manifest = StructureBridgeCandidateProbeManifest.from_mapping(
        {
            "source_name": SOURCE_NAME,
            "accession_bridge_targets": {
                "P68871": ["4hhb"],
                "P31749": ["4hhb"],
            },
        }
    )
    payloads = {
        "https://data.rcsb.org/rest/v1/core/entry/4hhb": _json(
            {
                "rcsb_id": "4hhb",
                "struct": {"title": "Hemoglobin"},
                "rcsb_entry_container_identifiers": {
                    "polymer_entity_ids": ["1", "2"],
                    "assembly_ids": ["1"],
                },
            }
        ),
        "https://data.rcsb.org/rest/v1/core/polymer_entity/4hhb/1": _json(
            {
                "rcsb_polymer_entity_container_identifiers": {
                    "entity_id": "1",
                    "auth_asym_ids": ["A", "C"],
                    "uniprot_ids": ["P69905"],
                }
            }
        ),
        "https://data.rcsb.org/rest/v1/core/polymer_entity/4hhb/2": _json(
            {
                "rcsb_polymer_entity_container_identifiers": {
                    "entity_id": "2",
                    "auth_asym_ids": ["B", "D"],
                    "uniprot_ids": ["P68871"],
                }
            }
        ),
        "https://www.ebi.ac.uk/pdbe/api/mappings/uniprot/4hhb": _json(
            {
                "4hhb": {
                    "UniProt": {
                        "P69905": {
                            "mappings": [
                                {"entity_id": 1, "chain_id": "A", "struct_asym_id": "A"},
                                {"entity_id": 1, "chain_id": "C", "struct_asym_id": "C"},
                            ]
                        },
                        "P68871": {
                            "mappings": [
                                {"entity_id": 2, "chain_id": "B", "struct_asym_id": "B"},
                                {"entity_id": 2, "chain_id": "D", "struct_asym_id": "D"},
                            ]
                        },
                    }
                }
            }
        ),
    }

    result = probe_structure_bridge_candidates(manifest, opener=_fake_opener(payloads))

    assert result.status == "ok"
    assert result.reason == "structure_bridge_probe_completed"
    assert result.provenance["bridge_semantics"] == PROBE_KIND
    assert result.provenance["positive_hit_count"] == 1
    assert result.provenance["reachable_empty_count"] == 1
    assert len(result.records) == 2

    positive = next(record for record in result.records if record.accession == "P68871")
    empty = next(record for record in result.records if record.accession == "P31749")

    assert positive.bridge_state == "positive_hit"
    assert positive.bridge_kind == PROBE_KIND
    assert positive.canonical_id == "protein:P68871"
    assert positive.entry_title == "Hemoglobin"
    assert positive.entity_ids == ("1", "2")
    assert positive.chain_ids == ("A", "C", "B", "D")
    assert positive.matched_uniprot_ids == ("P68871",)
    assert positive.evidence_refs == (
        "https://data.rcsb.org/rest/v1/core/entry/4hhb",
        "https://data.rcsb.org/rest/v1/core/polymer_entity/4hhb/1",
        "https://data.rcsb.org/rest/v1/core/polymer_entity/4hhb/2",
        "https://www.ebi.ac.uk/pdbe/api/mappings/uniprot/4hhb",
    )
    assert all(".cif" not in ref for ref in positive.evidence_refs)

    assert empty.bridge_state == "reachable_empty"
    assert empty.bridge_kind == PROBE_KIND
    assert empty.matched_uniprot_ids == ()
    assert empty.canonical_id == "protein:P31749"
    assert empty.notes == ("bridge_lookup_reachable_but_accession_not_linked",)


def test_probe_blocks_without_bridge_targets() -> None:
    manifest = build_structure_bridge_candidate_probe_manifest({"P68871": ()})

    result = probe_structure_bridge_candidates(manifest)

    assert result.status == "blocked"
    assert result.reason == "structure_bridge_probe_blocked"
    assert result.records == ()
    assert "missing_bridge_targets" in result.blockers[0]


def test_probe_reports_unavailable_when_bridge_fetch_fails() -> None:
    manifest = build_structure_bridge_candidate_probe_manifest({"P68871": ["4HHB"]})

    def opener(request, timeout=None):
        raise URLError("network down")

    result = probe_structure_bridge_candidates(manifest, opener=opener)

    assert result.status == "unavailable"
    assert result.records == ()
    assert "could not be completed" in result.unavailable_reason
