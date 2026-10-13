"""S4.9.3 — the `frontend` module's seeded Angular starter."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest import mock

import pytest
from rn_forge.tooling.generation import ArtifactKind

from rn_forge.kiln import commands
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.frontend import FRONTEND
from rn_forge.kiln.modules.frontend.angular import NGKIT_URL, scaffold_angular
from rn_forge.kiln.modules.frontend.scaffold import reconcile_frontend
from rn_forge.kiln.modules.python.scaffold import scaffold

FIXTURE = Path(__file__).parents[2] / "fixtures" / "scaffold" / "nx-angular"

WEB_CONFIG = """
schema_version = 1

[repository]
name = "demo"
archetype = "{archetype}"

[archetype."{archetype}"]
backend = "fastapi"
{extra}
"""


def _config(root: Path, *, archetype: str = "python-web-app", extra: str) -> KilnConfig:
    path = root / ".rn-forge" / "kiln" / "config.toml"
    path.parent.mkdir(parents=True)
    path.write_text(
        WEB_CONFIG.format(archetype=archetype, extra=extra), encoding="utf-8"
    )
    return KilnConfig.load(root)


def _stock(root: Path, web_dir: str, *, ngkit: bool = True) -> None:
    dependencies = {"@rn-forge/ng": NGKIT_URL} if ngkit else {}
    (root / "package.json").write_text(
        json.dumps({"dependencies": dependencies}), encoding="utf-8"
    )
    app = root / web_dir / "src" / "app"
    app.mkdir(parents=True)
    (app / "app.config.ts").write_text("// stock\n", encoding="utf-8")


def _paths(web_dir: str) -> set[str]:
    return {
        f"{web_dir}/src/app/app.config.ts",
        f"{web_dir}/src/app/app.config.spec.ts",
    }


def test_s4_9_3_1_angular_starter_artifacts(tmp_path: Path) -> None:
    config = _config(tmp_path, extra='frontend = "angular"')
    _stock(tmp_path, "apps/web")
    artifacts = FRONTEND.artifacts(config, tmp_path)
    assert {a.path for a in artifacts} == _paths("apps/web")
    assert all(a.kind is ArtifactKind.SEEDED for a in artifacts)
    assert all("{{" not in a.content for a in artifacts)
    by_path = {a.path: a.content for a in artifacts}
    assert "appName: 'demo'" in by_path["apps/web/src/app/app.config.ts"]
    assert "LocalStorageService" in by_path["apps/web/src/app/app.config.spec.ts"]


def test_s4_9_3_1_web_dir_moves_the_paths(tmp_path: Path) -> None:
    config = _config(tmp_path, extra='frontend = "angular"\nweb_dir = "services/web"')
    _stock(tmp_path, "services/web")
    assert {a.path for a in FRONTEND.artifacts(config, tmp_path)} == _paths(
        "services/web"
    )


def test_s4_9_3_1_no_stock_config_gives_nothing(tmp_path: Path) -> None:
    config = _config(tmp_path, extra='frontend = "angular"')
    assert FRONTEND.artifacts(config, tmp_path) == ()


def test_s4_9_3_1_no_ngkit_dependency_gives_nothing(tmp_path: Path) -> None:
    config = _config(tmp_path, extra='frontend = "angular"')
    _stock(tmp_path, "apps/web", ngkit=False)
    assert FRONTEND.artifacts(config, tmp_path) == ()
    (tmp_path / "package.json").unlink()
    assert FRONTEND.artifacts(config, tmp_path) == ()
    (tmp_path / "package.json").write_text("{not json", encoding="utf-8")
    assert FRONTEND.artifacts(config, tmp_path) == ()


def test_s4_9_3_1_other_archetype_or_frontend_gives_nothing(tmp_path: Path) -> None:
    api = _config(tmp_path / "api", archetype="python-web-api", extra="")
    _stock(tmp_path / "api", "apps/web")
    assert FRONTEND.artifacts(api, tmp_path / "api") == ()
    react = _config(tmp_path / "react", extra='frontend = "react"')
    _stock(tmp_path / "react", "apps/web")
    assert FRONTEND.artifacts(react, tmp_path / "react") == ()


@pytest.mark.parametrize("web_dir", ["apps/web", "services/web"])
def test_s4_9_3_2_reconcile_replaces_the_stock_config(
    tmp_path: Path, web_dir: str
) -> None:
    config = _config(
        tmp_path / "root",
        extra=f'frontend = "angular"\nweb_dir = "{web_dir}"',
    )
    root = tmp_path / "root"
    scaffold(root, config)
    workspace = tmp_path / "workspace"
    shutil.copytree(FIXTURE, workspace)
    # The captured Nx workspace predates `pnpm add`, which scaffold_angular runs.
    manifest = workspace / "package.json"
    package = json.loads(manifest.read_text(encoding="utf-8"))
    package["dependencies"]["@rn-forge/ng"] = NGKIT_URL
    manifest.write_text(json.dumps(package), encoding="utf-8")

    reconcile_frontend(root, workspace, config)

    app = root / web_dir / "src" / "app"
    assert "provideRnForgeCoreConfig" in (app / "app.config.ts").read_text(
        encoding="utf-8"
    )
    assert (app / "app.config.spec.ts").is_file()


def test_s4_9_3_3_scaffold_adds_the_ngkit_dependency(tmp_path: Path) -> None:
    calls: list[tuple[str, tuple[str, ...], object]] = []

    def run(name: str, *args: str, **kwargs: object) -> None:
        calls.append((name, args, kwargs.get("cwd")))

    with mock.patch(
        "rn_forge.kiln.modules.frontend.angular.Process.execute", side_effect=run
    ):
        workspace = scaffold_angular(tmp_path)

    names = [name for name, _, _ in calls]
    assert names.count("ngkit-core") == 1
    assert names.index("nx-angular-app") < names.index("ngkit-core")
    assert names.index("ngkit-core") < names.index("nx-install")
    _, args, cwd = calls[names.index("ngkit-core")]
    assert args == ("pnpm", "add", NGKIT_URL)
    assert cwd == str(workspace)


@pytest.mark.skipif(shutil.which("pnpm") is None, reason="pnpm is not on PATH")
def test_s4_9_3_4_new_records_seeded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / "demo"
    commands.new(
        directory,
        archetype="python-web-app",
        docs="none",
        backend="fastapi",
        frontend="angular",
        yes=True,
    )
    entries = json.loads(
        (directory / ".rn-forge" / "kiln" / "state.json").read_text(encoding="utf-8")
    )["entries"]
    for path in _paths("apps/web"):
        assert entries[path]["kind"] == "seeded"
