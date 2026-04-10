# Smoke Test Before Long Run

1. Start with:
   - planner: 1
   - coding workers: 2
   - analysis workers: 1
   - reviewer: 1
2. Let it run for 2–3 hours.
3. Confirm:
   - task queue advances
   - no repeated blocker loops
   - CI stays green
   - repo remains coherent
   - memory stays stable
4. Then scale to:
   - coding workers: 10
   - analysis workers: 3
