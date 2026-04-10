# Live Download Watch

The procurement supervisor is up, but the live download watch is currently idle. There are no active procurement download PIDs right now, so the report should be read as the latest operational state rather than an in-flight transfer snapshot.

## Running
- `scripts\procurement_supervisor.py --loop --poll-seconds 30 --max-parallel 2` is still present, but its state is idle.
- No procurement download process is actively streaming bytes at the moment.

## Completed
- `guarded_sources` completed, but STRING failed repeatedly and BioGRID was already present.
- `resolver_safe_bulk` completed, landing IntAct and BindingDB bytes.
- `q9ucm0_refresh` completed, but Q9UCM0 still remains a partial rescue case because the AlphaFold probe had already shown a 404.

## Blocked
- STRING is blocked by repeated `WinError 10060` timeouts.
- ELM is blocked by the current downloader manifest.
- SABIO-RK is blocked by the current downloader manifest.
- Q9UCM0 AlphaFold is likely partial or missing because the accession-scoped probe hit HTTP 404.

## Live Evidence
- AlphaFold v6 is still the best live byte lane in the logs: `swissprot_cif_v6.tar: 0.09% 35.0 MB/37.3 GB 1.1 MB/s`.
- UniProt TrEMBL is also landing bytes: `uniprot_trembl.dat.gz: 2.84% 4.3 GB/149.8 GB 13.0 MB/s`.
- IntAct completed at full size, and BindingDB downloaded its monthly files successfully.

## Next Best Launch Order
- Run the PROSITE local copy first because it is the only guaranteed byte-positive action.
- Then try the explicit `Q9UCM0` AlphaFold probe once more.
- Retry STRING only if the lane is explicitly requeued and connectivity looks better.
- Keep UniProt TrEMBL moving if the current wave is still open, because it is already producing real bytes.

## Cause Readout
- The network failure pattern is mostly timeout-driven for STRING.
- The manifest failure pattern is structural for ELM and SABIO-RK.
- The remaining Q9UCM0 issue is a remote-asset availability problem, not a transport problem.

## Bottom Line
The current live procurement posture is good on structure and sequence bytes, but not yet healthy enough on curated interaction breadth. The safest immediate gain is a local PROSITE copy, followed by the Q9UCM0 structure rescue attempt.
