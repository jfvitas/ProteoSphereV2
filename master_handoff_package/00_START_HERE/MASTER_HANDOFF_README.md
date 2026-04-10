# MASTER HANDOFF PACKAGE

This package is the single handoff bundle for coding agents.

## Required execution order
1. Read `00_START_HERE/MASTER_HANDOFF_README.md`
2. Read `00_START_HERE/AGENT_EXECUTION_ORDER.md`
3. Implement the Lockdown Spec first
4. Implement / integrate the Execution + Canonical Data System
5. Expand using the Max Complete Spec only after the baseline works end-to-end

## Source-of-truth hierarchy
Priority order:
1. Lockdown Spec
2. Execution + Canonical Data Spec
3. Max Complete Spec

If documents appear to overlap:
- The higher-priority document wins.
- Lower-priority documents are for expansion and elaboration, not override.

## Non-negotiable rules
- Do not redesign the reference pipeline before it works.
- Do not swap libraries in the first build.
- Do not skip canonicalization, provenance, or leakage-safe evaluation.
- Do not optimize early.
- Do not silently discard unresolved mappings or conflicting records.

## Deliverable phases
### Phase 1: Baseline
Build the exact reference pipeline end-to-end.

### Phase 2: Core system
Integrate canonical data model, execution engine, provenance, caching, retries, and resumability.

### Phase 3: Expansion
Add advanced feature families, multimodal models, motif/pathway/evolution layers, hybrid modeling, AutoML, richer GUI, and advanced diagnostics.
