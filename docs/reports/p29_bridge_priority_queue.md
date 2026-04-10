# P29 Bridge Priority Queue

This queue turns the completed source connection map into an implementation order for the next source-fusion work. The rule is conservative: normalize the identity spine first, then unlock structure, pathway, ligand, interaction, and motif bridges, and keep proxy lanes separate from direct evidence.

## Ranking Rule

The ranking favors practical impact on packet completion and summary-library usefulness. A bridge ranks higher when it:

1. Connects multiple modalities at once.
2. Uses a source-native identifier rather than a derived label.
3. Reduces ambiguity without collapsing source semantics.
4. Helps close one of the current partial or missing packet lanes.

## Highest-Value Bridges

| Rank | Bridge | Canonical join keys | Normalization steps | Impact |
|---|---|---|---|---|
| 1 | Normalize all protein-bearing sources to UniProt first | `UniProt accession`, `secondary accession`, `isoform ID`, `sequence version/hash`, `NCBI taxonomy` | Resolve to primary accession, keep secondary accessions as aliases, carry isoform/version lineage, reject taxon conflicts | Very high packet completion and very high summary-library value |
| 2 | Use RCSB/PDBe + SIFTS as the experimental structure bridge | `pdb_id`, `entity_id`, `assembly_id`, `chain ID`, `auth_asym_id`, `label_asym_id`, `residue span`, `SIFTS span`, `CCD component ID` | Join chains and entities before span projection, keep asymmetric unit and biological assembly distinct, preserve missing residues and renumbering gaps | Very high packet completion and very high summary-library value |
| 3 | Normalize pathway membership through Reactome stable IDs | `Reactome stable ID`, `versioned stable ID`, `species`, `UniProt accession`, `ChEBI ID`, `complex/reaction ID` | Keep species and version on every row, separate reaction membership from protein identity, preserve pathway ancestry and complex context | High packet completion and very high summary-library value |
| 4 | Normalize ligand identity across BindingDB, ChEMBL, ChEBI, and PDB CCD | `BindingDB Reactant_set_id`, `BindingDB MonomerID`, `InChIKey`, `SMILES`, `ChEBI ID`, `CCD component ID`, `HET ID`, `ChEMBL target ID`, `assay ID`, `activity ID` | Normalize chemical identity before assay rows, keep salt/tautomer/covalent-state notes explicit, separate assay measurements from ligand identity | High packet completion and very high summary-library value |
| 5 | Preserve IntAct and BioGRID native interaction identifiers | `BioGRID Interaction ID`, `BioGRID IDs`, `Entrez Gene ID`, `IntAct Interaction AC`, `IMEx ID`, `participant IDs`, `PubMed ID`, `taxid`, `UniProt accession` | Resolve participant accessions first, preserve physical-vs-genetic and binary-vs-native-complex lineage, keep publication and taxon context attached | High packet completion and very high summary-library value |
| 6 | Attach motif annotations through span-aware InterPro, Pfam, PROSITE, and ELM joins | `UniProt accession`, `IPRxxxxx`, `PFxxxxx`, `PDOCxxxxx`, `PSxxxxx`, `PRUxxxxx`, `ELME#####`, `residue span` | Require a stable residue span, preserve motif system and evidence count, keep integrated vs unintegrated provenance distinct | Medium packet completion and high summary-library value |
| 7 | Use BioLiP and PDBBind as structure-grounded ligand and pair context | `PDB ID`, `chain/interface context`, `ligand role`, `corpus row ID` | Keep corpus rows separate from curated PPI evidence, preserve chain/interface context, treat corpus row IDs as corpus identity only | Medium packet completion and high summary-library value |
| 8 | Keep AlphaFold as a predicted companion lane, not merged truth | `UniProt accession`, `sequenceChecksum`, `entryId`, `modelEntityId` | Join by accession first, keep predicted and experimental coordinates separate, preserve checksum and model IDs for provenance | Medium packet completion and medium summary-library value |
| 9 | Target the remaining partial packets with accession-mappable rescue probes | `Q9UCM0`, `P00387`, `P09105`, `Q2TAC2`, `Q9NZD4` | Probe already-present local sources first, fail closed on alias-only joins, promote only direct accession-mappable recoveries | Medium packet completion and medium summary-library value |

## Strongest Bridges

The connection map already shows the strongest bridges as:

- `UniProt <-> RCSB/PDBe + SIFTS`
- `UniProt <-> AlphaFold DB`
- `UniProt <-> Reactome`
- `UniProt <-> BindingDB / ChEMBL`
- `UniProt <-> BioGRID / IntAct`
- `UniProt <-> InterPro / Pfam / PROSITE / ELM`
- `RCSB/PDBe <-> BioLiP / PDBBind`
- `Reactome <-> ChEBI`

These are the lanes that should be implemented first because they attach the most downstream value to the least ambiguous identifier spine.

## Weak Bridges

The queue keeps these lanes explicit but secondary:

- `IntAct` binary projections from native complexes.
- `BioGRID` physical-vs-genetic mixing.
- `BindingDB` target sequence vs construct.
- `Reactome` complex membership or interaction-like context.
- `AlphaFold` predicted vs experimental structure.

These are useful for annotation and ranking, but they must not overwrite direct evidence.

## Known Broken Lanes

The current local registry still leaves several lanes broken or absent:

- `interaction_network` is missing for `string`, `biogrid`, and `intact`.
- `motif` is missing for `prosite`, `elm`, `mega_motif_base`, and `motivated_proteins`.
- `metadata / enzymology` is missing `sabio_rk`.
- `sequence_depth` is missing `uniprot_trembl`.
- `Q9UCM0` has no confirmed non-UniProt bridge in the current repo tree.

These are not fake gaps. They are the real boundaries that the priority queue has to respect.

## Deferred Lanes

Three sources are intentionally kept below the direct-evidence bridges:

- `STRING`, because it is metadata-only in the current seed mirror.
- `SABIO-RK`, because it is important but not currently present locally.
- `UniProt TrEMBL`, because the reviewed UniProt spine is still the higher-value anchor for the current slice.

## Bottom Line

If we implement the top of this queue in order, we will get the fastest increase in packet completeness and the highest reuse in the summary library without inventing joins or flattening evidence classes.
