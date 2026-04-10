from __future__ import annotations

import gzip
from pathlib import Path

from scripts.export_uniref_cluster_context_preview import (
    build_uniref_cluster_context_preview,
)


def test_build_uniref_cluster_context_preview_prefers_local_crossrefs_after_completion(
    tmp_path: Path,
) -> None:
    idmapping_selected = tmp_path / "idmapping_selected.tab.gz"
    with gzip.open(idmapping_selected, "wt", encoding="utf-8") as handle:
        handle.write(
            "P31749\tAKT1_HUMAN\t\tNP_005154.2\t\t\tGO:0001\tUniRef100_P31749\tUniRef90_P31749\tUniRef50_P31749\tUPI0000000001\t\t9606\n"
        )

    payload = build_uniref_cluster_context_preview(
        {"rows": [{"accession": "P31749"}]},
        {"gate_status": "ready_to_freeze_complete_mirror"},
        {"uniprot_completion_ready": True},
        idmapping_selected_path=idmapping_selected,
    )

    row = payload["rows"][0]
    assert row["uniref100_cluster_id"] == "UniRef100_P31749"
    assert row["materialization_basis"] == "local_idmapping_selected"
    assert row["local_materialization_status"] == "materialized_from_local_uniprot_crossrefs"
    assert payload["summary"]["local_crossref_row_count"] == 1
