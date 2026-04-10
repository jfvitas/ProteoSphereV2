from __future__ import annotations

from scripts.export_pdb_enrichment_harvest_preview import (
    build_pdb_enrichment_harvest_preview,
)
from scripts.export_pdb_enrichment_scrape_registry_preview import (
    build_pdb_enrichment_scrape_registry_preview,
)
from scripts.export_pdb_enrichment_validation_preview import (
    build_pdb_enrichment_validation_preview,
)
from scripts.export_structure_entry_context_preview import (
    build_structure_entry_context_preview,
)


def test_build_pdb_enrichment_scrape_registry_preview_collects_seed_structures() -> None:
    payload = build_pdb_enrichment_scrape_registry_preview(
        {
            "records": [
                {
                    "structure_id": "4HHB",
                    "protein_ref": "protein:P69905",
                    "chain_id": "A",
                }
            ]
        },
        {"best_pdb_id": "1Y01", "accession": "Q9NZD4", "chain_ids": ["B"]},
    )

    assert payload["status"] == "report_only"
    assert payload["summary"]["seed_structure_ids"] == ["1Y01", "4HHB"]
    assert payload["rows"][0]["structured_sources"][0]["source_id"] == "rcsb_core_entry"


def test_build_structure_entry_context_preview_harvests_structured_sources(
    monkeypatch,
) -> None:
    def fake_fetch_json(url: str, *, timeout: int = 60):  # noqa: ARG001
        if "core/entry/4HHB" in url:
            return {
                "struct": {"title": "Hemoglobin"},
                "exptl": [{"method": "X-RAY DIFFRACTION"}],
                "rcsb_entry_info": {
                    "resolution_combined": [1.74],
                    "assembly_count": 1,
                    "polymer_composition": "heteromeric protein",
                    "nonpolymer_bound_components": ["HEM"],
                },
                "rcsb_accession_info": {
                    "deposit_date": "1984-03-07T00:00:00+0000",
                    "initial_release_date": "1984-07-17T00:00:00+0000",
                    "revision_date": "2024-05-22T00:00:00+0000",
                },
                "citation": [{"pdbx_database_id_pub_med": 6726807}],
            }
        if "summary/4hhb" in url:
            return {
                "4hhb": [
                    {
                        "assemblies": [{"assembly_id": "1", "name": "tetramer"}],
                        "experimental_method": "X-RAY DIFFRACTION",
                    }
                ]
            }
        if "mappings/uniprot/4hhb" in url:
            return {
                "4hhb": {
                    "UniProt": {
                        "P69905": {"mappings": [{"chain_id": "A"}]},
                        "P68871": {"mappings": [{"chain_id": "B"}]},
                    }
                }
            }
        raise AssertionError(url)

    monkeypatch.setattr(
        "scripts.export_structure_entry_context_preview.fetch_json", fake_fetch_json
    )

    payload = build_structure_entry_context_preview(
        {"rows": [{"structure_id": "4HHB", "seed_accessions": ["P69905"]}]}
    )

    assert payload["status"] == "report_only_live_harvest"
    assert payload["summary"]["harvested_structure_count"] == 1
    assert payload["rows"][0]["mapped_uniprot_accessions"] == ["P68871", "P69905"]


def test_build_pdb_harvest_and_validation_previews_stay_aligned() -> None:
    harvest = build_pdb_enrichment_harvest_preview(
        {"rows": [{"structure_id": "4HHB", "structured_sources": [1, 2, 3]}]},
        {
            "rows": [
                {
                    "structure_id": "4HHB",
                    "seed_accessions": ["P69905"],
                    "mapped_uniprot_accessions": ["P69905"],
                    "nonpolymer_bound_components": ["HEM"],
                    "source_api_statuses": {
                        "rcsb_core_entry": "ok",
                        "pdbe_entry_summary": "ok",
                        "sifts_uniprot_mapping": "ok",
                    },
                }
            ]
        },
    )
    validation = build_pdb_enrichment_validation_preview(
        {"rows": [{"structure_id": "4HHB"}]},
        harvest,
    )

    assert harvest["rows"][0]["harvest_status"] == "complete"
    assert validation["status"] == "aligned"
    assert validation["issues"] == []
