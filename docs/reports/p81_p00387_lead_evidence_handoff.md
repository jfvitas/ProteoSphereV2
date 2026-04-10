# P00387 Lead Evidence Handoff

This report-only note captures the narrowest truthful handoff we can derive from the local P00387 ChEMBL payload.

Current evidence:
- Accession: `P00387`
- Target: `CHEMBL2146` / `NADH-cytochrome b5 reductase`
- Emitted rows: `25`
- Activity count total: `93`
- Distinct assays in payload: `10`
- Distinct ligands in payload: `23`
- Top ligand: `CHEMBL35888`
- Source DB: `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db`

Operator summary:
- This is a planning-grade local ChEMBL lead anchor, not a canonical ligand materialization.
- The payload is useful as a bundle-friendly evidence handoff because it is concrete, bounded, and accession-clean.
- The counts reflect evidence volume only; they do not claim potency, selectivity, or rescue completion.

Safest next executable step:
- Run a bounded `P00387`-only ligand extraction validation pass.
- Keep the scope on fresh-run local evidence only.
- Validate whether a truthful ligand lane can be emitted without making any promotion claim.

Do not claim:
- canonical ligand materialization
- canonical assay resolution
- rescue complete
- packet promotion
