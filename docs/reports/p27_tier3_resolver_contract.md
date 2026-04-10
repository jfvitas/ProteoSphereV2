# P27 Tier 3 Resolver Contract

## Goal

Define the resolver outputs and stop conditions for the sources that cannot yet be bulk-procured safely from the uploaded manifest.

## Tier 3 sources

- `alphafold_db`
- `intact`
- `bindingdb`
- `chembl`
- `complex_portal`
- `rnacentral`
- `interpro`

## Resolver requirements by source

### AlphaFold DB

- Discovery method:
  - probe the EBI FTP directory family behind the bulk tar URLs
  - enumerate available `swissprot_*` tar artifacts
- Expected release token:
  - bundle version token such as `v4`
  - plus the directory marker such as `latest`
- Resolver outputs:
  - resolved artifact URLs
  - detected bundle version
  - file names and sizes
  - snapshot timestamp
  - manifest patch payload for chosen files
- Stop conditions:
  - expected tar names absent
  - multiple incompatible version families exposed with no clear winner
  - FTP listing unavailable
  - filename version differs from expected policy and no operator approval exists

### IntAct

- Discovery method:
  - probe the EBI FTP tree for current `psimitab`, PSI-MI XML, and mutation export locations
- Expected release token:
  - `current` FTP subtree plus dated file metadata or archive names
- Resolver outputs:
  - resolved MITAB bulk URL
  - resolved mutation table URL
  - optional XML URLs
  - detected path layout signature
  - release snapshot metadata
- Stop conditions:
  - MITAB path moved or missing
  - mutation export missing
  - only HTML index available with no stable file target
  - path layout differs from known signature

### BindingDB

- Discovery method:
  - derive the current `YYYYMM` token from the BindingDB download endpoints or landing page
  - test the expected monthly bulk filenames
- Expected release token:
  - `YYYYMM`
- Resolver outputs:
  - resolved month token
  - resolved TSV, SDF, and MySQL dump URLs
  - per-file existence matrix
  - preferred procurement set
  - stale-manifest warning if token advanced
- Stop conditions:
  - month token cannot be determined
  - expected monthly filenames return not found
  - only a partial file family exists where policy requires the full set
  - redirect, login, or challenge behavior appears

### ChEMBL

- Discovery method:
  - parse the official downloads page
  - extract concrete release artifact links for SQLite, SDF, or PostgreSQL dumps
- Expected release token:
  - ChEMBL release number such as `chembl_36`
- Resolver outputs:
  - resolved release number
  - resolved SQLite URL
  - optional checksum URL
  - release page snapshot URL
  - manifest-ready artifact record
- Stop conditions:
  - downloads page has no direct artifact links
  - release number cannot be extracted
  - multiple release families conflict
  - page structure changed enough that parser confidence is low

### Complex Portal

- Discovery method:
  - parse the Complex Portal download page
  - extract species-level TSV, ComplexTab, or PSI-MI download links
- Expected release token:
  - page-derived release or date token if exposed
  - otherwise snapshot timestamp only
- Resolver outputs:
  - resolved download URLs by format and species
  - selected species targets
  - detected format inventory
  - page snapshot metadata
- Stop conditions:
  - landing page only, no direct files found
  - species files require interactive selection not reproducible by parser
  - format names changed beyond resolver rules

### RNAcentral

- Discovery method:
  - parse the RNAcentral downloads page and or FTP listing
  - detect current bulk archive, database dump, and BED assets
- Expected release token:
  - RNAcentral release identifier if exposed
  - otherwise dated snapshot token
- Resolver outputs:
  - resolved primary archive URLs
  - detected release identifier
  - artifact family map by type
  - chosen preferred procurement subset
- Stop conditions:
  - no machine-resolvable file links
  - release token missing and multiple snapshots coexist
  - only documentation or HTML targets found
  - FTP and page disagree on current release

### InterPro

- Discovery method:
  - resolve from authoritative InterPro data and download endpoints
  - enumerate XML, entry lists, mapping tables, and optional InterProScan packages
- Expected release token:
  - InterPro release number or date from the resolved download location
- Resolver outputs:
  - resolved core data URLs
  - release token
  - artifact map by type
  - selected minimum viable procurement set
- Stop conditions:
  - only landing or tutorial page available
  - no authoritative file URLs found
  - release token absent
  - artifact set ambiguous between docs and bulk assets

## Common resolver contract

Every Tier 3 resolver should emit:

- `source_id`
- `resolver_status`
- `resolved_release_token`
- `resolved_urls`
- `preferred_artifacts`
- `discovery_evidence`
- `stop_reason` when unresolved
- `requires_manual_review`

Resolvers must fail closed when:

- release token cannot be determined
- concrete downloadable files cannot be resolved
- layout drift lowers confidence
- the result is only a landing page instead of stable assets
