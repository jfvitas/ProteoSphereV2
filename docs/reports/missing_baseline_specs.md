# Baseline Input Status

The original bootstrap started before the authoritative handoff package was present. That blocker is now resolved.

Now present:

- `master_handoff_package/`
- `ml_platform_level3_spec/`
- `protein_execution_canonical_spec/`
- `protein_platform_lockdown_spec/`
- `protein_platform_max_complete_spec/`

Current interpretation:

- the master handoff package is now authoritative
- the lockdown spec defines the exact first working build
- the execution and canonical spec defines correctness requirements
- the max-complete spec defines expansion and release-grade completeness

Remaining open items are narrower than before:

- any places where the current bootstrap primitives are weaker than the authoritative spec
- exact third-party runtime setup details for heavy dependencies such as ESM2, RDKit, MMseqs2, and related feature backends
- any contradictions discovered between earlier placeholder work and the newly authoritative contracts

Current handling:

- do not guess when the master handoff package is explicit
- treat existing early implementations as bootstrap placeholders if the authoritative spec requires richer behavior
- log blockers only for true unresolved runtime or source issues, not for the baseline architecture itself
