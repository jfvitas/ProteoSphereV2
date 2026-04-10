# P71 Namespace Inventory Preview Family

This report-only note inventories the live reference namespaces visible in the protein summary, variant summary, and structure summary artifacts and identifies the best current candidates for a dictionary preview family.

## Live Sources Inspected

- [artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [artifacts/status/protein_variant_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_variant_summary_library.json)
- [artifacts/status/structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)
- [artifacts/status/summary_library_inventory.json](/D:/documents/ProteoSphereV2/artifacts/status/summary_library_inventory.json)
- [artifacts/status/protein_variant_summary_library_inventory.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_variant_summary_library_inventory.json)
- [artifacts/status/structure_unit_summary_library_inventory.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library_inventory.json)

## What Is Actually Present

The live namespace-bearing references are concentrated in the protein and structure summary artifacts. The protein-variant summary currently has no namespace-bearing reference arrays, so it is not a preview-family candidate yet.

### Protein Summary

11 protein records contain the following namespace-bearing references:

| Namespace | Reference Count | Records Touched | Preview Family Hint |
|---|---:|---:|---|
| Reactome | 254 | 3 | pathway |
| InterPro | 61 | 11 | domain |
| Pfam | 16 | 10 | domain |
| PROSITE | 13 | 9 | motif |
| CATH | 4 | 2 | structure |
| SCOPe | 4 | 2 | structure |
| IntAct | 2 | 1 | interaction / cross-reference |

### Variant Summary

1874 protein-variant records are present, but none of them currently expose namespace-bearing `motif_references`, `domain_references`, `pathway_references`, or `cross_references`.

That means:

- zero current namespace inventory from the variant summary
- no dictionary-preview family candidate from this artifact yet
- the artifact is still useful as a lineage/identity layer, not a namespace dictionary layer

### Structure Summary

4 structure-unit records contain the following namespace-bearing references:

| Namespace | Reference Count | Records Touched | Preview Family Hint |
|---|---:|---:|---|
| CATH | 4 | 4 | structure |
| SCOPe | 4 | 4 | structure |

## Best Dictionary Preview Candidates

Ranked by live reference volume and current usefulness for a preview family:

1. Reactome: 254 refs across 3 protein records.
1. InterPro: 61 refs across 11 protein records.
1. Pfam: 16 refs across 10 protein records.
1. PROSITE: 13 refs across 9 protein records.
1. CATH: 8 total refs across protein and structure summaries.
1. SCOPe: 8 total refs across protein and structure summaries.
1. IntAct: 2 refs across 1 protein record.

## Notes on Exclusions

- ELM is not currently present as a namespace-bearing reference in these live summary artifacts. The protein summary only records it as a partial registry lane, so it is not a preview-family candidate yet.
- The protein-variant summary has 1874 records, but no namespace-bearing reference arrays to inventory.
- The operator dashboard and release-grade blockers are outside the namespace inventory and are not treated as dictionary candidates.

## Bottom Line

The strongest preview-family candidates right now are Reactome, InterPro, Pfam, and PROSITE from the protein summary, plus CATH and SCOPe from the protein and structure summaries. The variant summary is not yet a namespace-bearing candidate.
