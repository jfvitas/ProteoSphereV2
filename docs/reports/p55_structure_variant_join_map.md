# Structure-Variant Join Map

- Generated at: `2026-04-01T11:28:06.0244883-05:00`
- Scope: report-only structure-plus-variant join mapping note for the first executable slice
- Basis: the landed structure-unit library, the structure-unit materializer contract, and the proposed variant evidence hunt

## Join Rule

Join on `protein_ref`, then require an explicit `variant_signature` before any structure-plus-variant join is considered truthful. `variant_ref` must stay explicit and must not be inferred from chain, family, or naming similarity.

## Materialized Structure-Unit Rows

The current structure-unit library contains four rows:

- `structure_unit:protein:P68871:4HHB:B`
- `structure_unit:protein:P68871:4HHB:D`
- `structure_unit:protein:P69905:4HHB:A`
- `structure_unit:protein:P69905:4HHB:C`

All four rows are `feature_cache` records with `variant_ref = null`, so none of them can truthfully join to a variant record yet.

## Proposed Variant Slice

The supported first protein-variant slice currently covers:

- `P04637`
- `P31749`

Those proposed variant records are accession-scoped and mutation/isoform-oriented. They do not currently share accession anchors with the structure-unit rows above.

## Join Map

There are no direct joinable pairs yet.

- `P68871` and `P69905` are the structure-unit accessions.
- `P04637` and `P31749` are the proposed variant accessions.
- The current verdict is `disjoint_accessions`.

Blocked pairs:

- `structure_unit:protein:P68871:4HHB:B` remains blocked because the proposed variant records do not support `P68871`.
- `structure_unit:protein:P68871:4HHB:D` remains blocked because the proposed variant records do not support `P68871`.
- `structure_unit:protein:P69905:4HHB:A` remains blocked because the proposed variant records do not support `P69905`.
- `structure_unit:protein:P69905:4HHB:C` remains blocked because the proposed variant records do not support `P69905`.

## First Executable Slice

The first executable structure-plus-variant join slice is still blocked.

To unlock it truthfully, we would need one of the following:

- a proposed variant record for `P68871` or `P69905` with an explicit `variant_signature`
- or a structure-unit record for `P04637` or `P31749` with an explicit `variant_ref`

Until then, the right report is a boundary note, not a fabricated join.

## What This Is Not

- No code edits.
- No invented variant support for `P68871` or `P69905`.
- No invented structure-unit support for `P04637` or `P31749`.
- No implicit join on names, family membership, or chain similarity.

## Evidence Anchors

- [`structure_unit_summary_library.json`](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)
- [`p53_protein_variant_materializer_contract.json`](/D:/documents/ProteoSphereV2/artifacts/status/p53_protein_variant_materializer_contract.json)
- [`p54_variant_evidence_hunt.json`](/D:/documents/ProteoSphereV2/artifacts/status/p54_variant_evidence_hunt.json)
- [`structure_unit_summary_library.md`](/D:/documents/ProteoSphereV2/docs/reports/structure_unit_summary_library.md)
- [`p53_protein_variant_materializer_contract.md`](/D:/documents/ProteoSphereV2/docs/reports/p53_protein_variant_materializer_contract.md)
- [`p54_variant_evidence_hunt.md`](/D:/documents/ProteoSphereV2/docs/reports/p54_variant_evidence_hunt.md)
- [`p52_structure_unit_materializer_contract.md`](/D:/documents/ProteoSphereV2/docs/reports/p52_structure_unit_materializer_contract.md)
- [`execution_wave_2_status.md`](/D:/documents/ProteoSphereV2/docs/reports/execution_wave_2_status.md)

