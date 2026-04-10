# Model Studio Beta-Agent and Reference-Library Contract

## Purpose

This document defines the current contract for:

- cross-functional beta test agents that evaluate the Studio at `1920x1080` as the primary signoff viewport
- the compact `proteosphere-lite` reference-library bundle and its chunk catalog

The beta-agent system is delivered inside the existing Studio review and readiness control plane. It is not a separate QA product.

## Beta Test Agents

The shipped set is:

- `visual-cleanliness-agent`
- `usability-agent`
- `content-relevance-agent`
- `scientific-output-agent`
- `failure-recovery-agent`
- `release-governance-agent`

Every signoff-quality sweep uses a real browser window at:

- width `1920`
- height `1080`

The minimum regression viewport remains:

- width `1280`
- height `720`

Each agent result includes:

- `agent_id`
- `flow_id`
- `viewport`
- `scores`
- `top_findings`
- `blocking_findings`
- `recommended_actions`
- `artifact_paths`
- `overall_verdict`

## Required Flow Coverage

The required audited flows are:

- PPI benchmark launchable flow
- governed PPI subset flow
- protein-ligand pilot flow
- blocked `PyRosetta` flow
- blocked `Free-state comparison` flow

## Artifact Layout

Beta-agent artifacts live under the existing review root. The stable primary bundle shape is:

```text
artifacts/reviews/model_studio_internal_alpha/.../1080p/
  agent_catalog.json
  agent_status.json
  agent_matrix.json
  agent_findings.json
  environment.json
  visual-cleanliness-agent/
  usability-agent/
  content-relevance-agent/
  scientific-output-agent/
  failure-recovery-agent/
  release-governance-agent/
```

## Reference Library

The Studio prefers bundled summary data before falling back to heavy external materialization.

Current bundle model:

- core bundle format: `compressed_sqlite`
- chunk layout: `core_bundle_plus_family_chunks`
- decoder: `proteosphere-lite-decoder-v1`

Current functional boundary:

- bundled local summary data:
  - governance
  - launchability
  - split diagnostics
  - leakage and balance analysis
  - packet blueprint planning
- local chunk hydration:
  - ligand support family
  - motif/signature family
- still requires heavy external raw sources:
  - full raw structure files
  - full upstream mirrors
  - heavy example materialization

## Security Boundary

The chunk format is suite-readable by format and decoder. It is intentionally not treated as a cryptographic secrecy boundary in this phase.
