from __future__ import annotations

import pytest

from core.provenance.lineage import (
    ProvenanceLineage,
    ProvenanceLineageLink,
)
from core.provenance.record import ProvenanceRecord, ProvenanceSource


def _source() -> ProvenanceSource:
    return ProvenanceSource(source_name="UniProt", acquisition_mode="api")


def test_lineage_builds_stable_links_and_traverses_multiple_ancestors() -> None:
    root = ProvenanceRecord(
        provenance_id="prov-root",
        source=_source(),
        transformation_step="ingest",
        child_ids=("prov-branch-a", "prov-branch-b"),
    )
    branch_a = root.spawn_child(
        provenance_id="prov-branch-a",
        transformation_step="extract_a",
    )
    branch_b = root.spawn_child(
        provenance_id="prov-branch-b",
        transformation_step="extract_b",
    )
    merged = ProvenanceRecord(
        provenance_id="prov-merged",
        source=_source(),
        transformation_step="merge",
        parent_ids=("prov-branch-a", "prov-branch-b"),
        child_ids=("prov-report",),
    )
    report = merged.spawn_child(
        provenance_id="prov-report",
        transformation_step="publish",
    )

    lineage = ProvenanceLineage.from_records((report, merged, branch_b, root, branch_a))

    assert lineage.record_ids == (
        "prov-branch-a",
        "prov-branch-b",
        "prov-merged",
        "prov-report",
        "prov-root",
    )
    assert lineage.links == (
        ProvenanceLineageLink("prov-root", "prov-branch-a"),
        ProvenanceLineageLink("prov-root", "prov-branch-b"),
        ProvenanceLineageLink("prov-branch-a", "prov-merged"),
        ProvenanceLineageLink("prov-branch-b", "prov-merged"),
        ProvenanceLineageLink("prov-merged", "prov-report"),
    )
    assert lineage.root_ids == ("prov-root",)
    assert lineage.leaf_ids == ("prov-report",)
    assert lineage.parent_ids_of("prov-merged") == ("prov-branch-a", "prov-branch-b")
    assert lineage.child_ids_of("prov-root") == ("prov-branch-a", "prov-branch-b")
    assert lineage.ancestor_ids_of("prov-report") == (
        "prov-merged",
        "prov-branch-a",
        "prov-branch-b",
        "prov-root",
    )
    assert lineage.descendant_ids_of("prov-root") == (
        "prov-branch-a",
        "prov-branch-b",
        "prov-merged",
        "prov-report",
    )


def test_lineage_round_trips_through_serialization() -> None:
    parent = ProvenanceRecord(
        provenance_id="prov-parent",
        source=_source(),
        transformation_step="capture",
        child_ids=("prov-child",),
    )
    child = parent.spawn_child(
        provenance_id="prov-child",
        transformation_step="derive",
    )

    lineage = ProvenanceLineage.from_records((child, parent))

    restored = ProvenanceLineage.from_dict(lineage.to_dict())

    assert restored == lineage
    assert restored.to_dict()["links"] == [
        {"parent_id": "prov-parent", "child_id": "prov-child"}
    ]


def test_lineage_rejects_unresolved_references() -> None:
    root = ProvenanceRecord(
        provenance_id="prov-root",
        source=_source(),
        transformation_step="ingest",
        child_ids=("prov-missing",),
    )

    with pytest.raises(ValueError, match="lineage references must resolve"):
        ProvenanceLineage.from_records((root,))
