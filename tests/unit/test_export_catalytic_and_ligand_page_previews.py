from __future__ import annotations

from scripts.export_catalytic_site_context_preview import (
    build_catalytic_site_context_preview,
)
from scripts.export_ligand_context_scrape_registry_preview import (
    build_ligand_context_scrape_registry_preview,
)
from scripts.export_targeted_page_scrape_registry_preview import (
    build_targeted_page_scrape_registry_preview,
)


def test_build_catalytic_site_context_preview_filters_to_supported_accessions() -> None:
    payload = build_catalytic_site_context_preview(
        {
            "rows": [
                {
                    "accession": "P00387",
                    "protein_name": "NADH-cytochrome b5 reductase 3",
                    "ec_numbers": ["1.6.2.2"],
                    "comment_flags": {
                        "catalytic_activity": True,
                        "cofactor": True,
                    },
                    "source_url": "https://rest.uniprot.org/uniprotkb/P00387.json",
                }
            ]
        },
        {
            "rows": [
                {
                    "accession": "P00387",
                    "support_sources": ["sabio_rk"],
                    "support_source_count": 1,
                    "kinetics_support_status": "supported_now",
                },
                {
                    "accession": "P02042",
                    "support_sources": [],
                    "support_source_count": 0,
                    "kinetics_support_status": "unsupported_now",
                },
            ]
        },
    )

    assert payload["row_count"] == 1
    assert payload["rows"][0]["accession"] == "P00387"
    assert payload["rows"][0]["catalytic_activity_comment_present"] is True


def test_build_ligand_context_scrape_registry_preview_groups_by_accession() -> None:
    payload = build_ligand_context_scrape_registry_preview(
        {
            "rows": [
                {
                    "accession": "P00387",
                    "ligand_namespace": "PDB_CCD",
                    "ligand_ref": "HEM",
                    "readiness": "grounded preview-safe",
                },
                {
                    "accession": "Q9NZD4",
                    "ligand_namespace": "CHEMBL",
                    "ligand_ref": "CHEMBL25",
                    "readiness": "candidate-only non-governing",
                },
            ]
        }
    )

    assert payload["row_count"] == 2
    assert payload["rows"][0]["default_ingest_status"] == "candidate_only_non_governing"
    assert payload["summary"]["candidate_only_accession_count"] == 1


def test_build_targeted_page_scrape_registry_preview_stays_report_only() -> None:
    payload = build_targeted_page_scrape_registry_preview()

    assert payload["status"] == "report_only"
    assert payload["row_count"] == 2
    assert payload["rows"][0]["accession"] == "P04637"
    assert payload["truth_boundary"]["page_scraping_started"] is False
