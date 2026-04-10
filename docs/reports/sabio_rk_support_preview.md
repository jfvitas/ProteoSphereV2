# SABIO-RK Support Preview

- Status: `complete`
- Surface kind: `accession_level_kinetics_support_matrix`
- Matrix accessions: `11`
- SABIO seed accessions: `6943`
- Supported accessions: `3`
- Unsupported accessions: `8`
- Dashboard status: `blocked_on_release_grade_bar`
- Operator go/no-go: `no-go`

## Supported Accessions

- `P00387` -> priority=`observe`, bundle=`protein_only_current_preview`, blocker=`local_sabio_seed_only_no_live_kinetic_ids_verified`, next=`verify_accession_scoped_sabio_export`
- `P04637` -> priority=`high`, bundle=`included_current_preview`, blocker=`local_sabio_seed_only_no_live_kinetic_ids_verified`, next=`verify_accession_scoped_sabio_export`
- `P31749` -> priority=`high`, bundle=`included_current_preview`, blocker=`local_sabio_seed_only_no_live_kinetic_ids_verified`, next=`verify_accession_scoped_sabio_export`

## Truth Boundary

- This is a support-only SABIO-RK accession matrix built from the local UniProt accession seed and query-field registry. It does not verify live kinetic-law IDs or SBML exports, and it does not change the blocked operator dashboard.
