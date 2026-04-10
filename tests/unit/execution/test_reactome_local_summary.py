from __future__ import annotations

import json
from pathlib import Path

from execution.library.reactome_local_summary import (
    load_reactome_pathway_assignments,
    materialize_reactome_local_summary_library,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_load_reactome_pathway_assignments_builds_ancestor_aware_references(tmp_path: Path) -> None:
    mapping_path = tmp_path / "UniProt2Reactome_All_Levels.txt"
    pathways_path = tmp_path / "ReactomePathways.txt"
    relations_path = tmp_path / "ReactomePathwaysRelation.txt"

    mapping_path.write_text(
        "\n".join(
            (
                (
                    "P12345\tR-HSA-1\thttps://reactome.org/PathwayBrowser/#/R-HSA-1\t"
                    "Child Pathway\tTAS\tHomo sapiens"
                ),
                (
                    "Q99999\tR-HSA-2\thttps://reactome.org/PathwayBrowser/#/R-HSA-2\t"
                    "Other Pathway\tIEA\tHomo sapiens"
                ),
            )
        ),
        encoding="utf-8",
    )
    pathways_path.write_text(
        "\n".join(
            (
                "R-HSA-0\tParent Pathway\tHomo sapiens",
                "R-HSA-1\tChild Pathway\tHomo sapiens",
            )
        ),
        encoding="utf-8",
    )
    relations_path.write_text("R-HSA-0\tR-HSA-1\n", encoding="utf-8")

    assignments = load_reactome_pathway_assignments(
        accessions=("P12345",),
        mapping_path=mapping_path,
        pathways_path=pathways_path,
        relations_path=relations_path,
    )

    assert len(assignments["P12345"]) == 1
    assignment = assignments["P12345"][0]
    assert assignment.stable_id == "R-HSA-1"
    assert assignment.ancestor_ids == ("R-HSA-0",)
    reference = assignment.to_summary_reference()
    assert reference.namespace == "Reactome"
    assert reference.identifier == "R-HSA-1"
    assert "ancestors:R-HSA-0" in reference.notes


def test_materialize_reactome_local_summary_library_uses_canonical_records_and_keeps_empty_hits(
    tmp_path: Path,
) -> None:
    mapping_path = tmp_path / "UniProt2Reactome_All_Levels.txt"
    pathways_path = tmp_path / "ReactomePathways.txt"
    relations_path = tmp_path / "ReactomePathwaysRelation.txt"
    canonical_summary_path = tmp_path / "canonical" / "LATEST.json"

    mapping_path.write_text(
        (
            "P12345\tR-HSA-1\thttps://reactome.org/PathwayBrowser/#/R-HSA-1\t"
            "Child Pathway\tTAS\tHomo sapiens\n"
        ),
        encoding="utf-8",
    )
    pathways_path.write_text("R-HSA-1\tChild Pathway\tHomo sapiens\n", encoding="utf-8")
    relations_path.write_text("", encoding="utf-8")
    _write_json(
        canonical_summary_path,
        {
            "sequence_result": {
                "canonical_proteins": [
                    {
                        "accession": "P12345",
                        "name": "Example protein",
                        "organism": "Homo sapiens",
                        "sequence_length": 123,
                        "gene_names": ["GENE1"],
                        "aliases": ["EXAMPLE_HUMAN"],
                    }
                ]
            }
        },
    )

    library = materialize_reactome_local_summary_library(
        accessions=("P12345", "Q99999"),
        canonical_summary_path=canonical_summary_path,
        mapping_path=mapping_path,
        pathways_path=pathways_path,
        relations_path=relations_path,
        library_id="reactome-test",
    )

    assert library.library_id == "reactome-test"
    assert library.record_count == 2
    by_id = {record.summary_id: record for record in library.protein_records}
    assert by_id["protein:P12345"].protein_name == "Example protein"
    assert len(by_id["protein:P12345"].context.pathway_references) == 1
    assert by_id["protein:P12345"].join_status == "joined"
    assert by_id["protein:Q99999"].join_status == "partial"
    assert by_id["protein:Q99999"].notes == ("reactome_only_accession", "reactome_empty")
