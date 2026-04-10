# REFERENCE PIPELINE (MANDATORY FIRST BUILD)

Step 1: Ingest
- RCSB PDB (structures)
- UniProt (sequence)
- BindingDB (affinity)

Step 2: Canonicalization
- Map chains → UniProt using sequence alignment
- Store unresolved mappings explicitly

Step 3: Feature extraction
- Structure:
    - Graph (atom + residue)
- Sequence:
    - ESM2 embeddings
- Ligand:
    - RDKit descriptors
- Interface:
    - KD-tree contact calculation

Step 4: Model
- Structure encoder: EGNN (default)
- Sequence encoder: ESM2 frozen embeddings
- Fusion: cross-modal attention
- Head: XGBoost on fused embeddings

Step 5: Training
- Loss: MSE
- Optimizer: AdamW
- Scheduler: cosine

Step 6: Evaluation
- Split: sequence-clustered (<=30% identity)
- Metrics: RMSE, Pearson

THIS PIPELINE MUST WORK END-TO-END BEFORE ANY EXPANSION.
