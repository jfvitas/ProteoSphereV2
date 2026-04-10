# Master Handoff Adoption

The newly added `master_handoff_package/` is now the authoritative implementation hierarchy:

1. Lockdown spec
2. Execution and canonical spec
3. Max-complete spec

Immediate adoption changes:

- the baseline is no longer inferred; it is the locked RCSB + UniProt + BindingDB pipeline
- chain-to-protein mapping must be MMseqs2-backed sequence alignment, not only exact matching
- the first working feature stack must explicitly include:
  - atom and residue graphs
  - frozen ESM2 embeddings
  - RDKit ligand descriptors
  - KD-tree interface contacts
- the first model stack must explicitly include:
  - EGNN structure encoder
  - frozen ESM2 sequence encoder
  - cross-modal attention fusion
  - XGBoost prediction head
  - AdamW, cosine scheduler, MSE loss
- the first evaluation contract must explicitly include:
  - MMseqs2 protein clustering at 30% identity
  - Murcko scaffold handling
  - no train/test cluster overlap
  - RMSE and Pearson

Interpretation of current completed work:

- existing bootstrap clients, parsers, canonical records, and DAG scaffolding remain useful
- they should be treated as early primitives or placeholders where the master handoff requires richer or stricter behavior
- they are not automatically final just because a queue item was previously marked done

Next queue priorities:

1. locked baseline implementation
2. canonical/provenance/resource-manager hardening
3. broader source coverage and summary-library expansion
4. real-data benchmark runs and release-grade validation
5. schema-driven UI and configuration surfaces
