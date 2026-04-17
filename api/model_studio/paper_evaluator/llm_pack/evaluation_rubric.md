# Evaluation Rubric

Verdicts:
- `usable`: evidence is strong, policy is satisfied, and no major leakage or warehouse gap remains.
- `usable_with_caveats`: the split can be discussed or compared, but caveats materially limit trust.
- `audit_only`: useful for review/comparison, not acceptable as a governing training split.
- `blocked_pending_mapping`: explicit members or split details cannot be mapped reliably enough.
- `blocked_pending_cleanup`: mapping exists but provenance/cleanup issues block use.
- `unsafe_for_training`: leakage or policy failure makes the split unacceptable for training.

Core comparison rule:
- Matching means the same `verdict` and the same core `reason_codes`.
- Wording may differ.

Use `needs_human_review=true` only when:
- split parsing is genuinely ambiguous
- provenance is insufficient
- warehouse coverage is inadequate for a reliable conclusion
