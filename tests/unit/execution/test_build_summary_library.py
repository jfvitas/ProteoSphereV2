from __future__ import annotations

from core.library.summary_record import (
    ProteinLigandSummaryRecord,
    ProteinProteinSummaryRecord,
    ProteinSummaryRecord,
    ProteinVariantSummaryRecord,
    StructureUnitSummaryRecord,
    SummaryLibrarySchema,
    SummaryProvenancePointer,
    SummaryRecordContext,
)
from execution.indexing.protein_pair_crossref import build_protein_pair_crossref_index
from execution.library.build_summary_library import build_summary_library


def _protein_record() -> ProteinSummaryRecord:
    return ProteinSummaryRecord(
        summary_id="protein:P12345",
        protein_ref="protein:P12345",
        protein_name="Example protein",
        organism_name="Homo sapiens",
        taxon_id=9606,
        sequence_checksum="abc123",
        sequence_version="2026_03",
        sequence_length=6,
        gene_names=("GENE1",),
        aliases=("P12345",),
        join_status="joined",
        context=SummaryRecordContext(
            storage_notes=("already materialized",),
        ),
    )


def _ppi_record() -> ProteinProteinSummaryRecord:
    return ProteinProteinSummaryRecord(
        summary_id="pair:ppi:1",
        protein_a_ref="P12345",
        protein_b_ref="Q99999",
        interaction_type="physical association",
        interaction_id="EBI-0001",
        interaction_refs=("IM-12345-1",),
        evidence_refs=("PMID:12345",),
        organism_name="Homo sapiens",
        taxon_id=9606,
        physical_interaction=True,
        confidence=0.92,
        context=SummaryRecordContext(
            provenance_pointers=(
                SummaryProvenancePointer(
                    provenance_id="prov:ppi:1",
                    source_name="IntAct",
                    source_record_id="EBI-0001",
                    release_version="247",
                ),
            ),
        ),
    )


def _stale_ppi_record() -> ProteinProteinSummaryRecord:
    return ProteinProteinSummaryRecord(
        summary_id="pair:ppi:1",
        protein_a_ref="P12345",
        protein_b_ref="Q99999",
        interaction_type="physical association",
        interaction_id=None,
        interaction_refs=("IM-12345-1",),
        evidence_refs=("PMID:12345",),
        organism_name="Homo sapiens",
        taxon_id=9606,
        physical_interaction=True,
        confidence=0.92,
        context=SummaryRecordContext(
            storage_notes=("stale placeholder",),
        ),
    )


def _pli_record() -> ProteinLigandSummaryRecord:
    return ProteinLigandSummaryRecord(
        summary_id="pair:pli:1",
        protein_ref="P28482",
        ligand_ref="CHEM-UNKNOWN",
        association_type="binding",
        association_id="RS999",
        interaction_refs=("BIOL-2",),
        assay_refs=("ASSAY-2",),
        organism_name="Homo sapiens",
        taxon_id=9606,
        confidence=0.5,
    )


def test_build_summary_library_preserves_existing_library_without_overrides() -> None:
    library = SummaryLibrarySchema(
        library_id="summary-library",
        source_manifest_id="manifest:summary-library",
        records=(_protein_record(),),
    )

    rebuilt = build_summary_library(library)

    assert rebuilt is library


def test_build_summary_library_materializes_pair_crossref_records_conservatively() -> None:
    source_library = SummaryLibrarySchema(
        library_id="source-library",
        source_manifest_id="manifest:source",
        records=(_ppi_record(), _pli_record()),
    )
    pair_crossref_index = build_protein_pair_crossref_index(source_library)
    base_library = SummaryLibrarySchema(
        library_id="summary-library",
        records=(_protein_record(),),
    )

    summary_library = build_summary_library(
        base_library,
        pair_crossref_index=pair_crossref_index,
    )

    assert summary_library.library_id == "summary-library"
    assert summary_library.source_manifest_id == "manifest:source"
    assert summary_library.record_count == 3
    assert summary_library.index_guidance[0] == (
        "route protein, pair, and ligand summaries accession-first"
    )
    assert summary_library.storage_guidance[0] == (
        "treat the summary library as a rebuildable feature-cache layer"
    )
    assert summary_library.lazy_loading_guidance[0] == (
        "hydrate heavy source payloads only after selection"
    )

    protein = next(
        record
        for record in summary_library.protein_records
        if record.summary_id == "protein:P12345"
    )
    assert protein.protein_ref == "protein:P12345"
    assert protein.context.storage_notes == ("already materialized",)

    ppi = next(
        record
        for record in summary_library.pair_records
        if record.summary_id == "pair:ppi:1"
    )
    assert ppi.protein_a_ref == "protein:P12345"
    assert ppi.protein_b_ref == "protein:Q99999"
    assert ppi.interaction_refs == ("IM-12345-1", "EBI-0001", "PMID:12345")
    assert ppi.evidence_refs == ("EBI-0001",)
    assert ppi.context.provenance_pointers[0].provenance_id == "prov:ppi:1"
    assert ppi.context.provenance_pointers[0].source_record_id == "EBI-0001"
    assert ppi.notes == ()

    pli = next(
        record
        for record in summary_library.ligand_records
        if record.summary_id == "pair:pli:1"
    )
    assert pli.protein_ref == "protein:P28482"
    assert pli.ligand_ref == "CHEM-UNKNOWN"
    assert pli.interaction_refs == ("BIOL-2", "RS999", "ASSAY-2")
    assert pli.assay_refs == ("RS999",)
    assert pli.context.provenance_pointers == ()
    assert pli.join_status == "partial"
    assert pli.notes == ("unresolved_reference:ligand:CHEM-UNKNOWN:missing",)


def test_build_summary_library_replaces_stale_pair_records_when_crossref_is_available() -> None:
    source_library = SummaryLibrarySchema(
        library_id="source-library",
        source_manifest_id="manifest:source",
        records=(_ppi_record(), _pli_record()),
    )
    pair_crossref_index = build_protein_pair_crossref_index(source_library)
    base_library = SummaryLibrarySchema(
        library_id="summary-library",
        source_manifest_id="manifest:summary",
        records=(_protein_record(), _stale_ppi_record()),
    )

    summary_library = build_summary_library(
        base_library,
        pair_crossref_index=pair_crossref_index,
    )

    assert summary_library.source_manifest_id == "manifest:summary"
    ppi = next(
        record
        for record in summary_library.pair_records
        if record.summary_id == "pair:ppi:1"
    )
    assert ppi.interaction_id is None
    assert ppi.interaction_refs == ("IM-12345-1", "EBI-0001", "PMID:12345")
    assert ppi.evidence_refs == ("EBI-0001",)
    assert ppi.context.provenance_pointers[0].provenance_id == "prov:ppi:1"
    assert ppi.context.storage_notes != ("stale placeholder",)


def test_build_summary_library_keeps_missing_crossref_inputs_explicit() -> None:
    base_library = SummaryLibrarySchema(
        library_id="summary-library",
        source_manifest_id="manifest:summary",
        records=(_protein_record(), _stale_ppi_record()),
    )

    rebuilt = build_summary_library(base_library)

    assert rebuilt is base_library


def test_build_summary_library_preserves_variant_and_structure_unit_records() -> None:
    variant = ProteinVariantSummaryRecord(
        summary_id="variant:P04637:R175H",
        protein_ref="protein:P04637",
        parent_protein_ref="protein:P04637",
        variant_signature="R175H",
        variant_kind="point_mutation",
        mutation_list=("p.Arg175His",),
    )
    structure_unit = StructureUnitSummaryRecord(
        summary_id="structure:P04637:1TUP:A",
        protein_ref="protein:P04637",
        variant_ref="variant:R175H",
        structure_source="PDB",
        structure_id="1TUP",
        chain_id="A",
        entity_id="1",
        experimental_or_predicted="experimental",
        mapping_status="joined",
    )

    rebuilt = build_summary_library(
        (_protein_record(), variant, structure_unit),
        library_id="summary-library:v2",
        schema_version=2,
    )

    assert rebuilt.record_count == 3
    assert rebuilt.protein_records[0].summary_id == "protein:P12345"
    assert rebuilt.variant_records == (variant,)
    assert rebuilt.structure_unit_records == (structure_unit,)
