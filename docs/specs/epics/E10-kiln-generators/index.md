# E10 — kiln generators

**Status:** deferred — backlog, to be elaborated after release-1

**Entry criteria:** release-1 has shipped and the owner picks this up for
elaboration.

## Scope, as known today

- **`kiln generate package <name>` for the application archetypes** — adding an
  internal package to a `python-app` or `python-tool` workspace. D56 put the
  whole command in Phase D, and this epic deferred it until after release-1.
  On 2026-09-26 its `python-lib` half moved back into release-1 as
  [F11.3](../E11-package-docs/F11.3-generate-package.md), because a
  `python-lib` repository now starts with no packages
  ([ADR-0008](../../../adr/ADR-0008.md)). What stays here is the internal
  package: no docs site, no `[project.urls]`, and no remote needed.
- **Framework code generators** — `kiln generate django app billing` and the
  like. The generators themselves ship as `[codegen]` extras of their runtime
  package, in a subpackage the runtime surface never imports, registered under
  `rn_forge.kiln.generators`; kiln supplies only the command surface (D2,
  D37).

The boundary for these generators is: kiln generates repo structure, frameworks
generate their own code, and kiln generates nothing inside `src/` or `tests/`
itself.

Risk carried into this epic, and its guard: the codegen extra leaking into the
runtime surface — pykit's import-linter contract exists before the first codegen
module, and `import rn_forge.django` with no extras is a checklist item.
