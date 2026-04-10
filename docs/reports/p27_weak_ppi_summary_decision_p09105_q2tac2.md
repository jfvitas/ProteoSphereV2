# Weak PPI Candidate Summary Decision

Date: 2026-03-23

## Artifact

- `artifacts/status/p27_weak_ppi_summary_decision_p09105_q2tac2.json`
- `docs/reports/p27_weak_ppi_summary_decision_p09105_q2tac2.md`

## Scope

- Source: `IntAct`
- Snapshot: `data\raw\intact\20260323T182231Z`
- Accessions: P09105, Q2TAC2

## Decision Summary

- Summary-library inclusion allowed: `True`
- Strong curated packet-ready PPI allowed: `False`
- Direct binary claims allowed: `False`
- Self rows must be excluded: `True`

## Accessions

| accession | include in summary library | confidence tier | classification | total / non-self / self / unique pairs | packet-ready | blockers |
| --- | --- | --- | --- | --- | --- | --- |
| P09105 | true | weak | weak_non_direct_summary_candidate | 5 / 5 / 0 / 4 | false | no_direct_binary_confirmation, curated_assay_context_not_packet_ready |
| Q2TAC2 | true | weak | weak_noisy_summary_candidate | 5 / 4 / 1 / 4 | false | self_rows_must_be_excluded_from_pair_summaries, heterogeneous_assay_methods, mixed_interaction_types, no_direct_binary_confirmation, curated_assay_context_not_packet_ready |

## Entry Notes

### P09105
- 5 total IntAct rows observed for P09105
- 5 non-self rows remain after exclusion
- 1 duplicate non-self row(s) repeat existing pair evidence
- all non-self rows use the same assay family: psi-mi:"MI:0397"(two hybrid array)
- interaction types observed: psi-mi:"MI:0915"(physical association)
- the rows provide curated interaction context, but not direct-binary packet-ready proof
- 4 unique non-self pair(s) are usable for summary inclusion

### Q2TAC2
- 5 total IntAct rows observed for Q2TAC2
- 4 non-self rows remain after exclusion
- 1 self row(s) must be excluded from pair summaries
- assay methods are heterogeneous: psi-mi:"MI:0007"(anti tag coimmunoprecipitation), psi-mi:"MI:0397"(two hybrid array), psi-mi:"MI:0399"(two hybrid fragment pooling approach), psi-mi:"MI:0729"(luminescence based mammalian interactome mapping), psi-mi:"MI:1356"(validated two hybrid)
- interaction types observed: psi-mi:"MI:0914"(association), psi-mi:"MI:0915"(physical association)
- the rows provide curated interaction context, but not direct-binary packet-ready proof
- 4 unique non-self pair(s) are usable for summary inclusion

## Interpretation

Both accessions are suitable for summary-library inclusion at weak confidence, but neither should be promoted to strong curated packet-ready PPI evidence. `P09105` is all non-self rows yet remains assay-style, non-direct evidence with one duplicated partner pair in the slice. `Q2TAC2` is weaker still because one self row must be removed and the remaining rows span heterogeneous IntAct assay methods without direct-binary confirmation.