# Duplicate Storage Inventory

- Generated at: `2026-04-01T16:17:47.577796+00:00`
- Machine note: [`artifacts/status/duplicate_storage_inventory.json`](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_storage_inventory.json)

## Summary

- Scanned files: `270011`
- Duplicate groups: `42339`
- Duplicate files: `130460`
- Reclaimable files (estimate): `87513`
- Reclaimable bytes (estimate): `100930747119`
- Partial files excluded from reclamation: `9`
- Protected latest files excluded from reclamation: `2`

## Top Reclaimable Groups

- `equivalent_archive_copy`: `3` files, `57160101888` reclaimable bytes, lead file `data\raw\local_copies\alphafold_db\swissprot_pdb_v6.tar`
- `exact_duplicate_cross_location`: `2` files, `29739835392` reclaimable bytes, lead file `data\raw\local_copies\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db`
- `equivalent_archive_copy`: `2` files, `5611751319` reclaimable bytes, lead file `data\raw\local_copies\chembl\chembl_36_sqlite.tar.gz`
- `equivalent_archive_copy`: `2` files, `3340256670` reclaimable bytes, lead file `data\raw\local_copies\pdbbind\P-L.tar.gz`
- `equivalent_archive_copy`: `2` files, `692563345` reclaimable bytes, lead file `data\raw\local_copies\uniprot\uniprot_sprot.dat.gz`
- `equivalent_archive_copy`: `3` files, `579151182` reclaimable bytes, lead file `data\raw\local_copies\bindingdb\BDB-mySQL_All_202603_dmp.zip`
- `exact_duplicate_same_release`: `2` files, `548522694` reclaimable bytes, lead file `data\raw\local_copies\biolip\BioLiP.txt`
- `equivalent_archive_copy`: `2` files, `154422487` reclaimable bytes, lead file `data\raw\local_copies\pdbbind\P-NA.tar.gz`
- `exact_duplicate_cross_location`: `2` files, `115419080` reclaimable bytes, lead file `data\raw\local_copies\reactome\UniProt2Reactome_All_Levels.txt`
- `exact_duplicate_same_release`: `9` files, `57260816` reclaimable bytes, lead file `data\raw\local_copies\models\model_studio\graph_dataset\graph_dataset_records.json`

## Safety Notes

- This report is inventory-only and performs no cleanup.
- Exact duplicates are defined by full SHA-256 identity only.
- Partial transfer files and protected latest pointers are excluded from reclamation.
- Any future cleanup must validate manifests, canonical rebuilds, and packet planning after changes.
