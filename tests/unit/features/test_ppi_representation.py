from __future__ import annotations

from core.canonical.ligand import CanonicalLigand
from core.canonical.protein import CanonicalProtein
from core.canonical.registry import CanonicalEntityRegistry
from core.library.summary_record import (
    ProteinLigandSummaryRecord,
    ProteinProteinSummaryRecord,
    SummaryBiologicalOrigin,
    SummaryLibrarySchema,
    SummaryProvenancePointer,
    SummaryRecordContext,
)
from features.ppi_representation import (
    DEFAULT_PPI_FEATURE_NAMES,
    PPIRepresentation,
    build_ppi_representation,
)


def _registry(*, include_q99999: bool = True) -> CanonicalEntityRegistry:
    proteins = [CanonicalProtein(accession="P12345", sequence="ACDEFG", name="Alpha")]
    if include_q99999:
        proteins.append(CanonicalProtein(accession="Q99999", sequence="ACDEFG", name="Beta"))
    return CanonicalEntityRegistry(
        proteins=tuple(proteins),
        ligands=(
            CanonicalLigand(
                ligand_id="bindingdb:120095",
                name="Example ligand",
                source="BindingDB",
                source_id="120095",
            ),
        ),
    )


def _ppi_record(*, protein_b_ref: str = "Q99999") -> ProteinProteinSummaryRecord:
    return ProteinProteinSummaryRecord(
        summary_id="pair:ppi:1",
        protein_a_ref="P12345",
        protein_b_ref=protein_b_ref,
        interaction_type="physical association",
        interaction_id="EBI-0001",
        interaction_refs=("IM-12345-1",),
        evidence_refs=("PMID:12345",),
        organism_name="Homo sapiens",
        taxon_id=9606,
        physical_interaction=True,
        directionality="undirected",
        evidence_count=2,
        confidence=0.92,
        context=SummaryRecordContext(
            provenance_pointers=(
                SummaryProvenancePointer(
                    provenance_id="prov:ppi:1",
                    source_name="IntAct",
                    source_record_id="EBI-0001",
                    release_version="247",
                    checksum="abc123",
                ),
            ),
            biological_origin=SummaryBiologicalOrigin(
                organism_name="Homo sapiens",
                taxon_id=9606,
            ),
        ),
        notes=("native complex projection",),
    )


def _pli_record() -> ProteinLigandSummaryRecord:
    return ProteinLigandSummaryRecord(
        summary_id="pair:pli:1",
        protein_ref="P12345",
        ligand_ref="bindingdb:120095",
        association_type="binding",
        association_id="RS123",
        interaction_refs=("BIOL-1",),
        assay_refs=("ASSAY-1",),
        organism_name="Homo sapiens",
        taxon_id=9606,
        measurement_type="Ki",
        measurement_value=21800.0,
        measurement_unit="nM",
        confidence=0.81,
        context=SummaryRecordContext(
            provenance_pointers=(
                SummaryProvenancePointer(
                    provenance_id="prov:pli:1",
                    source_name="BindingDB",
                    source_record_id="RS123",
                    release_version="2026.02",
                ),
            ),
            biological_origin=SummaryBiologicalOrigin(
                organism_name="Homo sapiens",
                taxon_id=9606,
            ),
        ),
        notes=("assay-backed binding record",),
    )


def test_build_ppi_representation_preserves_pair_features_and_provenance() -> None:
    library = SummaryLibrarySchema(
        library_id="summary-library",
        source_manifest_id="manifest:summary-library",
        records=(_ppi_record(),),
    )

    representation = build_ppi_representation(
        library,
        registry=_registry(),
        provenance=("builder:run-001",),
        notes=("selected-example focused",),
    )

    assert isinstance(representation, PPIRepresentation)
    assert representation.status == "ready"
    assert representation.record_count == 1
    assert representation.pair_ids == ("pair:protein_protein:protein:P12345|protein:Q99999",)
    assert representation.provenance == ("manifest:summary-library", "builder:run-001")
    assert representation.issues == ()

    record = representation.records[0]
    assert record.summary_id == "pair:ppi:1"
    assert record.canonical_protein_ids == ("protein:P12345", "protein:Q99999")
    assert record.feature_names == DEFAULT_PPI_FEATURE_NAMES
    assert record.feature_vector[0] == record.pair_id
    assert record.feature_vector[4:6] == ("protein:P12345", "protein:Q99999")
    assert record.feature_values["interaction_type"] == "physical association"
    assert record.source_record_ids == ("EBI-0001",)
    assert record.provenance_pointers[0].provenance_id == "prov:ppi:1"
    assert representation.to_dict()["records"][0]["pair_id"] == record.pair_id
    round_tripped = type(representation).from_dict(representation.to_dict())
    assert round_tripped.pair_ids == representation.pair_ids
    assert round_tripped.records[0].feature_vector == record.feature_vector


def test_build_ppi_representation_reports_skipped_and_unresolved_inputs() -> None:
    library = SummaryLibrarySchema(
        library_id="summary-library",
        records=(_ppi_record(protein_b_ref="UNKNOWN"), _pli_record()),
    )

    representation = build_ppi_representation(library, registry=_registry(include_q99999=False))

    assert representation.status == "partial"
    assert representation.record_count == 1
    assert {issue.kind for issue in representation.issues} == {
        "unresolved_protein_reference",
        "skipped_non_ppi_record",
    }

    record = representation.records[0]
    assert record.canonical_protein_ids == ("protein:P12345",)
    assert record.unresolved_references[0].reason == "missing"
    assert record.feature_values["canonical_protein_count"] == 1
    assert record.feature_values["provenance_pointer_count"] == 1
