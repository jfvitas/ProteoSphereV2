# Complete Feature Ontology

Features must be tracked with:
- feature key
- entity level
- source or calculator
- units
- value type
- missingness policy
- confidence availability
- aggregation rules

## A. Atom-level features
- element identity
- atomic number
- ordinal electronegativity proxy(optional encoding)
- residue-conditioned electronegativity proxy(optional)
- coordinates x,y,z
- formal charge
- partial charge (computed if available)
- van der Waals radius
- covalent radius
- aromatic flag
- donor flag
- acceptor flag
- hybridization(optional)
- occupancy
- B-factor / temperature factor
- altloc flag
- atom type classes
- local neighborhood counts
- solvent exposure proxy(optional)
- per-atom SASA
- local electrostatic environment(optional derived)

## B. Residue / nucleotide-level features
- residue identity
- residue class: polar/nonpolar/aromatic/charged
- nucleotide identity / base class
- secondary structure class
- backbone torsions if available/derived
- side-chain torsions where relevant
- residue SASA
- relative SASA
- B-factor aggregates
- hydrophobicity index
- pKa-related proxies(optional)
- residue conservation
- residue entropy
- disorder mask / disorder score
- interface membership
- motif membership
- domain membership
- PTM flags
- sequence position normalized
- chain terminal flags
- insertion/deletion/mutation flags

## C. Pairwise and edge features
- covalent bond type
- graph edge class
- euclidean distance
- distance encoded with radial basis functions
- contact flag
- hydrogen bond flag
- salt bridge flag
- pi-pi interaction flag
- cation-pi flag
- hydrophobic interaction flag
- metal coordination flag
- relative orientation descriptors
- angle
- dihedral
- co-evolution score between positions(optional)
- edge confidence
- edge provenance

## D. Interface-level features
- interface area
- buried surface area
- contact density
- shape complementarity
- interface residue counts by type
- hydrogen bond counts
- salt bridge counts
- hydrophobic contact counts
- aromatic interaction counts
- inter-chain distance summaries
- interface conservation
- interface disorder fraction
- symmetry flags where relevant
- pocket enclosure metrics for ligands
- pocket depth
- pocket polarity
- pocket hydrophobicity
- pocket volume

## E. Global structure features
- sequence length
- chain length
- number of chains
- stoichiometry
- radius of gyration
- compactness
- global surface area
- volume
- secondary structure composition ratios
- confidence summaries
- experimental method
- resolution / map quality
- predicted structure confidence aggregates
- missing residue fraction

## F. Ligand features
- molecular weight
- logP
- TPSA(optional)
- H-bond donor count
- H-bond acceptor count
- rotatable bonds
- ring counts
- aromatic rings
- formal charge
- fingerprints (e.g. binary or count fingerprints)
- scaffold identifier(optional)
- protonation state(optional)
- tautomer class(optional)
- ligand graph descriptors
- 3D conformer descriptors if available

## G. Sequence and embedding features
- one-hot sequence
- learned amino acid embeddings
- protein language model embeddings
- MSA profiles
- conservation scores
- entropy
- co-evolution matrices
- domain architecture vectors
- motif occurrence vectors
- low complexity region flags

## H. Biological context features
- pathway membership vector
- pathway overlap score
- pathway graph embedding
- functional annotation vector
- interaction evidence counts
- evidence confidence summaries
- subcellular localization(optional later)
- family and superfamily labels
- evolutionary distance proxies

## I. Uncertainty / quality features
- pLDDT-like confidence
- PAE-derived summaries if available
- experimental resolution
- assay confidence / curation confidence
- annotation evidence strength
- structural completeness score
- conflict count per object
- source agreement score

## J. Derived multi-scale features
- conserved interface residue fraction
- motif-conserved pocket score
- pathway-aware interaction prior
- disorder-at-interface fraction
- chain-to-canonical mismatch burden
- structure-quality-weighted feature reliability
