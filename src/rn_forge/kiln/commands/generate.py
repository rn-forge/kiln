"""`kiln generate` and `kiln docs-generate`."""

from __future__ import annotations

from pathlib import Path

from rn_forge.cli import CliApp
from rn_forge.commons.fs.documents import DocumentUtils
from rn_forge.commons.generation import ApplyResult
from rn_forge.commons.runtime.console import console

from rn_forge.kiln.commands import output
from rn_forge.kiln.config import CONFIG_PATH
from rn_forge.kiln.modules.core import cycle, umbrella
from rn_forge.kiln.modules.core.config import catalog
from rn_forge.kiln.modules.core.config.manager import ConfigManager
from rn_forge.kiln.modules.core.names import module_name
from rn_forge.kiln.modules.docs import generate as docs_generator
from rn_forge.kiln.modules.docs import scaffold as docs_scaffold
from rn_forge.kiln.modules.python import scaffold as python_scaffold

__all__ = ["add_package", "docs_generate", "generate_app", "generate_package"]


def generate_package(
    name: str,
    path: Path = Path(),
    json: bool = False,
    module: str | None = None,
) -> None:
    """Add the package NAME to the `python-lib` repository at `--path`.

    Writes the package, its docs site, changelog and README, and updates the
    config, the workspace and the managed files that list packages. Everything
    is checked before anything is written. `--module` sets a dotted import
    module (a namespace package such as `rn_forge.cli`) in place of the one
    derived from NAME.

    Raises:
        AppException: The archetype is not `python-lib`
            (`generate.unsupported-archetype`), NAME is not a kebab-case
            distribution name (`generate.invalid-name`), `--module` is not a
            dotted import module (`generate.invalid-module`), NAME is already a
            package or `packages/NAME` exists (`generate.package-exists`),
            or a step or the apply fails.
    """
    output.use_json(json)
    root = umbrella.find_root(path.resolve())
    result = add_package(root, name, module)
    relative = f"packages/{name}"

    written = sorted(
        file.relative_to(root).as_posix()
        for file in (root / relative).rglob("*")
        if file.is_file() and "__pycache__" not in file.parts
    )
    rows = output.change_rows(result.changes)
    output.emit_rows(
        {
            "root": str(root),
            "written": [CONFIG_PATH.as_posix(), "pyproject.toml", *written],
            "artifacts": rows,
        },
        rows,
    )


def add_package(root: Path, name: str, module: str | None) -> ApplyResult:
    """Add the package NAME to the `python-lib` repository at *root*; see `generate_package`."""
    config = ConfigManager().load(root)
    python_scaffold.package_preflight(root, config, name, module)
    # A dry run still refuses on drift, so nothing is written for a repository
    # the closing apply would refuse.
    cycle.apply(root, dry_run=True)
    relative = f"packages/{name}"

    section: dict[str, object] = {"packages": [*config.packages, relative]}
    if module is not None and module != module_name(name):
        section["modules"] = {relative: module}
    DocumentUtils.update(root / CONFIG_PATH, {"archetype": {"python-lib": section}})
    config = ConfigManager().load(root)
    catalog.write(root, config)
    python_scaffold.add_package(root, config, name, config.owner, config.name)
    docs_scaffold.add_package(root, config, name)
    result = cycle.apply(root)
    docs_generator.generate(
        root, config.packages, ci_matrix=config.ci_matrix(every_archetype=True)
    )
    return result


def docs_generate(path: Path) -> None:
    """Regenerate the derived regions of PATH's docs, such as `mkdocs.yml`'s nav.

    `kiln doctor` checks that they are current.
    """
    config = ConfigManager().load(path)
    packages = config.docs_packages
    written, findings = docs_generator.generate(
        path, packages, ci_matrix=config.ci_matrix(every_archetype=True)
    )
    if not written:
        console.info("no change")
    for file in written:
        console.success("updated {}", file)
    output.report_findings(findings, path, "finding(s) in")


generate_app = CliApp("kiln", "Generate parts of a repository.")
"""The `generate` namespace; each generator is a command on it."""
generate_app.command(name="package")(generate_package)
