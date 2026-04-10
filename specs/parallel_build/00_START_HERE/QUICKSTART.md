# Quickstart

Recommended concurrency on your machine:
- planner: 1
- reviewer: 1
- coding workers: 8 to 12
- data-analysis workers: 2 to 4

Start target:
- MAX_CODING_WORKERS=10
- MAX_ANALYSIS_WORKERS=3

Order:
1. locked baseline
2. canonical + execution
3. source acquisition + source analysis
4. storage/index/package system
5. full multimodal expansion

Hard rules:
- one task = one branch
- no direct commits to main
- no redesign before baseline runs
- blocked tasks must report blockers instead of improvising
