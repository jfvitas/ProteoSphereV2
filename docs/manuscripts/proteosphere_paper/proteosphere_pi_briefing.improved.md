# PI Briefing: ProteoSphere Manuscript

## Bottom line

ProteoSphere is a working dataset reviewer, not a concept note. It runs a compact, release-pinned evidence warehouse in front of a multi-terabyte source estate, exposes a default `best_evidence` view, and applies a code-driven audit layer that maps each benchmark paper to a canonical split policy, measures overlap at five biological levels, and assigns one of six admissibility verdicts. It has already produced a proof-backed Tier 1 set of 29 hard-failure papers — 18 of them from 2023 or later — organized into four distinct failure classes. The manuscript is publishable as a methods-and-governance paper in the Briefings in Bioinformatics / NAR Methods / JCIM / Patterns corridor.

## Why this is a real paper

Three things separate this from the usual "benchmark leakage exists" commentary.

1. **A system, not an anecdote.** Thirteen materialized record families, a `best_evidence` claim surface, a release-pinned source contract, and a registry-driven materialization layer. A reviewer can actually run the pipeline on a new paper.
2. **A taxonomy, not a complaint.** Six canonical split policies, twelve reason codes, six verdicts, and an explicit human-review gate. Each paper in the proof set is labelled the same way.
3. **Recoverable evidence, not memory.** All 29 Tier 1 article PDFs and 119 supplemental items are locally bundled. Every quantitative claim in the flagship cases traces to a JSON or Markdown audit artifact.

## The five cases to lead with

- **Struct2Graph (2022).** Released `create_examples.py` reproduces with 643 shared PDB IDs across train/test; 4EQ6 alone appears 78× in train and 9× in test.
- **Silva *et al.* 2023 (D2CP05644E).** All three "external" panels (PDBbind, nanobody, metadynamics) are contaminated by direct protein, exact-sequence, and shared-partner overlap. The metadynamics panel reuses 26 of its own structures.
- **DeepDTA setting-1.** On Davis *and* KIBA, every test drug and every test target appears in training. Fourteen downstream Tier 1 papers inherit this split.
- **PDBbind core (v2013, v2016).** 108/108 (v2013) and 288/290 (v2016) test complexes carry direct protein overlap with the remaining pool. Twelve downstream Tier 1 papers inherit this family.
- **AttentionDTA (2023).** Shuffling the interaction table before random-CV preserves every drug and target across folds on all three evaluation datasets.

These are deliberately four different classes of failure. The paper is strongest when that is preserved explicitly.

## Where we should be disciplined

**Claim.** ProteoSphere is operationally effective for warehouse-first review; it recovers recurring, recent benchmark failures that materially change interpretation; a compact evidence warehouse makes routine audit practical.

**Do not claim.** That the warehouse is a full evidence-equivalent replacement for every raw source; that the proof set is a field-wide prevalence estimate; that every Tier 1 paper fails in the same way; or any specific condensation ratio (the "≈2 TB → ≈25 GB" phrase is explicitly avoided pending a dedicated proof artifact).

## Publication assessment

- **Quality.** Strong. System is real and validated; proof set is recoverable.
- **Novelty.** Strong. The warehouse-first framing and the canonical reason-code/verdict contract are not standard in the field.
- **Publishability.** Strong, conditional on framing this as a methods-and-governance paper rather than a blanket critique.
- **Target venues (ranked).** Briefings in Bioinformatics (best fit — methods + governance); NAR Methods (fit — database/resource angle); JCIM (fit if DTA emphasis is retained); Patterns (fit if the data-governance framing is foregrounded).

## What changed in this revision

- Abstract restructured into the Briefings style (Motivation / Results / Conclusions / Availability).
- Verbose meta-commentary removed; each boundary stated once.
- A compact Table 1 (warehouse families) and Table 2 (flagship overlaps) added so reviewers can see the claims at a glance.
- Reference list converted from local file paths to twenty journal DOIs.
- Figure set regenerated without the watermarked Struct2Graph asset and with a consistent professional palette.
- Supplement and this memo rewritten so they complement, rather than duplicate, the main draft.

## Next steps before submission

1. **Protein–protein expansion.** Three to five more non-DTA direct-failure cases would remove the strongest reviewer objection (scope concentration).
2. **Independent manual check on one flagship case.** Struct2Graph or AttentionDTA is ideal — the reproduction is short, and a hand-check strengthens the methods paper claim.
3. **Pre-register the public release.** Warehouse manifest, source registry (STRING / PDBbind excluded), audit code, proof bundle, claim ledger, figure manifest. A DOI'd Zenodo deposit is the cleanest route.
4. **Venue-specific framing pass.** A short tightening of Intro §1 and Discussion §7 to the chosen journal's lane (methods vs. database vs. governance).

## Files in this revision

- `proteosphere_manuscript_draft.improved.md` — rewritten main draft.
- `proteosphere_supplementary_appendix.improved.md` — rewritten supplement.
- `proteosphere_pi_briefing.improved.md` — this memo.
- `scripts/generate_figures.improved.py` — regenerates the six figures into `output/pdf/proteosphere_paper_assets/` with a consistent palette and no watermarked assets.
