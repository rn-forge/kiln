"""The `kiln-devops` console script."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rn_forge.kiln.devops import (
    ci,
    consumer,
    dist,
    git,
    github,
    integration,
    licenses,
    notes,
    nx,
    requirements,
    site,
    sonar,
    umbrella,
    uv,
    verify_release,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kiln-devops",
        description="Plan and run a workspace's CI pipeline from its own manifests.",
    )
    parser.set_defaults(validate=_unchecked)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="print `$GITHUB_OUTPUT` lines for the run")
    plan.set_defaults(func=_plan)
    plan.add_argument("base", nargs="?", default="", metavar="BASE")
    releasable = commands.add_parser(
        "releasable", help="print the NAMEs whose checks all passed"
    )
    releasable.set_defaults(func=_releasable)
    releasable.add_argument("ok_dir", metavar="OK_DIR")
    releasable.add_argument("names", nargs="*", metavar="NAME")
    commands.add_parser(
        "released", help="print `name dir module version` per tag at HEAD"
    ).set_defaults(func=_released)
    smoke = commands.add_parser(
        "smoke", help="install one extra from built wheels and import it"
    )
    smoke.set_defaults(func=_smoke)
    smoke.add_argument("package", metavar="PACKAGE")
    smoke.add_argument("extra", nargs="?", default="", metavar="EXTRA")
    services = commands.add_parser(
        "integration", help="run one package's tests against its service containers"
    )
    services.set_defaults(func=_integration)
    services.add_argument("package", metavar="PACKAGE")
    verify = commands.add_parser(
        "verify-release",
        help="install each released version from its registry and import it",
    )
    verify.set_defaults(func=_verify_release, validate=_check_tag)
    verify.add_argument("--source", required=True, choices=["pypi", "git"])
    verify.add_argument(
        "tag",
        nargs="?",
        default=None,
        metavar="TAG",
        help="the release tag of a single-package repository; omit to read the tags at HEAD",
    )
    commands.add_parser(
        "adapters", help="check each declared adapter has a module and an extra"
    ).set_defaults(func=_adapters)
    commands.add_parser(
        "sonar-target",
        help="print the `$GITHUB_OUTPUT` line with the Sonar branch argument",
    ).set_defaults(func=_sonar_target)
    local = commands.add_parser(
        "sonar-local",
        help="run the coverage tests and scan the checked-out branch on SonarCloud",
    )
    local.set_defaults(func=_sonar_local)
    local.add_argument("--dry-run", action="store_true")
    local.add_argument("--branch", default=None, metavar="NAME")
    state = commands.add_parser(
        "release-state", help="print the release's state as `$GITHUB_OUTPUT` lines"
    )
    state.set_defaults(func=_release_state, validate=_check_tag)
    state.add_argument("tag", metavar="TAG")
    source = commands.add_parser(
        "release-source", help="check out the tag when it exists and print its commit"
    )
    source.set_defaults(func=_release_source, validate=_check_tag)
    source.add_argument("tag", metavar="TAG")
    publish = commands.add_parser(
        "release-publish", help="publish the GitHub release unless it is published"
    )
    publish.set_defaults(func=_release_publish, validate=_check_publish)
    publish.add_argument("tag", metavar="TAG")
    publish.add_argument("--title", required=True)
    publish.add_argument("--target", required=True, metavar="SHA")
    publish.add_argument("--notes-file", default=None, metavar="FILE")
    publish.add_argument("--upload", choices=["pypi", "testpypi"], default=None)
    publish.add_argument("files", nargs="+", metavar="FILE")
    changelog = commands.add_parser(
        "notes", help="print a version's section of a changelog"
    )
    changelog.set_defaults(func=_notes, validate=_check_notes)
    changelog.add_argument("changelog", metavar="CHANGELOG")
    changelog.add_argument("version", metavar="VERSION")
    resolve = commands.add_parser(
        "dist-resolve", help="rewrite `workspace:` ranges in a dist package.json"
    )
    resolve.set_defaults(func=_dist_resolve)
    resolve.add_argument("dist_dir", metavar="DIST_DIR")
    check = commands.add_parser(
        "dist-verify", help="fail when a dist package.json is not publishable"
    )
    check.set_defaults(func=_dist_verify)
    check.add_argument("dist_dir", metavar="DIST_DIR")
    assemble = commands.add_parser(
        "site-assemble", help="assemble the docs site from compodoc and storybook"
    )
    assemble.set_defaults(func=_site_assemble)
    assemble.add_argument("site_dir", nargs="?", default=None, metavar="SITE_DIR")
    smoke_consumer = commands.add_parser(
        "consumer", help="install a packed library per peer cell and smoke-test it"
    )
    smoke_consumer.set_defaults(func=_consumer)
    smoke_consumer.add_argument("project_root", metavar="PROJECT_ROOT")
    smoke_consumer.add_argument("--cell", default=None)
    policy = commands.add_parser(
        "licenses", help="fail when a dependency's licence matches the deny list"
    )
    policy.set_defaults(func=_licenses)
    policy.add_argument("--format", required=True, choices=["pip-licenses", "pnpm"])
    policy.add_argument("--deny", action="append", default=None, metavar="PATTERN")
    policy.add_argument("--ignore", action="append", default=[], metavar="PACKAGE")
    ranges = commands.add_parser(
        "requirements", help="fail when members depend on each other by exact pin"
    )
    ranges.set_defaults(func=_requirements)
    ranges.add_argument("--root", default=".", metavar="DIR")
    ranges.add_argument(
        "--stack",
        choices=["python", "node"],
        default="python",
        help="node reads `pnpm ls -r --depth -1 --json` from stdin"
        " and `nx.json` under --root",
    )
    release_all = commands.add_parser(
        "umbrella", help="create a GitHub release for the newest shipped release page"
    )
    release_all.set_defaults(func=_umbrella, validate=_check_umbrella)
    release_all.add_argument("--releases", default="docs/releases", metavar="DIR")
    release_all.add_argument("--sha", required=True, metavar="SHA")
    release_all.add_argument("--dry-run", action="store_true")
    return parser


def _checked(pattern: str, kind: str, value: str) -> str:
    if re.fullmatch(pattern, value) is None:
        raise ValueError(f"invalid {kind} '{value}'")
    return value


def _inside(value: str, *roots: str) -> str:
    """Return the resolved `value` when it is at or below one of `roots`."""
    resolved = os.path.realpath(value)
    for root in map(os.path.realpath, roots):
        if resolved == root or resolved.startswith(root + os.sep):
            return resolved
    raise ValueError(f"'{value}' is outside the working directory")


def _unchecked(args: argparse.Namespace) -> None:
    """Accept the arguments of a subcommand that has nothing to check."""


def _check_tag(args: argparse.Namespace) -> None:
    if args.tag is not None:
        args.tag = _checked(r"[A-Za-z0-9][A-Za-z0-9._+-]*", "tag", args.tag)


def _check_publish(args: argparse.Namespace) -> None:
    cwd = os.getcwd()
    _check_tag(args)
    args.target = _checked(r"[0-9a-f]{7,40}", "target", args.target)
    args.title = _checked(r"[^\x00-\x1f\x7f-][^\x00-\x1f\x7f]*", "title", args.title)
    args.files = [_inside(f, cwd) for f in args.files]
    if args.notes_file:
        args.notes_file = _inside(args.notes_file, cwd, tempfile.gettempdir())


def _check_umbrella(args: argparse.Namespace) -> None:
    args.sha = _checked(r"[0-9a-f]{7,40}", "sha", args.sha)
    args.releases = _inside(args.releases, os.getcwd())


def _check_notes(args: argparse.Namespace) -> None:
    args.changelog = _inside(args.changelog, os.getcwd())


def _validate(args: argparse.Namespace) -> None:
    """Replace each argument that reaches a command or a file with its checked value.

    Raises:
        ValueError: With the message to print when an argument is not allowed.
    """
    args.validate(args)


def _upload(args: argparse.Namespace) -> None:
    name, _, version = args.tag.rpartition("-v")
    host = "test.pypi.org" if args.upload == "testpypi" else "pypi.org"
    indexed = github.indexed_files(host, name, version)
    for command in github.upload_commands(
        args.upload, name, version, args.files, indexed
    ):
        github.run(command)


def _release_source(args: argparse.Namespace) -> int:
    print(f"sha={github.release_source(args.tag)}")
    return 0


def _release_state(args: argparse.Namespace) -> int:
    tag: str = args.tag
    status = github.release_status(tag)
    tagged = github.remote_tag_exists(tag)
    for line in github.output_lines(github.release_state(tag, status, tagged)):
        print(line)
    if status is github.ReleaseStatus.PUBLISHED:
        github.already_published(tag)
    return 0


def _release_publish(args: argparse.Namespace) -> int:
    tag: str = args.tag
    upload: str | None = args.upload
    if upload == "testpypi":
        _upload(args)
        return 0
    status = github.release_status(tag)
    tagged = github.remote_tag_exists(tag)
    assets = [f for f in args.files if not f.endswith(".publish.attestation")]
    commands = github.publish_commands(
        tag, args.title, args.target, assets, status, tagged, args.notes_file
    )
    if not commands:
        github.already_published(tag)
    elif upload:
        _upload(args)
    for command in commands:
        github.run(command)
    return 0


def _notes(args: argparse.Namespace) -> int:
    try:
        text = Path(args.changelog).read_text(encoding="utf-8")
        print(notes.changelog_section(text, args.version))
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


def _read_manifest(dist_dir: str) -> tuple[Path, dict[str, Any]] | None:
    path = Path.cwd() / dist_dir / "package.json"
    try:
        manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return path, manifest
    except (OSError, ValueError) as error:
        print(f"Could not read/parse {path} ({error})", file=sys.stderr)
        return None


def _dist_resolve(args: argparse.Namespace) -> int:
    read = _read_manifest(args.dist_dir)
    if read is None:
        return 1
    path, manifest = read
    root = Path.cwd()
    shown = f"{args.dist_dir}/package.json"
    try:
        resolved, changed = dist.resolve(manifest, lambda: nx.local_versions(root))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1
    if changed:
        path.write_text(json.dumps(resolved, indent=2) + "\n", encoding="utf-8")
        print(f"Resolved workspace: protocol dependencies in {shown}")
    else:
        print(f"No workspace: protocol dependencies found in {shown}")
    return 0


def _dist_verify(args: argparse.Namespace) -> int:
    read = _read_manifest(args.dist_dir)
    if read is None:
        return 1
    found = dist.problems(read[1])
    if found:
        print(
            f"Dist manifest verification failed for {args.dist_dir}:\n", file=sys.stderr
        )
        for problem in found:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"Dist manifest verification passed for {args.dist_dir}")
    return 0


def _site_assemble(args: argparse.Namespace) -> int:
    root = Path.cwd()
    target = Path(args.site_dir) if args.site_dir else Path("dist/site")
    repository = os.environ.get("GITHUB_REPOSITORY", "").partition("/")[2]
    try:
        projects = {
            target_name: [
                (project, nx.project_root(root, project))
                for project in nx.projects(root, target_name)
            ]
            for target_name in ("compodoc", "build-storybook")
        }
        site.assemble(root, root / target, projects, repository or None)
    except (OSError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


def _consumer(args: argparse.Namespace) -> int:
    return consumer.run(Path.cwd(), args.project_root, args.cell)


def _licenses(args: argparse.Namespace) -> int:
    deny = args.deny if args.deny is not None else licenses.DEFAULT_DENY
    try:
        offenders = licenses.run(sys.stdin.read(), args.format, deny, args.ignore)
    except ValueError as error:
        print(f"kiln-devops: {error}", file=sys.stderr)
        return 2
    for line in offenders:
        print(line, file=sys.stderr)
    return 1 if offenders else 0


def _requirements(args: argparse.Namespace) -> int:
    try:
        if args.stack == "node":
            problems = requirements.check_node(
                json.load(sys.stdin),
                fixed=requirements.release_is_fixed(Path(args.root)),
            )
        else:
            problems = requirements.check(Path(args.root))
    except (FileNotFoundError, ValueError) as error:
        print(f"kiln-devops: {error}", file=sys.stderr)
        return 2
    for line in problems:
        print(line)
    return 1 if problems else 0


def _umbrella(args: argparse.Namespace) -> int:
    try:
        return umbrella.run(Path(args.releases), args.sha, args.dry_run)
    except FileNotFoundError as error:
        print(f"kiln-devops: {error}", file=sys.stderr)
        return 2


def _workspace() -> ci.Workspace:
    try:
        return uv.load_workspace(uv.find_root(Path.cwd()))
    except (FileNotFoundError, ValueError) as error:
        sys.exit(str(error))


def _plan(args: argparse.Namespace) -> int:
    workspace = _workspace()
    base: str = args.base
    changed: list[str] | None = None
    if base:
        if git.usable_base(workspace.root, base):
            changed = git.changed_files(workspace.root, base)
        else:
            print(
                f"base {base} is not a commit or an ancestor of HEAD; selecting all packages",
                file=sys.stderr,
            )
    for line in github.output_lines(ci.plan(workspace, changed)):
        print(line)
    return 0


def _releasable(args: argparse.Namespace) -> int:
    workspace = _workspace()
    ok, blocked = ci.releasable(workspace.packages, Path(args.ok_dir), args.names)
    for name in blocked:
        print(
            f"not releasing {name}: a check or a prerequisite failed", file=sys.stderr
        )
    for name in ok:
        print(name)
    return 0


def _released(_: argparse.Namespace) -> int:
    workspace = _workspace()
    for found in ci.released(workspace, git.tags_at_head(workspace.root)):
        print(found.name, found.dir, found.module, found.version)
    return 0


def _smoke(args: argparse.Namespace) -> int:
    return uv.smoke(_workspace(), args.package, args.extra)


def _integration(args: argparse.Namespace) -> int:
    workspace = _workspace()
    package = workspace.packages[ci.normalize(args.package)]
    return integration.run(
        package, integration.subprocess_runner, workspace.pytest_args
    )


def _adapters(_: argparse.Namespace) -> int:
    problems = uv.check_adapters(_workspace())
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


def _verify_release(args: argparse.Namespace) -> int:
    workspace = _workspace()
    url = os.environ.get("REPOSITORY_URL", "")
    if args.source == "git" and not url:
        print("kiln-devops: REPOSITORY_URL is not set", file=sys.stderr)
        return 2
    if args.tag:
        (package,) = workspace.packages.values()
        found = [
            ci.Release(
                package.name,
                package.dir,
                package.module,
                args.tag.removeprefix("v"),
                args.tag,
            )
        ]
    else:
        found = ci.released(workspace, git.tags_at_head(workspace.root))
    status = 0
    for release in found:
        spec = verify_release.Spec(
            release.name,
            release.module,
            release.version,
            release.tag,
            args.source,
            url,
            release.dir,
        )
        status = verify_release.run(spec, integration.subprocess_runner) or status
    return status


def _sonar_target(_: argparse.Namespace) -> int:
    try:
        print(github.sonar_target())
    except ValueError as error:
        sys.exit(str(error))
    return 0


def _sonar_local(args: argparse.Namespace) -> int:
    return sonar.run(args.branch, args.dry_run)


def main(argv: list[str] | None = None) -> int:
    """Run a subcommand and return its exit status.

    Args:
        argv: The arguments after the program name; `sys.argv[1:]` when omitted.
    """
    args = _parser().parse_args(argv)
    try:
        _validate(args)
    except ValueError as error:
        print(f"kiln-devops: {error}", file=sys.stderr)
        return 2
    handler: Callable[[argparse.Namespace], int] = args.func
    return handler(args)
