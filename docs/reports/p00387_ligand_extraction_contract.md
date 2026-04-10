# P00387 Ligand Extraction Contract

- Generated at: `2026-03-31T18:16:52.019264+00:00`
- Accession: `P00387`
- Contract status: `ready_for_next_step`
- Rescue claim permitted: `False`

## Source

- Source DB path: `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db`
- Source DB exists: `True`
- Source table names: `['action_type', 'activities', 'activity_properties', 'activity_smid', 'activity_stds_lookup', 'activity_supp', 'activity_supp_map', 'assay_class_map', 'assay_classification', 'assay_parameters', 'assay_type', 'assays', 'atc_classification', 'binding_sites', 'bio_component_sequences', 'bioassay_ontology', 'biotherapeutic_components', 'biotherapeutics', 'cell_dictionary', 'chembl_id_lookup', 'chembl_release', 'component_class', 'component_domains', 'component_go', 'component_sequences', 'component_synonyms', 'compound_properties', 'compound_records', 'compound_structural_alerts', 'compound_structures', 'confidence_score_lookup', 'curation_lookup', 'data_validity_lookup', 'defined_daily_dose', 'docs', 'domains', 'drug_indication', 'drug_mechanism', 'drug_warning', 'formulations', 'go_classification', 'indication_refs', 'ligand_eff', 'mechanism_refs', 'metabolism', 'metabolism_refs', 'molecule_atc_classification', 'molecule_dictionary', 'molecule_hierarchy', 'molecule_synonyms', 'organism_class', 'patent_use_codes', 'pesticide_class_mapping', 'pesticide_classification', 'predicted_binding_domains', 'product_patents', 'products', 'protein_class_synonyms', 'protein_classification', 'relationship_type', 'site_components', 'source', 'sqlite_stat1', 'structural_alert_sets', 'structural_alerts', 'target_components', 'target_dictionary', 'target_relations', 'target_type', 'tissue_dictionary', 'usan_stems', 'variant_sequences', 'version', 'warning_refs']`

## Candidate Tables

- `component_sequences` (accession anchor): candidate columns = component_id, accession, sequence, description, tax_id, organism, db_source, db_version; present columns = component_id, accession, sequence, description, tax_id, organism, db_source, db_version
- `target_components` (component-to-target bridge): candidate columns = component_id, tid, targcomp_id, homologue; present columns = component_id, tid, targcomp_id, homologue
- `target_dictionary` (target identity): candidate columns = tid, target_type, pref_name, tax_id, organism, chembl_id, species_group_flag; present columns = tid, target_type, pref_name, tax_id, organism, chembl_id, species_group_flag
- `assays` (assay grain): candidate columns = assay_id, doc_id, description, assay_type, assay_test_type, assay_category, assay_organism, assay_tax_id, assay_strain, assay_tissue, assay_cell_type, assay_subcellular_fraction, tid, relationship_type, confidence_score, curated_by, src_id, src_assay_id, chembl_id, cell_id, bao_format, tissue_id, variant_id, aidx, assay_group; present columns = assay_id, doc_id, description, assay_type, assay_test_type, assay_category, assay_organism, assay_tax_id, assay_strain, assay_tissue, assay_cell_type, assay_subcellular_fraction, tid, relationship_type, confidence_score, curated_by, src_id, src_assay_id, chembl_id, cell_id, bao_format, tissue_id, variant_id, aidx, assay_group
- `activities` (activity grain): candidate columns = activity_id, assay_id, doc_id, record_id, molregno, standard_relation, standard_value, standard_units, standard_flag, standard_type, activity_comment, data_validity_comment, potential_duplicate, pchembl_value, bao_endpoint, uo_units, qudt_units, toid, upper_value, standard_upper_value, src_id, type, relation, value, units, text_value, standard_text_value, action_type; present columns = activity_id, assay_id, doc_id, record_id, molregno, standard_relation, standard_value, standard_units, standard_flag, standard_type, activity_comment, data_validity_comment, potential_duplicate, pchembl_value, bao_endpoint, uo_units, qudt_units, toid, upper_value, standard_upper_value, src_id, type, relation, value, units, text_value, standard_text_value, action_type

## Join Chain

- `component_sequences.component_id` -> `target_components.component_id`: carry the P00387 accession into the target bridge
- `target_components.tid` -> `target_dictionary.tid`: resolve the ChEMBL target identity
- `target_dictionary.tid` -> `assays.tid`: count the assays tied to the target
- `assays.assay_id` -> `activities.assay_id`: count the activity records tied to those assays

## Live Signal

- Target hit count: `1`
- Activity count: `93`
- Selected target hit: `P00387` -> `CHEMBL2146` (`NADH-cytochrome b5 reductase`), activities=93

## Expected Output Schema

- Required fields: `schema_id`, `report_type`, `generated_at`, `accession`, `source_db_path`, `candidate_tables`, `join_chain`, `live_signal`, `expected_output_schema`, `success_criteria`, `blockers`, `truth_boundary_notes`

## Success Criteria

- the local ChEMBL accession join stays accession-clean for P00387
- the contract records the source DB path, candidate tables, and join chain
- the next-step output preserves the boundary between planning signal and rescue completion
- any follow-on extraction can materialize a ligand-lane artifact without asserting completion

## Blockers

- none

## Truth Boundary

- this artifact is planning-grade and does not claim ligand rescue is complete
- a ChEMBL target hit confirms local target evidence, not canonical assay resolution
- activity counts are evidence volume only and do not imply potency, selectivity, or readiness to promote
- the rescue claim stays false until a downstream ligand extraction lane is validated separately

## Next Step

- Name: `bounded_p00387_ligand_extraction`
- Description: Use the local ChEMBL hit as the starting point for a bounded ligand extraction pass, then validate whether the result can support a truthful ligand lane without promotion claims.
- Do not claim: rescue complete, canonical assay resolution, packet promotion