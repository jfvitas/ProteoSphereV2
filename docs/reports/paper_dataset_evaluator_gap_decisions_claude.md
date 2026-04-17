# ProteoSphere Paper Dataset Evaluator — LLM Gap Bridge Decisions

**Artifact ID:** `paper_dataset_evaluator_gap_decisions_claude`  
**Mode:** Gap-bridge (bounded LLM review of code-first escalations only)  
**Source report:** `paper_dataset_evaluator_report`  
**Gap packet:** `paper_dataset_evaluator_llm_gap_packet` (7 papers escalated)  
**Decided:** 2026-04-13  
**Evidence basis:** `best_evidence` logical view — warehouse-first, no raw/archive fallback

---

## Decision Summary

All 7 escalated papers had code-first verdicts and policy mappings that are correct under conservative ProteoSphere logic. No verdict or policy overrides were issued. The sole change across all 7 papers is the clearing of `needs_human_review` from `true` to `false`.

| paper_id | code-first verdict | LLM verdict | policy override | needs_human_review (before → after) |
|---|---|---|---|---|
| zhang2012preppi | `audit_only` | `audit_only` | none | true → **false** |
| sun2017sequence | `unsafe_for_training` | `unsafe_for_training` | none | true → **false** |
| du2017deepppi | `blocked_pending_mapping` | `blocked_pending_mapping` | none | true → **false** |
| hashemifar2018dppi | `blocked_pending_mapping` | `blocked_pending_mapping` | none | true → **false** |
| chen2019siamese_rcnn | `blocked_pending_mapping` | `blocked_pending_mapping` | none | true → **false** |
| sledzieski2021dscript | `audit_only` | `audit_only` | none | true → **false** |
| szymborski2022rapppid | `audit_only` | `audit_only` | none | true → **false** |

---

## Per-Paper Rationale

### zhang2012preppi — `audit_only` (unchanged)
Zero roster membership; the paper describes a genome-scale discovery workflow with no recoverable train/test boundary. Policy maps to `paper_faithful_external` with `recommended_for_training=false`. STRING is internal-only. All four reason codes are accurate. The outcome is deterministic, not ambiguous — `needs_human_review` cleared.

### sun2017sequence — `unsafe_for_training` (unchanged)
10-fold cross-validation fails ProteoSphere's stable holdout policy (POLICY_MISMATCH). This is a rule-driven, unambiguous outcome aligned with the evaluation rubric's example for CV papers. STRING is internal-only. `needs_human_review` cleared: CV policy failure is not a judgment call.

### du2017deepppi — `blocked_pending_mapping` (unchanged)
Held-out test claimed with no roster and no grouping rule. `accession_grouped` is the correct canonical mapping for a plain held-out test. STRING is internal-only. All four reason codes accurate. `needs_human_review` cleared: zero-roster + no-grouping-rule is an unambiguous blocking condition.

### hashemifar2018dppi — `blocked_pending_mapping` (unchanged)
Named benchmarks (S. cerevisiae core subset, homodimers) without membership evidence. Naming a benchmark ≠ supplying its roster. Same pattern as du2017deepppi. `needs_human_review` cleared.

### chen2019siamese_rcnn — `blocked_pending_mapping` (unchanged)
SHS27k and SHS148k are STRING-derived benchmarks. The STRING internal-only coverage gap is especially well-grounded here because the benchmarks themselves originate from STRING. Even naming the benchmarks does not resolve membership through the `best_evidence` surface. `needs_human_review` cleared.

### sledzieski2021dscript — `audit_only` (unchanged)
The cross-species split (human train / Drosophila test) is conceptually clear and both source families are redistributable. However, the policy resolves to `paper_faithful_external` with `recommended_for_training=false`, and the `protein_protein_edges` surface does not materialize IntAct roster rows at the depth needed. Note: `AUDIT_ONLY_EVIDENCE` was not added — IntAct and UniProt are redistributable; the gap is specifically best_evidence surface depth (WAREHOUSE_COVERAGE_GAP). The three existing reason codes are sufficient. `needs_human_review` cleared: `paper_faithful_only` determination is unambiguous.

### szymborski2022rapppid — `audit_only` (unchanged)
Strict unseen-protein claim maps correctly to `uniref_grouped` with `recommended_for_training=true`. The split would be strong if verified. However, no roster is supplied and STRING is internal-only. `audit_only` is correct: credible methodology useful for comparison, but not a governing split without roster + STRING gap resolution. `needs_human_review` cleared.

---

## Common Pattern Across All 7

The code-first evaluator set `needs_human_review=true` for all 7 papers in this packet. In each case, review of the paper wording and warehouse evidence surfaces confirms the escalation was a false positive on the review gate: all 7 outcomes are deterministic under conservative ProteoSphere logic. Quoting the `human_review_gate.md` authority: *"Do not set it merely because the verdict is negative. A clear deterministic failure should stay code- and rule-driven."*

No paper in this packet has:
- Genuinely ambiguous split parse
- Multiple plausible canonical policies that cannot be resolved by the wording
- A warehouse coverage situation that prevents a reliable conclusion

All 7 escalations reduce to: missing roster + source coverage gap = deterministic blocking/audit outcome.

---

*Gap-bridge mode: only escalated papers reviewed. Non-escalated papers from the base report are unchanged.*
