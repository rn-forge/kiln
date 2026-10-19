# Ideas

Ideas not yet agreed as this repository's work. An entry takes no ID and no
state, and does not authorize starting anything. Promoting one moves its section
into a new epic or feature and deletes its row; a dropped idea's row is deleted
too.

[Back to the specs](index.md)

| Idea | Summary | Source |
| -- | -- | -- |
| node-docs-site-assembly | The Node archetypes build their MkDocs site and assemble Compodoc and Storybook under it, as E13's design describes | ADR-0012, 2026-10-01 |
| java-archetype | A Java archetype on the same docs model, with Javadoc assembled under `api/` | ADR-0012, 2026-10-01 |
| local-sonar-scan | A task verb that runs the workspace coverage tests and scans the checked-out branch with the gate awaited, as pykit's `sonar_local.py` does | F6.3, 2026-10-13 |
| rn-forge-devops-non-python | rn-forge-devops plans non-Python workspaces (Nx, Maven) | [ADR-0016](../adr/ADR-0016.md), 2026-10-18 |
| init-workflow-findings-per-file | `kiln init` and `doctor` report one finding per hand-written workflow beside the generated `ci.yml` ("retire once its jobs are covered"), instead of one `ci.entrypoint` error per line; pykit's adoption trial reported 27 for `main.yml` | pykit adoption trial, 2026-10-18 |
| install-before-tag | `release` installs each package from `git+…@$GITHUB_SHA` in a clean venv and imports it before tagging, in dependency order, and holds back a failure and its dependents; `external-install` then goes away. Today it runs after publishing, so a broken tag is caught but stays published. Worth it once packages have consumers outside the owner's repos, pins move automatically, or a broken tag reaches a consumer | Review of S6.4.7, 2026-10-19 |
