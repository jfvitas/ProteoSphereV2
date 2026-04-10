# ML Platform Spec Overview

This section defines the complete ML platform surface area:
- supported model families
- backend frameworks
- global training controls
- architecture-builder controls
- hybrid and ensemble patterns
- uncertainty and multitask options
- GUI exposure rules
- parameter registries and extensibility requirements

The UI must not simply be a flat form. It must be schema-driven and dependency-aware.

## Core principle
Every exposed option must belong to one of these classes:
1. global run option
2. model-family option
3. backend-specific option
4. data-dependent option
5. experimental/advanced option

Every option must include:
- internal key
- user-facing label
- data type
- default
- allowed values/range
- whether searchable by AutoML
- whether safe to expose in basic mode
- dependency conditions
- serialization path
