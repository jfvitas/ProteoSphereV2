# P22-T005 Failure Injection Plan

## Scope

This slice exercises the current fail-closed boundary for failure injection until a dedicated chaos harness lands.

The integration coverage should stay explicit about three failure modes:

- repeated errors
- bad manifests
- corrupted checkpoints

It should also preserve the prerequisite semantics from `P22-T002` and `P22-T003`:

- repeated errors are recorded as explicit failure envelopes
- restart/resume state is not fabricated after a failed cycle
- checkpoint identity mismatches are treated as corruption, not repaired

## Expected behavior

### Repeated errors

- each injected attempt must be observable
- the test path must stop after the configured failure budget
- no success state should be inferred from a retry loop that never actually recovered

### Bad manifests

- invalid manifest payloads must raise immediately
- unsupported retrieval modes must stay explicit
- no fallback manifest should be synthesized for an invalid payload

### Corrupted checkpoints

- checkpoint identity mismatches must fail validation
- corrupted checkpoint payloads must not be loaded as if they were valid state
- restore semantics must remain fail-closed instead of auto-correcting the payload

## Non-goals

- no silent recovery from malformed inputs
- no checkpoint repair heuristics
- no overclaim that the harness is a full restore system

## Acceptance bar

The integration test is acceptable when it proves the current primitives stay fail-closed for the three injected cases above and leaves the missing dedicated harness module explicit.
