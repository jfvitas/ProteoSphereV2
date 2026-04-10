# Exhaustive Model Catalog

## 1. Tree / boosting / tabular families
### Required families
- XGBoost
- LightGBM
- CatBoost
- Random Forest
- Extra Trees
- Gradient Boosting Regressor / Classifier
- HistGradientBoosting
- AdaBoost (optional but supported)
- decision tree baselines

### Typical use
- engineered tabular features
- hybrid stack heads
- baseline comparators
- residual learners over neural embeddings

### GUI-exposed controls
Common:
- task_type: regression | binary_classification | multiclass | ranking(optional)
- objective
- eval_metric
- n_estimators
- learning_rate
- max_depth
- min_child_weight / min_samples_leaf analogues
- subsample
- colsample_bytree / feature_fraction analogues
- regularization_l1
- regularization_l2
- min_split_gain / gamma
- class_weight handling
- monotonic constraints
- categorical handling mode
- random_seed
- early_stopping_rounds
- train/validation split policy
- backend selection
- device option if supported (CPU/GPU)

XGBoost-specific:
- booster
- tree_method
- grow_policy
- max_bin
- max_leaves
- sampling_method
- scale_pos_weight
- reg_alpha
- reg_lambda
- gamma
- colsample_bylevel
- colsample_bynode
- interaction_constraints

LightGBM-specific:
- boosting_type
- num_leaves
- min_data_in_leaf
- min_sum_hessian_in_leaf
- bagging_fraction
- bagging_freq
- feature_fraction
- lambda_l1
- lambda_l2
- min_gain_to_split
- max_bin
- linear_tree(optional)
- extra_trees_mode(optional)

CatBoost-specific:
- depth
- iterations
- learning_rate
- l2_leaf_reg
- loss_function
- eval_metric
- bootstrap_type
- bagging_temperature
- random_strength
- leaf_estimation_method
- cat_features handling
- text_features handling(optional)
- border_count
- one_hot_max_size

## 2. Classical neural / dense families
- plain MLP
- residual MLP / ResMLP
- dense block MLP
- tabular attention MLP
- mixture-of-experts MLP

GUI controls:
- input normalization strategy
- number_of_hidden_layers
- hidden_width_per_layer
- hidden_width_schedule
- residual_connections on/off
- dense_connections on/off
- dropout per layer or schedule
- normalization layer type
- activation function per layer or global
- bias on/off
- weight initialization
- layer freezing
- embedding projection size
- output head type

## 3. CNN families
- 1D CNN
- 2D CNN
- 3D CNN
- residual CNN
- DenseNet-style CNN
- dilated CNN
- separable CNN
- UNet and encoder-decoder variants

Global CNN controls:
- spatial_dimension
- channels per block
- kernel size(s)
- stride(s)
- padding mode
- dilation
- pooling type
- pooling kernel / stride
- normalization layer
- activation
- residual block type
- attention block insertion
- skip connection style
- global pooling type
- flatten vs pooling finalization

### U-Net / encoder-decoder controls
- encoder_depth
- decoder_depth
- base_channels
- channel_multiplier
- skip_connection_enable
- skip_merge_type: concat | add | gated_concat | gated_add
- bottleneck_block_type
- deep_supervision on/off
- upsampling type: transpose_conv | interpolation+conv | pixelshuffle(where relevant)
- attention_gate on/off
- residual_unet on/off

## 4. Sequence model families
- vanilla RNN
- LSTM
- GRU
- bidirectional variants
- temporal CNN
- transformer encoder
- transformer decoder
- encoder-decoder transformer
- protein language model wrapper (ESM, ProtBERT-style embedding input adapters)
- frozen-embedding adapter head
- fine-tuned sequence transformer head

Controls:
- tokenization mode
- max sequence length
- truncation policy
- embedding dim
- positional encoding type
- number of layers
- hidden size
- FFN size
- attention heads
- dropout
- causal mask on/off
- bidirectional on/off
- pretrained weight source
- freeze strategy
- pooling strategy for sequence embedding

## 5. Graph model families
### Generic GNNs
- GCN
- GraphSAGE
- GAT
- GIN
- EdgeConv
- MPNN
- graph transformer
- Graph U-Net
- hierarchical graph pooling networks

### Geometric / molecular / equivariant GNNs
- SchNet
- DimeNet / DimeNet++
- EGNN
- PaiNN
- SE(3)-Transformer
- equivariant graph transformer
- directional message passing models
- custom edge-conditioned geometric networks

Controls:
- graph level: atom | residue | hybrid multi-resolution
- node feature schema selection
- edge feature schema selection
- graph construction mode: covalent | contact | radius | knn | mixed
- radius cutoff
- knn k
- self loops on/off
- directionality handling
- message passing layers
- hidden dim
- edge dim
- update dim
- aggregation type: sum | mean | max | attention | set2set | learned
- residual per layer
- normalization per layer
- dropout per layer
- positional encoding
- radial basis encoding type and count
- angle / dihedral feature inclusion
- equivariance level
- coordinate update on/off
- global pooling
- graph batching mode
- readout head type

## 6. Generative / representation learning families
- autoencoder
- variational autoencoder
- denoising autoencoder
- graph autoencoder
- contrastive embedding model
- Siamese / triplet model
- diffusion model (future-ready, optional)
- normalizing flow (future-ready)
- GAN (optional research path)

## 7. Probabilistic / uncertainty families
- deep ensemble
- MC dropout approximation
- Bayesian neural networks
- Gaussian process head / surrogate model
- heteroscedastic regression head
- conformal prediction wrapper
- evidential deep learning head(optional)

## 8. Hybrid / ensemble families
- early fusion multimodal network
- late fusion multimodal ensemble
- stacked ensemble
- residual learning chain
- feature union + tree head
- structure encoder + tabular booster
- sequence encoder + structure encoder + biology encoder + gating
- graph + sequence + ligand co-encoder
- graph embedding -> XGBoost
- XGBoost features -> neural residual
- cross-modal attention fusion

## 9. Baseline families required for honest evaluation
- mean predictor
- median predictor
- linear regression
- ridge/lasso/elastic net
- logistic regression
- shallow random forest
- shallow MLP
- simple GCN baseline
- simple sequence baseline

No advanced architecture may be reported without baseline comparison.
