# Struct2Graph Reproduced Overlap

- Paper: `baranwal2022struct2graph`
- Basis: representative reproduction of released `create_examples.py` logic using seed `1337`
- Interaction rows: `10,004`
- Train rows: `8,003`
- Test rows: `1,000`
- Shared PDB IDs across reproduced train/test: `643`
- Highlight structure: `4EQ6`
- Highlight reuse counts: `78` reproduced train examples and `9` reproduced test examples
- Interpretation: the same PDB structure is reused across train and test under the released pair-level split logic, which is leakage-prone under ProteoSphere rules.

![Struct2Graph overlay](D:/documents/ProteoSphereV2/artifacts/status/struct2graph_overlap/4EQ6_train_test_overlay.png)
