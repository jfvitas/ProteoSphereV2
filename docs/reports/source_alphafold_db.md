# Source Analysis Report

Source:
AlphaFold Protein Structure Database (AlphaFold DB). The current site advertises open access to 200M+ protein structure predictions, and the March 2026 update adds large-scale protein-complex predictions alongside the original monomer archive. Primary sources: [AlphaFold DB home](https://alphafold.ebi.ac.uk/), [AlphaFold DB downloads](https://alphafold.ebi.ac.uk/download), [AlphaFold DB API openapi.json](https://alphafold.ebi.ac.uk/api/openapi.json), [License and Disclaimer PDF](https://alphafold.ebi.ac.uk/assets/License-Disclaimer.pdf)

Acquisition:
Use the API as the planning and lookup surface, then pull coordinate assets only for selected examples. The API exposes `/api/prediction/{qualifier}` for monomer-style entries, `/api/complex/{qualifier}` for complex entries, `/api/sequence/summary` for sequence/checksum lookup, `/api/uniprot/summary/{qualifier}.json` for UniProt-centered summaries, and `/api/annotations/{qualifier}.json` for computational annotations. The download page also provides bulk FTP archives plus per-entry `bcif`, `cif`, `pdb`, `MSA`, `pLDDT`, and `PAE` asset URLs.

Structural coverage:
AlphaFold DB is the broadest structure-source fit when the platform needs predicted coverage rather than experimental validation. The download page currently reports bulk downloads for 48 organism proteomes plus the majority of Swiss-Prot, with 550,122 Swiss-Prot coordinate files available in CIF and PDB form. Long proteins over 2700 aa are split into overlapping 1400 aa fragments in the proteome archives, and those fragment archives are currently described as human-proteome-only on the website. The March 2026 home page update also states that millions of predicted protein-complex structures are now openly available, with priority coverage for 20 major species and WHO priority pathogens.

Identifiers and schema:
- `/prediction/{qualifier}` accepts a UniProt accession or model ID and returns an array of `NewEntrySummary` objects.
- Key identifiers are `uniprotAccession`, `uniprotId`, `entryId`, `modelEntityId`, `sequenceChecksum`, `latestVersion`, and `allVersions`.
- Identity and provenance fields include `toolUsed`, `providerId`, `entityType`, `isUniProt`, `isUniProtReviewed`, `isUniProtReferenceProteome`, `gene`, `taxId`, and `organismScientificName`.
- Coordinate and support assets are surfaced as `bcifUrl`, `cifUrl`, `pdbUrl`, `msaUrl`, `plddtDocUrl`, `paeDocUrl`, `paeImageUrl`, and optional AlphaMissense annotation URLs.
- Sequence placement is explicit through `sequenceStart`, `sequenceEnd`, `sequence`, `uniprotSequence`, `uniprotStart`, and `uniprotEnd`.
- `/api/complex/{qualifier}` returns `ComplexModelMetadata` with `assemblyType`, `oligomericState`, `complexName`, `complexComposition`, and complex confidence metrics such as `ipTM`, `ipSAE`, `pDockQ`, `pDockQ2`, and `LIS`.
- `/api/sequence/summary` is useful for bulk index construction because it is checksum-aware and capped for query-sized retrieval.
- `/api/annotations/{qualifier}.json` currently exposes computational `MUTAGEN` annotations with `COMPUTATIONAL/PREDICTED` evidence.

Use in platform:
This source is a strong fit for the summary library when we want a structure-backed protein record even without experimental coordinates. It should improve coverage for canonical proteins that lack PDB entries, add a stable predicted-structure pointer for sequence-centric examples, and provide a lightweight geometry fallback for training-packet selection. Complex coverage is especially useful for oligomeric summaries and for distinguishing predicted assemblies from monomer-only coverage.

Join strategy:
Use UniProt accession as the primary join to the canonical protein record. Preserve `modelEntityId` as the source-specific instance key, and keep `sequenceChecksum` as the secondary join for release drift, exact-sequence dedupe, and fragment reconciliation. Map predicted fragments with `sequenceStart`/`sequenceEnd` and `uniprotStart`/`uniprotEnd` so the canonical protein can retain residue-local provenance. For complex entries, normalize each component in `complexComposition` into stoichiometric complex-member records keyed by accession when present, or checksum when accession is missing. Do not let AlphaFold DB become the authority for experimental chain identity; that role should remain with RCSB/PDBe/SIFTS.

Storage recommendation:
Preload a compact planning index with accession, model ID, checksum, taxon, organism, reviewed/reference-proteome flags, complex flag, assembly state, oligomeric state, version numbers, sequence bounds, and coarse confidence summaries. Keep raw payloads and file URLs in an append-only source cache. Materialize canonical protein and complex links, provenance, and source lineage, but do not hot-load every coordinate artifact. Coordinate files, MSA, PAE, confidence JSON, and annotation CSVs should stay lazy until a candidate enters an active analysis set or a training packet.

Quality and caveats:
Treat AlphaFold DB as predicted evidence, not experimental truth. The site license explicitly says the structures are predictions with varying confidence and should be interpreted carefully. `globalMetricValue` is average pLDDT, while the confidence fractions are only coarse buckets around that average; low-confidence or disordered regions should not become hard labels. Complex scores such as `ipTM` and `pDockQ` are model-quality indicators, not experimental interface validation. `providerId` also matters because the complex release includes multiple provider sources, so trust and reproducibility should remain source-aware. Unreviewed entries, non-reference proteome entries, fragment models, and isoform-related records should all be preserved rather than flattened.

Interaction with RCSB/PDBe/PDB-CIF materialization:
AlphaFold DB should be a predicted-structure companion to the experimental archive, not a replacement for it. If a protein already has an experimental RCSB/PDBe/PDB-CIF structure, that experimental archive should remain the authoritative coordinate layer, with AlphaFold stored as a parallel predicted model linked by canonical protein and accession. If no experimental structure exists, AlphaFold DB can supply the default structure record. If experimental coverage is partial, AlphaFold should fill the sequence-complete gap while keeping experimental and predicted coordinates separate. In practice, use RCSB/PDBe/SIFTS for chain-to-UniProt resolution on experimental entries, and use AlphaFold accession/checksum joins for predicted entries. Never merge predicted and experimental coordinates into a single canonical coordinate object.

Lazy materialization advice:
Preload metadata and confidence summaries, index the accession/checksum/model-ID graph, and fetch coordinate artifacts only when a selected example needs them. For summary-library search, a structure row can often be served from the preloaded header plus confidence summaries alone. For training-packet export, hydrate the exact `bcif` or `cif` file, the matching confidence JSON, and any relevant PAE/MSA assets only after the example has passed canonical protein mapping and split assignment.

Sources used:
- [AlphaFold DB home](https://alphafold.ebi.ac.uk/)
- [AlphaFold DB downloads](https://alphafold.ebi.ac.uk/download)
- [AlphaFold DB API openapi.json](https://alphafold.ebi.ac.uk/api/openapi.json)
- [License and Disclaimer PDF](https://alphafold.ebi.ac.uk/assets/License-Disclaimer.pdf)
