# P62 Structure Follow-up Publication Validation

This is a report-only validation contract for the current `structure_followup_anchor_candidates` slice. It does not claim a promoted `structure_unit` row or a bridge materialization yet.

Source surfaces used:
- [structure_followup_anchor_candidates.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_followup_anchor_candidates.json)
- [p53_structure_unit_operator_surface_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p53_structure_unit_operator_surface_contract.json)
- [p53_structure_unit_publication_validation_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p53_structure_unit_publication_validation_contract.json)
- [p52_structure_unit_materializer_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p52_structure_unit_materializer_contract.json)
- [p61_structure_anchor_evidence_review.json](/D:/documents/ProteoSphereV2/artifacts/status/p61_structure_anchor_evidence_review.json)

## Truth Boundary

`P04637` and `P31749` are still `candidate_only_no_variant_anchor`. The current structure-side truth is that each accession has strong local evidence for a follow-up anchor, but no row yet names one explicit `protein_variant.summary_id` in `variant_ref`.

The contract stays strict on that point:
- no accession-only join is allowed
- no family-level inference is allowed
- no bridge is allowed to substitute for an explicit structure-side anchor
- no protected latest surface may be rewritten

## Candidate Rows

| Accession | Best experimental anchor | AlphaFold coverage | Candidate variant signatures | Missing anchor |
|---|---|---:|---|---|
| `P04637` | `9R2Q` chain `K`, cryo-EM, 3.2 A, span `1-393` | model `AF-P04637-F1`, span `1-393` | `Q5H`, `V10I`, `A119D`, `A129D`, `G389W` | explicit structure-side `variant_ref` |
| `P31749` | `7NH5` chain `A`, X-ray, 1.9 A, span `2-446` | model `AF-P31749-F1`, span `1-480` | `K14Q`, `E17K`, `R25C`, `V167A`, `T435P` | explicit structure-side `variant_ref` |

## Required Validation Gates Before Promotion

Before a candidate row can move into `structure_unit` publication, all of these must pass:

1. The accession must match exactly.
2. One and only one `protein_variant.summary_id` must be written to `variant_ref`.
3. `structure_id`, `chain_id`, `residue_span_start`, and `residue_span_end` must all be explicit.
4. The claimed residue must sit inside the covered UniProt span and the structure-chain span.
5. Operator surfaces must remain truth-bearing only and must not describe the row as complete or release-ready.
6. The join must not be inferred from sequence family, display-name similarity, or any other heuristic.
7. Publication must stay on a versioned or run-scoped output path, never a protected latest file.

For bridge materialization, the bar is the same plus one extra rule:

1. The bridge must reuse the exact same accession, `variant_ref`, `structure_id`, chain, and residue span.
2. The bridge must preserve provenance instead of replacing the structure-side anchor.
3. The bridge must remain one row per explicit anchor pair.
4. The bridge cannot be used before the structure-side `variant_ref` exists.
5. The bridge must not change release-gate status or latest pointers.

## Recommended Operator Action

The truthful next step is to pick exactly one `protein_variant.summary_id` for each accession, write the explicit structure-side anchor, and then re-run operator-surface validation. If any field is inferred or absent, the row stays `candidate_only`.

The key missing piece is the same for both accessions: an explicit structure-side `variant_ref` tied to the structure, chain, and residue span.
