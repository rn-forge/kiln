# ADR-0008 — The task vocabulary

**Status:** accepted

## Context

`task` is the single entrypoint, but "single entrypoint" is worth nothing if the
verbs differ per repo. apollo's vocabulary had `format-check`, `dev` and `docs`;
agentkit's had `test:coverage`, `docs:build` and no `dev`. An agent that has to
read a Taskfile before it can run the gate does not have a vocabulary, it has a
lookup table.

Both repos had also, independently, arrived at the same structural rule — the
root file holds wrappers, the namespaces shell out — and neither could state the
verb list without reading its own file. apollo's `docs/guides/task-vocabulary.md`
is the closest thing to a written vocabulary in the fleet, and it is generated
prose describing whatever the tool emitted.

## Decision

**Ten root verbs, fixed:**

```text
setup  validate  lint  format  typecheck  test  test:coverage  build  clean  version
```

Plus four public docs verbs, and only under `docs.profile = mkdocs`:

```text
docs:build  docs:serve  docs:nav  docs:structure
```

**Every other task is `internal: true`.** `docs:*` is public because
`task docs:serve` is something a developer runs directly while writing prose; a
namespace whose public name is already correct is reached through the include
and carries no root wrapper.

`validate` calls `lint`, `typecheck`, `test`, and — only for the `mkdocs`
profile — `docs:build`.

**The root `Taskfile.yml` holds wrappers only**: every one of its `cmds:` entries
is a `task:` call into a namespace file. Anything that shells out lives in the
namespace that owns it. Every task, everywhere, carries a non-empty `desc:`, so
`task --list` is the vocabulary's own documentation.

**The gate cannot shrink.** The generated `scripts/task/check_task_layout.py`
carries the archetype's `required_validate` list in its config header and fails
if any of those tasks stops being reachable from `validate`. `kiln doctor`
checks the same list as `gate.shrunk`.

Repo-specific work attaches through config — `[tasks.includes]` for a
repository-owned namespace file, `[tasks.extra_refs]` to append a call to a
managed wrapper, `[tasks.command_overrides]` to replace one primitive's shell
line — never by editing a managed file.

## Consequences

- An agent can run any rn-forge repo's gate without reading its Taskfile.
- A repo that needs a fifteenth verb needs a config key or an ADR of its own,
  which is the friction that keeps the list at ten.
- `dev` is deliberately absent from the root list: it means something different
  in every archetype, and it belongs to the namespace that owns the server.
