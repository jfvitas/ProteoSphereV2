# Human Review Gate

Set `needs_human_review=true` when any of these are true:
- split parse confidence is low
- provenance is insufficient
- warehouse coverage gap prevents a reliable conclusion
- multiple canonical split policies remain plausible

Do not set it merely because the verdict is negative. A clear deterministic failure should stay code- and rule-driven.
