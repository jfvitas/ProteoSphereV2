# P29 Source Connection Map

- Generated at: `2026-03-30T00:47:27.252684-05:00`
- Local registry summary: `data/raw/local_registry_runs/LATEST.json`
- Seed promotion summary: `data/raw/protein_data_scope_seed/promotions/LATEST.json`
- Selected source count: `39`
- Local registry status counts: `{'present': 29, 'partial': 2, 'missing': 8}`
- Seed promotion source count: `6`

This map stays conservative: every bridge below is backed by the current local registry summary, the broad seed mirror, or an existing report. No alias-only or invented joins are promoted as truth.

## Join Key Families

| Lane | Canonical Keys | Representative Anchors | Bridge Sources | Strength |
| --- | --- | --- | --- | --- |
| accession | UniProt primary accession; secondary accession; isoform ID; sequence version/hash; NCBI taxonomy | P69905; P68871; P09105; Q9UCM0 | UniProt; AlphaFold DB; Reactome; InterPro; Pfam; BindingDB; ChEMBL; BioGRID; IntAct | strong |
| structure | pdb_id; entry_id; entity_id; assembly_id; auth_asym_id; label_asym_id; residue spans; SIFTS spans; CCD component ID | 10JU; 4HHB; 9LWP; 1A00; 5JJM; 6O3O; 1ARJ; 1BYJ; 9S6C | RCSB/PDBe; SIFTS; AlphaFold DB; BioLiP; PDBBind; CATH; SCOPE | strong |
| ligand | BindingDB Reactant_set_id; BindingDB MonomerID; InChIKey; SMILES; ChEBI ID; CCD component ID; HET ID | CHEMBL2146; 1BB0; 5Q16; 5TQF; 4HHB; 9S6C | BindingDB; ChEMBL; ChEBI; PDB CCD; BioLiP; PDBBind | strong |
| pathway | Reactome stable ID; versioned stable ID; species; UniProt accession; ChEBI ID; complex/reaction ID | R-HSA-114452; R-HSA-109581; R-HSA-9824439; R-HSA-9711123 | Reactome; UniProt; ChEBI | strong |
| interaction | BioGRID Interaction ID; BioGRID IDs; Entrez Gene ID; IntAct Interaction AC; IMEx ID; participant IDs; PubMed ID; taxid; UniProt accession | EBI-4370729; IM-16920-1; EBI-5772682; IM-17256-1 | BioGRID; IntAct; UniProt | strong |

## Strongest Bridges

| Bridge | Join Keys | Examples | Why Strong |
| --- | --- | --- | --- |
| UniProt <-> RCSB/PDBe + SIFTS | UniProt accession; pdb_id; entity_id; assembly_id; chain ID; residue span; SIFTS span | P69905 <-> 4HHB; P69905 <-> 10JU | Clean accession-to-experimental-structure bridge |
| UniProt <-> AlphaFold DB | UniProt accession; sequenceChecksum; entryId; modelEntityId | P69905; P68871 | Predicted structure companion, kept separate from experimental coordinates |
| UniProt <-> Reactome | UniProt accession; Reactome stable ID; species; version | P69905 -> R-HSA-114452 | Pathway/reaction authority with accession anchor |
| UniProt <-> BindingDB / ChEMBL | UniProt accession; BindingDB Reactant_set_id; MonomerID; InChIKey; SMILES; ChEMBL target ID; assay ID; activity ID | P31749 -> ChEMBL target bridge; P00387 -> CHEMBL2146 | Strongest ligand/assay lane when target accession is explicit |
| UniProt <-> BioGRID / IntAct | UniProt accession; BioGRID Interaction ID; IntAct Interaction AC; IMEx ID; participant IDs | EBI-4370729 / IM-16920-1 -> P31749|Q92831; EBI-5772682 / IM-17256-1 -> P31749|Q9Y6K9 | Curated pair evidence with lineage preserved |
| UniProt <-> InterPro / Pfam / PROSITE / ELM | UniProt accession; IPRxxxxx; PFxxxxx; PDOCxxxxx; PSxxxxx; PRUxxxxx; ELME#####; residue span | P69905 -> InterPro/Pfam spans | Span-aware motif and domain annotations |
| RCSB/PDBe <-> BioLiP / PDBBind | PDB ID; chain/interface context; ligand role; corpus row ID | 4HHB; 9S6C; 6O3O; 1ARJ; 1BYJ; 9LWP; 9QTN; 9SYV | Supporting corpora, but still hinge on the same PDB and chain keys |
| Reactome <-> ChEBI | Reactome stable ID; ChEBI ID | pathway small-molecule context | Safest pathway-linked ligand identity bridge |

## Weak Bridges

| Bridge | Join Keys | Reason |
| --- | --- | --- |
| IntAct binary projection from native complexes | IntAct Interaction AC; IMEx ID; participant IDs | Displayed pairs can be projections of n-ary complexes |
| BioGRID physical-vs-genetic mixing | BioGRID Interaction ID; experimental system type; taxid | Physical and genetic interactions live in the same family |
| BindingDB target sequence vs construct | UniProt accession; target sequence; assay row | Target sequence can differ from the assayed construct |
| Reactome complex membership / interaction-like context | Reactome stable ID; complex membership; participant accession | Complex membership is context, not direct binding evidence |
| AlphaFold predicted vs experimental structure | UniProt accession; sequenceChecksum | Accessions can align proteins, but coordinate truth must stay separate |

## Known Broken Lanes

| Lane | Local Status | Seed State | Why It Matters |
| --- | --- | --- | --- |
| interaction_network | missing for string / biogrid / intact | BioGRID and IntAct are present in the broad seed mirror; STRING is metadata-only | Curated PPI breadth is the largest missing class in the registry |
| motif | missing for prosite / elm / mega_motif_base / motivated_proteins | PROSITE is present in the seed mirror; ELM and the motif-base lanes are absent | The platform lacks a second independent annotation channel |
| metadata / enzymology | sabio_rk missing | no seed payload in this repo tree | Catalytic and kinetics metadata remains a gap |
| sequence_depth | uniprot is partial; uniprot_trembl is absent | reviewed-only sequence coverage in the current registry slice | The sequence lane is a good anchor but too narrow for deeper coverage |
| packet-level hard gap | Q9UCM0 has no confirmed non-UniProt bridge | no AlphaFold, ligand, or interaction rescue path in the current repo tree | This is the cleanest example of a true dead end in the current packet set |

## Source Panels

| Panel | Local Status | Seed Status | Join Keys | Role | Notes |
| --- | --- | --- | --- | --- | --- |
| UniProt | partial | present | primary accession; secondary accession; isoform ID; sequence version/hash; NCBI taxonomy | canonical accession spine | P69905; P68871; P09105; Q9UCM0 |
| RCSB/PDBe + local extracted assets | present | absent | pdb_id; entry_id; entity_id; assembly_id; auth_asym_id; label_asym_id; residue spans; SIFTS spans; CCD component ID | experimental structure bridge | 10JU; 4HHB; 9LWP; 1A00; 5JJM; 6O3O; 1ARJ; 1BYJ; 9S6C |
| SIFTS | not_selected | present | pdb_chain_uniprot.tsv.gz; uniprot_segments_observed.tsv.gz; pdb_chain_taxonomy.tsv.gz; pdb_pubmed.tsv.gz | accession-to-structure crosswalk | cleanest protein-to-structure join |
| AlphaFold DB | present | metadata_only | UniProt accession; sequenceChecksum; entryId; modelEntityId | predicted structure companion | P69905; P68871 |
| Reactome | present | present | Reactome stable ID; versioned stable ID; species; UniProt accession; ChEBI ID; complex/reaction ID | pathway/reaction authority | P69905; P09105; R-HSA-114452; R-HSA-9824439 |
| BindingDB + ChEMBL | present | present | BindingDB Reactant_set_id; BindingDB MonomerID; InChIKey; SMILES; ChEMBL target ID; assay ID; activity ID; UniProt accession; PDB ID | ligand/assay authority | 1BB0; 5Q16; 5TQF; 5JJM; P31749; CHEMBL2146 |
| BioGRID + IntAct | missing | present | BioGRID Interaction ID; BioGRID IDs; Entrez Gene ID; IntAct Interaction AC; IMEx ID; participant IDs; PubMed ID; taxid; UniProt accession | curated interaction spine | EBI-4370729; IM-16920-1; EBI-5772682; IM-17256-1 |
| InterPro + Pfam + PROSITE + ELM | mixed | partial | IPRxxxxx; PFxxxxx; PDOCxxxxx; PSxxxxx; PRUxxxxx; ELME#####; UniProt accession; residue span | motif/domain spine | InterPro and Pfam present locally; PROSITE and ELM are locally missing |
| BioLiP + PDBBind | present | absent | PDB ID; chain/interface context; ligand role; corpus row ID | structure-grounded ligand/pair corpus | 4HHB; 9S6C; 6O3O; 1ARJ; 1BYJ; 9LWP; 9QTN; 9SYV |
| ChEBI + PDB CCD | not_selected | present | ChEBI ID; CCD component ID; HET ID | chemical identity spine | seed mirror only in this run |
| CATH + SCOPE | present | absent | CATH ID; SCOPE ID; PDB ID; UniProt accession | fold/classification support | 10JU; 4HHB |
| STRING | missing | metadata_only | STRING protein identifier; network score; neighborhood / fusion / coexpression / textmining scores | breadth/context only | no current strong bridge in this repo tree |

## Evidence References

- `docs/reports/source_uniprot.md`
- `docs/reports/source_rcsb_pdbe.md`
- `docs/reports/source_bindingdb.md`
- `docs/reports/source_reactome.md`
- `docs/reports/source_biogrid.md`
- `docs/reports/source_intact.md`
- `docs/reports/source_interpro.md`
- `docs/reports/source_joinability_analysis.md`
- `docs/reports/source_join_strategies.md`
- `docs/reports/source_compatibility_matrix.md`
- `docs/reports/source_release_matrix.md`
- `docs/reports/source_storage_strategy.md`
