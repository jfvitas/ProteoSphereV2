# Q9NZD4 Bridge Validation Handoff

This report-only note captures the narrowest truthful validation surface for `Q9NZD4` using only current live artifacts.

Current bridge facts:
- Accession: `Q9NZD4`
- Candidate status: `rescuable_now`
- Bridge state: `ready_now`
- Selected accession count: `1`
- Matched PDB IDs: `3` (`1Y01`, `1Z8U`, `3OVU`)
- Concrete bridge paths: `4`
- Local bridge payload entries: `9`
- Resolved entries: `7`
- Unresolved entries: `2`

What the preview should expose:
- `accession`
- `candidate_status`
- `bridge_state`
- `selected_accessions`
- `matched_pdb_ids`
- `concrete_paths`
- `bridge_payload_entry_count`
- `resolved_count`
- `unresolved_count`
- `operator_truth`
- `next_safe_step`

Safest next executable step:
- Ingest the local structure bridge for `Q9NZD4` using `1Y01`.
- Keep the preview candidate-only.
- Do not certify a ligand row or claim full materialization.

Operator boundary:
- This is report-only.
- It is routing guidance for bridge validation, not a materialization claim.
- The bridge is ready for operator use, but still not for direct promotion.
