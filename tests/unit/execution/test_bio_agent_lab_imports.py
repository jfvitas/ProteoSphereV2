from __future__ import annotations

from pathlib import Path

import pytest

from execution.acquire.bio_agent_lab_imports import (
    BioAgentLabImportSource,
    build_bio_agent_lab_import_manifest,
)
from execution.acquire.local_source_registry import (
    LocalSourceDefinition,
    build_local_source_registry,
)


def test_build_bio_agent_lab_import_manifest_projects_explicit_join_keys_and_provenance(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    (storage_root / "data" / "catalog").mkdir(parents=True)
    (storage_root / "data_sources" / "uniprot").mkdir(parents=True)
    uniprot_root = storage_root / "data_sources" / "uniprot" / "uniprot_sprot.dat.gz"
    uniprot_root.write_text("stub", encoding="utf-8")

    registry = build_local_source_registry(
        storage_root,
        (
            LocalSourceDefinition(
                source_name="catalog",
                category="metadata",
                candidate_roots=("data/catalog",),
                likely_join_anchors=("P69905",),
                load_hints=("preload",),
                notes=("catalog root",),
            ),
            LocalSourceDefinition(
                source_name="uniprot",
                category="sequence",
                candidate_roots=(
                    "data_sources/uniprot/uniprot_sprot.dat.gz",
                    "data_sources/uniprot/uniprot_trembl_latest.gz",
                ),
                likely_join_anchors=("P69905", "P09105"),
                load_hints=("index",),
                notes=("sequence snapshot",),
            ),
        ),
        registry_id="temp-registry",
    )

    manifest = build_bio_agent_lab_import_manifest(
        storage_root,
        registry=registry,
        source_names=("catalog", "uniprot"),
        manifest_id="temp-manifest",
        notes=("temp import manifest",),
    )

    assert manifest.manifest_id == "temp-manifest"
    assert manifest.registry_id == "temp-registry"
    assert manifest.storage_root == str(storage_root)
    assert manifest.source_count == 2
    assert manifest.present_source_count == 1
    assert manifest.partial_source_count == 1
    assert manifest.missing_source_count == 0

    catalog = manifest.get_source("catalog")
    uniprot = manifest.get_source("uniprot")
    assert catalog is not None
    assert uniprot is not None
    assert isinstance(catalog, BioAgentLabImportSource)
    assert catalog.join_keys == ("P69905",)
    assert catalog.provenance["registry_id"] == "temp-registry"
    assert catalog.provenance["present_root_count"] == 1
    assert uniprot.join_keys == ("P69905", "P09105")
    assert uniprot.provenance["missing_root_count"] == 1
    assert manifest.join_key_index == {
        "P69905": ("catalog", "uniprot"),
        "P09105": ("uniprot",),
    }

    payload = manifest.to_dict()
    assert payload["source_count"] == 2
    assert payload["join_key_index"]["P69905"] == ["catalog", "uniprot"]
    assert payload["sources"][1]["missing_roots"] == [
        str(storage_root / "data_sources" / "uniprot" / "uniprot_trembl_latest.gz")
    ]


def test_default_bio_agent_lab_import_manifest_reflects_real_workspace() -> None:
    manifest = build_bio_agent_lab_import_manifest()

    assert manifest.storage_root == str(Path(r"C:\Users\jfvit\Documents\bio-agent-lab"))
    assert manifest.source_count == len(manifest.sources)
    assert manifest.get_source("catalog") is not None
    assert manifest.get_source("string") is not None

    catalog = manifest.get_source("catalog")
    uniprot = manifest.get_source("uniprot")
    bindingdb = manifest.get_source("bindingdb")
    pdbbind_pp = manifest.get_source("pdbbind_pp")
    string = manifest.get_source("string")

    assert catalog is not None and catalog.status == "present"
    assert uniprot is not None and uniprot.status == "partial"
    assert bindingdb is not None and bindingdb.status == "present"
    assert pdbbind_pp is not None and pdbbind_pp.status == "present"
    assert string is not None and string.status == "missing"

    assert "P69905" in manifest.join_key_index
    assert "uniprot" in manifest.join_key_index.get("P69905", ())
    assert "bindingdb" in manifest.join_key_index.get("1BB0", ())

    missing_source_names = {
        source.source_name for source in manifest.sources if source.status == "missing"
    }
    assert {
        "string",
        "biogrid",
        "intact",
        "sabio_rk",
        "prosite",
        "elm",
        "mega_motif_base",
        "motivated_proteins",
    }.issubset(missing_source_names)

    payload = manifest.to_dict()
    assert payload["registry_id"] == "bio-agent-lab-local-source-registry:v1"
    assert payload["source_count"] == len(manifest.sources)
    assert payload["present_source_count"] >= 5
    assert payload["partial_source_count"] >= 1
    assert payload["missing_source_count"] >= 1


def test_build_bio_agent_lab_import_manifest_rejects_unknown_sources(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    storage_root.mkdir()

    with pytest.raises(KeyError, match="source_name not found"):
        build_bio_agent_lab_import_manifest(
            storage_root,
            source_names=("not_a_real_source",),
        )
