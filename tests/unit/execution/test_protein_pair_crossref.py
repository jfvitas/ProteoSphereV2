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
    SummaryReference,
)
from core.storage.planning_index_schema import PlanningIndexMaterializationPointer
from execution.indexing.protein_pair_crossref import (
    ProteinPairCrossReferenceIndex,
    build_protein_pair_crossref_index,
)


def _registry() -> CanonicalEntityRegistry:
    return CanonicalEntityRegistry(
        proteins=(
            CanonicalProtein(accession="P12345", sequence="ACDEFG", name="Alpha"),
            CanonicalProtein(accession="Q99999", sequence="ACDEFG", name="Beta"),
            CanonicalProtein(accession="P28482", sequence="ACDEFG", name="Gamma"),
        ),
        ligands=(
            CanonicalLigand(
                ligand_id="bindingdb:120095",
                name="Example ligand",
                source="BindingDB",
                source_id="120095",
            ),
        ),
    )


def _ppi_record() -> ProteinProteinSummaryRecord:
    return ProteinProteinSummaryRecord(
        summary_id="pair:ppi:1",
        protein_a_ref="protein:P12345",
        protein_b_ref="uniprot:Q99999",
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
            cross_references=(
                SummaryReference(
                    reference_kind="cross_reference",
                    namespace="reactome",
                    identifier="R-HSA-1",
                    label="Pathway",
                    join_status="joined",
                ),
            ),
            biological_origin=SummaryBiologicalOrigin(
                organism_name="Homo sapiens",
                taxon_id=9606,
            ),
            materialization_pointers=(
                PlanningIndexMaterializationPointer(
                    materialization_kind="table",
                    pointer="cache/pairs/ppi.tsv",
                    source_name="IntAct",
                    source_record_id="EBI-0001",
                ),
            ),
        ),
        notes=("native complex projection",),
    )


def _pli_record() -> ProteinLigandSummaryRecord:
    return ProteinLigandSummaryRecord(
        summary_id="pair:pli:1",
        protein_ref="P28482",
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


def test_build_protein_pair_crossref_index_resolves_pair_kinds_and_preserves_provenance() -> None:
    library = SummaryLibrarySchema(
        library_id="summary-library",
        source_manifest_id="manifest:summary-library",
        records=(_ppi_record(), _pli_record()),
    )

    index = build_protein_pair_crossref_index(library, registry=_registry())

    assert isinstance(index, ProteinPairCrossReferenceIndex)
    assert index.record_count == 2
    assert index.source_manifest_id == "manifest:summary-library"
    assert index.index_guidance
    assert index.storage_guidance
    assert index.lazy_loading_guidance

    ppi = next(record for record in index.records if record.summary_id == "pair:ppi:1")
    assert ppi.record_type == "protein_protein"
    assert ppi.protein_refs == ("protein:P12345", "uniprot:Q99999")
    assert ppi.canonical_protein_ids == ("protein:P12345", "protein:Q99999")
    assert ppi.ligand_refs == ()
    assert ppi.source_evidence_refs == ("IM-12345-1", "EBI-0001", "PMID:12345")
    assert ppi.source_record_ids == ("EBI-0001",)
    assert ppi.provenance_pointers[0].provenance_id == "prov:ppi:1"
    assert ppi.context.biological_origin is not None
    assert ppi.context.materialization_pointers[0].pointer == "cache/pairs/ppi.tsv"
    assert ppi.unresolved_references == ()
    assert ppi.pair_id == "pair:protein_protein:protein:P12345|protein:Q99999"

    pli = next(record for record in index.records if record.summary_id == "pair:pli:1")
    assert pli.record_type == "protein_ligand"
    assert pli.protein_refs == ("P28482",)
    assert pli.canonical_protein_ids == ("protein:P28482",)
    assert pli.ligand_refs == ("bindingdb:120095",)
    assert pli.canonical_ligand_ids == ("ligand:bindingdb:120095",)
    assert pli.source_evidence_refs == ("BIOL-1", "RS123", "ASSAY-1")
    assert pli.source_record_ids == ("RS123",)
    assert pli.context.biological_origin is not None
    assert pli.unresolved_references == ()
    assert pli.pair_id == "pair:protein_ligand:protein:P28482|ligand:bindingdb:120095"


def test_build_protein_pair_crossref_index_accepts_bare_accessions_without_registry() -> None:
    library = SummaryLibrarySchema(
        library_id="summary-library",
        records=(
            ProteinProteinSummaryRecord(
                summary_id="pair:ppi:bare",
                protein_a_ref="P28482",
                protein_b_ref="Q99999",
                interaction_type="physical association",
                interaction_id="EBI-0004",
                organism_name="Homo sapiens",
            ),
            ProteinLigandSummaryRecord(
                summary_id="pair:pli:bare",
                protein_ref="P28482",
                ligand_ref="bindingdb:120095",
                association_type="binding",
                association_id="RS444",
                organism_name="Homo sapiens",
            ),
        ),
    )

    index = build_protein_pair_crossref_index(library)

    ppi = next(record for record in index.records if record.summary_id == "pair:ppi:bare")
    assert ppi.canonical_protein_ids == ("protein:P28482", "protein:Q99999")
    assert ppi.join_status == "joined"
    assert ppi.source_evidence_refs == ("EBI-0004",)
    assert ppi.source_record_ids == ("EBI-0004",)
    assert ppi.provenance_pointers == ()

    pli = next(record for record in index.records if record.summary_id == "pair:pli:bare")
    assert pli.canonical_protein_ids == ("protein:P28482",)
    assert pli.canonical_ligand_ids == ("ligand:bindingdb:120095",)
    assert pli.join_status == "joined"
    assert pli.source_evidence_refs == ("RS444",)
    assert pli.source_record_ids == ("RS444",)
    assert pli.provenance_pointers == ()


def test_build_protein_pair_crossref_index_preserves_native_direct_ppi_evidence() -> None:
    library = SummaryLibrarySchema(
        library_id="summary-library",
        records=(
            ProteinProteinSummaryRecord(
                summary_id="pair:4HHB:protein_protein",
                protein_a_ref="protein:P69905",
                protein_b_ref="protein:P68871",
                interaction_type="protein complex",
                interaction_id="4HHB",
                interaction_refs=("4HHB",),
                organism_name="Homo sapiens",
                physical_interaction=True,
                directionality="undirected",
                confidence=0.99,
            ),
        ),
    )

    index = build_protein_pair_crossref_index(library)

    assert index.record_count == 1
    entry = index.records[0]
    assert entry.summary_id == "pair:4HHB:protein_protein"
    assert entry.record_type == "protein_protein"
    assert entry.canonical_protein_ids == ("protein:P69905", "protein:P68871")
    assert entry.source_evidence_refs == ("4HHB",)
    assert entry.source_record_ids == ("4HHB",)
    assert entry.provenance_pointers == ()
    assert entry.join_status == "joined"


def test_build_protein_pair_crossref_index_keeps_unresolved_refs_explicit() -> None:
    registry = CanonicalEntityRegistry(
        proteins=(CanonicalProtein(accession="P12345", sequence="ACDEFG"),),
    )
    library = SummaryLibrarySchema(
        library_id="summary-library",
        records=(
            ProteinLigandSummaryRecord(
                summary_id="pair:pli:2",
                protein_ref="P12345",
                ligand_ref="CHEM-UNKNOWN",
                association_type="binding",
                association_id="RS999",
                interaction_refs=("BIOL-2",),
                assay_refs=("ASSAY-2",),
                organism_name="Homo sapiens",
                confidence=0.5,
                context=SummaryRecordContext(
                    provenance_pointers=(
                        SummaryProvenancePointer(
                            provenance_id="prov:pli:2",
                            source_name="BindingDB",
                            source_record_id="RS999",
                            release_version="2026.02",
                        ),
                    ),
                ),
            ),
        ),
    )

    index = build_protein_pair_crossref_index(library, registry=registry)

    assert index.record_count == 1
    entry = index.records[0]
    assert entry.record_type == "protein_ligand"
    assert entry.protein_refs == ("P12345",)
    assert entry.canonical_protein_ids == ("protein:P12345",)
    assert entry.canonical_ligand_ids == ()
    assert entry.join_status == "partial"
    assert entry.unresolved_count == 1
    assert entry.unresolved_references[0].entity_type == "ligand"
    assert entry.unresolved_references[0].reason == "missing"
    assert entry.source_evidence_refs == ("BIOL-2", "RS999", "ASSAY-2")


def test_build_protein_pair_crossref_index_round_trips_through_dict() -> None:
    index = build_protein_pair_crossref_index(
        [
            {
                "record_type": "protein_protein",
                "summary_id": "pair:ppi:3",
                "protein_a_ref": "protein:P12345",
                "protein_b_ref": "protein:Q99999",
                "interaction_id": "EBI-0003",
                "interaction_refs": ("IM-1",),
                "evidence_refs": ("PMID:1",),
                "context": {
                    "provenance_pointers": [
                        {
                            "provenance_id": "prov:ppi:3",
                            "source_name": "IntAct",
                            "source_record_id": "EBI-0003",
                        }
                    ]
                },
            }
        ],
        registry=_registry(),
    )

    payload = index.to_dict()
    assert payload["record_count"] == 1
    assert payload["records"][0]["pair_id"] == "pair:protein_protein:protein:P12345|protein:Q99999"

    restored = ProteinPairCrossReferenceIndex.from_dict(payload)
    assert restored == index
    assert restored.records[0].source_record_ids == ("EBI-0003",)
