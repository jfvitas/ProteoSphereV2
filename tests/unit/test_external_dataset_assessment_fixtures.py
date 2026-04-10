from __future__ import annotations

import json

from scripts.external_dataset_assessment_support import (
    REPO_ROOT,
    build_external_dataset_intake_contract_preview,
)

FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "external_dataset"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _required_keys(contract: dict, shape_id: str) -> tuple[list[str], list[str]]:
    shape = next(item for item in contract["accepted_shapes"] if item["shape_id"] == shape_id)
    return shape["required_top_level_keys"], shape["required_row_keys"]


def test_sample_dataset_manifest_matches_json_manifest_contract() -> None:
    contract = build_external_dataset_intake_contract_preview()
    required_top_level, required_row = _required_keys(contract, "json_manifest")
    fixture = _load_fixture("sample_dataset_manifest.json")

    for key in required_top_level:
        assert key in fixture
    assert fixture["manifest_id"] == "sample-external-dataset-v1"
    assert fixture["rows"]
    for row in fixture["rows"]:
        for key in required_row:
            assert key in row


def test_sample_folder_package_manifest_matches_folder_package_contract() -> None:
    contract = build_external_dataset_intake_contract_preview()
    required_top_level, required_row = _required_keys(contract, "folder_package_manifest")
    fixture = _load_fixture("sample_folder_package_manifest.json")

    for key in required_top_level:
        assert key in fixture
    assert fixture["rows"]
    for row in fixture["rows"]:
        for key in required_row:
            assert key in row
