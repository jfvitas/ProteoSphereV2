# Forbidden Shortcuts

Agents must not:
- bypass canonical IDs and join directly on ad hoc text fields in production paths
- flatten all source records into one denormalized table without provenance
- ignore unresolved mappings
- silently drop low-confidence records without logging
- implement GUI conditionals in arbitrary frontend code instead of schema-driven rules
- report final performance from random split only when family/group leakage is a concern
- treat AlphaFold confidence as equivalent to curated disorder truth
- conflate assay types (e.g. Kd with IC50) without explicit transformation policy
- claim biological relevance of assemblies without a stored confidence/evidence basis
