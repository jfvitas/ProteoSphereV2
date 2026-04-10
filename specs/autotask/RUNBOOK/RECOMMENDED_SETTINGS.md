# Recommended Settings

For your hardware:
- MAX_CODING_WORKERS=10
- MAX_ANALYSIS_WORKERS=3
- MAX_GPU_TRAINING_WORKERS=1
- ORCH_POLL_SECONDS=20
- REVIEW_POLL_SECONDS=180
- TASK_REPLENISH_THRESHOLD=12
- TASK_BATCH_GENERATION_SIZE=25

Reasoning levels:
- planner: high
- reviewer: high
- coding workers: medium
- analysis workers: high
- deep blocker escalation: xhigh
