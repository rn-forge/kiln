"""Tests for `kiln-devops evidence collect`."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from rn_forge.kiln.devops import cli, evidence, github

FIXTURES = Path(__file__).parent / "fixtures" / "evidence"
SHA = "abc1234def"
R = "repos/{owner}/{repo}"
TAG = "rn-forge-kiln-v0.4.0"
Api = dict[str, tuple[int, Any]]


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _api() -> Api:
    return {
        R: (200, _load("repository.json")),
        f"{R}/actions/runs/123/attempts/1/jobs?per_page=100": (200, _load("jobs.json")),
        f"{R}/git/matching-refs/tags": (200, _load("refs.json")),
        f"{R}/releases/tags/{TAG}": (200, _load("release.json")),
        f"{R}/attestations/sha256:aaa": (200, {}),
        f"{R}/attestations/sha256:bbb": (200, {}),
        f"{R}/contents/SECURITY.md?ref={SHA}": (200, {}),
        f"{R}/actions/workflows/scorecard.yml/runs?branch=main&status=completed&per_page=1": (
            200,
            _load("scorecard-runs.json"),
        ),
    }


def _install(
    monkeypatch: pytest.MonkeyPatch,
    api: Api,
    wheels: frozenset[str] = frozenset(),
    provenance: int = 200,
) -> None:
    def fake(path: str) -> tuple[int, Any]:
        if path not in api:
            raise AssertionError(f"unexpected read: {path}")
        return api[path]

    monkeypatch.setattr(github, "api", fake)
    monkeypatch.setattr(github, "indexed_files", lambda *_: wheels)
    monkeypatch.setattr(github, "pypi_provenance_status", lambda *_: provenance)
    monkeypatch.setattr(github, "scorecard_result", lambda _: None)


def _controls(tmp_path: Path, **changes: Any) -> Path:
    body = _load("controls.json")
    body.update(changes)
    path = tmp_path / "controls.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def _collect(tmp_path: Path, controls: Path | None = None) -> int:
    return cli.main(
        [
            "evidence", "collect", "--run", "123", "--sha", SHA,
            "--controls", str(controls or _controls(tmp_path)),
            "--out", str(tmp_path / "out.json"),
        ]
    )  # fmt: skip


def _record(tmp_path: Path) -> dict[str, Any]:
    return json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))


def _results(tmp_path: Path) -> dict[str, str]:
    return {c["name"]: c["result"] for c in _record(tmp_path)["controls"]}


def test_collect_records_every_control_passed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install(monkeypatch, _api())
    assert _collect(tmp_path) == 0
    record = _record(tmp_path)
    assert list(record) == [
        "repository", "commit", "run", "attempt", "packages", "controls",
    ]  # fmt: skip
    assert record["repository"] == "rn-forge/kiln"
    assert (record["commit"], record["run"], record["attempt"]) == (SHA, 123, 1)
    assert record["packages"] == [
        {"name": "rn-forge-kiln", "version": "0.4.0", "tag": TAG}
    ]
    names = [c["name"] for c in record["controls"]]
    assert names == [c["name"] for c in _load("controls.json")["controls"]]
    results = [c["result"] for c in record["controls"]]
    assert results == ["passed"] * 4 + ["not checked"] + ["passed"] * 4


def test_collect_records_a_failed_job(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    api = _api()
    jobs = copy.deepcopy(_load("jobs.json"))
    jobs["jobs"][0]["conclusion"] = "failure"
    api[f"{R}/actions/runs/123/attempts/1/jobs?per_page=100"] = (200, jobs)
    _install(monkeypatch, api)
    assert _collect(tmp_path) == 0
    controls = _record(tmp_path)["controls"]
    for control in controls[:3]:
        assert control["result"] == "failed"
        assert control["evidence"]["url"] == jobs["jobs"][0]["html_url"]
    assert controls[3]["result"] == "passed"


def test_collect_fails_the_sbom_of_a_package_without_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    api = _api()
    refs = _load("refs.json")
    refs.append(
        {"ref": "refs/tags/other-v1.0.0", "object": {"type": "commit", "sha": SHA}}
    )
    api[f"{R}/git/matching-refs/tags"] = (200, refs)
    bare = {"html_url": "https://example/r", "assets": [{"name": "x.whl"}]}
    api[f"{R}/releases/tags/other-v1.0.0"] = (200, bare)
    _install(monkeypatch, api)
    assert _collect(tmp_path) == 0
    sbom = next(c for c in _record(tmp_path)["controls"] if c["name"] == "SBOM")
    assert sbom["result"] == "failed"
    assert "other-v1.0.0: no SBOM" in sbom["evidence"]["detail"]


def test_collect_records_scorecard_off_as_not_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    api = _api()
    del api[
        f"{R}/actions/workflows/scorecard.yml/runs?branch=main&status=completed&per_page=1"
    ]
    _install(monkeypatch, api)
    body = _load("controls.json")
    body["controls"][-1]["runs"] = False
    assert _collect(tmp_path, _controls(tmp_path, controls=body["controls"])) == 0
    scorecard = _record(tmp_path)["controls"][-1]
    assert scorecard["result"] == "not run"
    assert scorecard["evidence"] == {
        "url": None,
        "detail": "not run by this repository",
    }


def test_collect_names_the_commit_scorecard_scored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    api = _api()
    runs = copy.deepcopy(_load("scorecard-runs.json"))
    runs["workflow_runs"][0]["head_sha"] = "1111111"
    api[
        f"{R}/actions/workflows/scorecard.yml/runs?branch=main&status=completed&per_page=1"
    ] = (200, runs)
    _install(monkeypatch, api)
    assert _collect(tmp_path) == 0
    scorecard = _record(tmp_path)["controls"][-1]
    assert "commit 1111111" in scorecard["evidence"]["detail"]


def test_collect_checks_pypi_provenance_for_each_wheel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install(
        monkeypatch,
        _api(),
        wheels=frozenset({"rn_forge_kiln-0.4.0-py3-none-any.whl"}),
        provenance=404,
    )
    assert _collect(tmp_path, _controls(tmp_path, release="pypi")) == 0
    attestation = next(
        c for c in _record(tmp_path)["controls"] if c["name"] == "Attestation"
    )
    assert attestation["result"] == "failed"
    assert (
        "rn_forge_kiln-0.4.0-py3-none-any.whl 404" in attestation["evidence"]["detail"]
    )


def test_collect_resolves_an_annotated_tag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    api = _api()
    api[f"{R}/git/matching-refs/tags"] = (
        200,
        [{"ref": f"refs/tags/{TAG}", "object": {"type": "tag", "sha": "tagsha"}}],
    )
    api[f"{R}/git/tags/tagsha"] = (200, {"object": {"type": "commit", "sha": SHA}})
    _install(monkeypatch, api)
    assert _collect(tmp_path) == 0
    assert _record(tmp_path)["packages"][0]["tag"] == TAG


def test_collect_exits_2_when_the_jobs_cannot_be_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    api = _api()
    path = f"{R}/actions/runs/123/attempts/1/jobs?per_page=100"
    api[path] = (404, None)
    _install(monkeypatch, api)
    assert _collect(tmp_path) == 2
    assert path in capsys.readouterr().err
    assert not (tmp_path / "out.json").exists()


def test_table_renders_one_row_per_control() -> None:
    record = {
        "controls": [
            {
                "name": "A",
                "effect": "fails the build",
                "result": "passed",
                "evidence": {"url": "https://x/1", "detail": "job a"},
            },
            {
                "name": "B|C",
                "effect": "reports only",
                "result": "failed",
                "evidence": {"url": None, "detail": "x | y"},
            },
        ]
    }
    assert evidence.table(record).splitlines() == [
        "| Control | Effect | Result | Evidence |",
        "| -- | -- | -- | -- |",
        "| A | fails the build | passed | [job a](https://x/1) |",
        "| B\\|C | reports only | failed | x \\| y |",
    ]


def test_api_reads_the_status_from_gh(monkeypatch: pytest.MonkeyPatch) -> None:
    result = subprocess.CompletedProcess(
        ["gh"], 1, stdout="", stderr="gh: Not Found (HTTP 404)"
    )
    monkeypatch.setattr(github.subprocess, "run", lambda *_a, **_k: result)
    assert github.api("x") == (404, None)
    ok = subprocess.CompletedProcess(["gh"], 0, stdout='{"a": 1}', stderr="")
    monkeypatch.setattr(github.subprocess, "run", lambda *_a, **_k: ok)
    assert github.api("x") == (200, {"a": 1})
