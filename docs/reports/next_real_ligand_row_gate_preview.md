# Next Real Ligand Row Gate Preview

- Status: `complete`
- Selected accession: `P09105` -> `blocked_pending_acquisition`
- Fallback accession: `Q2TAC2` -> `blocked_pending_acquisition`
- Current grounded accessions: `P00387`
- Can materialize a new grounded accession now: `False`
- Next unlocked stage: `record_selected_accession_blocker_then_recheck_fixed_fallback_accession`

## Reasons

- `P09105`: hold_for_ligand_acquisition
- `Q2TAC2`: hold_for_ligand_acquisition

## Truth Boundary

- This is a report-only gate for the next real ligand-row accession after the current grounded ligand family. It preserves the fixed P09105 -> Q2TAC2 order, does not emit new ligand rows, and does not change split or leakage behavior.
