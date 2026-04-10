# P21 Onboarding Friction

Date: 2026-03-22  
Task: `P21-A006`

## Bottom Line

The current operator onboarding path is workable, but it is still too artifact-heavy for a scientist who wants to answer, "What should I trust, what should I inspect, and what should I do next?" without already knowing the repo.

The strongest evidence says the system is truth-preserving, not friction-free:

- the PowerShell-first operator surface is real and coherent
- the benchmark, packet, and user-sim artifacts now preserve weak, blocked, and partial states honestly
- the phase-20 user-sim regression shows one supported workflow, four weak workflows, and one blocked workflow
- but the user-facing docs still force the operator to jump across many reports, JSON files, and status surfaces to reconstruct a decision

That means the onboarding problem is no longer "missing core evidence." It is "too many separate surfaces, too little guided interpretation."

## What Is Already Landed

The following pieces already exist and should be treated as the current baseline, not future work:

- the PowerShell operator surface in [scripts/powershell_interface.ps1](/D:/documents/ProteoSphereV2/scripts/powershell_interface.ps1)
- the operator parity contract in [docs/reports/operator_state_parity.md](/D:/documents/ProteoSphereV2/docs/reports/operator_state_parity.md)
- the operator fallback regression in [docs/reports/operator_fallback_regression.md](/D:/documents/ProteoSphereV2/docs/reports/operator_fallback_regression.md)
- the library materialization regression in [docs/reports/operator_library_materialization_regression.md](/D:/documents/ProteoSphereV2/docs/reports/operator_library_materialization_regression.md)
- the training envelope report in [docs/reports/p19_training_envelopes.md](/D:/documents/ProteoSphereV2/docs/reports/p19_training_envelopes.md)
- the user-sim personas in [docs/reports/p20_simulated_researcher_personas.md](/D:/documents/ProteoSphereV2/docs/reports/p20_simulated_researcher_personas.md)
- the user-sim regression in [docs/reports/p20_user_sim_regression.md](/D:/documents/ProteoSphereV2/docs/reports/p20_user_sim_regression.md)
- the transcript exporter output path in [runs/real_data_benchmark/full_results/user_sim_regression.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/user_sim_regression.json)

These artifacts show that the system can already distinguish:

- supported versus weak versus blocked workflows
- partial packets versus stronger examples
- prototype runtime versus release-grade claims
- PowerShell-first operator state versus a later WinUI path

## High-Friction Points

### 1. Decision-making still requires too many hops

A scientist trying to answer a simple question like "Is this packet useful?" still has to move between:

- [runs/real_data_benchmark/full_results/source_coverage.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/source_coverage.json)
- [runs/real_data_benchmark/full_results/training_packet_audit.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/training_packet_audit.json)
- [runs/real_data_benchmark/full_results/model_portfolio_benchmark.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/model_portfolio_benchmark.json)
- [runs/real_data_benchmark/full_results/user_sim_regression.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/user_sim_regression.json)
- [docs/reports/p19_training_envelopes.md](/D:/documents/ProteoSphereV2/docs/reports/p19_training_envelopes.md)
- [docs/reports/p20_user_sim_regression.md](/D:/documents/ProteoSphereV2/docs/reports/p20_user_sim_regression.md)

That is fine for a maintainer, but too much for a new scientist onboarding into the tool.

### 2. The PowerShell surface is honest, but not yet guided

The current surface in [scripts/powershell_interface.ps1](/D:/documents/ProteoSphereV2/scripts/powershell_interface.ps1) is good at surfacing queue, library, benchmark, and runtime state.

It is still friction-heavy because it is:

- status-oriented rather than workflow-oriented
- split across several command modes
- dependent on remembering which report or JSON file answers which question

The operator can inspect state, but they still have to assemble meaning themselves.

### 3. User-sim outputs are strong, but the acceptance layer is still easy to miss

The phase-20 regression in [docs/reports/p20_user_sim_regression.md](/D:/documents/ProteoSphereV2/docs/reports/p20_user_sim_regression.md) is useful because it names:

- `pass` for `P69905`
- `weak` for `P68871`, `P04637`, `P31749`, and `Q9NZD4`
- `blocked` for the soak path

The acceptance matrix now exists in [docs/reports/p20_acceptance_matrix.md](/D:/documents/ProteoSphereV2/docs/reports/p20_acceptance_matrix.md), which is a real improvement. The remaining friction is that a new operator still has to know that this is the right front-door summary instead of discovering it naturally from the current PowerShell-first flow.

### 4. The release boundary is still easy to misread

Several reports correctly state that the runtime is still prototype-bound, including:

- [docs/reports/p19_training_envelopes.md](/D:/documents/ProteoSphereV2/docs/reports/p19_training_envelopes.md)
- [docs/reports/p22_weeklong_soak.md](/D:/documents/ProteoSphereV2/docs/reports/p22_weeklong_soak.md)
- [docs/reports/p20_user_sim_regression.md](/D:/documents/ProteoSphereV2/docs/reports/p20_user_sim_regression.md)

That is good, but it also means a new operator can easily overread "stable," "useful," or "completed" as if they implied release readiness. The docs need a more obvious truth-signaling layer at the front door.

## Missing Docs And Surfaces

These are the gaps that most directly hurt onboarding:

- a single operator quickstart that says, in plain language, which file to open first for queue, benchmark, packet, and user-sim questions
- a guided evidence drilldown page that maps "where do I inspect this result?" to one canonical artifact path per question
- a packet interpretation guide that explains `useful`, `weak`, `partial`, `blocked`, and `mixed` without requiring the reader to infer meanings from several reports
- a clearer front-door pointer from the operator surface to the acceptance matrix that summarizes the phase-20 user-sim outcomes in one place
- a concise truth-boundary banner in the operator surface that warns when the user is looking at prototype, partial, or blocked evidence
- a scientist-facing walkthrough for dataset design that starts from cohort selection and ends at training packet materialization

## Recommended Follow-On Work

### 1. Add a guided operator entrypoint

Create a short, human-readable operator guide that answers:

- where to inspect current queue and runtime state
- where to inspect source coverage and packet completeness
- where to inspect user-sim and benchmark outcomes
- what "blocked" and "partial" mean in this repo

### 2. Collapse the most common evidence paths

Provide one top-level doc or dashboard view that links the core artifacts together:

- source coverage
- packet audit
- benchmark portfolio
- training envelopes
- user-sim regression

### 3. Make the acceptance matrix the obvious review surface

Now that the acceptance matrix is landed, the next step is to make it the obvious review surface so phase-20 regression does not stop at "we ran scenarios" and instead gives the operator a one-page decision surface without extra artifact hunting.

### 4. Add explicit operator affordances for truth boundaries

The PowerShell surface should surface prototype, partial, and blocked states before the user has to drill into JSON. That would reduce misreads without pretending the system is more complete than it is.

### 5. Write a scientist onboarding path

Document a single recommended path for a new scientist:

1. check the operator surface
2. inspect source coverage
3. inspect packet audit
4. inspect user-sim regression
5. decide whether the result is useful, weak, or blocked

## What This Means Practically

The project is already past the point where onboarding can be solved by more core plumbing alone.

The next biggest win is not another backend lane. It is a clearer front door that tells the operator:

- what is real
- what is partial
- what is blocked
- what is safe to trust
- what still needs more evidence

That is the highest-friction gap left in the current PowerShell-first workflow.
