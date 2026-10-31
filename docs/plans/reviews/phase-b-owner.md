# review

**Historical record:** proposals and numbered decisions below describe the
review at that time, not current policy. ADR references use current
destinations; retired references use topic names. Current scope and decisions
are in [the spec board](../../specs/index.md) and
[the decision log](../../adr/index.md).

> File citations use plain references in place of machine-local paths, and
> retired ADR numbers use topic names. What was done about each item is in
> [context §7](../context.md), which carries the plan's §0.6.

my questions/feedback:

## ADRs

- ownership policy: seems redundant. everything is kiln owned now
- dependency boundary: same as ownership policy
- CI policy: needs better/cleaner explanation. I thought CI will use predefined
  templates provided by another devops repo. config in kiln will drive wrapper
  type (GitHub / ADO), which will have steps call reusable templates/scripts
  in that devops repo. this helps in not cloning in every repo and then manage
  drift
- Repository-standard proposal: sounds more like a spec for kiln and design for
  it, rather than an ADR that will drive future design
- Dependency-defaults proposal: archetypes should be 'python-lib', 'python-cli',
  'python-django-ng', 'python-fastapi-ng'. and this should get folded into the
  archetype proposal. Also, this again sounds more like a spec+design then an
  ADR

## python-lib

- pyproject.toml: review it against pytkit and agentkit for tool configuration
  (pyright, mypy, ruff, pytest etc.)
- AGENTS.md: It should be static text referring to CLAUDE.md (see agentkit).
  This helps prevent drift by keeping only updatable file
- Taskfile.yml: format only calls python format. do we also need a docs
  formatting task using mdformat ? see format:markdown in
  '/Users/rohitnarayanan/Devel/workspaces/rn-forge/agentkit/tasks/quality.yml'
- is there mre standard boilerplate that should be part of the init template ?
  logging config etc.

## python-cli

- same comments as python-lib
- here I feel that there is standard boilerplate around cli config, arg parsing,
  error handling etc. if tooling will provide these, we could still further
  simplify by adding a config.toml layer to automater the entire typer setup
