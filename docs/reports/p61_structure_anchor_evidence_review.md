# P61 Structure Anchor Evidence Review

Read-mostly evidence review for the next lightweight-library tranche, focused on `P04637` and `P31749`.

## Truth Boundary

- This note is report-only.
- It does not authorize code changes or publication.
- It reviews current structure and variant evidence only as candidate support.
- It does not claim direct structure-backed joins.

## Summary

Both accessions are good candidates for a future structure-backed variant anchor, but the current structure side still lacks an explicit `variant_ref` anchor. That keeps the review at candidate-only status.

## P04637

- Best experimental structure target: `9R2Q`
- Experimental method: Electron Microscopy
- Resolution: `3.2`
- Chains: `K`, `L`, `M`, `N`
- Reported covered UniProt span: `1-393`
- AlphaFold presence: yes
- AlphaFold model span: `1-393`

Candidate variant signatures inside the covered span:

- `Q5H` at position `5`
- `V10I` at position `10`
- `A119D` at position `119`
- `A129D` at position `129`
- `G389W` at position `389`

Review state: `candidate_only`

The structure evidence is strong enough to justify keeping `P04637` on the shortlist, but not strong enough to claim a direct structure-backed join. The missing anchor is still an explicit structure-side `variant_ref`.

## P31749

- Best experimental structure target: `7NH5`
- Experimental method: X-ray diffraction
- Resolution: `1.9`
- Chain: `A`
- Reported covered UniProt span: `2-446`
- AlphaFold presence: yes
- AlphaFold model span: `1-480`

Candidate variant signatures inside the covered span:

- `K14Q` at position `14`
- `E17K` at position `17`
- `R25C` at position `25`
- `V167A` at position `167`
- `T435P` at position `435`

Review state: `candidate_only`

`P31749` also remains candidate-only. The local evidence supports a future anchor, but the structure side still does not name a concrete `variant_ref`.

## Operator Note

Use these accessions as the next tranche candidates, but keep the current boundary explicit: covered-span evidence and AlphaFold presence are supportive only. They do not authorize a direct structure-backed join until the structure row carries an explicit variant anchor.

## Bottom Line

`P04637` and `P31749` both have enough local evidence to stay in the next tranche, with structure targets `9R2Q` and `7NH5` respectively. The exact missing piece is still a structure-side `variant_ref`, so the truthful status remains candidate-only.
