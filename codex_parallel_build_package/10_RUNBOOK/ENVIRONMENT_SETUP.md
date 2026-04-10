# Environment Setup

Set:
- CODEX_CMD
- MAX_CODING_WORKERS
- MAX_ANALYSIS_WORKERS
- ORCH_POLL_SECONDS
- REVIEW_POLL_SECONDS

Suggested initial values:
CODEX_CMD=codex
MAX_CODING_WORKERS=10
MAX_ANALYSIS_WORKERS=3
ORCH_POLL_SECONDS=15
REVIEW_POLL_SECONDS=180

If memory pressure appears:
- drop coding workers to 8
- drop analysis workers to 2
