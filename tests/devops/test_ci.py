"""Tests for the CI core: graph ordering and release gating."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from rn_forge.kiln.devops import (
    Package,
    Service,
    Smoke,
    normalize,
    plan,
    release_order,
    releasable,
)
from rn_forge.kiln.devops.ci import Workspace, changed_files, select


def _packages() -> dict[str, Package]:
    return {
        "base": Package("base", "packages/base", "base"),
        "app": Package(
            "app", "packages/app", "app", requires={"base"}, release_requires={"base"}
        ),
    }


def _group_cycle() -> dict[str, Package]:
    return {
        "auth": Package(
            "auth", "auth", "auth", requires={"web"}, release_requires={"web"}
        ),
        "web": Package("web", "web", "web", requires={"auth"}),
    }


def test_s6_7_2_normalize_collapses_separators() -> None:
    assert normalize("Rn_Forge.Devops") == "rn-forge-devops"


def test_s6_7_2_release_order_puts_requirements_first() -> None:
    assert release_order(_packages(), {"app", "base"}) == ["base", "app"]


def test_s6_7_2_missing_marker_blocks_package_and_dependents(tmp_path: Path) -> None:
    ok, blocked = releasable(_packages(), tmp_path, ["app", "base"])
    assert (ok, blocked) == ([], ["base", "app"])


def test_s6_7_2_passed_markers_release_in_order(tmp_path: Path) -> None:
    for name in ("base", "app"):
        for check in Package(name, name, name).checks():
            (tmp_path / check["marker"]).touch()
    assert releasable(_packages(), tmp_path, ["app", "base"]) == (
        ["base", "app"],
        [],
    )


def test_s6_7_2_plan_lists_smoke_checks_per_extra(tmp_path: Path) -> None:
    packages = _packages()
    packages["app"].smoke = Smoke(modules=["app"], extras={"x": ["app.x"]})
    workspace = Workspace(root=tmp_path, packages=packages)
    outputs = plan(workspace, "")
    assert outputs["release-order"] == ["base", "app"]
    assert outputs["smoke"] == [
        {"name": "base", "extra": "", "marker": "base.smoke"},
        {"name": "app", "extra": "", "marker": "app.smoke"},
        {"name": "app", "extra": "x", "marker": "app.smoke-x"},
    ]


def test_s6_7_2_plan_lists_one_empty_extra_smoke_entry_without_a_declaration(
    tmp_path: Path,
) -> None:
    outputs = plan(Workspace(root=tmp_path, packages=_packages()), "")
    assert outputs["smoke"] == [
        {"name": "base", "extra": "", "marker": "base.smoke"},
        {"name": "app", "extra": "", "marker": "app.smoke"},
    ]


def test_s6_7_2_plan_omits_smoke_entries_of_unselected_packages(tmp_path: Path) -> None:
    outputs = plan(_git_workspace(tmp_path), "v1")
    assert outputs["smoke"] == [{"name": "a", "extra": "", "marker": "a.smoke"}]


def test_s6_8_1_1_release_order_ignores_a_cycle_through_a_dependency_group() -> None:
    assert release_order(_group_cycle(), {"auth", "web"}) == ["web", "auth"]


def test_s6_8_1_2_release_order_raises_on_a_runtime_cycle() -> None:
    packages = {
        "a": Package("a", "a", "a", release_requires={"b"}),
        "b": Package("b", "b", "b", release_requires={"a"}),
    }
    with pytest.raises(ValueError, match=r"cycle among \['a', 'b'\]"):
        release_order(packages, {"a", "b"})


def test_s6_8_1_3_plan_orders_a_group_only_cycle(tmp_path: Path) -> None:
    workspace = Workspace(root=tmp_path, packages=_group_cycle())
    assert plan(workspace, "")["release-order"] == ["web", "auth"]


def test_s6_8_1_4_releasable_gates_on_release_requires_only(tmp_path: Path) -> None:
    packages = _group_cycle()
    for check in packages["auth"].checks():
        (tmp_path / check["marker"]).touch()
    assert releasable(packages, tmp_path, ["auth", "web"]) == ([], ["web", "auth"])
    for check in packages["web"].checks():
        (tmp_path / check["marker"]).touch()
    assert releasable(packages, tmp_path, ["auth", "web"]) == (["web", "auth"], [])
    (tmp_path / packages["auth"].checks()[0]["marker"]).unlink()
    assert releasable(packages, tmp_path, ["auth", "web"]) == (["web"], ["auth"])


def _services() -> tuple[Service, ...]:
    return (
        Service("postgres", "postgres:17", ports=("5432:5432",)),
        Service("redis", "redis:7"),
    )


def test_s15_8_2_2_plan(tmp_path: Path) -> None:
    packages = _packages()
    packages["app"].services = _services()
    outputs = plan(Workspace(root=tmp_path, packages=packages), "")
    assert outputs["integration"] == [
        {
            "name": "app",
            "dir": "packages/app",
            "services": ["postgres", "redis"],
            "marker": "app.integration",
        }
    ]
    assert "postgres" not in outputs
    assert "redis" not in outputs
    assert plan(Workspace(root=tmp_path, packages=_packages()), "")["integration"] == []


def test_s15_8_2_3_marker() -> None:
    package = Package("app", "packages/app", "app")
    assert not [c for c in package.checks() if c["kind"] == "integration"]
    package.services = _services()
    assert {"kind": "integration", "marker": "app.integration"} in package.checks()
    assert {c["kind"] for c in package.checks()} == {"test", "integration", "smoke"}


def test_s15_8_2_3_missing_marker_blocks_a_package(tmp_path: Path) -> None:
    packages = _packages()
    packages["base"].services = _services()
    for package in packages.values():
        for check in package.checks():
            if check["marker"] != "base.integration":
                (tmp_path / check["marker"]).touch()
    assert releasable(packages, tmp_path, ["base", "app"]) == ([], ["base", "app"])


def test_s6_7_2_checks_always_include_the_smoke_marker() -> None:
    package = Package("base", "packages/base", "base")
    assert {"kind": "smoke", "extra": "", "marker": "base.smoke"} in package.checks()


def test_s6_7_2_missing_smoke_marker_blocks_a_package_without_a_declaration(
    tmp_path: Path,
) -> None:
    packages = _packages()
    (tmp_path / "base.test").touch()
    assert releasable(packages, tmp_path, ["base"]) == ([], ["base"])
    (tmp_path / "base.smoke").touch()
    assert releasable(packages, tmp_path, ["base"]) == (["base"], [])


def test_s15_8_1_2_marker_kind(tmp_path: Path) -> None:
    package = Package("base", "packages/base", "base")
    assert package.checks()[0] == {"kind": "test", "marker": "base.test"}
    packages = {"base": package}
    for check in package.checks()[1:]:
        (tmp_path / check["marker"]).touch()
    assert releasable(packages, tmp_path, ["base"]) == ([], ["base"])
    (tmp_path / "base.verify").touch()
    assert releasable(packages, tmp_path, ["base"]) == ([], ["base"])
    (tmp_path / "base.test").touch()
    assert releasable(packages, tmp_path, ["base"]) == (["base"], [])


def _git_workspace(tmp_path: Path) -> Workspace:
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

    git("init", "-q")
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "f.txt").write_text("1")
    git("add", ".")
    git("commit", "-q", "-m", "one")
    git("tag", "v1")
    (tmp_path / "a" / "f.txt").write_text("2")
    git("commit", "-q", "-am", "two")
    packages = {n: Package(n, n, n) for n in ("a", "b")}
    return Workspace(root=tmp_path, packages=packages)


def test_s6_7_2_select_uses_valid_base(tmp_path: Path) -> None:
    assert select(_git_workspace(tmp_path), "v1") == {"a"}


def test_s6_7_2_select_rejects_option_like_base_without_running_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = _git_workspace(tmp_path)

    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("git must not run for an invalid base")

    monkeypatch.setattr(subprocess, "run", fail)
    assert select(workspace, "--output=x") == {"a", "b"}
    assert "selecting all packages" in capsys.readouterr().err


def test_s6_7_2_changed_files_rejects_option_like_base(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid base"):
        changed_files(tmp_path, "--output=x")


def test_s6_7_2_plan_outputs_match_documented_keys(tmp_path: Path) -> None:
    page = Path(__file__).parents[2] / "docs" / "reference" / "kiln-devops.md"
    text = page.read_text(encoding="utf-8")
    table = text.split("<!-- plan-outputs:start -->")[1].split(
        "<!-- plan-outputs:end -->"
    )[0]
    documented = set(re.findall(r"^\| `([^`]+)` \|", table, flags=re.MULTILINE))
    workspace = Workspace(tmp_path, _packages())
    assert documented == set(plan(workspace, ""))


def test_s6_10_3_3_plan_has_none_of_the_retired_sonar_outputs(tmp_path: Path) -> None:
    outputs = plan(Workspace(root=tmp_path, packages=_packages()), "")
    for key in ("cov-args", "test-paths", "sonar-sources", "sonar-tests", "sonar"):
        assert key not in outputs
