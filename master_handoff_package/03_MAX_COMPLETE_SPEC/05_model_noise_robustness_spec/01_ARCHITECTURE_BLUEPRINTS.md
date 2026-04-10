# Architecture Blueprints

## Blueprint A: Multimodal flagship model
Inputs:
- structure graph(s): protein and optionally ligand
- sequence embeddings / conservation maps
- pathway/evidence vector
- quality/confidence vector

Modules:
1. Structure encoder
   - recommended default: geometric GNN (EGNN or equivalent configurable choice)
2. Ligand encoder
   - MPNN or chemistry GNN, or descriptor MLP fallback
3. Sequence encoder
   - pretrained embedding adapter or transformer head
4. Biology encoder
   - MLP over pathway/evidence/domain features
5. Fusion
   - cross-modal attention + gating
6. Heads
   - regression/classification head(s)
   - uncertainty head
   - optional auxiliary head(s)

Outputs:
- task predictions
- uncertainty
- intermediate embeddings
- attention/gating diagnostics

## Blueprint B: Hybrid tabular + embedding stack
- encode structure/sequence into embeddings
- concatenate with engineered features
- feed XGBoost/CatBoost or residual MLP
Use as high-performance pragmatic baseline.

## Blueprint C: Ensemble family
- neural multimodal model
- tree-based engineered feature model
- baseline graph model
- combine via stacking/meta-learner
