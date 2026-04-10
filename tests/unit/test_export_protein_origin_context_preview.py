from __future__ import annotations

from scripts.export_protein_origin_context_preview import (
    build_protein_origin_context_preview,
)


def test_build_protein_origin_context_preview_harvests_uniprot_fields(
    monkeypatch,
) -> None:
    def fake_fetch_json(url: str, *, timeout: int = 60):  # noqa: ARG001
        assert url.endswith("/P31749.json")
        return {
            "entryType": "UniProtKB reviewed (Swiss-Prot)",
            "annotationScore": 5.0,
            "organism": {
                "scientificName": "Homo sapiens",
                "commonName": "Human",
                "taxonId": 9606,
                "lineage": ["Eukaryota", "Metazoa", "Homo"],
            },
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "AKT1"},
                    "ecNumbers": [{"value": "2.7.11.1"}],
                }
            },
            "genes": [{"geneName": {"value": "AKT1"}}],
            "proteinExistence": "1: Evidence at protein level",
            "comments": [
                {"commentType": "CATALYTIC ACTIVITY"},
                {"commentType": "COFACTOR"},
                {"commentType": "SUBCELLULAR LOCATION"},
            ],
        }

    monkeypatch.setattr(
        "scripts.export_protein_origin_context_preview.fetch_json", fake_fetch_json
    )

    payload = build_protein_origin_context_preview({"rows": [{"accession": "P31749"}]})

    row = payload["rows"][0]
    assert payload["summary"]["harvested_accession_count"] == 1
    assert row["reviewed"] is True
    assert row["ec_numbers"] == ["2.7.11.1"]
    assert row["comment_flags"]["catalytic_activity"] is True
    assert row["organism_scientific_name"] == "Homo sapiens"
