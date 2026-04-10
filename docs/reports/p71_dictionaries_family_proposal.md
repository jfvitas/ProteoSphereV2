# P71 Dictionaries Family Proposal

This is a report-only proposal for the safest real `dictionaries` family shape, grounded in the current live protein, variant, and structure library references plus the current lightweight bundle manifest.

## What Is Actually Present Today

The live libraries already expose a small, stable namespace set that can support a truthful dictionary lookup family:

- `domain / InterPro`
- `domain / Pfam`
- `domain / CATH`
- `domain / SCOPe`
- `motif / PROSITE`
- `pathway / Reactome`
- `cross_reference / IntAct`

The current protein-variant slice does not contribute namespace-bearing rows, so it does not enlarge the dictionary namespace set.

## Proposed Row Shape

The safest shape is one row per `(reference_kind, namespace)` pair.

Recommended keys:

- `dictionary_id`
- `reference_kind`
- `namespace`
- `reference_count`
- `protein_count`
- `example_identifiers`
- `source_artifacts`
- `truth_boundary`

Recommended sort order:

1. highest `reference_count`
2. namespace ascending

This keeps the family compact and makes it easy for operators to see which namespaces are actually populated today.

## Expected Row Count

The proposal is `7` rows total:

- `domain / InterPro` - 61 references across 11 proteins
- `domain / Pfam` - 16 references across 10 proteins
- `domain / CATH` - 4 references across 2 proteins
- `domain / SCOPe` - 4 references across 2 proteins
- `motif / PROSITE` - 13 references across 9 proteins
- `pathway / Reactome` - 254 references across 3 proteins
- `cross_reference / IntAct` - 2 references across 1 protein

That is the smallest truthful dictionary family that still reflects the current live reference namespaces without inventing new classes.

## Truth Boundary

This proposal is report-only.

It does not say the bundle manifest already includes dictionaries. In the current bundle manifest, `dictionaries` is still excluded and recorded at `0`.

It also does not widen the family to any namespace that is not already present in the live library references. In particular, it does not invent new variant namespaces.

## Safest Reading

If bundle iteration three ever adds dictionaries, this is the safest real family shape:

- it is lookup-shaped rather than payload-heavy
- it reuses namespaces already present in the protein and structure libraries
- it stays bounded to 7 rows
- it keeps the release gate separate from the reporting proposal

## Boundary

This note is report-only. It is meant to guide bundle iteration planning, not to rewrite the manifest or claim dictionary materialization has already happened.
