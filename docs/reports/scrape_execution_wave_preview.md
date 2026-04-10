# Scrape Execution Wave Preview

- Status: `report_only`
- Structured jobs: `9`
- Page jobs: `2`
- Tail-blocked jobs: `0`
- Active downloads: `0`

## Structured Jobs

- `1` `motif_active_site_enrichment` / `elm_motif_backbone` status `implemented` / `harvest_now`
  sources: PROSITE, ELM, InterPro complements
- `2` `motif_active_site_enrichment` / `interpro_motif_backbone` status `implemented` / `harvest_now`
  sources: PROSITE, ELM, InterPro complements
- `3` `interaction_context_enrichment` / `biogrid_interaction_backbone` status `implemented` / `harvest_now`
  sources: BioGRID complements, IntAct complements, literature context
- `4` `interaction_context_enrichment` / `intact_interaction_backbone` status `implemented` / `harvest_now`
  sources: BioGRID complements, IntAct complements, literature context
- `5` `interaction_context_enrichment` / `string_interaction_backbone` status `implemented` / `harvest_now`
  sources: BioGRID complements, IntAct complements, literature context
- `6` `kinetics_pathway_metadata_enrichment` / `sabio_rk_kinetics_backbone` status `implemented` / `harvest_now`
  sources: SABIO-RK complements, pathway narrative metadata
- `7` `bindingdb_assay_bridge_backbone` / `bindingdb_assay_bridge_backbone` status `implemented` / `harvest_now`
  sources: bindingdb
- `8` `pdbbind_measurement_backbone` / `pdbbind_measurement_backbone` status `implemented` / `harvest_now`
  sources: pdbbind
- `9` `rcsb_pdbe_sifts_structure_backbone` / `rcsb_pdbe_sifts_structure_backbone` status `implemented` / `harvest_now`
  sources: rcsb_pdbe

## Page Jobs

- `1` `P04637` / `Targeted page scrape for P04637` / `candidate_only_non_governing`
- `2` `P31749` / `Targeted page scrape for P31749` / `candidate_only_non_governing`

## Tail-Blocked Jobs


## Truth Boundary

- This scrape wave preview is report-only. It ranks structured, page, and tail-blocked jobs from existing artifacts, but it does not launch scraping or mutate curated truth.
