# Missing Data Policy Preview

- Generated at: `2026-04-02T16:23:45.488544+00:00`

## Category Counts

- `blocked_pending_acquisition`: `4`
- `candidate_only_non_governing`: `1`
- `eligible_for_task`: `7`

## Core Rules

- `retain_nulls_with_provenance`: Leave unavailable scientific fields blank/null and keep provenance flags explicit.
- `do_not_delete_from_library_by_default`: Keep accessions in the lightweight library unless they are invalid, orphaned, or exact redundant copies; missing modalities alone are not a deletion reason.
- `gate_emitted_training_sets_by_task`: Exclude examples from a generated cohort only when the selected task requires a modality that is not eligible_for_task.
- `candidate_only_rows_non_governing`: Never let candidate-only rows govern split, leakage, consensus, or release-grade decisions.
- `scrape_as_provenance_tagged_enrichment`: Use scraping and web enrichment as a targeted support lane for breadth holes, tagging source quality and keeping weaker evidence non-governing until validated.

## Scrape / Enrichment Priorities

- `1` `BioGRID guarded procurement first wave`: Restores a missing curated interaction_network class and directly targets the Q9UCM0 PPI gap.
- `2` `STRING guarded procurement first wave`: Adds a second curated interaction_network lane and improves breadth beyond the current registry coverage.
- `3` `IntAct authoritative mirror refresh or intake`: Closes the third interaction_network hole and improves curated PPI redundancy.
- `4` `PROSITE acquisition refresh`: Adds missing motif breadth and creates a new annotation channel beyond pathways and structure.
- `5` `ELM acquisition refresh`: Complements PROSITE with linear-motif depth and improves functional annotation coverage.
- `6` `SABIO-RK acquisition`: Adds missing enzymology and kinetics metadata, which is currently absent from the scope.
