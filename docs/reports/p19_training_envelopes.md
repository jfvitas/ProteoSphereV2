# P19 Training Envelopes

Date: 2026-03-22  
Task: `P19-I008`

## Bottom Line

The current prototype benchmark runtime shows a stable envelope for replaying the frozen 12-accession cohort, but only inside the existing prototype boundary.

The evidence supports repeatable checkpoint identity, identity-safe resume, and a lower resumed loss mean on the same frozen cohort. It does not support any production-grade or weeklong-soak claim.

## Stable Envelope

The stable portion of the envelope is the part already exercised by the frozen benchmark artifacts:

- `run_id` stayed fixed at `multimodal-run:c6ff74a7fb07cdcf`.
- `checkpoint_ref` stayed fixed across replay and resume.
- `checkpoint_path` stayed fixed across replay and resume.
- `checkpoint_resumes` is `1`.
- `checkpoint_writes` is `2`.
- processed example identity stayed stable across resume.
- split counts stayed fixed at `8 train / 2 val / 2 test`.
- the cohort stayed accession-level only with `12 / 12` resolved and `0` unresolved.

The loss envelope is also stable within the current prototype boundary:

- first-run loss mean: `0.07223631432937218`
- resumed-run loss mean: `0.053861256037867226`
- mean loss improved on resume instead of drifting upward.

That is the correct envelope interpretation for this phase: repeatable, identity-safe, and numerically consistent on the frozen cohort.

## Failure Boundaries

The envelope stops being valid if any of the following happen:

- `run_id`, `checkpoint_ref`, or `checkpoint_path` change without an explicit new benchmark run.
- processed example IDs differ between the first pass and resume.
- split counts drift away from `8 / 2 / 2`.
- unresolved or cross-split accessions appear.
- the runtime is described as production-grade instead of local prototype.
- the report is used to imply full corpus validation or unattended weeklong soak completion.

## Evidence Used

This report is grounded in the committed benchmark artifacts:

- [run_summary.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/run_summary.json)
- [checkpoint_summary.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/checkpoint_summary.json)
- [metrics_summary.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/metrics_summary.json)

## Validation Meaning

This phase validates repeatability and resume stability only.

It does not validate:

- production-grade training throughput,
- separate family sweeps,
- release-grade corpus completion,
- or unattended weeklong soak success.

The right release-safe reading is simple: the prototype training envelope is reproducible and resume-stable on the frozen cohort, but it is still a prototype envelope.
