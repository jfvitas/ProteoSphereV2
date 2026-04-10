# Git and Branch Policy

- main is protected
- one task = one branch
- branch name: task/<TASK_ID>-short-name
- no direct commits to main
- CI green required
- reviewer approval required
- workers must not touch overlapping files unless planner explicitly serializes them
