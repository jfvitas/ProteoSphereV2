# DATASET CURATION RULES

1. Remove duplicate structures (>95% sequence identity)
2. Cluster proteins (MMseqs2)
3. Enforce diversity:
   - no cluster overlap between train/test
4. Remove:
   - incomplete structures (>30% missing residues)
   - ligands without valid chemistry
