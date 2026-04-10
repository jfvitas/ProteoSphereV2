from __future__ import annotations

from scripts.export_motif_domain_compact_preview_family import (
    build_motif_domain_compact_preview_family,
)


def test_build_motif_domain_compact_preview_family_filters_expected_namespaces() -> None:
    dictionary_preview = {
        "rows": [
            {
                "dictionary_id": "dictionary:domain:InterPro:IPR0001",
                "reference_kind": "domain",
                "namespace": "InterPro",
                "identifier": "IPR0001",
                "supporting_record_count": 2,
            },
            {
                "dictionary_id": "dictionary:domain:Pfam:PF0001",
                "reference_kind": "domain",
                "namespace": "Pfam",
                "identifier": "PF0001",
                "supporting_record_count": 1,
            },
            {
                "dictionary_id": "dictionary:motif:PROSITE:PS0001",
                "reference_kind": "motif",
                "namespace": "PROSITE",
                "identifier": "PS0001",
                "supporting_record_count": 3,
            },
            {
                "dictionary_id": "dictionary:cross_reference:IntAct:EBI-1",
                "reference_kind": "cross_reference",
                "namespace": "IntAct",
                "identifier": "EBI-1",
                "supporting_record_count": 5,
            },
            {
                "dictionary_id": "dictionary:motif:ELM:ELM0001",
                "reference_kind": "motif",
                "namespace": "ELM",
                "identifier": "ELM0001",
                "supporting_record_count": 1,
            },
        ]
    }

    payload = build_motif_domain_compact_preview_family(dictionary_preview)

    assert payload["status"] == "complete"
    assert payload["row_count"] == 3
    assert [row["namespace"] for row in payload["rows"]] == ["InterPro", "PROSITE", "Pfam"]
    assert payload["summary"]["namespace_count"] == 3
    assert payload["summary"]["reference_kind_counts"] == {"domain": 2, "motif": 1}
    assert payload["summary"]["supporting_record_count"] == 6
    assert payload["truth_boundary"]["ready_for_bundle_preview"] is True
    assert payload["truth_boundary"]["biological_content_family"] is True
    assert payload["truth_boundary"]["governing_for_split_or_leakage"] is False
