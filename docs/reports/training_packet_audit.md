# Training Packet Audit

Date: 2026-03-22
Task: `P13-I008`
Status: `completed`

## Verdict

The selected-example training packet audit ran against the real benchmark artifact set under
`runs/real_data_benchmark/full_results`.

It found `12` packet rows for the frozen cohort. `1` packet is currently strong enough to call
useful, `11` are conservatively weak, and `0` are blocked. All `12` packets remain `partial`
rather than complete because at least one requested modality is still missing for every row.

## Aggregate Findings

- Packet count: `12`
- Useful packets: `1`
- Weak packets: `11`
- Blocked packets: `0`
- Complete packets: `0`
- Partial packets: `12`
- Missing `sequence`: `2`
- Missing `structure`: `11`
- Missing `ligand`: `11`
- Missing `ppi`: `10`

## What The Audit Shows

- `P69905` is the strongest current packet.
  It is the only row judged `useful`, with direct live smoke and multilane support across sequence
  and structure plus annotation/pathway support, but it is still partial because ligand and PPI
  modalities are absent.
- `P68871` is still packet-level `weak`.
  It has sequence plus PPI support, but the evidence remains probe-backed and mixed.
- The remaining rows are truthful packet stubs, not full training packets.
  They preserve accession, canonical id, planning index reference, leakage key, modality presence,
  coverage notes, and provenance pointers, but they do not justify a stronger completeness claim.

## Runtime Boundary

- Backend: `local-prototype-runtime`
- Runtime surface: `local prototype runtime with surrogate modality embeddings and identity-safe resume continuity`
- Selected accession count: `12`

This audit is about packet traceability and completeness on the current prototype benchmark
artifacts. It is not a claim that release-grade multimodal training packets already exist for the
whole cohort.

## Artifacts

- Machine-readable audit: `runs/real_data_benchmark/full_results/training_packet_audit.json`
- Supporting benchmark artifacts:
  - `runs/real_data_benchmark/full_results/source_coverage.json`
  - `runs/real_data_benchmark/full_results/provenance_table.json`
  - `runs/real_data_benchmark/full_results/usefulness_review.json`
  - `runs/real_data_benchmark/full_results/run_summary.json`

## Limits

- The audit is bounded to the frozen 12-accession cohort.
- Packet completeness is still partial across the board because modality coverage is incomplete.
- The underlying runtime remains prototype-class, so packet usefulness should not be upgraded into a
  release-readiness claim.
