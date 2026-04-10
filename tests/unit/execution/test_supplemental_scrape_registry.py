from __future__ import annotations

import pytest

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.supplemental_scrape_registry import (
    DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY,
    SupplementalScrapeRunRequest,
    build_default_supplemental_scrape_registry,
    plan_accession_supplemental_lanes,
    record_supplemental_scrape_run,
)


def test_default_registry_exposes_only_approved_target_allowlist() -> None:
    registry = build_default_supplemental_scrape_registry()

    assert registry.registry_id == "supplemental-scrape-registry:v1"
    assert registry.approved_target_ids == (
        "motif_interpro_entry",
        "motif_prosite_details",
        "motif_elm_class",
        "disorder_disprot_entry",
        "pathway_reactome_pathway",
        "related_rcsb_sequence_motif_search",
        "related_rcsb_3d_motif_search",
    )
    assert registry.get_target("disorder_disprot_entry").allowed_extraction_modes == (
        "html_document",
    )
    assert registry.get_target("related_rcsb_sequence_motif_search").allowed_extraction_modes == (
        "search_results",
    )
    assert registry.to_dict()["blocked_targets"][0]["blocker"]["code"] == "target_not_registered"


def test_record_supplemental_scrape_run_approves_pinned_release_and_records_provenance() -> None:
    request = SupplementalScrapeRunRequest(
        target_id="disorder_disprot_entry",
        extraction_mode="html_document",
        scope="P12345",
        source_release=SourceReleaseManifest(
            source_name="DisProt",
            release_version="9.8",
            release_date="2025-06-01",
            retrieval_mode="download",
            source_locator="https://disprot.org/api/search",
        ),
        provenance=("unit-test",),
        reproducibility_metadata=("parser=v1",),
    )

    result = record_supplemental_scrape_run(request, registry=DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY)

    assert result.succeeded is True
    assert result.status == "approved"
    assert result.reason == "supplemental_scrape_approved"
    assert result.target is not None
    assert result.target.source_name == "DisProt"
    assert result.provenance["source_release_manifest_id"] == request.source_release.manifest_id
    assert result.provenance["target_id"] == "disorder_disprot_entry"
    assert result.provenance["extraction_mode"] == "html_document"
    request_dict = result.request.to_dict()
    assert request_dict["source_release"]["manifest_id"] == request.source_release.manifest_id
    assert request_dict["source_release"]["release_version"] == "9.8"


def test_record_supplemental_scrape_run_blocks_unsupported_mode_and_broad_scope() -> None:
    registry = DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY

    mode_block = registry.plan_run(
        SupplementalScrapeRunRequest(
            target_id="pathway_reactome_pathway",
            extraction_mode="search_results",
            scope="R-HSA-199420",
            source_release=SourceReleaseManifest(
                source_name="Reactome",
                release_version="95",
                release_date="2025-12-09",
                retrieval_mode="download",
                source_locator="https://reactome.org/download-data",
            ),
        )
    )
    scope_block = registry.plan_run(
        SupplementalScrapeRunRequest(
            target_id="motif_elm_class",
            extraction_mode="html_document",
            scope="sitewide",
            source_release=SourceReleaseManifest(
                source_name="ELM",
                release_version="2025.03",
                release_date="2025-03-01",
                retrieval_mode="download",
                source_locator="https://elm.eu.org/",
            ),
        )
    )

    assert mode_block.status == "blocked"
    assert mode_block.blocker is not None
    assert mode_block.blocker.code == "unsupported_extraction_mode"
    assert scope_block.status == "blocked"
    assert scope_block.blocker is not None
    assert scope_block.blocker.code == "scope_too_broad"


def test_plan_accession_supplemental_lanes_keeps_fallback_explicit() -> None:
    registry = DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY
    results = plan_accession_supplemental_lanes(
        "P09105",
        [
            {
                "target_id": "motif_interpro_entry",
                "extraction_mode": "html_document",
                "source_release": {
                    "source_name": "InterPro",
                    "release_version": "108.0",
                    "release_date": "2026-01-01",
                    "retrieval_mode": "download",
                    "source_locator": "https://www.ebi.ac.uk/interpro/download/",
                },
            },
            {
                "target_id": "sitewide_crawl",
                "extraction_mode": "html_document",
                "source_release": {
                    "source_name": "InterPro",
                    "release_version": "108.0",
                    "release_date": "2026-01-01",
                    "retrieval_mode": "download",
                    "source_locator": "https://www.ebi.ac.uk/interpro/download/",
                },
            },
        ],
        registry=registry,
    )

    assert len(results) == 2
    assert results[0].status == "approved"
    assert results[0].request.scope == "P09105"
    assert results[0].target is not None
    assert results[0].target.target_id == "motif_interpro_entry"
    assert results[1].status == "blocked"
    assert results[1].blocker is not None
    assert results[1].blocker.code == "target_not_registered"


@pytest.mark.parametrize(
    ("scrape_request", "expected_code"),
    [
        (
            SupplementalScrapeRunRequest(
                target_id="sitewide_crawl",
                extraction_mode="html_document",
                scope="P12345",
                source_release=None,
            ),
            "target_not_registered",
        ),
        (
            SupplementalScrapeRunRequest(
                target_id="browser_walk",
                extraction_mode="html_document",
                scope="P12345",
                source_release=None,
            ),
            "target_not_registered",
        ),
        (
            SupplementalScrapeRunRequest(
                target_id="motif_interpro_entry",
                extraction_mode="html_document",
                scope="IPR000001",
                source_release=None,
            ),
            "missing_release_pin",
        ),
    ],
)
def test_record_supplemental_scrape_run_blocks_unregistered_targets_and_missing_release_pin(
    scrape_request: SupplementalScrapeRunRequest,
    expected_code: str,
) -> None:
    result = DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY.plan_run(scrape_request)

    assert result.status == "blocked"
    assert result.blocker is not None
    assert result.blocker.code == expected_code
    assert result.succeeded is False
