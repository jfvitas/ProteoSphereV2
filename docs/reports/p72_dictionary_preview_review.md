# P72 Dictionary Preview Review

This report-only note reviews the newly materialized dictionary preview and summarizes its grounded namespace and record composition.

## Source Artifacts

- [artifacts/status/dictionary_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/dictionary_preview.json)
- [docs/reports/dictionary_preview.md](/D:/documents/ProteoSphereV2/docs/reports/dictionary_preview.md)
- [artifacts/status/p71_namespace_inventory_preview_family.json](/D:/documents/ProteoSphereV2/artifacts/status/p71_namespace_inventory_preview_family.json)
- [docs/reports/p71_namespace_inventory_preview_family.md](/D:/documents/ProteoSphereV2/docs/reports/p71_namespace_inventory_preview_family.md)
- [artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [artifacts/status/protein_variant_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_variant_summary_library.json)
- [artifacts/status/structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)

## What The Preview Contains

The preview is a compact lookup surface, not a new biological acquisition family.

- Rows: `275`
- Namespaces: `7`
- Reference kinds:
  - `pathway`: `216`
  - `domain`: `49`
  - `motif`: `8`
  - `cross_reference`: `2`

## Grounded Namespace Composition

### By Namespace

| Namespace | Uses | Supporting Records | Preview Role |
|---|---:|---:|---|
| Reactome | 216 | 3 protein records | pathway |
| InterPro | 36 | 11 protein records | domain |
| Pfam | 11 | 10 protein records | domain |
| PROSITE | 8 | 9 protein records | motif |
| IntAct | 2 | 1 protein record | cross-reference / interaction |
| CATH | 1 | 1 structure-backed row | structure |
| SCOPe | 1 | 1 structure-backed row | structure |

### By Record Ownership

- `protein`-owned rows: `275`
- `structure_unit`-owned rows: `2`

The structure-owned rows are the only dual-purpose rows in the preview. Everything else is protein-owned.

## What This Means

The preview is strongest as a dictionary surface for:

1. Reactome pathway labels and identifiers.
1. InterPro domain identifiers.
1. Pfam domain identifiers.
1. PROSITE motif identifiers.
1. A small CATH and SCOPe structure preview.
1. A minimal IntAct interaction/cross-reference preview.

## Low-Risk Follow-Ups

- Add a small ELM preview family only after accession-scoped ELM namespace rows exist in the live summary artifacts.
- Keep Reactome as a dedicated pathway family, because it is the largest and cleanest namespace block in the preview.
- Separate structure-backed dictionary rows from protein-backed rows in any next preview so the dual ownership remains obvious.
- Add a compact per-namespace provenance count line in the preview report if operators need a quicker review surface.
- Promote the protein-variant summary into the dictionary preview only if it starts carrying namespace-bearing reference arrays; right now it does not.

## Truth-Boundary Cautions

- This preview is a lookup and packaging aid, not a completeness claim.
- It is not a new biological acquisition family.
- It reflects only the live summary-library reference rows already present in the current artifacts.
- It does not infer namespaces that are absent from the live reference arrays.
- The protein-variant summary is a lineage/identity layer today, not a namespace dictionary layer.

## Bottom Line

The preview is well-formed and useful as a compact bundle-preview lookup surface. Reactome, InterPro, Pfam, and PROSITE are the clearest candidates for continued dictionary preview work, while CATH, SCOPe, and IntAct are smaller but still grounded live namespaces.
