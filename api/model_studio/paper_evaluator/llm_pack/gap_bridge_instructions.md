# Gap Bridge Instructions

Use this mode when the code-first evaluator has already run and produced:
- a base report
- a gap packet listing only papers that need LLM judgment

In gap-bridge mode:
- do not recompute the entire evaluation from scratch
- do not override papers that are not present in the gap packet
- treat the code-first report as the primary factual output
- answer only the bounded ambiguity questions for each paper in the packet

Allowed override fields per paper:
- `resolved_split_policy`
- `verdict`
- `reason_codes`
- `needs_human_review`
- `llm_rationale`

Do not introduce new reason codes outside `reason_code_catalog.json`.
Do not widen the evidence surface beyond `allowed_sources.json`.

If the code-first result is already clearly correct, keep it unchanged.
