# Adopting an existing repo

`kiln init` does the mechanical part of bringing a repository under kiln. A
coding agent does the rest by following the `adopt` prompt. This runbook covers
how to hand the prompt over, and the points where the decision is yours.

## 1. Choose the route

Adopt in place when the repository already has the archetype's shape, and
rebuild with `kiln new` when it does not. The prompt's section 1 draws the line.

## 2. Hand the prompt to an agent

A prompt is a procedure for a coding agent. kiln ships no skills (D30), so
`kiln prompt --name adopt` prints the procedure and nothing else. Hand it to the
agent working in the repository, either by asking the agent to run that command
and follow it, or by piping it in:

```bash
kiln prompt --name adopt | claude
```

`kiln prompt` with no name lists the prompts.

## 3. Decide what the agent must ask about

- The `[kiln] ref` that `init` wrote: a branch before kiln's first release, a
  `v<version>` tag after. kiln is not added to the repository's dependencies.
- Every judgement the prompt marks as the owner's.

## 4. Commit in three steps

1. `init`'s change, on its own.
1. The `task format` commit: `init` formats nothing.
1. The reconciliation the prompt walks through.

## 5. Done when

`task validate` and `kiln doctor . --full` exit 0.
