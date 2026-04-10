# Bio-Agent-Lab Reference Notes

This note captures the most relevant carryover goals from `C:\Users\jfvit\Documents\bio-agent-lab` for ProteoSphereV2.

## Product Aim Carryover

ProteoSphereV2 should preserve the older platform's core intent:

- local-first biological source packaging rather than thin online-only workflows
- explicit provenance and cross-source reconciliation
- conservative canonical identity handling that preserves ambiguity instead of guessing
- leakage-resistant training/validation/test governance
- support for multiple graph and multimodal packaging strategies
- operator-facing reporting that makes dataset quality, readiness, and blockers visible

## Architectural Themes Worth Reusing

- source packaging and capability registry
- canonical planning and identity layers for proteins, ligands, and pair records
- staged extraction, normalization, screening, split design, and packaging
- workspace-first operational manifests and status reporting
- readiness reporting that distinguishes exploratory outputs from release-grade outputs

## Specific Strategy Signals

- do not optimize only for row count; optimize for representative, defensible training sets
- keep split logic inspectable and resistant to duplicate-heavy leakage
- treat planned sources differently from implemented sources
- keep GUI/API surfaces honest about data maturity and operational state
- preserve multiple structural viewpoints instead of assuming one graph design is universally correct

## Implications For V2 Queue Management

- prioritize canonical and provenance correctness before multimodal expansion
- keep data-source analysis and storage policy explicit for each source
- require blocker logging whenever the missing master handoff package leaves the baseline underspecified
- treat long-run autonomy as an orchestration problem with visible manifests, not as hidden background behavior
