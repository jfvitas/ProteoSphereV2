# GUI and Dynamic Option Exposure Rules

## GUI sections
1. Project / storage location
2. Data source acquisition
3. Canonicalization and normalization
4. Feature extraction
5. Dataset filtering and split strategy
6. Model family selection
7. Architecture builder
8. Training and optimization
9. Experiment control / AutoML
10. Evaluation and diagnostics
11. Export and deployment
12. Logs / lineage / provenance / monitoring

## UX modes
- Basic
- Advanced
- Expert / Research

Options must specify visibility tier.
Example:
- batch_size visible in Basic
- mixed_precision visible in Advanced
- FSDP shard policy visible in Expert

## Dynamic dependencies
Examples:
- if model_family in [xgboost, lightgbm, catboost] -> show tree controls, hide neural layer builder
- if model_family == unet -> show encoder/decoder depth, skip merge type
- if graph_model selected -> show graph construction controls
- if uncertainty_head enabled -> show variance loss parameters, calibration options
- if mixed_precision disabled -> hide grad scaler options
- if evaluation split == group_kfold -> show group key selector
- if source AlphaFold selected -> show pLDDT confidence thresholds
- if disorder source selected -> show region join policy

## GUI constraints
- Do not expose impossible combinations
- Do not silently ignore hidden invalid fields
- Show dependency rationale/tooltips
- Save all settings to versioned config files
- Allow cloning and diffing experiment configs
