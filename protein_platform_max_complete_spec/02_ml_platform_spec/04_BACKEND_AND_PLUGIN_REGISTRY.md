# Backend Registry and Extensibility Requirements

## Required abstraction points
- data connector registry
- feature calculator registry
- model family registry
- optimizer registry
- scheduler registry
- loss registry
- metric registry
- visualizer registry
- export/deployment registry

## Registry rules
Each plugin must declare:
- name
- semantic version
- category
- required dependencies
- supported tasks
- supported input schemas
- supported backends
- parameter schema
- validation function
- execution entrypoint

## No hardcoding rule
Agents may not implement one-off special cases in the GUI or training system for a specific model.
All behavior must route through registries and schemas.

## Parameter registry requirement
For maximum completeness, each backend family must be backed by a parameter registry file, not scattered literals.
