# Codex Parallel Build Package
Generated: 2026-03-21T23:04:02.501741+00:00

Single package for running a large parallel Codex build of the biomolecular ML platform.

Use this with the existing master handoff package and specs already created.
This package adds:
- one master prompt
- planner / worker / reviewer operating model
- orchestration scripts
- task queue scaffolding
- source acquisition + source-analysis mission
- storage/index/package mission
- launch runbook

Important:
This is designed for maximal autonomy, but no unattended software process can be guaranteed to make perfect architectural decisions without any review.
The package minimizes drift using strict phases, branch isolation, CI, and blocker reporting.
