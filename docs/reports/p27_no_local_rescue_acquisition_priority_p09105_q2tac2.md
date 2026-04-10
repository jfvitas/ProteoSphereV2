# P27 No-Local-Rescue Acquisition Priority Note for P09105 and Q2TAC2

Date: 2026-03-23

Scope: establish the next truthful acquisition posture for `P09105` and `Q2TAC2` using the current local ligand source-map results only.

## Grounding Artifact

- [artifacts/status/local_ligand_source_map.json](/D:/documents/ProteoSphereV2/artifacts/status/local_ligand_source_map.json)

## Current Local Source-Map State

### `P09105`

- classification: `structure_companion_only`
- recommended next action: `hold_for_ligand_acquisition`
- local structure-bridge hits: none
- local ChEMBL hits: none
- local BindingDB index hits: none
- local AlphaFold companion: present
  - `AF-P09105-F1-model_v6`

### `Q2TAC2`

- classification: `structure_companion_only`
- recommended next action: `hold_for_ligand_acquisition`
- local structure-bridge hits: none
- local ChEMBL hits: none
- local BindingDB index hits: none
- local AlphaFold companion: present
  - `AF-Q2TAC2-F1-model_v6`

## Truth Boundary

For both accessions, the local `bio-agent-lab` assets provide only structure-companion context. They do not provide a truthful local ligand recovery lane.

That means:

- do not queue either accession for local ligand ingestion
- do not treat AlphaFold presence as ligand rescue
- do not spend more local structure-bridge effort on these rows until a real ligand-bearing source appears

## Acquisition Priority

These two accessions should move as a pair into the fresh-acquisition queue for ligand evidence.

Priority order:

1. `P09105`
   Smaller AlphaFold companion asset and no local recovery signal. It is a clean direct-acquisition candidate with no credible local detour.
2. `Q2TAC2`
   Same truth state as `P09105`, but with a larger AlphaFold companion payload and no better local rescue evidence.

## Recommended Next External Lanes

- direct assay acquisition from external ligand-capable sources
- structure-linked ligand acquisition only if a real target-bound structure is found
- keep AlphaFold as protein-structure context only after ligand evidence is acquired elsewhere

## Operational Recommendation

Treat both accessions as `no_local_ligand_rescue` in planning, even though the current source-map classification remains `structure_companion_only`.

That is the conservative operational interpretation of the current artifact:

- local companion structure exists
- local ligand source does not
- next useful move is fresh acquisition, not more local mining
