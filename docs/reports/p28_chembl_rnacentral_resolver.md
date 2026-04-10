# P28 ChEMBL / RNAcentral Resolver Pinning

## Purpose

Take ownership of the resolver-tier gap for `chembl` and `rnacentral` and record only what we can prove from the current procurement package and official source pages.

## Current package state

- `protein_data_scope/sources_manifest.json` now pins concrete ChEMBL and RNAcentral bulk URLs.
- `protein_data_scope/source_policy.json` still keeps both `chembl` and `rnacentral` in the `resolver` tier.
- `protein_data_scope/catalog_summary.md` now uses public Postgres database wording instead of implying a `Postgres dump`.

## ChEMBL

### What is true now

- The manifest entry is still manual-review resolver tier, with only the downloads landing page wired in.
- The official ChEMBL downloads page reports current release `36` and last update `July 2025`.
- The official ChEMBLdb FTP directory exposes a concrete `latest/` file set, so this source is pin-ready instead of blocked.

### Safe bulk-download URLs

- `https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_36_sqlite.tar.gz`
- `https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_36_postgresql.tar.gz`
- `https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_36_mysql.tar.gz`
- `https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_36.sdf.gz`
- `https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_36.fa.gz`
- `https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_36_release_notes.txt`
- `https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/checksums.txt`

### Verdict

`chembl` can be pinned safely now. The remaining work is to promote the manifest from a landing-page pointer to concrete bulk artifacts.

## RNAcentral

### What is true now

- The manifest entry is still manual-review resolver tier, but the fixed current-release bulk files are already pinned.
- The official RNAcentral downloads page points to the FTP archive, and the help page explicitly documents current-release file URLs.
- Several RNAcentral assets are pin-ready today, but the genome-coordinate BED fan-out is still directory-driven and needs resolver enumeration before it becomes manifest-ready.
- RNAcentral also provides a public Postgres database for SQL access, so the manifest and summary docs should not reintroduce a `pg_dump.sql.gz` expectation.

### Safe bulk-download URLs

- `https://ftp.ebi.ac.uk/pub/databases/RNAcentral`
- `https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/go_annotations/rnacentral_rfam_annotations.tsv.gz`
- `https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/gpi/rnacentral.gpi.gz`
- `https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/id_mapping/id_mapping.tsv.gz`
- `https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/md5/md5.tsv.gz`
- `https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/rfam/rfam_annotations.tsv.gz`
- `https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/sequences/rnacentral_active.fasta.gz`
- `https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/sequences/rnacentral_inactive.fasta.gz`
- `https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/sequences/rnacentral_species_specific_ids.fasta.gz`

### Still blocked

- `https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/genome_coordinates/bed/`
- `https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/id_mapping/database_mappings/`

Those subtrees are documented by RNAcentral, but the exact per-file names are fan-out lists rather than a single stable artifact URL. They need a resolver pass that enumerates the directory contents before we can pin them safely in the manifest.

### Verdict

`rnacentral` is partially pin-ready. The fixed release files above can be automated now, the SQL access path should go through the public Postgres database, and the BED and per-database mapping families still need resolver logic.

## Next step

Keep the remaining RNAcentral directory fan-out items in the gap queue, keep the catalog summary aligned with the public Postgres database wording, and run the downloader against the pinned bulk artifacts.

If we want to keep the resolver tier isolated instead of expanding the manifest by hand, the next implementation should live under `scripts/` and only enumerate URLs from the official FTP and downloads pages.
