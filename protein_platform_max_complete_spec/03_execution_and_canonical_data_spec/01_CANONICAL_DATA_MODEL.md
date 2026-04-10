# Canonical Data Model

## 1. Canonical entities
### ProteinRecord
Represents canonical protein identity anchored primarily by UniProt accession or other designated primary identifier.
Fields:
- protein_id_internal
- primary_external_id_type
- primary_external_id
- gene_name
- protein_name
- organism_name
- taxonomy_id
- canonical_sequence
- sequence_length
- isoform_id(optional)
- sequence_hash
- provenance_refs
- quality_flags

### ChainRecord
Represents a structure-specific chain or polymer entity instance.
Fields:
- chain_id_internal
- structure_source
- structure_id
- model_id(optional)
- assembly_id(optional)
- entity_id(optional)
- chain_label
- auth_chain_label(optional)
- mapped_protein_internal_id(optional)
- extracted_sequence
- sequence_alignment_to_canonical
- mutation_summary
- missing_residue_ranges
- altloc_summary
- confidence_summary
- provenance_refs

### LigandRecord
Fields:
- ligand_id_internal
- source_chem_id
- canonical_smiles
- inchi
- inchikey
- formal_charge
- molecular_weight
- logp(optional)
- rotatable_bond_count(optional)
- aromatic_ring_count(optional)
- hbond_donor_count(optional)
- hbond_acceptor_count(optional)
- fingerprints(optional multiple types)
- protonation_state(optional)
- provenance_refs

### NucleicAcidRecord
Fields:
- na_id_internal
- na_type: DNA | RNA | hybrid | modified
- canonical_sequence(optional if fully known)
- chain_source
- structure_id
- chain_label
- modifications
- provenance_refs

### ComplexRecord
Represents a bound system or assembly used as a modeling object.
Fields:
- complex_id_internal
- complex_type: protein | protein_ligand | protein_protein | protein_na | mixed
- structure_source
- structure_id
- assembly_id(optional)
- member_chain_ids
- member_ligand_ids
- member_na_ids
- stoichiometry
- biologically_relevant_flag
- relevance_confidence
- extraction_notes
- provenance_refs

### AssayMeasurementRecord
Fields:
- assay_id_internal
- assay_source
- target_reference_type
- target_reference_id
- ligand_reference_id(optional)
- partner_reference_id(optional)
- measured_quantity_type: Kd | Ki | IC50 | EC50 | ΔG | binary_interaction | other
- measured_value
- measured_unit
- transformed_value(optional standardized)
- p_value_form(optional pKd/pKi etc.)
- temperature(optional)
- pH(optional)
- assay_context_text(optional)
- curation_confidence
- replicate_policy
- provenance_refs

### AnnotationRecord
Fields:
- annotation_id_internal
- target_entity_type
- target_entity_internal_id
- annotation_category: domain | motif | disorder | PTM | pathway | family | active_site | binding_site | confidence | quality | custom
- annotation_label
- region_start(optional)
- region_end(optional)
- score(optional)
- evidence_type
- source_name
- source_accession(optional)
- provenance_refs

### InteractionEvidenceRecord
Fields:
- interaction_id_internal
- interactor_a_type
- interactor_a_id
- interactor_b_type
- interactor_b_id
- evidence_source
- evidence_class: physical | genetic | curated_pathway | literature | predicted
- experimental_system(optional)
- score(optional)
- source_publication(optional)
- provenance_refs

### ProvenanceRecord
Fields:
- provenance_id
- source_name
- source_version
- acquisition_mode: api | bulk_download | manual_curated | derived
- acquisition_timestamp
- original_identifier
- parser_version
- transformation_history
- confidence
- checksum(optional)
- raw_payload_pointer(optional)

## 2. Relationship rules
- ProteinRecord is the preferred identity anchor for proteins.
- ChainRecord may exist before mapping to ProteinRecord; unmapped chains must remain explicit, not discarded.
- ComplexRecord references chain/ligand/NA members by internal IDs.
- AssayMeasurementRecord must never be silently merged across incompatible assay types.
- AnnotationRecord must preserve source specificity; conflicting annotations coexist with confidence metadata.
- ProvenanceRecord must be attached to all first-class records.

## 3. Required canonical relationship examples
ProteinRecord 1---many ChainRecord
ComplexRecord many---many ChainRecord
ComplexRecord many---many LigandRecord
ComplexRecord many---many NucleicAcidRecord
ProteinRecord many---many AnnotationRecord
ComplexRecord many---many AnnotationRecord
ProteinRecord many---many InteractionEvidenceRecord
