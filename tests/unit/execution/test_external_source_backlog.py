from __future__ import annotations

from execution.acquire.external_source_backlog import (
    DEFAULT_EXTERNAL_SOURCE_BACKLOG,
    build_external_source_backlog,
)


def test_default_external_source_backlog_exposes_primary_and_related_priorities() -> None:
    manifest = DEFAULT_EXTERNAL_SOURCE_BACKLOG

    assert manifest.manifest_id == "external-source-backlog:v1"
    assert manifest.entry_count == 12
    assert len(manifest.primary_entries) == 8
    assert len(manifest.related_entries) == 4

    intact = manifest.get_entry("IntAct")
    biogrid = manifest.get_entry("BioGRID")
    string = manifest.get_entry("STRING")
    sabio_rk = manifest.get_entry("SABIO-RK")
    prosite = manifest.get_entry("PROSITE")
    elm = manifest.get_entry("ELM")
    mega = manifest.get_entry("MegaMotifBase")
    motivated = manifest.get_entry("Motivated Proteins")
    rcsb_bridge = manifest.get_entry("RCSB/PDBe bridge")
    disprot = manifest.get_entry("DisProt")
    emdb = manifest.get_entry("EMDB")
    msa = manifest.get_entry("Evolutionary / MSA")

    assert intact is not None
    assert biogrid is not None
    assert string is not None
    assert sabio_rk is not None
    assert prosite is not None
    assert elm is not None
    assert mega is not None
    assert motivated is not None
    assert rcsb_bridge is not None
    assert disprot is not None
    assert emdb is not None
    assert msa is not None

    assert intact.priority == 1
    assert biogrid.priority == 2
    assert string.priority == 3
    assert sabio_rk.priority == 4
    assert prosite.priority == 5
    assert elm.priority == 6
    assert mega.priority == 7
    assert motivated.priority == 8
    assert rcsb_bridge.priority == 9
    assert disprot.priority == 10
    assert emdb.priority == 11
    assert msa.priority == 12

    assert intact.category == "interaction_network"
    assert biogrid.category == "interaction_network"
    assert sabio_rk.category == "assay"
    assert prosite.category == "motif"
    assert elm.category == "motif"
    assert rcsb_bridge.category == "bridge"
    assert disprot.category == "disorder"
    assert emdb.category == "structure_depth"
    assert msa.category == "evolutionary"

    assert intact.acquisition_mode == "release_download"
    assert biogrid.acquisition_mode == "release_download"
    assert string.acquisition_mode == "targeted_query"
    assert sabio_rk.acquisition_mode == "accession_scoped_query"
    assert prosite.acquisition_mode == "release_download"
    assert elm.acquisition_mode == "export_download"
    assert mega.acquisition_mode == "release_download"
    assert motivated.acquisition_mode == "release_download"
    assert rcsb_bridge.acquisition_mode == "bridge_query"
    assert disprot.acquisition_mode == "api_query"
    assert emdb.acquisition_mode == "release_download"
    assert msa.acquisition_mode == "analysis_job"

    assert intact.missing_state == "missing_local"
    assert intact.blocker_state == "needs_acquisition"
    assert string.blocker_state == "needs_live_probe"
    assert sabio_rk.blocker_state == "needs_live_probe"
    assert rcsb_bridge.blocker_state == "needs_live_probe"
    assert emdb.blocker_state == "needs_acquisition"
    assert msa.blocker_state == "needs_live_probe"

    assert intact.expected_join_anchors == ("P69905", "P09105")
    assert biogrid.expected_join_anchors == ("P69905", "P09105")
    assert string.expected_join_anchors == ("P69905", "P09105")
    assert sabio_rk.expected_join_anchors == ("P31749",)
    assert prosite.expected_join_anchors == ("P69905",)
    assert elm.expected_join_anchors == ("P69905",)
    assert mega.expected_join_anchors == ("P69905",)
    assert motivated.expected_join_anchors == ("P69905",)
    assert rcsb_bridge.expected_join_anchors == ("1FC2", "10JU")
    assert disprot.expected_join_anchors == ("P69905",)
    assert emdb.expected_join_anchors == ("1FC2", "10JU")
    assert msa.expected_join_anchors == ("P69905", "P68871")


def test_external_source_backlog_to_dict_is_machine_readable() -> None:
    payload = DEFAULT_EXTERNAL_SOURCE_BACKLOG.to_dict()

    assert payload["manifest_id"] == "external-source-backlog:v1"
    assert payload["entry_count"] == 12
    assert payload["primary_entry_count"] == 8
    assert payload["related_entry_count"] == 4
    assert payload["category_counts"]["interaction_network"] == 3
    assert payload["acquisition_mode_counts"]["release_download"] == 6
    assert payload["missing_state_counts"]["missing_local"] == 12
    assert payload["blocker_state_counts"]["needs_live_probe"] >= 1
    assert payload["entries"][0]["source_name"] == "IntAct"
    assert payload["entries"][0]["scope"] == "primary"
    assert payload["entries"][0]["evidence_refs"][0] == "docs/reports/source_intact.md"


def test_external_source_backlog_can_select_a_subset() -> None:
    manifest = build_external_source_backlog(source_names=("BioGRID", "ELM"))

    assert manifest.entry_count == 2
    assert [entry.source_name for entry in manifest.entries] == ["BioGRID", "ELM"]
    assert manifest.primary_entries[0].source_name == "BioGRID"
    assert manifest.get_entry("ELM") is not None
    assert manifest.by_category("motif")[0].source_name == "ELM"


def test_external_source_backlog_rejects_unknown_sources() -> None:
    try:
        build_external_source_backlog(source_names=("NotARealSource",))
    except KeyError as exc:
        assert "NotARealSource" in str(exc)
    else:
        raise AssertionError("expected KeyError for unknown source name")
