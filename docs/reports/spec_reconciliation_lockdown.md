# Spec Reconciliation: Lockdown / Reference Pipeline

## Source Priority

The new authoritative order is explicit:

1. `master_handoff_package/01_LOCKDOWN_SPEC`
2. `master_handoff_package/02_EXECUTION_AND_CANONICAL_SPEC`
3. `master_handoff_package/03_MAX_COMPLETE_SPEC`

The lockdown spec is now the baseline source of truth. The current bootstrap and queue must be interpreted through that lens.

## Exact Baseline Contract

The mandatory first working system is:

1. Ingest
   - RCSB PDB for structures
   - UniProt for sequence
   - BindingDB for affinity
2. Canonicalization
   - map chains to UniProt by sequence alignment
   - store unresolved mappings explicitly
3. Feature extraction
   - structure graphs at atom and residue level
   - sequence embeddings from ESM2
   - ligand descriptors from RDKit
   - interface contacts from KD-tree calculation
4. Model
   - structure encoder: EGNN
   - sequence encoder: frozen ESM2 embeddings
   - fusion: cross-modal attention
   - head: XGBoost on fused embeddings
   - uncertainty: enabled
5. Training defaults
   - loss: MSE
   - optimizer: AdamW
   - scheduler: cosine
   - learning rate: `1e-4`
   - batch size: `32`
   - epochs: `100`
   - mixed precision: `true`
6. Evaluation
   - protein clustering with MMseqs2 at 30% identity
   - no cluster overlap across splits
   - ligand Murcko scaffold split
   - train/val/test = `70/15/15`
   - metrics: RMSE and Pearson

## Locked Backend Mapping

These are mandatory for the first build:

- alignment: MMseqs2
- sequence embeddings: ESM2 (`facebook/esm`)
- ligand features: RDKit
- contacts: SciPy KDTree or MDAnalysis
- SASA: `freesasa`
- conservation: MSA pipeline using MMseqs2 plus custom scoring

The startup docs are explicit: no substitutions in the first build.

## Dataset Rules

Required curation behavior:

- remove duplicate structures above 95% sequence identity
- cluster proteins with MMseqs2
- enforce no cluster overlap between train and test
- remove structures with more than 30% missing residues
- remove ligands without valid chemistry

The provided quality scoring baseline is intentionally simple:

- reward better resolution
- reward pLDDT
- reward assay confidence
- penalize missing structural fraction

## Test Expectations

The startup docs require the reference pipeline to work end-to-end before any expansion.

The packaged test file in the lockdown spec is only a placeholder, so the real interpretation is:

- the lockdown spec defines the end-to-end contract
- the current repo must supply the real integration tests, not inherit the placeholder literally

## Direct Contradictions With The Current Bootstrap

### 1. Canonical mapping is currently too weak

Current queue/bootstrap:
- `P1-T010` is framed as exact chain-to-protein mapping
- `P1-T011` preserves ambiguity

Lockdown requirement:
- chain to UniProt mapping must be sequence-alignment based
- MMseqs2 is the locked backend

Implication:
- exact-match mapping is not sufficient as the primary baseline contract

### 2. Baseline feature plan is underspecified relative to lockdown

Current queue/bootstrap:
- generic sequence and assay feature tasks

Lockdown requirement:
- atom + residue graphs
- frozen ESM2 embeddings
- RDKit ligand descriptors
- KD-tree interface contacts
- `freesasa` and MSA/MMseqs2 are part of the locked backend map

Implication:
- the current feature tasks need to be split or rewritten around those concrete backends

### 3. Model/training defaults are currently too generic

Current queue/bootstrap:
- generic reference model skeleton and training loop tasks

Lockdown requirement:
- EGNN + frozen ESM2 + cross-attention + XGBoost head
- MSE / AdamW / cosine with fixed default hyperparameters

Implication:
- the current model/training tasks are missing critical architectural specificity

### 4. Split policy is currently below spec

Current queue/bootstrap:
- baseline dataset builder exists, but the locked split policy is not encoded as the baseline contract

Lockdown requirement:
- MMseqs2 protein clustering at 30% identity
- Murcko scaffold split
- 70/15/15 proportions
- no cluster overlap

Implication:
- leakage-safe evaluation is not optional metadata; it is part of the baseline definition

### 5. Expansion work is currently too visible too early

Current queue/bootstrap:
- later multimodal, UI, and real-data expansion tasks are already queued

Startup docs:
- do not proceed beyond lockdown until the exact baseline works end-to-end

Implication:
- the queue should prioritize and potentially gate later tasks behind completion of the locked baseline pipeline

## Required Queue / Implementation Adjustments

1. Reframe baseline canonical mapping around MMseqs2-based chain-to-UniProt alignment.
2. Replace generic baseline feature tasks with concrete ESM2 / RDKit / KD-tree / graph / SASA tasks.
3. Lock the baseline model stack to EGNN + cross-attention + XGBoost with the specified training defaults.
4. Add explicit split-governance implementation tasks for MMseqs2 clustering and Murcko scaffold partitioning.
5. Freeze non-baseline expansion work until the reference pipeline passes a real end-to-end test.

## Practical Read Of The Current Repo

The current bootstrap is still usable, but it should now be treated as scaffolding plus early primitives rather than the baseline design itself. The authoritative lockdown package removes the earlier ambiguity and requires a tighter, more concrete first-build implementation than the inferred queue originally captured.
