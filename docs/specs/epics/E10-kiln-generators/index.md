# E10 — kiln generators

**Status:** deferred — backlog, to be elaborated after release-1

**Entry criteria:** release-1 has shipped and the owner picks this up for
elaboration.

## Scope, as known today

- **`kiln generate package <name>`** — add a package to a workspace. It emits
  repo structure kiln already owns (D56), so it is kiln's to build.
  **Rescheduled:** D56 put this in Phase D, which is now E4 and release-1. The
  move to the spec tree deferred it to this backlog epic, because release-1
  ships no `generate` command surface for it to hang on. The scope did not
  change; only the timing did.
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
