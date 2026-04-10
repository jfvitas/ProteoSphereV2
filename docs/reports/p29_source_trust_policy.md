# P29 Source Trust Policy

Date: 2026-03-30  
Artifact: `p29_source_trust_policy`

## Purpose

This policy defines how summary values should be chosen when sources disagree in the current source set: `UniProt`, `Reactome`, `InterPro`, `ChEBI`, `BindingDB`, `ChEMBL`, `IntAct`, `BioGRID`, `STRING`, `RCSB/PDBe`, `AlphaFold DB`, `PDBBind`, `BioLiP`, and local extracted assets.

The core rule is simple: collapse only when the disagreement is artificial. If the sources are truly making different claims, keep the competing values visible.

## Value Classes

The policy separates summary values into classes because the same field name can mean different things across sources.

| Value class | Primary authority | Supporting sources | Collapse rule |
| --- | --- | --- | --- |
| Identity | `UniProt`, `ChEBI`, `RCSB/PDBe`, `Reactome`, `InterPro` | `BindingDB`, `ChEMBL`, `IntAct`, `BioGRID`, `PDBBind`, `BioLiP`, local extracted assets | Collapse only exact normalized equivalents or explicit aliases. |
| Sequence | `UniProt` | `RCSB/PDBe`, `AlphaFold DB`, local extracted assets | Collapse only if sequence version and normalized hash agree. |
| Structure | `RCSB/PDBe` | `AlphaFold DB`, `PDBBind`, `BioLiP`, local extracted assets | Never collapse experimental and predicted structure into one truth value. |
| Interaction evidence | `IntAct`, `BioGRID` | `STRING`, `PDBBind`, `BioLiP`, local extracted assets | Collapse only when pair, type, and evidence class agree. |
| Ligand identity | `ChEBI` | `BindingDB`, `ChEMBL`, `PDBBind`, `BioLiP`, local extracted assets | Collapse only after chemical standardization to the same entity. |
| Assay measurement | `BindingDB`, `ChEMBL` | local extracted assets | Collapse only after unit, endpoint, and construct compatibility checks. |
| Pathway annotation | `Reactome` | `UniProt`, `InterPro`, local extracted assets | Collapse only when pathway and species context agree. |
| Domain/motif annotation | `InterPro` | `UniProt`, `BioLiP`, `PDBBind`, local extracted assets | Collapse only when ontology accession and residue span agree or one term entails the other. |
| Context/proxy | `STRING`, `AlphaFold DB` | local extracted assets | Never let context-only values override direct evidence. |

## Precedence

Precedence is class-specific, not global. A source can be authoritative for one kind of value and merely supporting for another.

1. Direct evidence beats indirect context.
1. Source-native truth beats derived local summary.
1. The source native to the claim class beats a generic or broad context source.
1. Experimental values beat predicted values when they describe the same claim.
1. Curated pair evidence beats breadth-only network context.
1. Assay-backed measurements beat copied or inferred values.

That means `UniProt` is strongest for protein identity, `ChEBI` is strongest for small-molecule identity, `RCSB/PDBe` is strongest for experimental structure, `Reactome` is strongest for pathway membership, `InterPro` is strongest for domains and motifs, `IntAct` and `BioGRID` are strongest for curated interaction evidence, and `BindingDB`/`ChEMBL` are strongest for measured ligand activity.

`STRING`, `AlphaFold DB`, `PDBBind`, `BioLiP`, and local extracted assets still matter, but they are supporting or derived layers rather than automatic truth overrides.

## Consensus Rules

The consensus process should be deterministic:

1. Normalize identifiers, units, and ontology terms before comparison.
1. Collapse exact normalized matches into one canonical summary value with multiple provenance links.
1. Prefer the more specific term when one value is a strict ontology parent of another.
1. Prefer the source-native authority for the claim class when values still disagree.
1. For numeric values, only form consensus after unit normalization and endpoint matching.
1. If the values are still semantically different, preserve them as competing values instead of averaging or flattening them.

Numeric summary values need special care. A single averaged point is often less honest than a range, a source-ordered list, or a set of raw measurements. The policy therefore prefers the narrowest defensible representation that does not erase disagreement.

## Tie-Breaks

When normalization does not resolve the conflict, use the following order:

1. Prefer the source-native authority for the value class.
1. Prefer direct curated or experimental evidence over predicted, copied, or neighborhood-only evidence.
1. Prefer the value with the tighter semantic scope when one value entails the other.
1. Prefer the value backed by more independent primary sources, not just more copies of the same record.
1. Prefer release recency only for operational or correction-prone fields, never as a substitute for authority.
1. If nothing cleanly wins, keep both values and mark the field unresolved.

This is the main guardrail against over-collapse. The policy should not manufacture certainty just because a downstream summary wants a single cell.

## Provenance

Every summary value must carry provenance strong enough to reconstruct why it won.

Required fields for each summary value:

- `source_name`
- `source_record_id`
- `release_or_snapshot_id`
- `retrieval_timestamp`
- `normalized_value`
- `raw_value`
- `transformation_steps`
- `authority_tier`
- `claim_class`
- `confidence_or_support_status`

Consensus values need extra lineage:

- contributing source names
- contributing record IDs
- normalization pipeline
- tie-break reason
- retained alternates
- conflict status

Local extracted assets need even stricter provenance because they are derived:

- upstream source names
- upstream record IDs
- extractor or pipeline ID
- artifact path
- content hash

## Keep Multiple Values

Retain multiple competing values instead of collapsing them when any of the following is true:

- the values come from different claim classes, such as identity versus context
- experimental structure and predicted structure disagree
- the values are not equivalent after normalization
- the values refer to different species, assemblies, isoforms, constructs, or reaction contexts
- numeric values differ beyond the class tolerance after unit conversion
- a higher-authority source is indirect while a lower-authority source is direct and class-native
- a source-specific label would lose meaning if forced into a single canonical ontology term
- local extracted assets conflict with upstream native source values
- the safest representation is an interval, set, or ordered list rather than a scalar

## Recommended Output Shapes

- `single_value` when values are truly equivalent after normalization.
- `primary_value_plus_alternates` when one canonical value is defensible but alternatives still matter for auditability.
- `multi_value_set` when the disagreement is meaningful and collapsing would erase biological distinctions.
- `unresolved_conflict` when no source clearly wins without inventing evidence.

## Practical Summary

The policy is conservative on purpose. It lets the platform build clean summary values when sources agree, but it refuses to hide genuine disagreement. That is especially important for the current source set because it spans identity, pathway, motif, structure, assay, interaction, and context layers that should not all be treated as interchangeable truth sources.
