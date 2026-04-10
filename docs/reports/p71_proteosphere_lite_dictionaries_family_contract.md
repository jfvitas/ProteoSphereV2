# P71 ProteoSphere Lite Dictionaries Family Contract

Report-only contract for how `dictionaries` should be explained in the `proteosphere-lite` contents and schema docs.

## Current Posture

`dictionaries` is already a reserved family in the live bundle manifest and schema doc, with `0` records.

That is the right truth boundary for the current preview bundle. It should read as a deliberate omission, not as a broken or incomplete evidence surface.

## Proposed Contents Doc Wording

Use wording like this in `proteosphere-lite.contents.md`:

> `dictionaries`: declared in schema, currently `0` materialized records; reserved for compact lookup and normalization rows that support preview interpretation, not evidence-bearing biology.

This keeps three things clear:

- the family is currently empty
- the family is intentional
- the family is support metadata, not biological evidence

## Proposed Schema Doc Wording

Use wording like this in `proteosphere-lite.schema.md`:

> Reserved family for compact dictionary / lookup rows used to normalize codes, labels, and namespace-specific values in the preview bundle. Keep zero-count until real materialized rows exist. These rows are support metadata, not primary biological evidence.

This wording should also make clear that, if the family is ever populated, it needs explicit provenance and namespace-scoped keys.

## What To Avoid

Do not describe `dictionaries` as:

- a missing evidence family
- a core biological surface
- a completeness gap
- an implicit replacement for provenance-bearing source families

## Operator Read

The cleanest explanation is simple: `dictionaries` are auxiliary lookup and normalization tables. They help the preview bundle read cleanly, but they should never be confused with the bundle’s evidence-bearing data families.

## Truth Boundary

This is a report-only proposal. It does not materialize the family or change the manifest; it only defines the wording that would keep the current preview bundle truthful and easy to read.
