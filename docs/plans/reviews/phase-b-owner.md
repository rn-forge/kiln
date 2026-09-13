# review

> Kept verbatim. The only change is that the file citations, which pointed at
> absolute paths on the reviewer's machine, are rendered as plain references
> rather than as links — the wording is untouched. What was done about each item
> is in [context §7](../context.md), which carries the plan's §0.6.

my questions/feedback:

## ADRs

- ADR-0001: seems redundant. everything is kiln owned now
- ADR-0002: same as ADR-0001
- ADR-0003: needs better/cleaner explanation. I thought CI will use predefined
  templates provided by another devops repo. config in kiln will drive wrapper
  type (GitHub / ADO), which will have steps call reusable templates/scripts
  in that devops repo. this helps in not cloning in every repo and then manage
  drift
- ADR-0008: sounds more like a spec for kiln and design for it, rather than an
  ADR that will drive future design
- ADR-0009: archetypes should be 'python-lib', 'python-cli', 'python-django-ng',
  'python-fastapi-ng'. and this should get folded into ADR-0006. Also, this
  again sounds more like a spec+design then an ADR

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
