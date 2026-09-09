# Recovering from drift

`task lint` reports:

```text
Taskfile.yml: managed artifact has drifted from the committed state
```

Someone edited a file kiln owns. There are exactly two right answers, and
choosing between them is the judgement this runbook exists for.

## 1. Find out what changed

```bash
git diff -- Taskfile.yml
kiln diff Taskfile.yml
```

`git diff` shows the edit. `kiln diff` shows the edit *against a fresh render*,
which also tells you whether kiln itself would now produce something different.

## 2. Decide

- **The edit was a mistake, or a local hack.** Revert it: `kiln apply` restores
  the rendered bytes. Done.
- **The edit is right and the standard is wrong.** Then the change belongs in
  the golden repo, not here. Open it in `rn-forge/kiln` under
  `tests/fixtures/golden/`, make it there, let the snapshot test fail, and
  update the template until it passes. Then `kiln apply` here.

Never leave the third option — the edit in place, the state stale — in a branch
you intend to merge. CI is checking the committed baseline, not your intent.

## 3. If the drift is config, not content

A `config.toml` edit shows up as drift in every file the option touches. Run
`kiln apply` and review the whole diff at once.
