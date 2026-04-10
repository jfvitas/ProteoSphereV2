# Model Studio Bootstrap

This report captures the first implemented bootstrap slice of the Model Studio program.

## What exists now

- Canonical Studio contracts:
  - `api/model_studio/contracts.py`
  - `artifacts/schemas/model_studio_pipeline.schema.json`
- Design catalog and default preview pipeline:
  - `api/model_studio/catalog.py`
- Lightweight web/API scaffold:
  - `api/model_studio/server.py`
  - `gui/model_studio_web/index.html`
  - `gui/model_studio_web/app.js`
  - `gui/model_studio_web/styles.css`
- Master Studio Agent bootstrap:
  - `scripts/model_studio_task_catalog.py`
  - `scripts/model_studio_master_agent.py`

## What this slice is for

- establish a versioned contract for Studio pipeline drafts
- make the planned work visible as a dedicated queue-backed program
- provide a concrete web-first shell that can evolve into the real Studio
- preserve the repo's manifest-heavy orchestration style instead of inventing a hidden control plane

## Current limits

- the web app is a preview shell, not a full production UI
- the HTTP server is a lightweight standard-library scaffold, not the final backend
- the Master Studio Agent currently seeds and validates the Studio queue, but does not yet replace the main orchestrator
- the generated backlog is intentionally broad and parallelizable; implementation details still need to be filled in by the worker/reviewer system

## Bootstrap commands

- Preview the Studio task program:
  - `python scripts/model_studio_master_agent.py`
- Write the dedicated Studio queue:
  - `python scripts/model_studio_master_agent.py --write-queue`
- Run the preview web server:
  - `python api/model_studio/server.py`

The preview server exposes:

- `GET /api/model-studio/health`
- `GET /api/model-studio/catalog`
- `GET /api/model-studio/workspace-preview`
