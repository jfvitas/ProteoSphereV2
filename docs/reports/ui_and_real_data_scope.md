# UI And Real-Data Scope

Current direction:

- keep a usable PowerShell or CLI operator surface in the active development path
- add WinUI as an explicit later-phase task rather than leaving it implicit
- require true downloaded-source validation before claiming end-to-end success

Near-term operator goals:

- inspect queue state, blockers, and review items
- inspect summary-library population and corpus coverage
- trigger selective materialization and benchmark runs
- inspect benchmark outputs and split diagnostics

Real-data validation goals:

- validate on actual downloaded source content where terms and infrastructure allow
- verify pair-to-protein and ligand-to-protein cross-referencing on real corpora
- build robust example packets, including PDB/mmCIF retrieval and processing when needed
- report statistical outcomes and stability, not just successful execution

WinUI note:

The current session does not expose a dedicated WinUI skill. WinUI can still be scaffolded as code and documentation, but the active near-term path remains PowerShell-first unless a WinUI-focused toolchain is added later.
