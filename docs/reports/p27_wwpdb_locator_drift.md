# P27 wwPDB Locator Drift

## Summary

The uploaded `protein_data_scope` manifest used a stale locator for the Chemical Component Model file:

- stale locator:
  - `https://files.wwpdb.org/pub/pdb/data/monomers/chem_comp_model.cif.gz`
- corrected locator:
  - `https://files.wwpdb.org/pub/pdb/data/component-models/complete/chem_comp_model.cif.gz`

## What was verified

On March 23, 2026:

- the stale `monomers` locator returned `HTTP 403`
- sibling files under `monomers` still downloaded successfully:
  - `components.cif.gz`
  - `aa-variants-v1.cif.gz`
- the official wwPDB Chemical Component Dictionary page links the model file from `component-models/complete`
- after updating the manifest, the corrected locator downloaded successfully in the ProteoSphere seed run

## Interpretation

This is locator drift, not an authentication or user-agent problem.

ProteoSphere should therefore:

- classify the old locator as `blocked_stale_locator`
- prefer the wwPDB-linked replacement locator
- preserve provenance on:
  - requested locator
  - resolved locator
  - observed failure status on the stale locator when relevant

## Result

The direct source `pdb_chemical_component_dictionary` no longer has an outstanding procurement blocker from this file path.
