from __future__ import annotations

import json
from pathlib import Path

from execution.library.intact_local_summary import materialize_intact_local_summary_library


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_snapshot_row(
    path: Path,
    *,
    accession_a: str,
    accession_b: str,
    alt_a: str,
    alt_b: str,
    alias_a: str,
    alias_b: str,
    publication_ids: str,
    interaction_type: str,
    source_database: str,
    interaction_ids: str,
    confidence: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = "\t".join(
        (
            f"uniprotkb:{accession_a}",
            f"uniprotkb:{accession_b}",
            alt_a,
            alt_b,
            alias_a,
            alias_b,
            'psi-mi:"MI:0018"(two hybrid)',
            "Example et al. (2026)",
            publication_ids,
            "taxid:9606(Homo sapiens)",
            "taxid:9606(Homo sapiens)",
            interaction_type,
            source_database,
            interaction_ids,
            confidence,
        )
    )
    path.write_text(f"{row}\n", encoding="utf-8")


def test_materialize_intact_local_summary_library_builds_pair_and_probe_records(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "intact" / "20260323T002625Z"
    canonical_summary_path = tmp_path / "canonical" / "LATEST.json"

    _write_snapshot_row(
        snapshot_root / "P12345" / "P12345.psicquic.tab25.txt",
        accession_a="P12345",
        accession_b="Q99999",
        alt_a="intact:EBI-100|uniprotkb:P12345",
        alt_b="intact:EBI-200|uniprotkb:Q99999",
        alias_a="psi-mi:KINASE(display_short)",
        alias_b="psi-mi:PARTNER(display_short)",
        publication_ids="pubmed:12345|imex:IM-0001",
        interaction_type='psi-mi:"MI:0915"(physical association)',
        source_database='psi-mi:"MI:0469"(IntAct)',
        interaction_ids="intact:EBI-PAIR1|imex:IM-0001-1",
        confidence="intact-miscore:0.98",
    )
    _write_snapshot_row(
        snapshot_root / "Q11111" / "Q11111.psicquic.tab25.txt",
        accession_a="Q11111",
        accession_b="Q11111",
        alt_a="intact:EBI-300|uniprotkb:Q11111",
        alt_b="intact:EBI-300|uniprotkb:Q11111",
        alias_a="psi-mi:SELF(display_short)",
        alias_b="psi-mi:SELF(display_short)",
        publication_ids="pubmed:99999",
        interaction_type='psi-mi:"MI:0915"(physical association)',
        source_database='psi-mi:"MI:0469"(IntAct)',
        interaction_ids="intact:EBI-SELF1|imex:IM-SELF-1",
        confidence="intact-miscore:0.51",
    )
    _write_json(
        canonical_summary_path,
        {
            "sequence_result": {
                "canonical_proteins": [
                    {
                        "accession": "P12345",
                        "name": "Example kinase",
                        "organism": "Homo sapiens",
                        "taxon_id": 9606,
                        "sequence_length": 321,
                        "gene_names": ["KIN1"],
                        "aliases": ["KINASE_HUMAN"],
                    },
                    {
                        "accession": "Q11111",
                        "name": "Self only protein",
                        "organism": "Homo sapiens",
                        "taxon_id": 9606,
                        "sequence_length": 210,
                        "gene_names": ["SELF1"],
                        "aliases": ["SELF_HUMAN"],
                    },
                ]
            }
        },
    )

    library = materialize_intact_local_summary_library(
        accessions=("P12345", "Q11111"),
        raw_root=snapshot_root.parent,
        canonical_summary_path=canonical_summary_path,
        library_id="summary-library:intact-local:test",
    )

    assert library.library_id == "summary-library:intact-local:test"
    assert library.source_manifest_id is not None
    assert library.record_count == 3

    proteins = {record.summary_id: record for record in library.protein_records}
    assert proteins["protein:P12345"].join_status == "joined"
    assert proteins["protein:P12345"].protein_name == "Example kinase"
    assert proteins["protein:Q11111"].join_status == "partial"
    assert proteins["protein:Q11111"].join_reason == "intact_self_only_probe"
    assert "self_only_rows=1" in proteins["protein:Q11111"].notes

    pair = library.pair_records[0]
    assert pair.summary_id == "pair:protein_protein:protein:P12345|protein:Q99999"
    assert pair.join_status == "joined"
    assert pair.evidence_count == 1
    assert pair.confidence == 0.98
    assert pair.physical_interaction is True
    assert "EBI-PAIR1" in pair.interaction_refs
    assert "IM-0001-1" in pair.interaction_refs
    assert {reference.namespace for reference in pair.context.cross_references} == {
        "IMEx",
        "IntAct",
    }
