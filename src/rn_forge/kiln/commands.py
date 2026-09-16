"""The commands kiln's CLI exposes.

A command function is all that is written here. `CliApp.from_config` builds
the application around it — the root callback, the standard
`--log-level`/`--json` flags, the error-to-exit-code mapping — from the
declaration in `cli.toml`.

Nothing here imports Typer: a parameter without a default is a positional
argument, one with a default is an option. Failure is an `AppException`,
which `CliApp` maps to exit code 1.
"""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import console

from rn_forge.kiln import checks
from rn_forge.kiln.modules.docs.nav import update_nav


def doctor(path: Path, only: str | None = None) -> None:
    """Run the render-free checks over PATH's committed files.

    Prints each finding and raises `AppException` if any is an error.
    """
    findings = checks.run(path.resolve(), only)

    for finding in findings:
        console.error("{}", finding)

    errors = [finding for finding in findings if finding.is_error]
    if errors:
        raise AppException("{} check(s) failed in {}", len(errors), path)


def docs_nav(path: Path) -> None:
    """Regenerate the nav block in PATH's `mkdocs.yml` from its docs tree.

    `kiln doctor --only docs-nav` is the check that the block is current.
    """
    mkdocs_path = path / "mkdocs.yml"
    updated, changed = update_nav(mkdocs_path, path / "docs")
    if not changed:
        console.info("no change")
        return
    mkdocs_path.write_text(updated, encoding="utf-8")
    console.success("updated {}", mkdocs_path)
