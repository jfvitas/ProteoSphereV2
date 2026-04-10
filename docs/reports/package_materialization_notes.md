# Package Materialization Notes

This integration pass validates the selected-example storage path end to end:

- a package manifest with pinned raw-manifest lineage and explicit selected examples
- a planning index row for the selected example
- canonical-store presence for the selected canonical record
- feature and embedding caches with pinned artifact pointers
- selective materialization of only the selected example artifacts
- package assembly through the storage runtime into a finalized training package

Observed behavior:

- when the planning index, canonical record, and selected artifacts are present, the runtime returns `integrated`
- the resulting package keeps the selected-example set unchanged
- provenance stays explicit, including raw-manifest and package lineage
- when planning or cache inputs are missing, the runtime reports explicit issues and downgrades to `partial`

This confirms the storage runtime remains conservative and reproducible for selected-example-only package assembly.
