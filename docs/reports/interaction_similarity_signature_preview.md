# Interaction Similarity Signature Preview

- Policy family: `interaction_similarity_compact_family`
- Policy label: `report_only_non_governing`

- Rows: `2`
- Accessions: `2`
- Unique interaction similarity groups: `1`
- BioGRID matched rows total: `251`
- STRING top-level files present: `24`
- STRING top-level files partial: `2`
- STRING top-level files missing: `0`
- IntAct present rows: `2`

## Rows

| Accession | Group | BioGRID rows | STRING state | IntAct state |
| --- | --- | ---: | --- | --- |
| P69905 | biogrid:present__string:partial_on_disk__intact:present | 221 | partial_on_disk | present |
| P09105 | biogrid:present__string:partial_on_disk__intact:present | 30 | partial_on_disk | present |

## Source Surfaces

- `biogrid`: registry=`present`, disk=`present`
- `string`: registry=`missing`, disk=`partial_on_disk`
- `intact`: registry=`present`, disk=`present`

## Truth Boundary

- This is a compact, report-only interaction similarity preview grounded in current on-disk BioGRID, STRING, and IntAct surfaces. It does not materialize the interaction family, STRING remains partial on disk, and IntAct remains present on disk for the selected accessions.
