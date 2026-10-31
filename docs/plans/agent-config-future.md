# Agent configuration after kiln — parked

**Date:** 2026-09-11 · **Status:** parked, not scheduled

This file holds what was removed from the standardization plan in revision 10
([context](context.md)). None of it is v1 scope. It is kept so the decisions and
the prior art are not re-derived when the work restarts.

Two tools shaped the standardization plan and neither survives it:

- **taskkit** is retired with kiln (D23). It was a task-graph renderer and
  detector; kiln asserts the archetype instead of detecting it, which is what
  made detection dead weight.
- **agentkit** ideated the repo-config model that became kiln's, and is
  **rebuilt from scratch, later, from a blank sheet.** Nothing in this file is
  a commitment to its shape; it is the record of what the current one does and
  what kiln now does instead.

______________________________________________________________________

## 1. What kiln took over

When the plan was written, agentkit owned the instruction files and kiln called
it as a subprocess during `kiln apply`. Revision 10 removes that seam (D58):
kiln seeds `README.md`, `CLAUDE.md` and `AGENTS.md` itself and owns its own
fenced block in each. Apply has no step 6 and kiln has no optional dependency on
a binary that does not exist.

What that leaves genuinely unowned, for whoever rebuilds agent configuration:

| Concern | Was | Now |
| -- | -- | -- |
| `CLAUDE.md` / `AGENTS.md` **body** | agentkit-seeded | kiln-seeded (D57, D58) |
| the repository-standard block inside them | kiln block | unchanged |
| a second, agent-owned block inside them | agentkit block | **unowned** — the fenced-block model (D27) still admits one |
| `.claude/**`, `.codex/**`, installed skills | agentkit | **unowned** |
| `$RNF_HOME`-level (global, cross-repo) agent config | agentkit `global apply` | **unowned** |

The block model is what makes re-entry cheap: a future tool adds its own fence
to files kiln seeded, and no ownership is renegotiated.

## 2. The question that actually needs answering first

**What is global configuration for, once every repo is generated?**

agentkit had two scopes — `$RNF_HOME`-level config applied to the machine, and
project-level config applied to a repo — and the project scope existed largely
because nothing else owned repo files. kiln owns them now. So the project scope
of a rebuilt agent tool is no longer "install config into a repo"; it is at most
"contribute one block to files kiln seeds, and one directory kiln does not
touch".

That reframing has to be settled before any code, because it decides whether the
rebuilt tool is a repo-touching generator at all, or purely a machine-level tool
with a small repo-block adapter. Do not answer it by porting the old shape.

Related, and also open: whether machine-level configuration belongs in a
*separate* tool from repo generation at all, given that kiln already has
`$RNF_HOME` (it is a `python-tool`; see the tool lifecycle surface, D59).

## 3. Prior art worth reading before restarting

In `rn-forge/agentkit` on `feature/v0.6.0`:

| Path | What it is |
| -- | -- |
| `core/doctor.py` | the three-axis result model — `status` (what is true), `severity` (what it costs), `kind` (what was checked). Good; commons `Finding` is the thinner descendant |
| `core/operations/{apply,capture,init,remove}.py` | the apply loop kiln's `generation` engine replaced |
| `commands/self_command.py` | install / upgrade / cleanup / uninstall against `$RNF_HOME/<product>/versions/<v>` with a `current` symlink — the prior art for the tool lifecycle surface (D59) |
| `agents/{claude,codex}/adapter.py`, `agents/registry.py` | the per-agent adapter seam; the closest thing to a design that should survive |
| `docs/adr/0001`–`0021` | the decisions. ADR-0021 (ownership) was promoted into kiln ADR-0003; ADR-0018 (areas read from the repo) into D44; ADR-0014 (mdformat config is repository-owned) into the golden repos |
| `docs/architecture/lifecycle.md` | why managing *installs* is split from managing *config* |

Carried into kiln already, and **not** to be re-carried: the E17 docs area
model, `docs/_areas.yml` / `_structure.md`, the behaviour of `scripts/docs/**`,
`check_task_layout.py`, `check_ci_entrypoint.py`, the `Taskfile.yml` +
`tasks/**` verb layout, and the generic skills `gh-fix`, `python-simplify`,
`sonar-cleanup`.

Deliberately not carried, then or now: `core/**` (superseded by
`rn-forge-tooling`), the four setup skills and their assets, `feedback.md`,
`scripts/**` as committed files, and the skill entry-point distribution
mechanism.

## 4. taskkit — the retirement record

Retired (D23), archived rather than deleted: README banner pointing at kiln, tag
`archived/v0.2.0`, GitHub repo archived. What kiln took:

- `core/validator.py` rules and tests → kiln's `doctor/taskgraph.py` (doctor
  check 5).
- `tests/fixtures/repos/{python-pnpm-monorepo,python-django,python-fastapi*,python-angular-pnpm}`
  → kiln's scaffold-reconcile inputs for the web archetypes (Phase E).
- the `extra_refs` / repository-owned include model → kiln's `[tasks]` config.
- the `Envelope` `--json` shape → `rn-forge-cli`'s standard options.

Not taken: discovery, the planner, the adapters, the install layer. Detection is
what the archetype assertion replaced.

## 5. When this unparks

Not before kiln is self-hosting (Phase D) and the repos are rebuilt (Phase F).
At that point the inputs are: this file, §2 above as the first question, and the
adapter seam in §3 as the only piece of the old design presumed still good.
