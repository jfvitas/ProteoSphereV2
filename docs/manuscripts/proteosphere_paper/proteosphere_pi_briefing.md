# PI Briefing: ProteoSphere Manuscript Draft

## What We Built

ProteoSphere is now strong enough to be described as a real dataset-review system rather than a collection of one-off audits. The core idea is simple and valuable: instead of forcing every benchmark review to reopen a huge raw source estate, ProteoSphere places a compact, release-pinned evidence warehouse in front of that estate and uses it as the first truth surface for overlap checks, provenance review, and training-set admissibility decisions.

The local warehouse is rooted at `D:\ProteoSphere\reference_library` and defaults to a `best_evidence` view. It currently materializes compact but high-value families for proteins, variants, structures, ligands, interaction edges, annotation/site context, pathway roles, provenance, materialization routes, leakage groups, and similarity signatures. Heavy payloads are deliberately deferred until needed.

## Why This Matters Scientifically

The paper’s scientific importance is that it makes dataset review visible, reproducible, and practical. We are not just arguing that leakage exists in principle. We have a proof-backed review package showing that:

- recent biomolecular interaction ML papers still contain serious train/test or external-validation problems;
- those problems are often not obvious from paper prose alone;
- a warehouse-first reviewer can recover them reproducibly from released code, split files, and supplemental materials;
- the same reviewer can also validate stronger or mitigation-aware benchmark designs.

That last point matters a lot. The paper is stronger because ProteoSphere is not just a takedown tool. It is a decision tool.

## Strongest Results To Emphasize

The current flagship proof set contains 29 confirmed Tier 1 hard-failure papers, including 18 from 2023 or later. The strongest examples are:

- **Struct2Graph**: direct, code-reproduced train/test structure reuse.
- **D2CP05644E**: nominally external validation sets that are not actually independent.
- **AttentionDTA**: row-level random CV that preserves compound and target reuse across folds.
- **DeepDTA-setting-1 family**: a warm-start benchmark lineage inherited by many later papers.
- **PDBbind core-family**: a widely used “external” evaluation family that still retains direct protein overlap.

These cases let us tell a balanced but persuasive story: the problem is current, not historical; it is recoverable, not speculative; and it affects both paper-specific splits and benchmark families that many later papers inherit.

## What We Should And Should Not Claim

The paper is in very good shape if we stay disciplined about a few boundaries.

We **should** claim that:

- ProteoSphere is operationally effective for warehouse-first dataset review.
- The current proof set shows recurring, recent benchmark failures that materially change interpretation.
- A compact evidence warehouse makes this kind of review practical.

We **should not** claim, at least in this draft, that:

- the warehouse is a full evidence-equivalent replacement for every raw source surface;
- the current paper set gives a field-wide prevalence estimate;
- every Tier 1 paper is broken in the same way or to the same degree;
- the system condenses “>2 TB to ~25 GB” unless we create a dedicated proof artifact for that exact number.

## Publication Outlook

This is publishable if framed as a methods-and-governance paper rather than as a blanket critique of the field. The most natural journal lane is somewhere in the Bioinformatics / Briefings in Bioinformatics / NAR-methods corridor, with JCIM or Patterns also plausible depending on how strongly we emphasize the interaction-ML review angle versus the warehouse/system angle.

My honest assessment is:

- quality: strong;
- novelty: strong;
- publishability: strong if carefully framed and visually polished.

## What This Draft Gives You Now

The current package should give you a concrete manuscript to discuss rather than a concept note. It includes:

- a near-submission draft manuscript;
- a supplement with the Tier 1 paper table and truth boundaries;
- a generated figure set;
- a claim ledger tying sensitive statements to local evidence;
- a short storage-footprint note so the compact-warehouse story is grounded in current measurements rather than rough memory.

## Best Next Step After PI Review

If the scientific direction is approved, the highest-value next step is not more general prose. It is targeted strengthening:

- add a few more non-DTA direct hard-failure cases if possible;
- tighten the introduction and discussion to a journal-specific lane;
- convert the local evidence citations into journal-style references and supplementary note numbering;
- keep the paper constructive and adoption-oriented.
