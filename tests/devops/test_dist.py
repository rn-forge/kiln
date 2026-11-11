"""Tests for `kiln-devops dist-resolve` and `dist-verify` (S9.4.1)."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from rn_forge.kiln.devops import cli, dist

VERSIONS = {"@x/core": "1.2.3"}


def _manifest(range_: str) -> dict:
    return {"name": "a", "dependencies": {"@x/core": range_, "rxjs": "^7"}}


@pytest.mark.parametrize(
    ("range_", "expected"),
    [
        ("workspace:*", "1.2.3"),
        ("workspace:", "1.2.3"),
        ("workspace:^", "^1.2.3"),
        ("workspace:~", "~1.2.3"),
        ("workspace:>=1.0.0", ">=1.0.0"),
    ],
)
def test_s9_4_1_1_resolve_rewrites_ranges(range_: str, expected: str) -> None:
    manifest, changed = dist.resolve(_manifest(range_), lambda: VERSIONS)
    assert changed
    assert manifest["dependencies"] == {"@x/core": expected, "rxjs": "^7"}


def test_s9_4_1_1_resolve_covers_every_field_and_skips_other_ranges() -> None:
    source = {
        "peerDependencies": {"@x/core": "workspace:^"},
        "optionalDependencies": {"@x/core": "workspace:~"},
        "devDependencies": {"@x/core": "workspace:*"},
    }
    manifest, _ = dist.resolve(source, lambda: VERSIONS)
    assert manifest["peerDependencies"] == {"@x/core": "^1.2.3"}
    assert manifest["optionalDependencies"] == {"@x/core": "~1.2.3"}
    assert manifest["devDependencies"] == {"@x/core": "workspace:*"}


def test_s9_4_1_1_resolve_without_workspace_range_is_lazy() -> None:
    def versions() -> dict[str, str]:
        raise AssertionError("called")

    manifest, changed = dist.resolve({"dependencies": {"a": "^1"}}, versions)
    assert not changed
    assert manifest == {"dependencies": {"a": "^1"}}


def test_s9_4_1_2_resolve_unknown_dependency_raises() -> None:
    with pytest.raises(ValueError) as info:
        dist.resolve(_manifest("workspace:*"), lambda: {})
    assert str(info.value) == (
        'Cannot resolve "workspace:*" for "@x/core": no local package version found'
    )


def test_s9_4_1_2_versions_called_once() -> None:
    calls = []

    def versions() -> dict[str, str]:
        calls.append(1)
        return VERSIONS

    source = {
        "dependencies": {"@x/core": "workspace:*"},
        "peerDependencies": {"@x/core": "workspace:*"},
    }
    dist.resolve(source, versions)
    assert len(calls) == 1


def test_s9_4_1_3_problems_valid_is_empty() -> None:
    manifest = {"name": "a", "version": "1", "module": "m.js", "typings": "t.d.ts"}
    assert dist.problems(manifest) == []


def test_s9_4_1_3_problems_in_order() -> None:
    manifest = {
        "dependencies": {"d": "workspace:*"},
        "peerDependencies": {"p": "workspace:^"},
        "optionalDependencies": {"o": "workspace:~"},
    }
    assert dist.problems(manifest) == [
        'dependencies["d"] uses "workspace:" protocol (workspace:*) in dist manifest',
        'peerDependencies["p"] uses "workspace:" protocol (workspace:^) in dist manifest',
        'optionalDependencies["o"] uses "workspace:" protocol (workspace:~) in dist manifest',
        'missing required field "name"',
        'missing required field "version"',
        'missing both "module" and "exports" (no entry point referenced)',
        'missing both "typings" and "exports" (no type declarations referenced)',
    ]


def test_s9_4_1_3_exports_satisfies_entry_and_types() -> None:
    assert dist.problems({"name": "a", "version": "1", "exports": {}}) != []
    assert dist.problems({"name": "a", "version": "1", "exports": {".": "x"}}) == []


def _stub_pnpm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A `pnpm` on PATH that logs its calls and serves `nx show` JSON."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "pnpm.log"
    script = bin_dir / "pnpm"
    script.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> "{log}"\n'
        'case "$*" in\n'
        '  "exec nx show projects --json") echo \'["core","app"]\' ;;\n'
        '  "exec nx show project core --json") echo \'{"root": "libs/core"}\' ;;\n'
        '  "exec nx show project app --json") echo \'{"root": "apps/app"}\' ;;\n'
        "esac\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    return log


def _workspace(tmp_path: Path) -> None:
    (tmp_path / "libs/core").mkdir(parents=True)
    (tmp_path / "libs/core/package.json").write_text(
        json.dumps({"name": "@x/core", "version": "1.2.3"})
    )
    # apps/app has no package.json: skipped


def test_s9_4_1_4_dist_resolve_rewrites_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _stub_pnpm(tmp_path, monkeypatch)
    _workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "dist/libs/ng"
    out.mkdir(parents=True)
    (out / "package.json").write_text(json.dumps(_manifest("workspace:^")))
    assert cli.main(["dist-resolve", "dist/libs/ng"]) == 0
    assert capsys.readouterr().out == (
        "Resolved workspace: protocol dependencies in dist/libs/ng/package.json\n"
    )
    expected = {"name": "a", "dependencies": {"@x/core": "^1.2.3", "rxjs": "^7"}}
    assert (out / "package.json").read_text() == json.dumps(expected, indent=2) + "\n"


def test_s9_4_1_5_dist_resolve_without_range_leaves_file_and_skips_pnpm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log = _stub_pnpm(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "dist/ng"
    out.mkdir(parents=True)
    text = '{"name":"a","dependencies":{"b":"^1"}}'
    (out / "package.json").write_text(text)
    assert cli.main(["dist-resolve", "dist/ng"]) == 0
    assert capsys.readouterr().out == (
        "No workspace: protocol dependencies found in dist/ng/package.json\n"
    )
    assert (out / "package.json").read_text() == text
    assert not log.exists()


def test_s9_4_1_6_dist_verify_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "d").mkdir()
    (tmp_path / "d/package.json").write_text(
        json.dumps({"name": "a", "version": "1", "exports": {".": "./x.js"}})
    )
    assert cli.main(["dist-verify", "d"]) == 0
    assert capsys.readouterr().out == "Dist manifest verification passed for d\n"


def test_s9_4_1_6_dist_verify_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "d").mkdir()
    (tmp_path / "d/package.json").write_text(json.dumps({"name": "a"}))
    assert cli.main(["dist-verify", "d"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "Dist manifest verification failed for d:\n\n"
        '  - missing required field "version"\n'
        '  - missing both "module" and "exports" (no entry point referenced)\n'
        '  - missing both "typings" and "exports" (no type declarations referenced)\n'
    )


@pytest.mark.parametrize("command", ["dist-resolve", "dist-verify"])
@pytest.mark.parametrize("content", [None, "not json"])
def test_s9_4_1_7_unreadable_manifest_exits_one(
    command: str,
    content: str | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "d").mkdir()
    if content is not None:
        (tmp_path / "d/package.json").write_text(content)
    assert cli.main([command, "d"]) == 1
    err = capsys.readouterr().err
    assert len(err.strip().splitlines()) == 1
    assert "Traceback" not in err


def test_s9_4_5_9_resolve_drops_workspace_ci_and_counts_it_as_a_change() -> None:
    source = {"name": "a", "workspace-ci": {"consumer": {}}}
    manifest, changed = dist.resolve(source, lambda: {})
    assert changed
    assert "workspace-ci" not in manifest
    assert "workspace-ci" in source
