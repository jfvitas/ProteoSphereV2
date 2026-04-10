from __future__ import annotations

from core.release.cohort_registry import ReleaseCohortEntry, ReleaseCohortRegistry
from evaluation.release_corpus_completeness import (
    score_release_cohort_entry,
    score_release_cohort_registry,
)


def test_score_release_cohort_entry_marks_release_ready_examples() -> None:
    entry = ReleaseCohortEntry(
        canonical_id="protein:P69905",
        record_type="protein",
        inclusion_status="included",
        freeze_state="frozen",
        inclusion_reason="hemoglobin anchor is fully frozen for the release corpus",
        evidence_lanes=("uniprot", "rcsb_pdbe", "alphafold", "reactome"),
        source_manifest_ids=(
            "uniprot:2026_03:download:abc123",
            "rcsb:2026-03-22:download:def456",
        ),
        packet_ready=True,
        benchmark_priority=1,
    )

    score = score_release_cohort_entry(entry)

    assert score.grade == "release_ready"
    assert score.release_ready is True
    assert score.score >= 85
    assert "freeze_state=frozen" in score.rationale


def test_score_release_cohort_entry_marks_blocked_examples_explicitly() -> None:
    entry = ReleaseCohortEntry(
        canonical_id="protein:P04637",
        record_type="protein",
        inclusion_status="included",
        freeze_state="frozen",
        inclusion_reason="retain TP53 for evidence accounting",
        blocker_ids=("self_only_intact_slice", "missing_direct_pair_lane"),
        evidence_lanes=("uniprot", "reactome"),
        source_manifest_ids=("uniprot:2026_03:download:abc123",),
        packet_ready=False,
    )

    score = score_release_cohort_entry(entry)

    assert score.grade == "blocked"
    assert score.release_ready is False
    assert score.blocker_count == 2
    assert "blocker=self_only_intact_slice" in score.rationale


def test_score_release_cohort_entry_keeps_excluded_examples_out_of_ready_path() -> None:
    entry = ReleaseCohortEntry(
        canonical_id="protein:Q11111",
        record_type="protein",
        inclusion_status="excluded",
        exclusion_reason="below minimum evidence depth",
    )

    score = score_release_cohort_entry(entry)

    assert score.grade == "excluded"
    assert score.score == 0
    assert score.release_ready is False


def test_score_release_cohort_registry_summarizes_grade_counts() -> None:
    registry = ReleaseCohortRegistry(
        registry_id="release-cohort:rc2",
        release_version="0.9.0-rc2",
        entries=(
            ReleaseCohortEntry(
                canonical_id="protein:P69905",
                record_type="protein",
                inclusion_status="included",
                freeze_state="frozen",
                inclusion_reason="anchor release protein",
                evidence_lanes=("uniprot", "rcsb_pdbe", "alphafold"),
                source_manifest_ids=("uniprot:2026_03:download:abc123",),
                packet_ready=True,
            ),
            ReleaseCohortEntry(
                canonical_id="protein:P04637",
                record_type="protein",
                inclusion_status="included",
                freeze_state="draft",
                inclusion_reason="retain for unresolved evidence accounting",
                blocker_ids=("self_only_intact_slice",),
                evidence_lanes=("uniprot",),
            ),
            ReleaseCohortEntry(
                canonical_id="protein:Q11111",
                record_type="protein",
                inclusion_status="excluded",
                exclusion_reason="not enough evidence",
            ),
        ),
    )

    report = score_release_cohort_registry(registry)

    assert report.registry_id == "release-cohort:rc2"
    assert report.grade_counts["release_ready"] == 1
    assert report.grade_counts["blocked"] == 1
    assert report.grade_counts["excluded"] == 1
    assert report.release_ready_count == 1
    assert report.blocked_count == 1
