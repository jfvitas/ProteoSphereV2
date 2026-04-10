# P32 Remaining Download Queue

This queue is derived from the current repo-local source manifest, the broad seed mirror, and the latest p32 procurement artifacts. I treated the seed mirror as the truth for what can be copied now, and the downloader/runtime logs as the truth for what is still blocked.

## Summary
- Local-copy actions: 4
- Auto-runnable download actions: 2
- Blocked actions: 3

## Queue
| Priority | Kind | Source | Representative targets | Why now |
| --- | --- | --- | --- | --- |
| 1 | local_copy | `prosite` | prosite.dat, prosite.doc, prosite.aux | Already on disk, no network call is needed, and this is the cheapest way to close the motif lane that the summary library still treats as weak. |
| 2 | local_copy | `elm` | elm_classes.tsv, elm_interaction_domains.tsv | The current downloader path is blocked, but the source files are already in the broad seed mirror, so promotion is immediately actionable and restores a second motif channel. |
| 3 | local_copy | `biogrid` | BIOGRID-ALL-LATEST.mitab.zip, BIOGRID-ORGANISM-LATEST.psi25.zip | BioGRID is already mirrored and is one of the cleanest curated PPI breadth gains available, so copying it is cheaper than any network retry. |
| 4 | local_copy | `intact` | intact.zip, mutation.tsv | IntAct is already on disk and directly supports the curated PPI anchor used by the operator-facing summary library. |
| 5 | auto_runnable_download | `uniprot` | uniprot_trembl.dat.gz, uniprot_trembl.fasta.gz, idmapping_selected.tab.gz, uniref90.fasta.gz | This is the highest-value remaining sequence-depth continuation: the reviewed Swiss-Prot spine is already there, but TrEMBL and the related mapping/UniRef files still need to land. |
| 6 | auto_runnable_download | `reactome` | UniProt2ReactomeReactions.txt, ChEBI2Reactome_All_Levels.txt, NCBI2Reactome.txt, Ensembl2Reactome.txt | Reactome already has the core pathway spine on disk, but a large number of top-level tables are still absent from the broad seed mirror, so finishing the remaining pathway tables is still worthwhile. |
| 8 | blocked | `string` | protein.links.v12.0.txt.gz, protein.links.detailed.v12.0.txt.gz, protein.info.v12.0.txt.gz | STRING remains the main stalled network lane; the guarded attempts timed out, so this should stay parked until connectivity recovers. |
| 9 | blocked | `sabio_rk` | sabio_p31749_entry_ids.txt, sabio_p31749_sbml.xml | SABIO-RK is still a manifest gap in the downloader path, so the missing query exports are not automatable yet even though the broader lane is useful. |
| 10 | blocked | `bindingdb` | purchase_target_10000.tsv, BDB_my.tar | The main monthly BindingDB files are already present; the leftover legacy files 404ed in the live wave, so they should not be retried as a top-priority download. |

## Notes
- `local_copy` means the payload is already on disk in `data/raw/protein_data_scope_seed` and should be promoted into the active local-copy layer before any redownload.
- `auto_runnable_download` means the manifest still exposes a concrete file list and the lane can be advanced with the existing downloader.
- `blocked` means the lane is currently failing for a specific reason and should not be treated as a routine download.
- I intentionally did not queue `mega_motif_base` or `motivated_proteins` because they are not in the current manifest, and I left out RNAcentral fan-outs until the directory enumeration exists and the public Postgres database remains the truthful SQL access path.

## Blockers To Keep Visible
- `string`: repeated timeout failures in the guarded download wave.
- `sabio_rk`: downloader support is still missing for the manifest-backed lane.
- `bindingdb`: the leftover legacy files 404ed in the live wave and are not a good near-term retry target.
