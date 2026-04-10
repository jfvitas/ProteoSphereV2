# Operator Truth Review After Stage1 Panel

The ligand operator surfaces remain truthful after the consolidated stage1 panel was added.

What is truthful now:
- The consolidated panel is `report_only` and `ready_for_operator_preview`.
- The ligand queue still shows `P00387` as the lead anchor, `Q9NZD4` as the bridge rescue candidate, and `Q9UCM0` deferred.
- The support-readiness surface still keeps `Q9UCM0` deferred and does not materialize ligand rows.
- The top-level next-actions panel stays aligned with the lane-specific cards and does not overclaim promotion.

What it does not claim:
- ligand row materialization
- bundle ligand inclusion
- direct structure certification
- fold export unlock
- duplicate cleanup authorization

Main limitation:
- This is a consolidated steering surface, so it compresses lane detail. The detailed queue and support cards remain the right place to read row-level truth.

Bottom line:
- The new stage1 panel is truthful as an operator triage card. It is not a bundle-backed validation surface, and it should be treated as a summary over the existing truth-preserving lane cards.
