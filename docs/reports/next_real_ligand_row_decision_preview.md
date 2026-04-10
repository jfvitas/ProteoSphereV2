# Next Real Ligand Row Decision Preview

- Selected accession: `P09105`
- Selected gate status: `blocked_pending_acquisition`
- Fallback accession: `Q2TAC2`
- Fallback gate status: `blocked_pending_acquisition`

## Fallback Trigger

- Only advance from P09105 to Q2TAC2 after the selected accession remains blocked_pending_acquisition and the blocker has been recorded without emitting new grounded ligand rows.

## Minimum Grounded Promotion Evidence

- validated local bulk-assay payload or a truthful local structure bridge with ligand-bearing evidence
- grounded row emission passes accession-scoped validation without changing split policy
- candidate-only evidence is excluded from governance claims
