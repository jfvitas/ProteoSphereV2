# Motif Next-Step Priority Map

This map ranks the next three highest-value motif/domain steps for improving the summary library using the current repo truth only.

## Priority 1

Materialize the already-present imported backbone: `InterPro`, `PROSITE`, and local `Pfam` visibility.

What it unlocks:

- Canonical `domain_references` from `InterPro`.
- Canonical `motif_references` from `PROSITE`.
- Supporting domain projections from `Pfam` under the `InterPro` spine.
- Immediate library value from sources that are already grounded in the local registry and seed mirror.

What still stays blocked:

- `ELM` remains partial until its imported shape is fully promoted.
- `MegaMotifBase` remains capture-pending.
- `motivated_proteins` remains future-only.

## Priority 2

Complete `ELM` promotion and join its instance catalog into `motif_references`.

What it unlocks:

- Short-linear-motif coverage with explicit partner context.
- A second motif channel that complements `PROSITE`.
- Better span-level corroboration for motif hits that also appear in `InterPro` or `Pfam`.

What still stays blocked:

- `MegaMotifBase` is still future-only.
- `motivated_proteins` is still future-only.
- `ELM` still does not justify release-grade breadth until the partial import is fully landed.

## Priority 3

Capture and pin `MegaMotifBase` as a support-only supplemental lane.

What it unlocks:

- Supplemental structural-motif support.
- Family and superfamily context that can corroborate existing motif/domain calls.
- A new source-specific support lane in the summary library without overriding canonical labels.

What still stays blocked:

- The lane stays scrape-only until a real payload or stable export shape exists.
- `motivated_proteins` remains future-only and is still not a joined source.
- Release-grade motif breadth is still not complete after this step alone.

## Why This Order

The order follows the current truth stack:

1. land the sources we already have strongly enough for current library use,
2. finish the imported-but-partial motif channel,
3. then spend effort on the first true external capture lane.

## Evidence Paths

- `artifacts/status/p44_mega_motifbase_source_fusion_mapping.json`
- `artifacts/status/p43_mega_motifbase_capture_prep_checklist.json`
- `artifacts/status/p42_mega_motifbase_acquisition_contract.json`
- `artifacts/status/p41_motif_breadth_action_map.json`
- `artifacts/status/p40_motif_scope_completeness_view.json`
- `artifacts/status/p39_motif_gap_next_step_contract.json`
- `artifacts/status/source_coverage_matrix.json`
- `artifacts/status/broad_mirror_progress.json`
- `artifacts/status/p31_local_source_facts.json`
- `artifacts/status/p31_online_source_facts.json`
- `data/raw/protein_data_scope_seed/interpro/interpro.xml.gz`
- `data/raw/protein_data_scope_seed/prosite/prosite.dat`
- `data/raw/protein_data_scope_seed/elm/elm_classes.tsv`
- `data/raw/protein_data_scope_seed/elm/elm_interaction_domains.tsv`
- `data/raw/protein_data_scope_seed/pfam`

## Bottom Line

The best near-term payoff is to materialize the backbone that is already present, then finish `ELM`, then capture `MegaMotifBase`. `motivated_proteins` stays blocked outside the top three until its own surface becomes grounded in a real pinned capture path.
