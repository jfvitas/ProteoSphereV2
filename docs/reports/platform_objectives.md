# Platform Objectives

ProteoSphereV2 is the next-generation successor to the local-first ProteoSphere / `pbdata` platform in `C:\Users\jfvit\Documents\bio-agent-lab`.

Working objectives carried forward from that project:

- build a trustworthy, local-first biological data platform instead of a thin one-off benchmark script
- maintain explicit provenance and conservative cross-source reconciliation
- avoid leakage-prone dataset generation and shallow random splits
- support multiple structural and multimodal representations instead of one frozen graph worldview
- make the workflow explainable to scientific collaborators, not just to developers
- procure and cross-reference information for individual proteins, protein-protein systems, and protein-ligand systems in one summary library
- store biological origin, motifs, pathway context, Reactome links, and related metadata so training sets can be purpose-built and intelligently split
- materialize robust training packets that can fetch and process the exact structural assets needed for selected examples, including PDB/mmCIF content when required
- keep the modeling layer versatile, efficient, stable, and open-source friendly so other researchers can reuse the system directly

Operational strategy carried forward:

- local source packaging with explicit refresh and retention policy
- canonical planning and identity layers for proteins, ligands, and pair records
- decision-grade field auditing before fields drive curation or training
- representative training-set design instead of duplicate-heavy row maximization
- workflow status and artifact freshness reporting
- pair-to-protein and ligand-to-protein crosswalks so complex examples can be traced back to reusable single-entity summaries
- planning-index storage that is rich enough for experiment design but light enough to avoid downloading every heavy asset up front
- selective materialization so chosen training examples expand into full data packets only when needed

ProteoSphereV2 differences:

- clean-room bootstrap rather than incremental evolution of a dirty worktree
- stronger multi-agent orchestration from the start
- stricter task ownership and queue discipline
- explicit packaging for selective training-set materialization
- stronger emphasis on multimodal system expansion after canonical correctness is established
