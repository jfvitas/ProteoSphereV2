# External Cohort Audit

## What Was Audited
- Manifest id: `benchmark-cohort-manifest-2026-03-22`
- Split policy: `accession-level only`
- Split counts: `{"resolved": 12, "test": 2, "total": 12, "train": 8, "unresolved": 0, "val": 2}`
- Bucket counts: `{"moderate_coverage": 4, "rich_coverage": 4, "sparse_or_control": 4}`

## Audit Result
- Imbalance: `attention_needed`
- Leakage: `ok`
- Coverage gaps: `attention_needed`
- Ligand follow-through: `attention_needed` / `keep_ligand_split_non_governing`
- Modality readiness: `attention_needed` / `{"interaction": {"absent": 10, "candidate-only non-governing": 2}, "kinetics": {"absent": 9, "support-only": 3}, "ligand": {"absent": 1, "candidate-only non-governing": 1, "grounded preview-safe": 1, "support-only": 9}, "motif_domain": {"absent": 1, "grounded preview-safe": 11}, "structure": {"absent": 1, "grounded governing": 2, "support-only": 9}}`
- Ligand readiness ladder counts: `{"absent": 1, "candidate-only non-governing": 1, "grounded preview-safe": 1, "support-only": 9}`
- Overall: `attention_needed` / `usable_with_notes`

## Ligand Follow-Through
- Grounded accessions: `P00387`
- Candidate-only accessions: `Q9NZD4`
- Blocked accessions: `Q9UCM0`
- Library-only accessions: `P02042, P02100, P04637, P31749, P68871, P69892, P69905`
- Readiness ladder accessions:
  - grounded preview-safe: `P00387`
  - grounded governing: `none`
  - candidate-only non-governing: `Q9NZD4`
  - support-only: `P02042, P02100, P04637, P09105, P31749, P68871, P69892, P69905, Q2TAC2`
  - absent: `Q9UCM0`

## Recommended Next Action
- Keep the audited split read-only and do not silently widen or reshuffle it.
- Treat accession-level leakage as the hard floor for any external audit.
- Review sparse or coverage-skewed buckets before claiming broad generalization.
- Use packet deficit rows to explain missing-modality bias in the audited split.
- Do not let ligand-aware split behavior govern this audited cohort while only one grounded ligand accession is present.
