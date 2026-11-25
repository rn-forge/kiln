"""The security evidence record of a release run, read through the GitHub API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rn_forge.kiln.devops import github

_REPO = "repos/{owner}/{repo}"
_SOURCES = frozenset(
    {
        "lint-job",
        "job",
        "not-checked",
        "release-asset",
        "attestation",
        "file",
        "scorecard-run",
    }
)
_FAILED = frozenset({"failure", "cancelled", "timed_out"})


def load_controls(path: Path) -> dict[str, Any]:
    """Return the parsed controls file at `path`.

    Raises:
        ValueError: When the file is missing, is not JSON, or names an unknown source.
    """
    try:
        body: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        sources = {control["source"] for control in body["controls"]}
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError(f"cannot read controls file {path}: {error}") from error
    unknown = sources - _SOURCES
    if unknown:
        raise ValueError(f"unknown control source '{min(unknown)}'")
    return body


def _read(path: str) -> Any:
    status, body = github.api(path)
    if status != 200:
        raise ValueError(f"GitHub API {path}: HTTP {status}")
    return body


def _tags(sha: str) -> list[str]:
    tags: list[str] = []
    for ref in _read(f"{_REPO}/git/matching-refs/tags"):
        obj = ref["object"]
        if obj["type"] == "tag":
            obj = _read(f"{_REPO}/git/tags/{obj['sha']}")["object"]
        if obj["sha"] == sha:
            tags.append(ref["ref"].removeprefix("refs/tags/"))
    return sorted(tags)


def _package(tag: str, repository: str) -> dict[str, str]:
    name, _, version = tag.rpartition("-v")
    if not name:
        name, version = repository.partition("/")[2], tag[1:]
    return {"name": name, "version": version, "tag": tag}


def _release(tag: str) -> dict[str, Any] | None:
    body: dict[str, Any] | None = github.api(f"{_REPO}/releases/tags/{tag}")[1]
    return body


def _entry(result: str, url: str | None, detail: str) -> tuple[str, dict[str, Any]]:
    return result, {"url": url, "detail": detail}


def _job(
    control: dict[str, Any], jobs: list[dict[str, Any]]
) -> tuple[str, dict[str, Any]]:
    wanted = control["job"]
    found = next(
        (
            j
            for j in jobs
            if j["name"] == wanted or j["name"].startswith(f"{wanted} / ")
        ),
        None,
    )
    conclusion = found["conclusion"] if found else None
    result = (
        "passed"
        if conclusion == "success"
        else "failed"
        if conclusion in _FAILED
        else "not run"
    )
    detail = f"job {wanted}"
    if control["source"] == "lint-job":
        detail += f", step {control['step']}"
    return _entry(result, found["html_url"] if found else None, detail)


def _sbom(
    releases: list[tuple[str, dict[str, Any] | None]],
) -> tuple[str, dict[str, Any]]:
    if not releases:
        return _entry("not run", None, "no package tagged at the commit")
    details: list[str] = []
    passed = True
    for tag, release in releases:
        if release is None:
            details.append(f"{tag}: no release")
            passed = False
            continue
        sboms = [
            a["name"] for a in release["assets"] if a["name"].endswith(".cdx.json")
        ]
        passed = passed and bool(sboms)
        details.append(f"{tag}: {', '.join(sboms)}" if sboms else f"{tag}: no SBOM")
    first = next((r["html_url"] for _, r in releases if r), None)
    return _entry("passed" if passed else "failed", first, "; ".join(details))


def _attestation(
    packages: list[dict[str, str]],
    releases: list[tuple[str, dict[str, Any] | None]],
    mode: str,
) -> tuple[str, dict[str, Any]]:
    if not packages:
        return _entry("not run", None, "no package tagged at the commit")
    files: list[tuple[str, int]] = []
    for _, release in releases:
        for asset in (release or {"assets": []})["assets"]:
            if asset["name"].endswith(".publish.attestation"):
                continue
            digest = asset.get("digest")
            status = github.api(f"{_REPO}/attestations/{digest}")[0] if digest else 0
            files.append((asset["name"], status))
    if mode == "pypi":
        for package in packages:
            name, version = package["name"], package["version"]
            for filename in sorted(github.indexed_files("pypi.org", name, version)):
                if filename.endswith(".whl"):
                    files.append(
                        (
                            filename,
                            github.pypi_provenance_status(name, version, filename),
                        )
                    )
    result = "passed" if all(status == 200 for _, status in files) else "failed"
    return _entry(result, None, "; ".join(f"{name} {status}" for name, status in files))


def _scorecard(full_name: str, branch: str) -> tuple[str, dict[str, Any]]:
    status, body = github.api(
        f"{_REPO}/actions/workflows/scorecard.yml/runs"
        f"?branch={branch}&status=completed&per_page=1"
    )
    runs: list[dict[str, Any]] = body["workflow_runs"] if status == 200 else []
    if not runs:
        return _entry("not run", None, "no completed run")
    run = runs[0]
    detail = f"commit {run['head_sha']}"
    scored = github.scorecard_result(full_name)
    if scored is not None:
        detail += (
            f", score {scored['score']}, Scorecard {scored['scorecard']['version']}"
        )
    result = "passed" if run["conclusion"] == "success" else "failed"
    return _entry(result, run["html_url"], detail)


def collect(
    controls: dict[str, Any], run: int, attempt: int, sha: str
) -> dict[str, Any]:
    """Return the evidence record of run `run`, attempt `attempt`, for the commit `sha`.

    Args:
        controls: The result of `load_controls`.
        run: The workflow run ID.
        attempt: The run attempt number.
        sha: The pushed commit.

    Raises:
        ValueError: When the repository, the jobs or the tags cannot be read.
    """
    repository = _read(_REPO)
    full_name: str = repository["full_name"]
    jobs = _read(f"{_REPO}/actions/runs/{run}/attempts/{attempt}/jobs?per_page=100")[
        "jobs"
    ]
    packages = [_package(tag, full_name) for tag in _tags(sha)]
    releases = [(p["tag"], _release(p["tag"])) for p in packages]
    entries: list[dict[str, Any]] = []
    for control in controls["controls"]:
        source = control["source"]
        if not control["runs"]:
            result, evidence = _entry("not run", None, "not run by this repository")
        elif source in ("lint-job", "job"):
            result, evidence = _job(control, jobs)
        elif source == "not-checked":
            result, evidence = _entry("not checked", None, "not read by CI")
        elif source == "release-asset":
            result, evidence = _sbom(releases)
        elif source == "attestation":
            result, evidence = _attestation(packages, releases, controls["release"])
        elif source == "file":
            found = github.api(f"{_REPO}/contents/SECURITY.md?ref={sha}")[0]
            result = "passed" if found == 200 else "failed"
            evidence = {
                "url": f"https://github.com/{full_name}/blob/{sha}/SECURITY.md",
                "detail": "SECURITY.md",
            }
        else:
            result, evidence = _scorecard(full_name, repository["default_branch"])
        entries.append(
            {
                "name": control["name"],
                "effect": control["effect"],
                "result": result,
                "evidence": evidence,
            }
        )
    return {
        "repository": full_name,
        "commit": sha,
        "run": run,
        "attempt": attempt,
        "packages": packages,
        "controls": entries,
    }


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def table(record: dict[str, Any]) -> str:
    """Return the record's controls as a Markdown table, one row per control."""
    rows = ["| Control | Effect | Result | Evidence |", "| -- | -- | -- | -- |"]
    for control in record["controls"]:
        evidence = control["evidence"]
        shown = (
            f"[{_cell(evidence['detail'])}]({evidence['url']})"
            if evidence["url"]
            else _cell(evidence["detail"])
        )
        cells = [
            _cell(control["name"]),
            _cell(control["effect"]),
            control["result"],
            shown,
        ]
        rows.append(f"| {' | '.join(cells)} |")
    return "\n".join(rows)
