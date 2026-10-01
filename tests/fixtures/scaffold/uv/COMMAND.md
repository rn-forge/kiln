# How this fixture was captured

**Date:** 2026-10-01 · **uv version:** 0.12.21

`.gitignore` here is uv's own Git-enabled ignore body, byte for byte. It was
captured in an empty scratch directory, never in a generated repository:

```bash
uv --version     # uv 0.12.21
uv init --name capture --vcs git --no-readme --bare .
cp .gitignore tests/fixtures/scaffold/uv/.gitignore
```

`--bare` and `--package --build-backend uv` write the same body; `kiln new`
captures it the same way, in a temporary directory, and seeds it once at the
repository root. The generated repository's own `uv init` still runs with
`--vcs none`, so no `.git/` is created there.

A new uv version is a fixture review: re-run the command above and review the
diff of this file. The live test
`test_s5_3_6_1_live_uv_capture_matches_the_fixture` fails until they agree.
