"""`kiln new` with packages: members, the commented form, and failures."""

from __future__ import annotations
import pytest
import subprocess
import sys
import tomllib
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import OutputMode, console
from rn_forge.kiln import checks, commands
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core.config import catalog
from tests.conftest import new_repo, requires
from typing import Any


@pytest.fixture(autouse=True)
def _in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`kiln new` stages beneath the current directory; keep that out of the repo."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _reset_console_mode() -> Any:
    yield
    console.set_mode(OutputMode.PLAIN)


def _lib_layer(tmp_path: Path, body: str) -> str:
    layer = tmp_path / "layer"
    layer.mkdir(exist_ok=True)
    (layer / "config.toml").write_text(body, encoding="utf-8")
    return str(layer)


TWO_PACKAGES = (
    '[archetype.python-lib]\npackages = ["packages/alpha", "packages/beta"]\n'
)


MODULES = '\n[archetype.python-lib.modules]\n"packages/beta" = "rn_forge.beta"\n'


def _new_lib(directory: Path, layer: str, **kwargs: Any) -> None:
    commands.new(
        directory,
        archetype="python-lib",
        docs="mkdocs",
        config=layer,
        owner="rn-forge",
        yes=True,
        **kwargs,
    )


def test_s16_7_10_1_new_with_two_packages_makes_both_members(tmp_path: Path) -> None:
    target = tmp_path / "lib"
    _new_lib(target, _lib_layer(tmp_path, TWO_PACKAGES))

    for name in ("alpha", "beta"):
        member = target / "packages" / name
        assert (member / "pyproject.toml").is_file()
        for seeded in ("mkdocs.yml", "CHANGELOG.md", "README.md"):
            assert (member / seeded).is_file()
        assert (member / "docs").is_dir()
    members = tomllib.loads((target / "pyproject.toml").read_text(encoding="utf-8"))[
        "tool"
    ]["uv"]["workspace"]["members"]
    assert members == ["packages/alpha", "packages/beta"]
    assert KilnConfig.load(target).packages == ("packages/alpha", "packages/beta")


def test_s16_7_10_2_modules_come_from_the_config(tmp_path: Path) -> None:
    target = tmp_path / "lib"
    _new_lib(target, _lib_layer(tmp_path, TWO_PACKAGES + MODULES))

    assert (target / "packages/alpha/src/alpha").is_dir()
    assert (target / "packages/beta/src/rn_forge/beta").is_dir()
    config = tomllib.loads(
        (target / ".rn-forge/kiln/config.toml").read_text(encoding="utf-8")
    )
    assert config["archetype"]["python-lib"]["modules"] == {
        "packages/beta": "rn_forge.beta"
    }


def test_s16_7_10_3_same_result_as_generate_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layer = _lib_layer(tmp_path, TWO_PACKAGES + MODULES)
    listed = tmp_path / "a" / "lib"
    _new_lib(listed, layer)
    stepwise = tmp_path / "b" / "lib"
    stepwise.parent.mkdir()
    monkeypatch.chdir(stepwise.parent)
    commands.new(
        stepwise, archetype="python-lib", docs="mkdocs", owner="rn-forge", yes=True
    )
    commands.generate_package("alpha", path=stepwise)
    commands.generate_package("beta", path=stepwise, module="rn_forge.beta")

    def settled(root: Path) -> dict[str, Any]:
        """The committed config without `[source]` (the layer's location) and the
        default `import_contracts` a layer's table writes out."""
        document = tomllib.loads(
            (root / ".rn-forge/kiln/config.toml").read_text(encoding="utf-8")
        )
        document.pop("source", None)
        document["archetype"]["python-lib"].pop("import_contracts", None)
        return document

    assert settled(listed) == settled(stepwise)
    for name in (
        "pyproject.toml",
        "packages/alpha/pyproject.toml",
        "packages/beta/pyproject.toml",
        "mkdocs.yml",
    ):
        assert (listed / name).read_bytes() == (stepwise / name).read_bytes(), name


def _commented_form(root: Path) -> tuple[str, str]:
    """The committed `config.toml` and what `catalog.render` makes of its parse."""
    written = (root / ".rn-forge/kiln/config.toml").read_text(encoding="utf-8")
    return written, catalog.render(
        KilnConfig.load(root), header=commands._CONFIG_HEADER
    )


def test_s16_9_2_1_generate_package_writes_the_commented_form(
    tmp_path: Path,
) -> None:
    root = tmp_path / "lib"
    commands.new(
        root, archetype="python-lib", docs="mkdocs", owner="rn-forge", yes=True
    )
    commands.generate_package("alpha", path=root)
    commands.generate_package("beta", path=root, module="rn_forge.beta")

    written, rendered = _commented_form(root)
    assert written == rendered


def test_s16_9_2_2_new_with_packages_writes_the_commented_form(
    tmp_path: Path,
) -> None:
    root = tmp_path / "lib"
    _new_lib(root, _lib_layer(tmp_path, TWO_PACKAGES + MODULES))

    written, rendered = _commented_form(root)
    assert written == rendered


@requires("taplo")
@pytest.mark.parametrize("archetype", ["python-app", "python-lib"])
def test_s16_9_2_3_new_output_toml_is_taplo_clean(
    tmp_path: Path, archetype: str
) -> None:
    root = tmp_path / "out"
    if archetype == "python-lib":
        _new_lib(root, _lib_layer(tmp_path, TWO_PACKAGES + MODULES))
    else:
        commands.new(
            root, archetype=archetype, docs="mkdocs", owner="rn-forge", yes=True
        )
    taplo = Path(sys.executable).parent / "taplo"
    files = [
        ".rn-forge/kiln/config.toml",
        "pyproject.toml",
        *sorted(
            str(p.relative_to(root)) for p in root.glob("packages/*/pyproject.toml")
        ),
    ]

    run = subprocess.run(
        [str(taplo), "fmt", "--check", "--diff", *files],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert run.returncode == 0, run.stdout + run.stderr


def test_s16_7_10_4_a_failing_second_package_leaves_no_directory(
    tmp_path: Path,
) -> None:
    layer = _lib_layer(
        tmp_path,
        '[archetype.python-lib]\npackages = ["packages/alpha", "packages/Bad_Name"]\n',
    )
    target = tmp_path / "lib"

    with pytest.raises(AppException, match="generate.invalid-name"):
        _new_lib(target, layer)

    assert not target.exists()
    assert (tmp_path / ".staging" / "lib" / "workspace" / "packages" / "alpha").is_dir()


def test_s16_7_10_5_a_failing_member_step_leaves_no_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = commands.python_add_package
    calls: list[str] = []

    def flaky(*args: Any, **kwargs: Any) -> None:
        calls.append("call")
        if len(calls) == 2:
            raise AppException("boom")
        real(*args, **kwargs)

    monkeypatch.setattr(commands, "python_add_package", flaky)
    target = tmp_path / "lib"

    with pytest.raises(AppException, match="boom"):
        _new_lib(target, _lib_layer(tmp_path, TWO_PACKAGES))

    assert not target.exists()


def test_s16_7_10_6_new_with_no_packages_is_unchanged(tmp_path: Path) -> None:
    bare = tmp_path / "bare"
    commands.new(
        bare, archetype="python-lib", docs="mkdocs", owner="rn-forge", yes=True
    )
    assert not (bare / "packages").exists()

    layer = _lib_layer(
        tmp_path,
        '[archetype.python-lib]\npackages = ["packages/alpha", "packages/alpha"]\n',
    )
    target = tmp_path / "dup"
    with pytest.raises(AppException, match="generate.package-exists"):
        _new_lib(target, layer)
    assert not target.exists()


def test_s16_7_10_7_preview_with_packages_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    layer = _lib_layer(tmp_path, TWO_PACKAGES)
    target = tmp_path / "lib"
    for yes, dry_run in ((False, False), (True, True)):
        commands.new(
            target,
            archetype="python-lib",
            docs="mkdocs",
            config=layer,
            owner="rn-forge",
            yes=yes,
            dry_run=dry_run,
        )
        assert capsys.readouterr().out
        assert not target.exists()
        assert not (tmp_path / ".staging").exists()


def test_s11_2_2_4_new_python_lib_writes_no_member_and_passes_every_check(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "lib"
    new_repo(directory, archetype="python-lib", docs="mkdocs", yes=True)

    assert not list((directory / "packages").glob("*"))
    document = tomllib.loads((directory / "pyproject.toml").read_text(encoding="utf-8"))
    assert document["tool"]["uv"]["workspace"]["members"] == []
    assert not (directory / "docs" / "reference").exists()
    assert checks.run(directory) == []


def test_s16_4_7_6_new_writes_the_commented_form(tmp_path: Path) -> None:
    new_repo(tmp_path / "demo", archetype="python-tool", docs="none", yes=True)

    text = (tmp_path / "demo" / ".rn-forge/kiln/config.toml").read_text(
        encoding="utf-8"
    )
    assert '# One of: "default-branch", "every-run".' in text
