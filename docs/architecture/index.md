# Architecture

- [The rn-forge workspace](workspace.md) — components, ownership, the two
  dependency graphs, and the apply sequence.
- [CI](ci.md) — the generated CI of every archetype: the model, each pipeline,
  the checks and their switches, the hooks, and how a `python-lib` run flows.
- [Tasks](tasks.md) — the generated task surface of every archetype: the files
  and namespaces, the developer and CI surfaces, the gate, how a repository
  extends it, and what `task-layout` checks.
- [Formatting](formatting.md) — the formatter that owns each file type in every
  archetype, the quality tasks, the file list, the ignore files, and how
  kiln's own files are proven clean.
