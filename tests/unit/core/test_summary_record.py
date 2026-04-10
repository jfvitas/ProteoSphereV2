from __future__ import annotations

import pytest

from core.library.summary_record import (
    ProteinLigandSummaryRecord,
    ProteinProteinSummaryRecord,
    ProteinSummaryRecord,
    ProteinVariantSummaryRecord,
    StructureUnitSummaryRecord,
    SummaryBiologicalOrigin,
    SummaryCrossSourceView,
    SummaryLibrarySchema,
    SummaryProvenancePointer,
    SummaryRecordContext,
    SummaryReference,
    SummarySourceConnection,
)
from core.storage.planning_index_schema import PlanningIndexMaterializationPointer


def test_protein_summary_record_round_trips_with_context_and_guidance() -> None:
    connections = (
        SummarySourceConnection(
            connection_kind="accession",
            source_names=("UniProt", "Reactome"),
            direct_sources=("UniProt", "Reactome"),
            bridge_ids=("accession:P12345",),
            bridge_source="accession",
            join_mode="direct",
            join_status="joined",
        ),
        SummarySourceConnection(
            connection_kind="structure",
            source_names=("UniProt", "CATH"),
            direct_sources=("UniProt", "SIFTS"),
            indirect_sources=("CATH",),
            bridge_ids=("PDB:4HHB", "SIFTS:1.10.490.10", "CATH:1.10.490.10"),
            bridge_source="SIFTS",
            join_mode="indirect",
            join_status="joined",
        ),
        SummarySourceConnection(
            connection_kind="motif",
            source_names=("UniProt", "ELM"),
            direct_sources=("UniProt",),
            bridge_ids=("registry:elm",),
            bridge_source="local_registry_runs/LATEST.json",
            join_mode="partial",
            join_status="partial",
        ),
    )

    record = ProteinSummaryRecord(
        summary_id=" protein-summary-1 ",
        protein_ref=" protein:P12345 ",
        protein_name="Example protein",
        organism_name="Homo sapiens",
        taxon_id="9606",
        sequence_checksum=" sha256:abc123 ",
        sequence_version=" 2 ",
        sequence_length="10",
        gene_names=("GENE1", "GENE1", "GENE2"),
        aliases=("AliasA", " AliasA ", "AliasB"),
        join_status="joined",
        context=SummaryRecordContext(
            provenance_pointers=(
                SummaryProvenancePointer(
                    provenance_id="prov-1",
                    source_name="UniProt",
                    source_record_id="P12345",
                ),
            ),
            cross_references=(
                SummaryReference(
                    reference_kind="cross_reference",
                    namespace="uniprot",
                    identifier="P12345",
                    label="Primary accession",
                ),
            ),
            motif_references=(
                SummaryReference(
                    reference_kind="motif",
                    namespace="interpro",
                    identifier="IPR000001",
                    span_start=5,
                    span_end=25,
                ),
            ),
            domain_references=(
                SummaryReference(
                    reference_kind="domain",
                    namespace="pfam",
                    identifier="PF00001",
                    span_start=30,
                    span_end=80,
                ),
            ),
            pathway_references=(
                SummaryReference(
                    reference_kind="pathway",
                    namespace="reactome",
                    identifier="R-HSA-199420",
                ),
            ),
            biological_origin=SummaryBiologicalOrigin(
                organism_name="Homo sapiens",
                taxon_id=9606,
                lineage=("Eukaryota", "Metazoa"),
                compartment="cytosol",
            ),
            materialization_pointers=(
                PlanningIndexMaterializationPointer(
                    materialization_kind="coordinates",
                    pointer="s3://bucket/coords/P12345.bcif",
                    selector="protein:P12345",
                    source_name="AlphaFold",
                ),
            ),
            source_connections=connections,
            cross_source_view=SummaryCrossSourceView.from_connections(connections),
            storage_notes=("pin the release before materializing heavy annotations",),
        ),
    )

    assert record.record_type == "protein"
    assert record.protein_ref == "protein:P12345"
    assert record.gene_names == ("GENE1", "GENE2")
    assert record.context.storage_tier == "feature_cache"
    assert "accession" in record.context.planning_index_keys
    assert record.context.lazy_loading_guidance[0].startswith("preload accession")

    restored = ProteinSummaryRecord.from_dict(record.to_dict())
    assert restored == record


def test_summary_cross_source_view_groups_connections_by_join_mode() -> None:
    direct = SummarySourceConnection(
        connection_kind="accession",
        source_names=("UniProt", "Reactome"),
        direct_sources=("UniProt", "Reactome"),
        bridge_ids=("accession:P69905",),
        bridge_source="accession",
        join_mode="direct",
        join_status="joined",
    )
    indirect = SummarySourceConnection(
        connection_kind="structure",
        source_names=("UniProt", "CATH"),
        direct_sources=("UniProt", "SIFTS"),
        indirect_sources=("CATH",),
        bridge_ids=("PDB:4HHB", "SIFTS:1.10.490.10", "CATH:1.10.490.10"),
        bridge_source="SIFTS",
        join_mode="indirect",
        join_status="joined",
    )
    partial = SummarySourceConnection(
        connection_kind="motif",
        source_names=("UniProt", "ELM"),
        direct_sources=("UniProt",),
        bridge_ids=("registry:elm",),
        bridge_source="local_registry_runs/LATEST.json",
        join_mode="partial",
        join_status="partial",
    )

    view = SummaryCrossSourceView.from_connections((direct, indirect, partial))

    assert view.direct_joins == (direct,)
    assert view.indirect_bridges == (indirect,)
    assert view.partial_joins == (partial,)
    assert SummaryCrossSourceView.from_dict(view.to_dict()) == view


def test_pair_and_ligand_summary_records_preserve_join_state_and_lazy_loading() -> None:
    pair_record = ProteinProteinSummaryRecord(
        summary_id="pair-1",
        protein_a_ref="protein:P12345",
        protein_b_ref="protein:Q9XYZ1",
        interaction_type="physical interaction",
        interaction_id="biogrid:12345",
        interaction_refs=("intact:EBI-1", "biogrid:12345"),
        evidence_refs=("prov-1", "prov-2"),
        organism_name="Homo sapiens",
        taxon_id=9606,
        physical_interaction=True,
        directionality="undirected",
        evidence_count=2,
        confidence=0.91,
        join_status="joined",
        context=SummaryRecordContext(
            storage_notes=("preserve native interaction identifiers",),
        ),
    )
    ligand_record = ProteinLigandSummaryRecord(
        summary_id="ligand-1",
        protein_ref="protein:P12345",
        ligand_ref="ligand:CHEBI:15377",
        association_type="binding",
        association_id="bindingdb:row-1",
        interaction_refs=("bindingdb:row-1",),
        assay_refs=("assay-1", "assay-2"),
        organism_name="Homo sapiens",
        taxon_id=9606,
        measurement_type="Ki",
        measurement_value="12.5",
        measurement_unit="nM",
        confidence=0.85,
        join_status="candidate",
    )

    assert pair_record.record_type == "protein_protein"
    assert pair_record.context.deferred_payloads == (
        "full_interaction_row",
        "publication_context",
        "complex_projection_payload",
    )
    assert ligand_record.record_type == "protein_ligand"
    assert ligand_record.context.planning_index_keys[0] == "protein_ref"

    assert ProteinProteinSummaryRecord.from_dict(pair_record.to_dict()) == pair_record
    assert ProteinLigandSummaryRecord.from_dict(ligand_record.to_dict()) == ligand_record

    with pytest.raises(ValueError, match="must be different"):
        ProteinProteinSummaryRecord(
            summary_id="pair-2",
            protein_a_ref="protein:P12345",
            protein_b_ref="protein:P12345",
        )


def test_summary_library_schema_round_trips_and_rejects_duplicates() -> None:
    protein = ProteinSummaryRecord(
        summary_id="protein-1",
        protein_ref="protein:P12345",
        organism_name="Homo sapiens",
    )
    pair = ProteinProteinSummaryRecord(
        summary_id="pair-1",
        protein_a_ref="protein:P12345",
        protein_b_ref="protein:Q9XYZ1",
    )
    ligand = ProteinLigandSummaryRecord(
        summary_id="ligand-1",
        protein_ref="protein:P12345",
        ligand_ref="ligand:CHEBI:15377",
    )
    library = SummaryLibrarySchema(
        library_id="summary-library:v1",
        source_manifest_id="UniProt:2026_02:download",
        records=(protein, pair, ligand),
        index_guidance=("accession-first routing",),
        storage_guidance=("defer heavy payloads until selection",),
        lazy_loading_guidance=("hydrate only after candidate selection",),
    )

    assert library.record_count == 3
    assert library.protein_records == (protein,)
    assert library.pair_records == (pair,)
    assert library.ligand_records == (ligand,)

    restored = SummaryLibrarySchema.from_dict(library.to_dict())
    assert restored == library

    with pytest.raises(ValueError, match="duplicate summary_id"):
        SummaryLibrarySchema(
            library_id="summary-library:v1",
            records=(protein, protein),
        )


def test_variant_and_structure_unit_records_round_trip_and_expose_v2_views() -> None:
    variant = ProteinVariantSummaryRecord(
        summary_id="variant-1",
        protein_ref="protein:P04637",
        parent_protein_ref="protein:P04637",
        variant_signature="R175H",
        variant_kind="point_mutation",
        mutation_list=("p.Arg175His",),
        sequence_delta_signature="missense:R175H",
        construct_type="engineered_mutant",
        is_partial=False,
        organism_name="Homo sapiens",
        taxon_id=9606,
        variant_relation_notes=("common tumor suppressor hotspot mutant",),
    )
    structure_unit = StructureUnitSummaryRecord(
        summary_id="structure-1",
        protein_ref="protein:P04637",
        variant_ref="variant:R175H",
        structure_source="PDB",
        structure_id="1TUP",
        structure_kind="protein_dna_complex",
        entity_id="1",
        chain_id="A",
        assembly_id="1",
        residue_span_start=94,
        residue_span_end=289,
        resolution_or_confidence=2.2,
        experimental_or_predicted="experimental",
        mapping_status="joined",
        structure_relation_notes=("DNA-binding core domain chain",),
    )

    assert variant.record_type == "protein_variant"
    assert variant.context.planning_index_keys[0] == "protein_ref"
    assert structure_unit.record_type == "structure_unit"
    assert structure_unit.context.planning_index_keys[2] == "structure_source"

    assert ProteinVariantSummaryRecord.from_dict(variant.to_dict()) == variant
    assert StructureUnitSummaryRecord.from_dict(structure_unit.to_dict()) == structure_unit

    library = SummaryLibrarySchema(
        library_id="summary-library:v2",
        schema_version=2,
        records=(variant, structure_unit),
    )

    assert library.record_count == 2
    assert library.variant_records == (variant,)
    assert library.structure_unit_records == (structure_unit,)
    assert SummaryLibrarySchema.from_dict(library.to_dict()) == library

    with pytest.raises(ValueError, match="variant_signature must not be empty"):
        ProteinVariantSummaryRecord(
            summary_id="variant-2",
            protein_ref="protein:P04637",
        )

    with pytest.raises(ValueError, match="residue_span_start must be <="):
        StructureUnitSummaryRecord(
            summary_id="structure-2",
            protein_ref="protein:P04637",
            structure_source="PDB",
            structure_id="1TUP",
            residue_span_start=20,
            residue_span_end=10,
        )
