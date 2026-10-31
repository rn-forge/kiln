# Adding a package

A `python-lib` repository starts with no packages, and each one is added with
`kiln generate package`. The command writes the package's published URLs, so it
needs this repository's GitHub remote.

## 1. Set `origin`

```bash
git remote get-url origin
git remote add origin https://github.com/<owner>/<repo>
```

Both `https://github.com/<owner>/<repo>[.git]` and
`git@github.com:<owner>/<repo>[.git]` work. With no `origin`, or one that is not
on GitHub, the command stops with `generate.no-remote` before it writes
anything.

## 2. Generate the package

```bash
kiln generate package <name>
```

`<name>` is a kebab-case distribution name that is not already a package. The
command adds the package to `.rn-forge/kiln/config.toml` and to the root
workspace, runs `uv init` for it, seeds its site and `CHANGELOG.md`, then
applies and regenerates the nav so the root site includes it.

## 3. Fill the package's guides

Replace the seeded text in `packages/<name>/docs/guides/usage.md` and
`packages/<name>/README.md`, and add one kebab-case page per guide under
`packages/<name>/docs/guides/`. Run `task docs:generate` after adding a page.

## 4. Check it

```bash
uv sync
task validate
```
