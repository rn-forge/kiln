# ADR-0002 — The ownership table is normative

**Status:** accepted

## Context

[ADR-0001](0001-one-owner-per-file-or-block.md) says every file has one owner.
That is only enforceable if the assignment is written down somewhere both a
human and a generator can read, rather than inferred per repo from what a kit
happened to write last.

## Decision

The table below is the ownership assignment. It is normative: kiln's modules
render exactly these artifacts, `kiln doctor` checks exactly these paths, and a
path not in this table is the repository's.

| File / tree | Owner | Kind |
| --- | --- | --- |
| `.rn-forge/kiln/config.toml` | repo (hand-edited input) | input |
| `.rn-forge/kiln/state.json` | kiln | managed; the committed CI baseline; never hashes itself |
| `.rn-forge/kiln/standard.md` | kiln | managed — the rendered canon |
| `.rn-forge/kiln/backups/`, `rendered/` | kiln | gitignored derived data |
| `.rn-forge/agentkit/**` | agentkit | as today |
| `.gitignore` | repo body; `# BEGIN rn-forge kiln` → kiln; `# BEGIN rn-forge agentkit` → agentkit | block |
| `.editorconfig` | kiln | managed |
| `.importlinter` | kiln | managed |
| `Taskfile.yml`, `tasks/workspace.yml`, `tasks/quality.yml`, `tasks/docs.yml`, archetype namespace files | kiln | managed |
| `tasks/self.yml`, and any include declared `ownership = "repository"` | repo | seeded once, never rewritten |
| `scripts/task/check_task_layout.py`, `scripts/ci/check_ci_entrypoint.py` | kiln | managed (config header) |
| `scripts/standards/check_generated.py` | kiln | managed; stdlib-only CI checker |
| `scripts/standards/check_rn_forge_deps.py` | kiln | managed (config header); stdlib-only CI checker |
| `scripts/docs/_common.py`, `check_docs.py`, `gen_nav.py`, `check_structure.py` | kiln (docs profile `mkdocs`) | managed |
| `docs/_areas.yml`, `docs/_structure.md`, `docs/<area>/_structure.md` | kiln | **seeded** — repos extend their areas |
| `docs/index.md`, `docs/<area>/index.md` | kiln | **seeded** — written if absent, never touched again |
| `mkdocs.yml` | repo body; `# BEGIN generated nav` → kiln | block |
| `.github/workflows/ci.yml`, `docs.yml`; `sonar-project.properties` | kiln | managed |
| `CLAUDE.md`, `AGENTS.md` | body seeded by agentkit; `<!-- BEGIN rn-forge kiln -->` → kiln; agentkit's own block → agentkit | block |
| `.claude/**`, `.codex/**`, installed skills | agentkit | as today |
| Repo-specific lints (`check_brand.py`, `check_gate_tags.py`, …) | repo, wired via `[tasks.extra_refs]` | repo |
| `pyproject.toml`, `src/**`, `tests/**` | repo | not kiln's, at any point after the scaffold — but its rn-forge dependencies are constrained by [ADR-0009](0009-archetype-dependency-defaults.md) |

**`_areas.yml` and `_structure.md` are seeded, not managed.** intellibuild needs
a `context` area that agentkit's model does not have, and agentkit ADR-0018
already established that structure rules live in the target repo. kiln seeds the
reference model; `doctor` validates the tree against whatever the repo declares.

## Consequences

- Adding an artifact to kiln means adding a row here first. That is deliberate
  friction: the table is the review surface for scope creep.
- A repo can extend its docs areas without a kiln release.
- Three kinds — managed, block, seeded — are enough to describe every row, which
  is why the engine has exactly three
  ([ADR-0005](0005-the-rn-forge-umbrella.md)).
