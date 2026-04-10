# Model Studio V1 Module Matrix

## Runtime Truth Matrix

| Area | Module / Family | Catalog Visible | Runnable Now | Execution Notes |
|---|---|---:|---:|---|
| Task | protein-protein | yes | yes | Primary executable vertical slice |
| Task | protein-ligand | yes | no | Contract-ready only |
| Task | protein-nucleic-acid | yes | no | Contract-ready only |
| Task | nucleic-acid-ligand | yes | no | Contract-ready only |
| Split | leakage_resistant_benchmark | yes | yes | Default executable path |
| Split | paper_faithful_external | yes | partial | Selection visible; no dedicated runtime lane yet |
| Graph | interface_graph | yes | yes | Materialized from local structures |
| Graph | hybrid_graph | yes | yes | Current default |
| Graph | atom_graph | yes | no | Catalog only |
| Graph | shell_graph | yes | partial | Shell-aware summaries supported; no dedicated graph payload yet |
| Graph | whole_complex_graph | yes | no | Needed for spatial lanes |
| Features | chain extraction and canonical mapping | yes | yes | Real runnable preprocessing |
| Features | waters | yes | yes | Proxy signal from local PDB |
| Features | salt bridges | yes | yes | Proxy signal from local PDB |
| Features | hydrogen-bond/contact summaries | yes | yes | Proxy signal from local PDB |
| Features | pocket/interface geometry | yes | partial | Interface geometry only |
| Features | ligand descriptors | yes | no | Not in current PPI vertical slice |
| Features | sequence embeddings | yes | partial | Only if local path exists; otherwise adapter-backed |
| Features | AlphaFold-derived support | yes | no | Catalog-visible, not launched in v1 |
| Features | PyRosetta | yes | no | Catalog-visible, not launched in v1 |
| Model | xgboost | yes | yes | Resolved through sklearn gradient boosting adapter |
| Model | catboost | yes | yes | Resolved through sklearn random forest adapter |
| Model | mlp | yes | yes | sklearn MLP regressor |
| Model | multimodal_fusion | yes | yes | MLP fusion over tabular + graph-summary features |
| Model | graphsage | yes | yes | Lightweight torch graph adapter |
| Model | gin | yes | yes | Lightweight torch graph adapter |
| Model | gcn | yes | no | Catalog only |
| Model | gat | yes | no | Catalog only |
| Model | edge_message_passing | yes | no | Catalog only |
| Model | cnn | yes | no | Blocked unless spatial input lane is real |
| Model | unet | yes | no | Blocked unless spatial input lane is real |
| Model | heterograph | yes | no | Catalog only |
| Eval | metrics | yes | yes | Persisted per run |
| Eval | outliers | yes | yes | Persisted per run |
| Eval | leakage summary | yes | yes | Persisted per run |
| Eval | comparison | yes | yes | API-backed side-by-side payload |

## Recommendation Rules Already Enforced
- tree models warn when the representation is graph-heavy
- graph-native models block if no graph recipe is defined
- random split warns for protein-binding studies
- unsupported advanced modules stay visible but are marked adapter-backed or blocked

## Immediate Follow-On Targets
- true `gcn` / `gat` runtime support
- AlphaFold-derived feature lane
- PyRosetta adapter and runtime
- whole-complex graph construction
- spatial input support for CNN / U-Net
