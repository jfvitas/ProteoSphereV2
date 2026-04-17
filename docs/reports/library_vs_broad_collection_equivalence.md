# Library vs Broad Collection Equivalence

- Final verdict: `status_equivalent_but_not_evidence_equivalent`
- Overlap papers compared: `20`
- Status matches: `20` / `20` (100.0%)
- Supplemental-artifact paper matches: `3` / `3` (100.0%)
- Reference library validation: `passed`
- Raw-disconnected acceptance: `passed`

## Bottom Line

The condensed warehouse is operational and preserves much of the high-level evaluation behavior, but it is not yet a full evidence-equivalent replacement for the broader downloaded collection.

## Key Findings

- The condensed library supports warehouse-first evaluation and remains operational even when raw/archive roots are masked.
- The current code-first warehouse evaluator matches 20 of 20 top-level paper status outcomes against the broader audit path.
- For the three papers with recovered published split artifacts, the library-backed evaluator matches the broader audit path at the top-level status and now exposes warehouse-side identifier bridge summaries for D-SCRIPT and RAPPPID.
- The broader downloaded collection still preserves roster-, identifier-, and structure-level evidence that is not fully materialized into the condensed warehouse default surfaces.

## Mismatches

- None

## Detail Loss Case Studies

- `baranwal2022struct2graph`: same top-level unsafe outcome, but the broader path reproduces `643` shared PDB IDs across train/test from released split logic while the warehouse-first evaluator does not preserve that concrete reproduction evidence.
- `sledzieski2021dscript`: same audit-only outcome, and the warehouse now preserves identifier-bridge coverage plus overlap summaries, but the broader path still retains the raw recovered split files as a richer artifact surface.
- `szymborski2022rapppid`: same audit-only outcome, and the warehouse now preserves STRING/Ensembl bridge coverage plus cohort-level overlap summaries, but the broader path still retains the recovered C1/C2/C3 release package as the richer raw artifact surface.
- `10.1039/D2CP05644E`: the broader structure-audit path emits exact overlap counts, coverage fractions, and blocked reasons; there is no like-for-like warehouse-first default artifact with that same level of detail today.

## Recommended Interpretation

- Library is sufficient for: warehouse-first planning and governance
- Library is sufficient for: high-level paper admissibility screening
- Library is sufficient for: stable top-level outcomes for some recovered split-artifact papers
- Library is sufficient for: raw-disconnected Studio and evaluator workflows
- Library is not yet equivalent for: full paper-specific roster reconstruction
- Library is not yet equivalent for: full raw artifact reproduction for identifier-bridge-heavy external split audits
- Library is not yet equivalent for: structure-level overlap reproduction with exact flagged-pair counts
- Library is not yet equivalent for: all paper verdicts matching the broader audit path

## Next Repairs

- materialize paper-membership or benchmark-roster surfaces into the warehouse where licensing permits
- extend the new paper-side identifier bridge registry beyond D-SCRIPT and RAPPPID and promote more of it into default warehouse resolution paths
- capture recovered published split artifacts into a governed warehouse-facing audit surface instead of leaving them only in supplemental external artifacts
- materialize structure-side audit reproductions like the Struct2Graph shared-PDB proof into warehouse-facing audit surfaces
