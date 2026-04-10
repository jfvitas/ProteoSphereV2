# Storage Layout Recommendation

project_root/
  data/
    raw/
    planning_index/
    canonical/
    features/
    embeddings/
    packages/
    reports/
  cache/
  logs/
  runs/

Rules:
- raw is versioned and append-only
- planning indexes are rebuildable
- canonical objects are versioned and lineage-linked
- packages are immutable once versioned
