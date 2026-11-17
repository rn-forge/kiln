"""`uv init` for a new repository: the raw output kiln reconciles afterwards.

This is the only subprocess kiln starts. It never templates what `uv init`
writes; the reconcile only fixes the `pyproject.toml` sections the checks verify.
"""

from __future__ import annotations

import shutil
import tempfile
from functools import cache
from pathlib import Path

from rn_forge.kiln.modules.core import gitignore
from rn_forge.kiln.modules.core.names import module_name
from rn_forge.kiln.modules.core.process import run

__all__ = ["SAMPLE_TEST", "sample_test", "uv_gitignore", "uv_init", "write_sample_test"]

SAMPLE_TEST = Path("tests") / "test_package.py"
"""The sample test `scaffold_backend` writes into each package `uv init` creates."""


def sample_test(name: str, module: str | None = None) -> str:
    """The body of `SAMPLE_TEST` for the package *name* (dashes allowed).

    *module* is the dotted import module; it defaults to *name* with dashes
    as underscores.

    A new package has no tests, and pytest exits 5 on an empty suite, so
    without this a fresh repository's `task validate` fails.
    """
    module = module or module_name(name)
    return (
        f"import {module}\n\n\n"
        "def test_package_imports():\n"
        f"    assert {module}.__spec__ is not None\n"
    )


def write_sample_test(package: Path, name: str, module: str | None = None) -> None:
    path = package / SAMPLE_TEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sample_test(name, module), encoding="utf-8")


@cache
def uv_gitignore() -> str:
    """The `.gitignore` body uv writes into a new Git repository.

    Captured in a temporary directory, once per process: the target itself
    never gets a `.git/`.

    Raises:
        AppException: `uv` is not on `PATH`, or exits non-zero.
    """
    with tempfile.TemporaryDirectory(prefix="kiln-uv-") as scratch:
        run(
            "uv-init[gitignore]",
            "uv",
            "init",
            "--name",
            "capture",
            "--vcs",
            "git",
            "--no-readme",
            "--bare",
            cwd=Path(scratch),
        )
        return (Path(scratch) / gitignore.GITIGNORE).read_text(encoding="utf-8")


def uv_init(
    target: Path,
    *,
    name: str,
    bare: bool,
    member: bool = False,
    lib: bool = False,
    module: str | None = None,
) -> None:
    args = ["uv", "init", "--name", name, "--vcs", "none", "--no-readme"]
    if bare:
        args += ["--bare", "--pin-python"]
    else:
        args += ["--lib" if lib else "--package", "--build-backend", "uv"]
    # A root must not join a uv project above `.staging/`; a member joins its
    # root, and its Python pin comes from the root's `.python-version`.
    args += ["--no-pin-python"] if member else ["--no-workspace"]
    run(f"uv-init[{name}]", *args, cwd=target)
    if not bare:
        derived = target / "src" / module_name(name)
        package_dir = target / "src" / (module or derived.name).replace(".", "/")
        if package_dir != derived:
            package_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(derived, package_dir)
        if not lib:
            # `uv init --package` writes a `main()` stub the starter's
            # `main:app` console script never uses.
            (package_dir / "__init__.py").write_text("", encoding="utf-8")
        typed = package_dir / "py.typed"
        if not typed.exists():
            typed.touch()
