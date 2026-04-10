# Procurement and Gap Story

This slice is for deck use. The live story is straightforward: the procurement stack is already strong in structure and ligand bytes, but it is still weak in curated interaction-network breadth, motif breadth, and the residual Q9UCM0 packet gap.

## What Is Strong
- Structure is the strongest lane overall, backed by AlphaFold DB v6, RCSB/PDBe, and the broader local mirror.
- Ligand procurement is also strong, with BindingDB and the existing mirrored ligand assets carrying substantial byte volume.
- IntAct landed bytes cleanly, so curated PPI is not absent everywhere, even though the registry view is still incomplete.

## What Is Weak
- STRING, BioGRID, and IntAct still leave the curated interaction-network class underpowered in the registry view.
- PROSITE, ELM, Mega Motif Base, and Motivated Proteins are still missing, so motif breadth is structurally thin.
- UniProt is partial, and TrEMBL is still early enough that the sequence lane is not yet deep.

## What Is Actively Landing Bytes
- AlphaFold DB v6 bulk is live: `swissprot_cif_v6.tar: 0.09% 35.0 MB/37.3 GB 1.1 MB/s`.
- UniProt TrEMBL is live: `uniprot_trembl.dat.gz: 2.84% 4.3 GB/149.8 GB 13.0 MB/s`.
- IntAct completed successfully: `intact.zip` reached `100.00%` at `1.3 GB / 1.3 GB`, and `mutation.tsv` also completed.
- BindingDB downloaded the monthly bulk files successfully, even though two legacy filenames 404ed.

## What Is Blocked
- STRING is the main stalled lane: repeated `WinError 10060` timeouts hit the guarded download set.
- ELM is blocked by the current downloader manifest, so an automated rerun would not land bytes.
- SABIO-RK is also blocked by the current downloader manifest.
- The Q9UCM0 AlphaFold probe is still risky because earlier runs already returned AlphaFold HTTP 404 for that accession.

## Completion by Pinned Targets
- Source targets present: `29/39 = 74.4%`.
- Packet targets complete: `7/12 = 58.3%`.
- Packet targets still partial: `5/12 = 41.7%`.
- Remaining packet deficits are concentrated in `ligand=5`, `ppi=1`, and `structure=1`, with Q9UCM0 carrying the deepest hole.

## Model-Readiness Implication
- Canonical readiness is stable, so identity is not the blocker.
- The cohort is not yet balanced enough for multi-modal model readiness because the remaining partial packets are dominated by ligand gaps and a single high-value structure/PPI hole at Q9UCM0.
- This is ready for anchored analysis and deck framing, but not yet ready for a broad "complete enough" claim.

## Bottom Line
Procurement is landing bytes where the platform already has depth, but the next meaningful gains come from the missing breadth classes: curated PPI, motif systems, and the last Q9UCM0 rescue path.
