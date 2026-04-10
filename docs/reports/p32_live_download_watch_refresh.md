# Live Download Watch Refresh

The refreshed watch is a little better than the last snapshot: there are now multiple download jobs launched, but only two of them are clearly landing bytes right now.

## Actually Moving
- `AlphaFold DB v6` is moving bytes on PID `18908`: `swissprot_cif_v6.tar: 0.09% 35.0 MB/37.3 GB 1.1 MB/s`.
- `UniProt TrEMBL` is moving bytes on PID `77100`: `uniprot_trembl.dat.gz: 2.84% 4.3 GB/149.8 GB 13.0 MB/s`.

## Launched But Silent
- `Reactome + SIFTS expansion` is launched on PID `117960`, but no bytes have shown up in the log tail yet.
- `BindingDB bulk` is launched on PID `82012`, but the log is still silent.
- `STRING core slice` is launched on PID `39968`, but no current progress line is visible yet.
- `ELM + SABIO-RK bulk` is launched on PID `136480`, but it is the same manifest-gap lane we already expected to be weak.

## Completed Local Copies
- `pdbbind` copy finished.
- `skempi` copy finished.

## Blocked or Idle
- STRING remains the clearest failure-prone lane because the earlier guarded run hit repeated `WinError 10060` timeouts.
- ELM is still blocked by the downloader manifest.
- SABIO-RK is still blocked by the downloader manifest.
- Q9UCM0 AlphaFold remains a known partial rescue case because the earlier probe returned HTTP 404.

## Best Next Actions
- Let AlphaFold DB and UniProt keep running, because they are the only lanes proving they are landing bytes.
- Watch BindingDB and Reactome/SIFTS for first-byte emission before treating them as stalled.
- Treat ELM and SABIO-RK as blocked until the manifest support changes.
- Avoid spending more time on STRING unless connectivity materially improves.

## Bottom Line
This refresh confirms the live procurement picture is still narrow in practice: two lanes are paying off, a few lanes are merely launched, and the same structural blockers remain in place.
