# PDB Paper Split Leakage Matrix

- Decision: `blocked`
- Verdict: `high_direct_protein_overlap`
- Blocked categories: `1`
- Review categories: `6`

## Categories

- `direct_protein_overlap` count=`7` severity=`critical` blocking=`True`
- `accession_root_overlap` count=`7` severity=`high` blocking=`False`
- `uniref100_cluster_overlap` count=`7` severity=`high` blocking=`False`
- `uniref90_cluster_overlap` count=`8` severity=`medium` blocking=`False`
- `uniref50_cluster_overlap` count=`9` severity=`review` blocking=`False`
- `shared_partner_overlap` count=`48` severity=`contextual` blocking=`False`
- `flagged_structure_pair_overlap` count=`12` severity=`high` blocking=`False`

## Recommended Action

- Do not treat this paper split as training-ready. Re-split to remove direct protein reuse before deeper evaluation.
