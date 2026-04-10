from __future__ import annotations

from urllib.error import URLError

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.intact_snapshot import IntActSnapshotResult, acquire_intact_snapshot


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def _fake_opener(expected_url: str, payload: bytes):
    def opener(request, timeout=None):
        assert request.full_url == expected_url
        assert timeout == 30.0
        return _FakeResponse(payload)

    return opener


def test_acquire_intact_snapshot_round_trips_from_dict_artifacts() -> None:
    manifest = SourceReleaseManifest(
        source_name="IntAct",
        release_version="247",
        release_date="2024-06-10",
        source_locator="https://example.org/intact-247.tsv",
        local_artifact_refs=("cache/intact-247.tsv",),
        provenance=("source:ebi", "download:mitab"),
        reproducibility_metadata=("pinned-release",),
    )
    payload = (
        b"Interaction AC\tIMEx ID\tInteractor A IDs\tInteractor B IDs\tInteractor A aliases\t"
        b"Interactor B aliases\tInteraction detection method\tPublication IDs\tTaxid A\tTaxid B\t"
        b"Interaction type\tSource database\tConfidence values\tNative complex\t"
        b"Expanded from complex\tExpansion method\n"
        b"EBI-12345\tIM-12345\tuniprotkb:P12345|refseq:NP_000000\tuniprotkb:Q9XYZ1\t"
        b"geneA|proteinA\tgeneB|proteinB\tMI:0018(two hybrid)\tpubmed:123456|doi:10.1000/xyz\t"
        b"taxid:9606(Homo sapiens)\ttaxid:9606(Homo sapiens)\t"
        b"MI:0915(physical association)\tIntAct\tintact-miscore:0.72\ttrue\tfalse\t-\n"
    )

    result = acquire_intact_snapshot(
        manifest,
        opener=_fake_opener("https://example.org/intact-247.tsv", payload),
    )

    round_tripped = IntActSnapshotResult.from_dict(result.to_dict())

    assert round_tripped.status == "ok"
    assert round_tripped.manifest is not None
    assert round_tripped.manifest.manifest_id == manifest.manifest_id
    assert round_tripped.snapshot is not None
    assert round_tripped.snapshot.provenance.record_count == 1
    assert round_tripped.snapshot.records[0].interaction_ac == "EBI-12345"
    assert round_tripped.snapshot.records[0].interaction_representation == "native_complex"


def test_acquire_intact_snapshot_preserves_release_imex_and_projection_metadata() -> None:
    manifest = SourceReleaseManifest(
        source_name="IntAct",
        release_version="247",
        release_date="2024-06-10",
        source_locator="https://example.org/intact-247.tsv",
        local_artifact_refs=("cache/intact-247.tsv",),
        provenance=("source:ebi", "download:mitab"),
        reproducibility_metadata=("pinned-release",),
    )
    payload = (
        b"Interaction AC\tIMEx ID\tInteractor A IDs\tInteractor B IDs\tInteractor A aliases\t"
        b"Interactor B aliases\tInteraction detection method\tPublication IDs\tTaxid A\tTaxid B\t"
        b"Interaction type\tSource database\tConfidence values\tNative complex\t"
        b"Expanded from complex\tExpansion method\n"
        b"EBI-12345\tIM-12345\tuniprotkb:P12345|refseq:NP_000000\tuniprotkb:Q9XYZ1\t"
        b"geneA|proteinA\tgeneB|proteinB\tMI:0018(two hybrid)\tpubmed:123456|doi:10.1000/xyz\t"
        b"taxid:9606(Homo sapiens)\ttaxid:9606(Homo sapiens)\t"
        b"MI:0915(physical association)\tIntAct\tintact-miscore:0.72\ttrue\tfalse\t-\n"
        b"EBI-67890\t\tuniprotkb:Q11111\trefseq:NP_222222\tgeneC\tgeneD\t"
        b"MI:0398(spoke)\tpubmed:234567\t"
        b"taxid:9606(Homo sapiens)\ttaxid:9606(Homo sapiens)\t"
        b"MI:0915(physical association)\tIntAct\tintact-miscore:0.91\tfalse\ttrue\t"
        b"spoke expansion\n"
    )

    result = acquire_intact_snapshot(
        manifest,
        opener=_fake_opener("https://example.org/intact-247.tsv", payload),
    )

    assert result.status == "ok"
    assert result.succeeded is True
    assert result.manifest is not None
    assert result.snapshot is not None
    assert result.snapshot.provenance.source == "IntAct"
    assert result.snapshot.provenance.ecosystem == "IMEx"
    assert result.snapshot.provenance.record_count == 2
    assert result.snapshot.provenance.native_complex_count == 1
    assert result.snapshot.provenance.binary_projection_count == 1
    assert result.snapshot.provenance.imex_record_count == 1
    assert result.snapshot.source_release["manifest_id"] == manifest.manifest_id
    assert result.snapshot.source_release["release_version"] == "247"
    assert result.snapshot.source_release["source_name"] == "IntAct"
    assert result.snapshot.records[0].interaction_ac == "EBI-12345"
    assert result.snapshot.records[0].imex_id == "IM-12345"
    assert result.snapshot.records[0].lineage_state == "canonical_interaction"
    assert result.snapshot.records[0].lineage_blockers == ()
    assert result.snapshot.records[0].participant_a_primary_id == "P12345"
    assert result.snapshot.records[0].participant_b_primary_id == "Q9XYZ1"
    assert result.snapshot.records[0].native_complex is True
    assert result.snapshot.records[0].expanded_from_complex is False
    assert result.snapshot.records[0].interaction_representation == "native_complex"
    assert result.snapshot.records[1].participant_b_primary_id == "NP_222222"
    assert result.snapshot.records[1].native_complex is False
    assert result.snapshot.records[1].expanded_from_complex is True
    assert result.snapshot.records[1].interaction_representation == "binary_projection"
    assert result.raw_payload.startswith("Interaction AC\tIMEx ID")

    payload_dict = result.to_dict()
    assert payload_dict["status"] == "ok"
    assert payload_dict["manifest"]["manifest_id"] == manifest.manifest_id
    assert payload_dict["provenance"]["record_count"] == 2
    assert (
        payload_dict["snapshot"]["records"][1]["interaction_representation"]
        == "binary_projection"
    )
    assert payload_dict["snapshot"]["records"][0]["lineage_state"] == "canonical_interaction"


def test_acquire_intact_snapshot_flags_missing_canonical_lineage_fields_explicitly() -> None:
    manifest = SourceReleaseManifest(
        source_name="IntAct",
        release_version="247",
        release_date="2024-06-10",
        source_locator="https://example.org/intact-247.tsv",
        provenance=("source:ebi",),
    )
    payload = (
        b"Interaction AC\tIMEx ID\tInteractor A IDs\tInteractor B IDs\tInteraction type\t"
        b"Source database\tNative complex\tExpanded from complex\tExpansion method\n"
        b"\t\tuniprotkb:P12345\tuniprotkb:Q9XYZ1\tMI:0915(physical association)\t"
        b"IntAct\ttrue\tfalse\t-\n"
    )

    result = acquire_intact_snapshot(
        manifest,
        opener=_fake_opener("https://example.org/intact-247.tsv", payload),
    )

    assert result.status == "ok"
    assert result.snapshot is not None
    record = result.snapshot.records[0]
    assert record.interaction_ac == ""
    assert record.imex_id == ""
    assert record.lineage_state == "participant_only"
    assert record.lineage_blockers == ("missing_interaction_ac", "missing_imex_id")


def test_acquire_intact_snapshot_derives_lineage_from_headerless_interaction_ids() -> None:
    manifest = SourceReleaseManifest(
        source_name="IntAct",
        release_version="247",
        release_date="2024-06-10",
        source_locator="https://example.org/intact-247.tsv",
        provenance=("source:ebi",),
    )
    payload = (
        b"uniprotkb:P04637\tuniprotkb:P69905\tintact:EBI-366083|uniprotkb:P53_HUMAN\t"
        b"intact:EBI-123456|uniprotkb:HBA_HUMAN\tpsi-mi:TP53\tpsi-mi:HBA1\t"
        b"psi-mi:\"MI:0018\"(two hybrid)\tWang et al. (2011)\t"
        b"pubmed:21988832|doi:10.1000/xyz\t"
        b"taxid:9606(Homo sapiens)\ttaxid:9606(Homo sapiens)\t"
        b"psi-mi:\"MI:0915\"(physical association)\tpsi-mi:\"MI:0469\"(IntAct)\t"
        b"intact:EBI-3934232|imex:IM-15364-2608\tintact-miscore:0.98\tspoke expansion\n"
    )

    result = acquire_intact_snapshot(
        manifest,
        opener=_fake_opener("https://example.org/intact-247.tsv", payload),
    )

    assert result.status == "ok"
    assert result.snapshot is not None
    record = result.snapshot.records[0]
    assert record.interaction_ac == "EBI-3934232"
    assert record.imex_id == "IM-15364-2608"
    assert "intact:EBI-366083" in record.participant_a_ids
    assert "intact:EBI-123456" in record.participant_b_ids
    assert record.lineage_state == "canonical_interaction"
    assert record.lineage_blockers == ()


def test_acquire_intact_snapshot_blocks_when_manifest_is_missing_locator() -> None:
    manifest = SourceReleaseManifest(
        source_name="IntAct",
        release_version="247",
        release_date="2024-06-10",
        provenance=("source:ebi",),
    )

    result = acquire_intact_snapshot(manifest)

    assert result.status == "blocked"
    assert result.snapshot is None
    assert "source locator" in result.reason
    assert result.provenance.record_count == 0


def test_acquire_intact_snapshot_reports_unavailable_fetch_failures_honestly() -> None:
    manifest = SourceReleaseManifest(
        source_name="IntAct",
        release_version="247",
        release_date="2024-06-10",
        source_locator="https://example.org/intact-247.tsv",
        provenance=("source:ebi",),
    )

    def opener(request, timeout=None):
        raise URLError("network down")

    result = acquire_intact_snapshot(manifest, opener=opener)

    assert result.status == "unavailable"
    assert result.snapshot is None
    assert "network down" in result.reason


def test_acquire_intact_snapshot_blocks_unsupported_payload_format() -> None:
    manifest = SourceReleaseManifest(
        source_name="IntAct",
        release_version="247",
        release_date="2024-06-10",
        source_locator="https://example.org/intact-247.xml",
        provenance=("source:ebi",),
    )

    result = acquire_intact_snapshot(
        {
            "source_release": manifest.to_dict(),
            "payload_format": "xml",
        }
    )

    assert result.status == "blocked"
    assert "unsupported payload_format" in result.reason
