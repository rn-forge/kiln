# Handing the cutover to an agent

[The cutover runbook](cutover.md) is the procedure: build a reference with
`kiln new`, overlay its files, read one diff. A coding agent does the judgement
parts by following the `adopt` prompt.

A prompt is a procedure for a coding agent. kiln ships no skills (D30), so
`kiln prompt --name adopt` prints the procedure and nothing else. Hand it to the
agent working in the repository, either by asking the agent to run that command
and follow it, or by piping it in:

```bash
kiln prompt --name adopt | claude
```

`kiln prompt` with no name lists the prompts.

What stays the owner's call: the `[kiln] ref`, a branch before kiln's first
release and a `v<version>` tag after (kiln is not added to the repository's
dependencies); every judgement the prompt marks as the owner's; and the verdict
table for what the repository loses.
