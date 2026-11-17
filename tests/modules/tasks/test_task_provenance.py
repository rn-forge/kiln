"""Build provenance and an SBOM in the task files."""

from __future__ import annotations
import pytest
import re
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import cycle
from rn_forge.kiln.modules.tasks import TASKS
from tests.modules.tasks.support import (
    ARCHETYPES,
    WEB_CELLS,
    _audit_root,
    _ci_tasks,
    _codes,
    _load,
    _root,
    _ci_root,
    _unmarked,
)


SBOM_CELLS = [(a, "") for a in ARCHETYPES] + list(WEB_CELLS)


EXPORT = "uv export --format cyclonedx1.5 --frozen --no-default-groups"


def _build_text(root: Path) -> str:
    python = YamlUtils.load((root / "tasks/python.yml").read_text("utf-8"))
    return "\n".join(python["tasks"]["build"]["cmds"])


@pytest.mark.parametrize(("archetype", "extra"), SBOM_CELLS)
def test_build_writes_an_sbom(tmp_path: Path, archetype: str, extra: str) -> None:
    root = _audit_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    text = _build_text(root)
    (line,) = [ln for ln in text.splitlines() if "uv export" in ln]
    assert text.index("uv build") < text.index("uv export")
    assert EXPORT in line
    assert re.search(r'-o "?dist/\S*\.cdx\.json"?$', line), line
    if archetype == "python-lib":
        assert text.index("for package in") < text.index("uv export")
        assert '--package "$package"' in line
        assert "dist/$package.cdx.json" in line
    elif archetype.startswith("python-web"):
        assert "--package demo-api " in line
        assert "-o dist/demo-api.cdx.json" in line
    else:
        assert "--package" not in line
        assert "-o dist/demo.cdx.json" in line


def test_build_override_is_untouched(tmp_path: Path) -> None:
    extra = '\n[tasks]\n[tasks.command_overrides]\n"python:build" = "echo hi"\n'
    root = _root(tmp_path, extra=extra)
    cycle.apply(root, home=tmp_path / "home")
    python = YamlUtils.load((root / "tasks/python.yml").read_text("utf-8"))
    assert python["tasks"]["build"]["cmds"] == ["echo hi"]
    assert "uv export" not in YamlUtils.serialize(python["tasks"]["build"])


def test_lib_release_is_split(tmp_path: Path) -> None:
    tasks = _ci_tasks(_root(tmp_path, "python-lib"))["tasks"]
    assert "release" not in tasks
    build = "\n".join(tasks["release:build"]["cmds"])  # type: ignore[index]
    publish = "\n".join(tasks["release:publish"]["cmds"])  # type: ignore[index]
    for name in ("release:build", "release:publish"):
        assert tasks[name]["desc"], name  # type: ignore[index]
        assert "internal" not in tasks[name], name  # type: ignore[operator]
    for text in ("releasable ok", "uv build", "uv export --format cyclonedx1.5"):
        assert text in build, text
    assert "gh release" not in build
    for text in ("release-publish", "--title", "--target", "continue"):
        assert text in publish, text
    assert "gh release" not in publish
    assert "uv build" not in publish
    assert "uv export" not in publish


def test_lib_publish_calls_release_publish(tmp_path: Path) -> None:
    tasks = _ci_tasks(_root(tmp_path, "python-lib"))["tasks"]
    publish = "\n".join(tasks["release:publish"]["cmds"])  # type: ignore[index]
    assert 'if [ ! -d "dist/$name" ]; then' in publish
    assert "continue" in publish
    assert (
        '{{.DEVOPS}} release-publish "$name-v$version" --title "$name v$version"'
        ' --target "$GITHUB_SHA" --notes-file "$notes" dist/"$name"/*'
    ) in publish.replace('"$tag"', '"$name-v$version"')
    assert "gh release" not in publish
    for name in ("release:state", "release:source"):
        assert name not in tasks


def test_lib_publish_carries_the_changelog(tmp_path: Path) -> None:
    tasks = _ci_tasks(_root(tmp_path, "python-lib"))["tasks"]
    publish = "\n".join(tasks["release:publish"]["cmds"])  # type: ignore[index]
    assert 'notes="$(mktemp)"' in publish
    assert '{{.DEVOPS}} notes "$dir/CHANGELOG.md" "$version" > "$notes"' in publish
    assert (
        '{{.DEVOPS}} release-publish "$name-v$version" --title "$name v$version"'
        ' --target "$GITHUB_SHA" --notes-file "$notes" dist/"$name"/*'
    ) in publish.replace('"$tag"', '"$name-v$version"')
    assert "--generate-notes" not in publish
    for archetype in ("python-app", "python-tool"):
        single = _ci_tasks(_root(tmp_path / archetype, archetype))["tasks"]
        assert "--notes-file" not in "\n".join(single["release:publish"]["cmds"])  # type: ignore[index]


def test_single_package_release_tasks(tmp_path: Path) -> None:
    expected = {
        "release:state": ['{{.DEVOPS}} release-state "v$({{.TASK_EXE}} version)"'],
        "release:source": ['{{.DEVOPS}} release-source "$TAG"'],
        "release:publish": [
            '{{.DEVOPS}} release-publish "$TAG" --title "$TAG" --target "$SOURCE_SHA"'
            " dist/*.whl dist/*.tar.gz dist/*.cdx.json"
        ],
    }
    for archetype in ("python-app", "python-tool"):
        tasks = _ci_tasks(_root(tmp_path / archetype, archetype))["tasks"]
        for name, cmds in expected.items():
            assert tasks[name]["cmds"] == cmds, (archetype, name)  # type: ignore[index]
            assert tasks[name]["desc"].startswith("CI only:"), name  # type: ignore[index]
            assert "internal" not in tasks[name], (archetype, name)  # type: ignore[operator]


def test_lib_build_reports_how_many_it_built(tmp_path: Path) -> None:
    build = "\n".join(
        _ci_tasks(_root(tmp_path, "python-lib"))["tasks"]["release:build"]["cmds"]  # type: ignore[index]
    )
    assert "built=" in build
    assert "$GITHUB_OUTPUT" in build


def test_lib_publish_uploads_the_sbom(tmp_path: Path) -> None:
    tasks = _ci_tasks(_root(tmp_path, "python-lib"))["tasks"]
    publish = "\n".join(tasks["release:publish"]["cmds"])  # type: ignore[index]
    assert publish.count('dist/"$name"/*') == 1
    build = "\n".join(tasks["release:build"]["cmds"])  # type: ignore[index]
    assert build.count('dist/$name/$name.cdx.json"') == 2  # tag and worktree
    assert '--out-dir "$GITHUB_WORKSPACE/dist/$name"' in build
    assert '--out-dir "dist/$name"' in build


def test_quality_yml_has_no_docs_task(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    quality = _load(root, "tasks/quality.yml")["tasks"]
    assert not [key for key in quality if key.startswith("lint:docs")]


def test_without_mkdocs_lint_has_no_docs_ref(tmp_path: Path) -> None:
    root = _root(tmp_path, profile="none")
    cycle.apply(root, home=tmp_path / "home")
    cmds = _unmarked(_load(root, "Taskfile.yml")["tasks"]["lint"]["cmds"])
    assert not any(c["task"].startswith("docs:") for c in cmds)
    assert not (root / "tasks" / "docs.yml").exists()


@pytest.mark.parametrize(
    "key",
    [
        "docs:structure",
        "docs:lint",
        "quality:lint:docs",
        "quality:lint:docs-structure",
        "quality:lint:docs-generate",
    ],
)
def test_old_keys_are_refused(tmp_path: Path, key: str) -> None:
    root = _root(
        tmp_path,
        extra=f'\n[tasks]\n[tasks.command_overrides]\n"{key}" = "echo hi"\n',
    )
    with pytest.raises(AppException, match=re.escape(key)):
        TASKS.artifacts(KilnConfig.load(root), root)


@pytest.mark.parametrize(
    ("archetype", "extra"), [(a, "") for a in ARCHETYPES] + list(WEB_CELLS)
)
def test_task_layout_accepts_the_rendered_files(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    root = _ci_root(tmp_path, archetype, extra)
    cycle.apply(root, home=tmp_path / "home")
    assert _codes(root) == []
