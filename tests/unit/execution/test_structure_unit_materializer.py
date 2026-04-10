from __future__ import annotations

from core.library.summary_record import (
    ProteinSummaryRecord,
    SummaryLibrarySchema,
    SummaryRecordContext,
    SummaryReference,
    SummarySourceConnection,
)
from execution.library.structure_unit_materializer import (
    build_structure_unit_summary_library,
    materialize_structure_unit_records,
)


def _protein_with_structure_refs() -> ProteinSummaryRecord:
    return ProteinSummaryRecord(
        summary_id="protein:P69905",
        protein_ref="protein:P69905",
        protein_name="Hemoglobin subunit alpha",
        organism_name="Homo sapiens",
        context=SummaryRecordContext(
            domain_references=(
                SummaryReference(
                    reference_kind="domain",
                    namespace="CATH",
                    identifier="1.10.490.10",
                    label="Globins",
                    join_status="joined",
                    source_name="SIFTS",
                    source_record_id="4hhbA00",
                    span_start=2,
                    span_end=142,
                    evidence_refs=("SIFTS:4HHB:A:4hhbA00",),
                    notes=(
                        "captured_from:local_copies/cath",
                        "pdb_id:4HHB",
                        "chain:A",
                        "entry_span:2-142",
                        "domain_id:4hhbA00",
                    ),
                ),
                SummaryReference(
                    reference_kind="domain",
                    namespace="SCOPe",
                    identifier="a.1.1.2",
                    label="Globin fold",
                    join_status="joined",
                    source_name="SIFTS",
                    source_record_id="d4hhba_",
                    span_start=2,
                    span_end=142,
                    evidence_refs=("SIFTS:4HHB:A:d4hhba_",),
                    notes=(
                        "captured_from:local_copies/scope",
                        "pdb_id:4HHB",
                        "chain:A",
                        "entry_span:2-142",
                        "scop_id:d4hhba_",
                    ),
                ),
            ),
            source_connections=(
                SummarySourceConnection(
                    connection_kind="structure",
                    source_names=("UniProt", "CATH"),
                    direct_sources=("UniProt", "SIFTS"),
                    indirect_sources=("CATH",),
                    bridge_ids=("PDB:4HHB", "CHAIN:A", "SIFTS:4hhbA00", "CATH:1.10.490.10"),
                    bridge_source="SIFTS",
                    join_mode="indirect",
                    join_status="joined",
                ),
            ),
        ),
    )


def test_materialize_structure_unit_records_groups_classification_refs_by_chain() -> None:
    records = materialize_structure_unit_records((_protein_with_structure_refs(),))

    assert len(records) == 1
    record = records[0]
    assert record.record_type == "structure_unit"
    assert record.protein_ref == "protein:P69905"
    assert record.structure_id == "4HHB"
    assert record.chain_id == "A"
    assert record.residue_span_start == 2
    assert record.residue_span_end == 142
    assert len(record.context.domain_references) == 2
    assert record.context.source_connections[0].connection_kind == "structure"


def test_build_structure_unit_summary_library_wraps_materialized_records() -> None:
    protein_library = SummaryLibrarySchema(
        library_id="summary-library:protein-materialized:v1",
        source_manifest_id="manifest:protein",
        records=(_protein_with_structure_refs(),),
    )

    structure_library = build_structure_unit_summary_library(protein_library)

    assert structure_library.schema_version == 2
    assert structure_library.source_manifest_id == "manifest:protein"
    assert structure_library.record_count == 1
    assert structure_library.structure_unit_records[0].structure_id == "4HHB"
