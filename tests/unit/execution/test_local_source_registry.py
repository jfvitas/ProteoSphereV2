from __future__ import annotations

from pathlib import Path

from execution.acquire.local_source_registry import (
    LocalSourceDefinition,
    build_default_local_source_registry,
    build_local_source_registry,
)


def test_build_local_source_registry_partitions_present_and_missing_roots(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    present_root = storage_root / "data" / "catalog"
    present_root.mkdir(parents=True)
    missing_root = storage_root / "data" / "missing" / "archive.json"

    registry = build_local_source_registry(
        storage_root,
        (
            LocalSourceDefinition(
                source_name="catalog",
                category="metadata",
                candidate_roots=("data/catalog", "data/missing/archive.json"),
                likely_join_anchors=("P69905", "P69905", "P09105"),
                load_hints=("preload", "index", "lazy"),
                notes=("registry smoke",),
            ),
        ),
        registry_id="temp-registry",
        notes=("temp smoke",),
    )

    entry = registry.get("catalog")
    assert entry is not None
    assert entry.status == "partial"
    assert entry.present_roots == (str(present_root),)
    assert entry.missing_roots == (str(missing_root),)
    assert entry.candidate_roots == (str(present_root), str(missing_root))
    assert entry.likely_join_anchors == ("P69905", "P09105")
    assert entry.preload_worthy is True
    assert entry.index_worthy is True
    assert entry.lazy_import_worthy is True
    assert registry.by_category("meta") == (entry,)

    payload = registry.to_dict()
    assert payload["registry_id"] == "temp-registry"
    assert payload["entry_count"] == 1
    assert payload["present_entry_count"] == 0
    assert payload["partial_entry_count"] == 1
    assert payload["missing_entry_count"] == 0
    assert payload["entries"][0]["status"] == "partial"
    assert payload["entries"][0]["preload_worthy"] is True


def test_default_local_source_registry_reflects_workspace_inventory() -> None:
    registry = build_default_local_source_registry()

    assert registry.storage_root == str(Path(r"C:\Users\jfvit\Documents\bio-agent-lab"))
    assert registry.entry_count == len(registry.entries)

    catalog = registry.get("catalog")
    uniprot = registry.get("uniprot")
    bindingdb = registry.get("bindingdb")
    chembl = registry.get("chembl")
    biolip = registry.get("biolip")
    pdbbind_pl = registry.get("pdbbind_pl")
    pdbbind_pp = registry.get("pdbbind_pp")
    string = registry.get("string")
    model_studio = registry.get("model_studio")

    assert catalog is not None
    assert catalog.status == "present"
    assert catalog.preload_worthy is True

    assert uniprot is not None
    assert uniprot.status == "partial"
    assert any(
        path.endswith(r"data_sources\uniprot\uniprot_sprot.dat.gz")
        for path in uniprot.present_roots
    )
    assert any(
        path.endswith(r"data_sources\uniprot\uniprot_trembl_latest.gz")
        for path in uniprot.missing_roots
    )

    assert bindingdb is not None
    assert bindingdb.status == "present"
    assert bindingdb.index_worthy is True
    assert bindingdb.lazy_import_worthy is True

    assert chembl is not None
    assert chembl.status == "present"
    assert chembl.lazy_import_worthy is True

    assert biolip is not None
    assert biolip.status == "present"
    assert biolip.index_worthy is True
    assert biolip.lazy_import_worthy is True

    assert pdbbind_pl is not None
    assert pdbbind_pl.status == "partial"
    assert any(
        path.endswith(r"data_sources\pdbbind\P-L.tar.gz")
        for path in pdbbind_pl.present_roots
    )
    assert any(
        path.endswith(r"data_sources\pdbbind\index\INDEX_general_PL.2020R1.lst")
        for path in pdbbind_pl.present_roots
    )
    assert any(
        path.endswith(r"data_sources\pdbbind\P-L")
        for path in pdbbind_pl.missing_roots
    )

    assert pdbbind_pp is not None
    assert pdbbind_pp.status == "present"
    assert pdbbind_pp.index_worthy is True
    assert pdbbind_pp.lazy_import_worthy is True

    assert string is not None
    assert string.status == "missing"
    assert string.category == "interaction_network"

    assert model_studio is not None
    assert model_studio.status == "present"
    assert model_studio.index_worthy is True
    assert model_studio.lazy_import_worthy is True

    present_names = {entry.source_name for entry in registry.present_entries}
    partial_names = {entry.source_name for entry in registry.partial_entries}
    missing_names = {entry.source_name for entry in registry.missing_entries}

    assert {"catalog", "audit", "reports", "releases_test_v1", "splits"}.issubset(present_names)
    assert {"uniprot", "pdbbind_pl"}.issubset(partial_names)
    assert {
        "string",
        "biogrid",
        "intact",
        "sabio_rk",
        "prosite",
        "elm",
        "mega_motif_base",
        "motivated_proteins",
    }.issubset(missing_names)

    preload_names = {entry.source_name for entry in registry.preload_worthy_entries}
    index_names = {entry.source_name for entry in registry.index_worthy_entries}
    lazy_names = {entry.source_name for entry in registry.lazy_import_worthy_entries}

    assert {"catalog", "audit", "reports", "releases_test_v1", "splits"}.issubset(preload_names)
    assert {
        "uniprot",
        "bindingdb",
        "reactome",
        "interpro",
        "pfam",
        "cath",
        "scope",
    }.issubset(index_names)
    assert {"alphafold_db", "bindingdb", "biolip", "chembl", "model_studio"}.issubset(lazy_names)

    payload = registry.to_dict()
    assert payload["entry_count"] == len(registry.entries)
    assert payload["present_entry_count"] == len(registry.present_entries)
    assert payload["partial_entry_count"] == len(registry.partial_entries)
    assert payload["missing_entry_count"] == len(registry.missing_entries)
    assert payload["preload_worthy_entry_count"] == len(registry.preload_worthy_entries)
    assert payload["index_worthy_entry_count"] == len(registry.index_worthy_entries)
    assert payload["lazy_import_worthy_entry_count"] == len(registry.lazy_import_worthy_entries)
