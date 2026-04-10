from __future__ import annotations

from core.release.cohort_registry import ReleaseCohortEntry, ReleaseCohortRegistry
from scripts.emit_release_corpus_ledger import build_release_corpus_ledger


def test_build_release_corpus_ledger_emits_summary_and_rows() -> None:
    registry = ReleaseCohortRegistry(
        registry_id="release-cohort:rc3",
        release_version="0.9.0-rc3",
        freeze_state="draft",
        notes=("release candidate cohort",),
        entries=(
            ReleaseCohortEntry(
                canonical_id="protein:P69905",
                record_type="protein",
                inclusion_status="included",
                freeze_state="frozen",
                inclusion_reason="fully pinned anchor",
                evidence_lanes=("uniprot", "rcsb_pdbe", "alphafold"),
                source_manifest_ids=("uniprot:2026_03:download:abc123",),
                packet_ready=True,
            ),
            ReleaseCohortEntry(
                canonical_id="protein:P04637",
                record_type="protein",
                inclusion_status="included",
                freeze_state="draft",
                inclusion_reason="retain as a tracked blocker row",
                blocker_ids=("self_only_intact_slice",),
                evidence_lanes=("uniprot",),
            ),
            ReleaseCohortEntry(
                canonical_id="protein:Q11111",
                record_type="protein",
                inclusion_status="excluded",
                exclusion_reason="below minimum evidence depth",
            ),
        ),
    )

    ledger = build_release_corpus_ledger(registry)

    assert ledger["registry_id"] == "release-cohort:rc3"
    assert ledger["release_version"] == "0.9.0-rc3"
    assert ledger["summary"]["entry_count"] == 3
    assert ledger["summary"]["included_count"] == 2
    assert ledger["summary"]["excluded_count"] == 1
    assert ledger["summary"]["blocked_count"] == 1
    assert ledger["summary"]["grade_counts"]["release_ready"] == 1
    assert len(ledger["rows"]) == 3

    rows_by_id = {row["canonical_id"]: row for row in ledger["rows"]}
    assert rows_by_id["protein:P69905"]["grade"] == "release_ready"
    assert rows_by_id["protein:P69905"]["release_ready"] is True
    assert rows_by_id["protein:P04637"]["grade"] == "blocked"
    assert rows_by_id["protein:P04637"]["blocker_ids"] == ["self_only_intact_slice"]
    assert rows_by_id["protein:Q11111"]["grade"] == "excluded"
