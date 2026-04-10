from __future__ import annotations

from scripts.export_external_dataset_fixture_catalog_preview import build_fixture_catalog


def test_build_fixture_catalog_lists_expected_fixtures() -> None:
    payload = build_fixture_catalog()

    assert payload["artifact_id"] == "external_dataset_fixture_catalog_preview"
    assert payload["summary"]["fixture_count"] >= 5
    fixture_types = set(payload["summary"]["fixture_types"])
    assert "good_but_caveated" in fixture_types
    assert "mapping_conflict" in fixture_types
    assert "impossible_binding_normalization" in fixture_types
    assert "off_target_structure" in fixture_types
    assert "provenance_deficient" in fixture_types
