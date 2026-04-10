# P29 Identifier Join Contract

This contract turns the normalization queue into implementation rules. It is intentionally conservative: every join must start from a source-native identifier, preserve provenance, and fail closed when the evidence is incomplete or conflicting.

## Global Rules

The contract applies the same constraints across all families:

- Join by source-native ID first.
- Keep secondary accessions, aliases, and display names as lookup aids only.
- Preserve lineage, span, assembly, species, and evidence class.
- Keep experimental and predicted structure separate.
- Keep ligand identity separate from assay measurement.
- Keep curated PPI separate from projection or context-only evidence.
- If a join is still ambiguous after normalization, leave it unresolved.

## Join Families

| Family | Required keys | Fallback keys | Anti-join rules | Fail-closed conditions |
|---|---|---|---|---|
| UniProt accession spine | `UniProt accession`, `taxon_id`, `sequence version/hash` | `secondary accession`, `isoform ID`, `gene name / mnemonic`, `historical accession` | Do not join by symbol alone; do not promote aliases to primary; do not merge isoforms without explicit mapping | Missing accession, multiple candidates remain, exact sequence needed but hash/version missing, taxon conflict |
| RCSB/PDBe + SIFTS structure join | `pdb_id`, `entity_id`, `assembly_id`, `chain ID`, `residue span`, `SIFTS or PDBe UniProt mapping`, `UniProt accession` | `auth_asym_id`, `label_asym_id`, validation report ref, `CCD component ID` for ligand context only | Do not join on PDB ID alone; do not merge experimental and predicted structure; do not ignore assembly or span; do not use ligand IDs as protein keys | Missing entity/chain/span, no mapping for protein resolution, assembly ambiguity, span conflict, experimental/predicted conflation |
| Ligand identity join | Stable chemical identifier, `source_record_id`, standardized chemical form, `protein accession` when assay-linked | `SMILES`, `InChI`, `HET ID`, ligand synonym, `ChEMBL target ID` | Do not join on names alone; do not use target names as ligand identity; do not collapse salts/tautomers/covalent states without standardization; do not merge assay measurement into identity | No stable chemical identifier, only synonym available, standardized form missing, target accession missing, structure-bound ligand cannot be mapped |
| Curated PPI join | Native interaction ID, participant UniProt accessions, interaction type, `taxid`, publication/evidence ID | `Entrez Gene ID`, participant alias, source interaction IDs, binary projection flag | Do not use aliases as canonical identity; do not flatten native complexes; do not mix physical and genetic interactions; do not ignore projection lineage | No native interaction ID and no accession-resolved participants, unresolved participants, projection lineage missing, interaction type ambiguous, taxon conflict |
| Motif span join | `UniProt accession`, motif accession, `span_start`, `span_end`, source release/snapshot ID | member-signature accession, clan/set ID, motif label, portal payload if accession and span are retained | Do not join on display text alone; do not accept span-less motifs; do not replace a specific motif accession with a parent ontology; do not project across species or isoforms without support | No stable span, no accessioned motif source, incompatible motif systems without tie-breaker, span conflict, no release-stamped source record |

## Family Notes

### UniProt Spine

The accession spine is the only canonical protein identity layer. Everything protein-bearing should normalize here first, including structure mappings, ligand targets, pathway participants, and interaction participants.

### Structure Join

The structure join is experimentally grounded. PDB ID is not enough on its own. The join must preserve entity, chain, assembly, residue span, and the PDBe mapping that connects the chain back to UniProt.

### Ligand Join

The ligand join treats chemical identity as distinct from assay measurement. A target accession can support a protein-ligand record, but it cannot stand in for a chemical identifier.

### Curated PPI Join

IntAct and BioGRID are curated interaction sources, but the contract keeps their projection lineage visible. Native complexes, binary projections, and physical-vs-genetic evidence remain separate until they are explicitly resolved.

### Motif Span Join

Motif joining is span-aware and accessioned. The contract is defined now even though the current local registry still lacks motif coverage, because the implementation should be ready the moment those sources land.

## Implementation Posture

If a record cannot satisfy the required keys for its family, the implementation should keep it unresolved and preserve the candidates and provenance. The contract prefers explicit incompleteness over false certainty.

## Bottom Line

This contract gives the implementation layer a simple rule: join only when the source-native key, the class-specific validation key, and the provenance all agree. Anything less should stay visible as a partial or unresolved candidate.
