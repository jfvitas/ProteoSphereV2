# P19 Model Portfolio Matrix

Date: 2026-03-23  
Task: `P19-A001`

## Bottom Line

Phase 19 should be treated as a prototype-to-stronger-runtime exploration, not a release claim.

The current repo truth boundary is still:

- the multimodal runtime is prototype-backed with surrogate modality embeddings,
- resume is identity-safe but still prototype-shaped,
- the benchmark corpus is blocked on runtime maturity, source coverage depth, and provenance/reporting depth,
- and the release bundle is assembled with blockers, not release closure.

That means the phase-19 portfolio should rank model and modality combinations by how well they improve truth-preserving utility, not by any implied production readiness.

## Ranking Principles

1. Prefer modalities already grounded by real evidence in the frozen cohort.
2. Prefer architectures that preserve explicit provenance and blocker visibility.
3. Treat mixed evidence, thin coverage, and unresolved rows as valid evaluation outputs.
4. Stop if a candidate requires inventing a production runtime, trainer contract, or corpus-scale provenance that is not yet landed.

## Candidate Portfolio

| Rank | Candidate | Modalities | Why it belongs in Phase 19 | Stop condition |
| --- | --- | --- | --- | --- |
| 1 | Conservative fusion baseline | sequence + structure + ligand + ppi | Best fit for the current prototype runtime and the frozen benchmark slice; keeps the broadest truth-preserving input surface without overcommitting to release behavior. | Stop if the candidate cannot preserve the current blocker taxonomy or requires hidden fallback inputs. |
| 2 | Sequence-first + explicit missingness heads | sequence + missingness metadata | Strongest stability baseline for thin rows and blocked packets; good for verifying whether simple sequence signal plus explicit gaps can carry deterministic replay. | Stop if it collapses unresolved ligand/PPI gaps into clean successes. |
| 3 | Sequence + structure + PPI direct lane | sequence + structure + ppi | Useful for anchors like `P69905`, `P68871`, and `P04637`; tests whether direct interaction evidence improves over the prototype baseline. | Stop if it needs fabricated structure completion or assumes bridge-only evidence is direct. |
| 4 | Ligand-anchored subportfolio | sequence + ligand + ppi | Best for `P31749` and mixed ligand anchors; lets the portfolio measure whether assay-linked ligand evidence improves utility without forcing complete packets. | Stop if bridge-only or structure-linked ligand evidence is flattened into assay-complete evidence. |
| 5 | Thin-row control portfolio | sequence-only or sequence + one extra lane | Needed for the sparse/control rows (`P09105`, `Q9UCM0`, `P69892`, `Q9NZD4`, `Q2TAC2`, `P00387`, `P02042`, `P02100`) so the phase can measure honest failure rather than only rich examples. | Stop if the candidate claims multimodal completeness on single-lane rows. |
| 6 | Mixed-evidence stress portfolio | sequence + ppi + ligand with explicit mixed evidence | Useful for `P68871` and any row where mixed evidence is a feature, not a bug; measures whether the runtime and reporting stay honest under mixed lanes. | Stop if mixed evidence is normalized away or treated as a clean direct hit. |

## Recommended Ablation Order

Use the ablation matrix in this order so the results stay interpretable:

1. Full conservative fusion baseline.
2. Remove ligand lane.
3. Remove PPI lane.
4. Remove structure lane.
5. Sequence-only control.
6. Restore one lane at a time on the strongest anchors.

This order gives the cleanest signal on what the current prototype runtime actually contributes without pretending it is already production-grade.

## Success Metrics

### Primary metrics

- deterministic replay of the same cohort and split decisions,
- identity-safe resume continuity,
- preserved blocker visibility for thin, mixed, and unresolved rows,
- no silent leakage across splits,
- no silent widening of the cohort.

### Scientific metrics

- per-row utility rank on the frozen benchmark slice,
- coverage-aware candidate retention by accession bucket,
- fraction of rows with explicit unresolved or mixed-evidence handling preserved,
- pair/ligand utility on the anchored accessions,
- packet completeness visibility for the strongest rows.

### Operational metrics

- checkpoint writes and resumes,
- run completion rate under the prototype runtime,
- retry count by source,
- wall-clock runtime per candidate family,
- explicit blocker counts by class.

## Stop Conditions

Stop Phase 19 immediately if any of the following occur:

- the candidate architecture requires a production trainer contract that is not landed,
- blocker categories disappear from the outputs,
- mixed evidence or unresolved rows are collapsed into clean successes,
- the cohort widens silently,
- the evaluation uses unpinned or mutable source inputs,
- or the replay path stops being identity-safe.

## Explicit Truth Boundary

Phase 19 can optimize the portfolio around the frozen corpus and the current prototype runtime, but it cannot claim release readiness.

The current evidence still says:

- runtime maturity remains prototype-only,
- source coverage remains thin for most rows,
- provenance/reporting remains incomplete,
- and the release corpus ledger is fully blocked.

So the right question for phase 19 is not "which architecture is release-ready?"
The right question is "which architecture best preserves truth while improving utility inside the current prototype boundary?"

## Recommendation

Start with the conservative fusion baseline, then ablate ligand, PPI, and structure one at a time. Keep a sequence-first control lane and a mixed-evidence stress lane so the phase can measure honest degradation rather than only aggregate performance.

That gives the strongest signal for choosing a future production candidate without overclaiming beyond the current runtime state.
