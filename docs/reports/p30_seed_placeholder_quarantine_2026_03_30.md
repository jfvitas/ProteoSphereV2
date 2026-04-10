# P30 Seed Placeholder Quarantine

- Generated at: `2026-03-30T13:05:00-05:00`
- Focus: record which repo-seed lanes look present at a glance but must stay out of the effective merge because the local evidence is incomplete or placeholder-only.

## Quarantined Seed Lanes

| Source lane | Repo-seed evidence confirmed | Why it stays gated |
| --- | --- | --- |
| `bindingdb` | Six ZIP files under `data/raw/protein_data_scope_seed/bindingdb`, each only about `12 KB`, plus `_source_metadata.json` at `1,922` bytes | These are still placeholder-scale stubs, not a usable BindingDB dump |
| `alphafold_db` | `swissprot_cif_v6.tar.part` at `36,700,160` bytes plus `_source_metadata.json` | Partial archive only; not safe to count as a complete predicted-structure mirror |
| `string` | `_source_metadata.json` only at `4,149` bytes | Metadata without graph payloads would falsely inflate interaction coverage |

## Merge Consequences

1. Keep `bindingdb` bulk under quarantine even though accession-scoped or previously validated captures can still contribute provenance.
2. Keep repo-seed `alphafold_db` outside authoritative presence and only use already-validated non-seed AlphaFold material when explicitly traced.
3. Keep `string` excluded from the effective interaction merge until real link/info/alias tables are downloaded.

## Registry Guidance

- The source-definition notes in [`execution/acquire/local_source_registry.py`](D:/documents/ProteoSphereV2/execution/acquire/local_source_registry.py) now encode this quarantine guidance directly for:
  - `bindingdb`
  - `alphafold_db`
  - `string`

## Practical Blend Rule

Count repo-seed payloads as merge-eligible only when they provide real downloadable content or extracted corpora, not when they only provide a stub file, metadata marker, or partial archive fragment.
