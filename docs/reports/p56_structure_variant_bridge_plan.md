# P56 Structure-Variant Bridge Plan

This report-only plan closes the current `disjoint_accessions` gap by taking the variant side toward the structure-unit accessions already present in the repo, rather than inventing a structure match for the first variant slice.

## Current State

The join map is still blocked because the materialized structure-unit rows are anchored on `P68871` and `P69905`, while the first supported variant slice is anchored on `P04637` and `P31749`.

- Structure-unit accessions: `P68871`, `P69905`
- First variant-slice accessions: `P04637`, `P31749`
- Current verdict: `disjoint_accessions`

The key truth boundary is simple: there is no shared accession yet, so no direct join should be claimed.

## Ranked Bridge Actions

1. Materialize accession-scoped variant rows for `P68871` from local UniProt evidence.
   - Exact local sources: `data/raw/uniprot/20260323T154140Z/P68871/P68871.txt`, `data/raw/uniprot/20260323T154140Z/P68871/P68871.json`, `data/raw/rcsb_pdbe/20260323T154140Z/P68871/1DXT/1DXT.entry.json`, `data/raw/intact/20260323T154140Z/P68871/P68871.psicquic.tab25.txt`
   - Why first: the local UniProt payload already contains explicit variant lines, so this is the narrowest truthful bridge from the current structure-unit library into the variant layer.
   - Success criterion: at least one `protein_variant` record with `protein_ref = P68871` and an explicit `variant_signature`.

2. Materialize accession-scoped variant rows for `P69905` from local UniProt evidence.
   - Exact local sources: `data/raw/uniprot/20260323T154140Z/P69905/P69905.txt`, `data/raw/uniprot/20260323T154140Z/P69905/P69905.json`, `data/raw/rcsb_pdbe/20260323T154140Z/P69905/1BAB/1BAB.entry.json`, `data/raw/intact/20260323T154140Z/P69905/P69905.psicquic.tab25.txt`
   - Why second: the alpha-chain accession is equally variant-rich locally, but it is a second bridge lane after `P68871`.
   - Success criterion: at least one `protein_variant` record with `protein_ref = P69905` and an explicit `variant_signature`.

3. Refresh the join map and packet-facing surfaces after the new variant rows exist.
   - Exact basis artifacts: `artifacts/status/p55_structure_variant_join_map.json`, `artifacts/status/structure_unit_summary_library.json`, `artifacts/status/p53_protein_variant_materializer_contract.json`
   - Success criterion: the bridge report can point to at least one accession that exists on both sides.

## Blocked Route

The structure-side route for `P04637` or `P31749` remains blocked because the current structure-unit library does not contain those accessions.

- Blocked status: acquisition-bound
- Current evidence checked: `artifacts/status/structure_unit_summary_library.json`, `artifacts/status/p55_structure_variant_join_map.json`, `artifacts/status/p54_variant_evidence_hunt.json`
- Safe next step if structure-side closure is ever needed: procure a matching structure-unit accession for `P04637` or `P31749`

## Validation Boundary

This is report-only. It does not edit code, it does not weaken latest-promotion guards, and it keeps the protected latest surfaces untouched.

