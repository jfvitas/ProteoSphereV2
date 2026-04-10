# Global Training, Optimization, and Runtime Controls

## Framework/backends
- PyTorch (primary)
- TensorFlow (supported abstraction target)
- JAX (future extension point)
- sklearn-compatible classical backends
- xgboost/lightgbm/catboost native wrappers

## Device/runtime
- cpu
- single_cuda_gpu
- multi_gpu_data_parallel
- distributed_data_parallel
- fsdp(optional advanced)
- cpu fallback
- mixed precision: fp32 | fp16 | bf16
- deterministic mode
- cudnn benchmark toggle
- gradient accumulation
- gradient clipping
- anomaly detection toggle
- compile graph toggle(where backend supports)

## Optimizers
Required:
- SGD
- Adam
- AdamW
- RMSprop
- Adagrad
- Adadelta
- Lion(optional advanced)
- LAMB(optional large-batch)
- fused backend-specific optimizers where available

Per-optimizer controls:
SGD:
- lr
- momentum
- dampening
- weight_decay
- nesterov
Adam/AdamW:
- lr
- betas
- eps
- weight_decay
- amsgrad
RMSprop:
- lr
- alpha
- eps
- weight_decay
- momentum
- centered
Adagrad:
- lr
- lr_decay
- weight_decay
- eps

## Schedulers
- none
- step
- multi_step
- exponential
- cosine annealing
- cosine with warm restarts
- one_cycle
- reduce_on_plateau
- linear warmup
- warmup + cosine
- custom schedule via callback

Scheduler controls:
- initial_lr
- min_lr
- milestones
- gamma
- warmup_steps
- warmup_ratio
- cycle length
- plateau monitor metric
- plateau factor
- plateau patience

## Losses
Regression:
- mse
- rmse(wrapper or metric)
- mae
- huber
- smooth_l1
- quantile loss
- log-cosh
- heteroscedastic negative log likelihood
Classification:
- binary cross entropy
- cross entropy
- focal loss
- label-smoothed CE
Ranking/contrastive:
- margin ranking
- triplet loss
- contrastive InfoNCE
Multi-task:
- weighted sum of task losses
- uncertainty-weighted task balancing
- dynamic task balancing

## Early stopping / checkpoints
- monitor metric
- mode min/max
- patience
- min_delta
- restore_best_weights
- checkpoint_every_n_epochs
- checkpoint_every_n_steps
- save_top_k
- save_last
- checkpoint_by_metric
- checkpoint naming template
- resume_from_checkpoint
- optimizer state restore
- scheduler state restore
- RNG state restore

## Batch/data controls
- batch_size
- micro_batch_size
- gradient_accumulation_steps
- shuffle
- drop_last
- num_workers
- persistent_workers
- pin_memory
- prefetch_factor
- custom sampler
- class-balanced sampler
- group-aware sampler
- curriculum sampler
