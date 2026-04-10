# P28 InterPro / Complex Portal Resolver Pinning

As of `2026-03-29`, the procurement package still treats both sources as resolver-first in `protein_data_scope/source_policy.json`, and `protein_data_scope/sources_manifest.json` still points at landing pages instead of machine-downloadable payloads. I probed the live official FTP trees and split each source into concrete URLs that are safe to automate now versus URLs that should stay deferred because they are too large for a default pull.

## InterPro

Resolved release token: `108.0` from `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/release_notes.txt`.

Safe-to-automate URLs:
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/ParentChildTreeFile.txt`
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/entry.list`
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/interpro.dtd`
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/interpro.xml.gz`
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/interpro2go`
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/match_complete.dtd`
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/names.dat`
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/release_notes.txt`
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/short_names.dat`

Deferred because they are too large for a default resolver pull:
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/interpro-n.xml.gz` (`36G`)
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/match_complete.xml.gz` (`68G`)
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/matches-api-data.tar.gz` (`1.3T`)
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/protein2ipr.dat.gz` (`16G`)
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/sites.xml.gz` (`17G`)
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/uniparc_match.tar.gz` (`334G`)

## Complex Portal

Resolved snapshot token: `current` on `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/`. The live tree is under `pub/databases/intact/complex/current/`, not a standalone `complexportal` FTP root. The current directories are `complextab/`, `psi25/`, and `psi30/`, and the snapshot timestamps in the listing are `2026-01-14`.

Safe-to-automate URLs:
- `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/released_complexes.txt`
- `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/complextab/562.tsv`
- `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/complextab/3702.tsv`
- `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/complextab/6239.tsv`
- `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/complextab/9606.tsv`
- `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/complextab/10090.tsv`
- `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/complextab/559292.tsv`
- The full safe `complextab/*.tsv` set is enumerated in `artifacts/status/p28_interpro_complexportal_resolver.json`.

Deferred because they exceed the default size gate or are optional predicted/bulk archives:
- `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/psi25/Homo_sapiens_predicted.zip` (`146M`)
- `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/psi25/complexesMIF25.zip` (`379M`)
- `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/psi30/complexesMIF30.zip` (`154M`)
- `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/psi30/human_predicted.zip` (`115M`)

## Next Step

The concrete resolver output is saved at `artifacts/status/p28_interpro_complexportal_resolver.json`, and the live probe helper is `scripts/resolve_interpro_complexportal.py`. If the resolver snapshot needs to be refreshed, rerun:

`python scripts/resolve_interpro_complexportal.py --output artifacts/status/p28_interpro_complexportal_resolver.json`

Sources used:
- `https://interpro-documentation.readthedocs.io/en/latest/download.html`
- `https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/release_notes.txt`
- `https://www.ebi.ac.uk/training/online/courses/complex-portal-quick-tour/getting-data-from-complex-portal/`
- `https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/`
