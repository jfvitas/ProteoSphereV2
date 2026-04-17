# Paper Dataset Evaluator LLM Pack

Use this pack when an LLM needs to evaluate paper-described training/test sets against ProteoSphere logic.

Required inputs:
- the paper corpus JSON
- this folder
- the warehouse files listed in `allowed_sources.json`

Required behavior:
- use warehouse-first evidence only
- default to `best_evidence`
- emit JSON that matches `output_schema.json` before any prose summary
- use only the verdict classes and reason codes defined in this pack

Do not read raw/archive roots directly during normal evaluation. If audit fallback is needed, resolve it through `source_registry.json` and mark the result non-governing unless validated.

Preferred operating mode:
- do **not** act as a freeform independent evaluator when a code-first report and gap packet are available
- instead, use the code-first report as the base truth surface and answer only the bounded ambiguity questions in the gap packet
- your output should be a bounded decision payload that overrides only:
  - `resolved_split_policy`
  - `verdict`
  - `reason_codes`
  - `needs_human_review`
  - short rationale text
