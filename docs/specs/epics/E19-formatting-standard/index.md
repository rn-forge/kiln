# E19 — One formatter for each file type, in every archetype

|  |  |
| -- | -- |
| **State** | New |

<!-- BEGIN derived features -->

| Feature | State | Iteration | Stories |
| -- | -- | -- | -- |
| [F19.1 — YAML has a formatter, and kiln's own files pass it](F19.1-yaml-formatter.md) | New | release-1 | 4 New |

<!-- END derived features -->

Decision: [ADR-0021](../../../adr/ADR-0021.md). What is built is in
[the formatting architecture](../../../architecture/formatting.md), the
counterpart of [the task architecture](../../../architecture/tasks.md).

Markdown (mdformat) and TOML (taplo) are formatted and checked in every
archetype, through the `quality:` tasks. YAML is not. The Node archetypes format
YAML with Prettier and ignore the files kiln owns; the Python archetypes format
none. So the YAML that kiln generates and that every repository reads most often
(the workflows, `Taskfile.yml`, `tasks/*.yml`, `mkdocs.yml`) is never checked
for form. This epic gives YAML one uv-installed formatter in every archetype,
runs it over kiln's own output, and fixes the templates until a fresh render of
every archetype is clean for Markdown, TOML and YAML.

**Scope.** Release 1 (owner, 2026-11-10). It lands before the pykit and ngkit
cutovers, so they take formatter-clean YAML from the reference.

**Not in this epic.** JSON, which stays with Prettier in the Node archetypes and
has no formatter in the Python ones ([ADR-0021](../../../adr/ADR-0021.md)).
Adopting the new task in pykit and ngkit: each repository gets it by its own
cutover or `kiln apply` and writes its own story; none is written here.

**Precedent.**
[F16.9](../E16-init-adopts-by-overwrite/F16.9-overlay-cutover-findings.md) found
that `kiln new` wrote a `config.toml` taplo rejected, and fixed it with a test.
E19 does that for every rendered file and every formatted type.
