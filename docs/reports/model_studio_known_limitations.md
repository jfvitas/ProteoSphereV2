# Model Studio Known Limitations

## Current Truth Boundary

This controlled beta is designed for structure-backed protein-protein studies plus one narrow structure-backed protein-ligand pilot. It is not a general biomolecular modeling release.

## Current Limitations

- Most governed staged rows remain review-only, so governed-subset promotion is intentionally narrow.
- The protein-ligand pilot is intentionally narrow: structure-backed rows only, exact Kd/Ki-derived `delta_G`, and only `graphsage` plus `multimodal_fusion` are launchable.
- PyRosetta and free-state comparison are prototype tracks with artifacts, not launchable study lanes.
- Atom-native and sequence-embedding lanes are beta surfaces and should be used only when the selected controls still show `Launchable now`.
- The current sequence-embedding lane is a Studio-local deterministic materialization path, not a broader standalone embedding backend.
- The broader non-PPI surface remains inactive in this beta program.
- The governed staged candidate universe is still highly concentrated in `expanded_ppi_procurement_bridge`, so diversification work continues in parallel even though the current launchable lanes are already frozen for beta.

## What To Do If You Hit A Limit

- Use the guided flow and prefer launchable pools first.
- Open `Need help / report issue` if a limitation is unclear or a control behaves unexpectedly.
- Include the selected dataset, model family, and current step in the report.
