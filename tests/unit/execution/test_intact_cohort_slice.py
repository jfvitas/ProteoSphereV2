from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.intact_cohort_slice import (
    materialize_intact_cohort_slice,
    materialize_intact_cohort_slice_from_artifacts,
)
from execution.acquire.intact_snapshot import acquire_intact_snapshot
from execution.analysis.cohort_uplift_selector import (
    build_cohort_uplift_selection_from_artifacts,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def _selection():
    return build_cohort_uplift_selection_from_artifacts(
        RESULTS_DIR / "usefulness_review.json",
        RESULTS_DIR / "training_packet_audit.json",
    )


def _fake_opener(expected_url: str, payload: bytes):
    def opener(request, timeout=None):
        assert request.full_url == expected_url
        assert timeout == 30.0
        return _FakeResponse(payload)

    return opener


def _snapshot_result():
    manifest = SourceReleaseManifest(
        source_name="IntAct",
        release_version="live-smoke",
        release_date="2026-03-22",
        retrieval_mode="query",
        source_locator=(
            "https://www.ebi.ac.uk/Tools/webservices/psicquic/intact/webservices/current/"
            "search/query/id:P04637?format=tab25&firstResult=0&maxResults=3"
        ),
        provenance=("live-query", "psicquic", "intact"),
    )
    payload = (
        b"Interaction AC\tIMEx ID\tInteractor A IDs\tInteractor B IDs\tInteractor A aliases\t"
        b"Interactor B aliases\tInteraction detection method\tPublication IDs\tTaxid A\tTaxid B\t"
        b"Interaction type\tSource database\tConfidence values\tNative complex\t"
        b"Expanded from complex\tExpansion method\n"
        b"EBI-12345\tIM-12345\tuniprotkb:P04637\tuniprotkb:P69905\tTP53\tHBA1\t"
        b"MI:0018(two hybrid)\tpubmed:123456\t"
        b"taxid:9606(Homo sapiens)\ttaxid:9606(Homo sapiens)\t"
        b"MI:0915(physical association)\tIntAct\tintact-miscore:0.72\ttrue\tfalse\t-\n"
    )
    return acquire_intact_snapshot(
        manifest,
        opener=_fake_opener(manifest.source_locator, payload),
    )


def _snapshot_result_missing_lineage():
    manifest = SourceReleaseManifest(
        source_name="IntAct",
        release_version="live-smoke",
        release_date="2026-03-22",
        retrieval_mode="query",
        source_locator=(
            "https://www.ebi.ac.uk/Tools/webservices/psicquic/intact/webservices/current/"
            "search/query/id:P04637?format=tab25&firstResult=0&maxResults=3"
        ),
        provenance=("live-query", "psicquic", "intact"),
    )
    payload = (
        b"Interaction AC\tIMEx ID\tInteractor A IDs\tInteractor B IDs\tInteractor A aliases\t"
        b"Interactor B aliases\tInteraction detection method\tPublication IDs\tTaxid A\tTaxid B\t"
        b"Interaction type\tSource database\tConfidence values\tNative complex\t"
        b"Expanded from complex\tExpansion method\n"
        b"\t\tuniprotkb:P04637\tuniprotkb:P69905\tTP53\tHBA1\t"
        b"MI:0018(two hybrid)\tpubmed:123456\t"
        b"taxid:9606(Homo sapiens)\ttaxid:9606(Homo sapiens)\t"
        b"MI:0915(physical association)\tIntAct\tintact-miscore:0.72\ttrue\tfalse\t-\n"
    )
    return acquire_intact_snapshot(
        manifest,
        opener=_fake_opener(manifest.source_locator, payload),
    )


def test_materialize_intact_cohort_slice_returns_direct_hit_with_sorted_pair_key() -> None:
    selection = _selection()
    result = _snapshot_result()

    slice_result = materialize_intact_cohort_slice(
        "P04637",
        selection=selection,
        snapshot_result=result,
    )
    payload = slice_result.to_dict()

    assert slice_result.state == "direct_hit"
    assert slice_result.lineage_state == "canonical_interaction"
    assert slice_result.lineage_blockers == ()
    assert slice_result.priority_class == "single_lane_direct_anchor"
    assert slice_result.selector_rank == 2
    assert slice_result.pair_count == 1
    assert slice_result.pair_keys == (
        "pair:protein_protein:protein:P04637|protein:P69905",
    )
    assert slice_result.pair_records[0].accession_pair == ("P04637", "P69905")
    assert slice_result.pair_records[0].interaction_ac == "EBI-12345"
    assert slice_result.pair_records[0].imex_id == "IM-12345"
    assert slice_result.pair_records[0].lineage_state == "canonical_interaction"
    assert slice_result.pair_records[0].lineage_blockers == ()
    assert slice_result.pair_records[0].source_record_ids == ("EBI-12345", "IM-12345")
    assert "planning/P04637" in slice_result.provenance_pointers
    assert payload["state"] == "direct_hit"
    assert payload["lineage_state"] == "canonical_interaction"
    assert json.loads(json.dumps(payload))["pair_keys"] == [
        "pair:protein_protein:protein:P04637|protein:P69905",
    ]


def test_materialize_intact_cohort_slice_accepts_mapped_snapshot_artifacts() -> None:
    result = _snapshot_result()

    slice_result = materialize_intact_cohort_slice_from_artifacts(
        "P04637",
        snapshot_result=result.to_dict(),
    )

    assert slice_result.state == "direct_hit"
    assert slice_result.lineage_state == "canonical_interaction"
    assert slice_result.pair_count == 1
    assert slice_result.pair_records[0].interaction_ac == "EBI-12345"
    assert slice_result.pair_records[0].imex_id == "IM-12345"
    assert slice_result.pair_records[0].provenance_pointers[0] == (
        "pair:protein_protein:protein:P04637|protein:P69905"
    )
    assert slice_result.provenance_pointers[0] == "selector_rank=2"


def test_materialize_intact_cohort_slice_reports_empty_and_unavailable_honestly() -> None:
    selection = _selection()
    direct_result = _snapshot_result()

    empty_slice = materialize_intact_cohort_slice(
        "Q9NZD4",
        selection=selection,
        snapshot_result=direct_result,
    )
    assert empty_slice.state == "reachable_empty"
    assert empty_slice.lineage_state == "participant_only"
    assert empty_slice.lineage_blockers == ("no_curated_intact_pairs",)
    assert empty_slice.pair_records == ()
    assert "no curated IntAct pairs" in empty_slice.probe_reason

    unavailable_manifest = SourceReleaseManifest(
        source_name="IntAct",
        release_version="live-smoke",
        release_date="2026-03-22",
        retrieval_mode="query",
        source_locator=(
            "https://www.ebi.ac.uk/Tools/webservices/psicquic/intact/webservices/current/"
            "search/query/id:Q9NZD4?format=tab25&firstResult=0&maxResults=3"
        ),
        provenance=("live-query", "psicquic", "intact"),
    )

    def unavailable_opener(request, timeout=None):
        raise URLError("network down")

    unavailable_result = acquire_intact_snapshot(
        unavailable_manifest,
        opener=unavailable_opener,
    )
    unavailable_slice = materialize_intact_cohort_slice(
        "Q9NZD4",
        selection=selection,
        snapshot_result=unavailable_result,
    )
    assert unavailable_slice.state == "unavailable"
    assert unavailable_slice.lineage_state == "participant_only"
    assert unavailable_slice.lineage_blockers == ("intact_snapshot_unavailable",)
    assert unavailable_slice.pair_records == ()
    assert "network down" in (unavailable_slice.probe_reason or "")


def test_materialize_intact_cohort_slice_skips_self_pairs_in_live_like_rows() -> None:
    selection = _selection()
    manifest = SourceReleaseManifest(
        source_name="IntAct",
        release_version="live-smoke",
        release_date="2026-03-22",
        retrieval_mode="query",
        source_locator=(
            "https://www.ebi.ac.uk/Tools/webservices/psicquic/intact/webservices/current/"
            "search/query/id:P04637?format=tab25&firstResult=0&maxResults=3"
        ),
        provenance=("live-query", "psicquic", "intact"),
    )
    payload = (
        b"Interaction AC\tIMEx ID\tInteractor A IDs\tInteractor B IDs\tInteractor A aliases\t"
        b"Interactor B aliases\tInteraction detection method\tPublication IDs\tTaxid A\tTaxid B\t"
        b"Interaction type\tSource database\tConfidence values\tNative complex\t"
        b"Expanded from complex\tExpansion method\n"
        b"\t\tuniprotkb:P04637\tuniprotkb:P04637\tTP53\tTP53\t"
        b"MI:0018(two hybrid)\tpubmed:123456\t"
        b"taxid:9606(Homo sapiens)\ttaxid:9606(Homo sapiens)\t"
        b"MI:0915(physical association)\tIntAct\tintact-miscore:0.72\ttrue\tfalse\t-\n"
    )
    result = acquire_intact_snapshot(
        manifest,
        opener=_fake_opener(manifest.source_locator, payload),
    )

    slice_result = materialize_intact_cohort_slice(
        "P04637",
        selection=selection,
        snapshot_result=result,
    )

    assert slice_result.state == "reachable_empty"
    assert slice_result.pair_records == ()


def test_materialize_intact_cohort_slice_exposes_missing_canonical_lineage_blockers() -> None:
    selection = _selection()
    result = _snapshot_result_missing_lineage()

    slice_result = materialize_intact_cohort_slice(
        "P04637",
        selection=selection,
        snapshot_result=result,
    )

    assert slice_result.state == "direct_hit"
    assert slice_result.lineage_state == "participant_only"
    assert slice_result.lineage_blockers == (
        "missing_interaction_ac",
        "missing_imex_id",
    )
    assert slice_result.pair_records[0].interaction_ac is None
    assert slice_result.pair_records[0].imex_id is None
    assert slice_result.pair_records[0].lineage_state == "participant_only"
    assert slice_result.pair_records[0].lineage_blockers == (
        "missing_interaction_ac",
        "missing_imex_id",
    )
