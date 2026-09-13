# ADR-0007 — The task vocabulary is closed, and the gate cannot shrink

**Status:** accepted

## Context

`task` is the single entrypoint, but "single entrypoint" is worth nothing if the
verbs differ per repo. apollo's vocabulary had `format-check`, `dev` and `docs`;
another kit's had `test:coverage`, `docs:build` and no `dev`. An agent that must
read a Taskfile before it can run the gate does not have a vocabulary, it has a
lookup table.

Both repos had also, independently, arrived at the same structural rule — the
root file holds wrappers, the namespaces shell out — and neither could state its
verb list without reading its own file. apollo's generated
`docs/guides/task-vocabulary.md` is the closest thing the fleet had to a written
vocabulary, and it is prose describing whatever the tool emitted.

### Alternatives considered

- **A per-repo vocabulary, documented.** apollo's answer. Documentation of a
  variable is not a vocabulary.
- **An open vocabulary with a required core.** Repos add verbs freely as long as
  the core exists. The core then stops being where work happens, and an agent
  is back to reading the file.
- **Let `validate` be whatever a repo composes.** This is precisely how apollo
  lost five lint gates in one `adopt` run without anything failing.

## Decision

**The vocabulary is closed**: ten root verbs, plus four public `docs:*` verbs
under the `mkdocs` profile, and nothing else. Every other task is
`internal: true`. The list itself is in
[the standard-repo reference](../reference/standard-repo.md#1-one-entrypoint),
because it is a specification and it changes when an archetype does.

**The root `Taskfile.yml` holds wrappers only**: every one of its `cmds:`
entries is a `task:` call into a namespace file. Anything that shells out lives
in the namespace that owns it. Every task, everywhere, carries a non-empty
`desc:`, so `task --list` is the vocabulary's own documentation.

**The gate cannot shrink.** The generated `scripts/task/check_task_layout.py`
carries the archetype's `required_validate` list in its config header and fails
if any of those tasks stops being reachable from `validate`. `kiln doctor`
checks the same list as `gate.shrunk`.

**Repo-specific work attaches through config** — `[tasks.includes]` for a
repository-owned namespace file, `[tasks.extra_refs]` to append a call to a
managed wrapper, `[tasks.command_overrides]` to replace one primitive's shell
line — never by editing a managed file.

## Consequences

- An agent can run any rn-forge repo's gate without reading its Taskfile.
- A repo that needs a fifteenth verb needs a config key or an ADR of its own,
  which is the friction that keeps the list closed.
- `dev` is deliberately absent from the root list: it means something different
  in every archetype, and belongs to the namespace that owns the server.
- Wanting a third `command_overrides` entry is a strong signal the archetype is
  wrong. The config makes that visible instead of absorbing it.
