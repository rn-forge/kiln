"""The node setup action and its pnpm and Node block."""

from __future__ import annotations
import pytest
import re
from pathlib import Path
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.modules.core.pins import load_pins
from tests.modules.cicd.support import (
    ARCHETYPES,
    DEPENDABOT,
    HOOKS,
    SETUP_ACTION,
    UPSTREAM_PINS,
    _cell_root,
    _rendered,
    _root,
    _web_root,
    _with_ci,
)


def _updates_of(content: str) -> list[str]:
    """The package ecosystems a rendered `dependabot.yml` updates."""
    return [u["package-ecosystem"] for u in YamlUtils.load(content)["updates"]]


def _node_lib_action(tmp_path: Path, hooks: str = "") -> dict[str, object]:
    root = _root(tmp_path, "node-lib")
    if hooks:
        root = _with_ci(root, hooks)
    return YamlUtils.load(_rendered(root)[SETUP_ACTION])


def test_node_lib_action_inputs_and_steps(tmp_path: Path) -> None:
    action = _node_lib_action(tmp_path)
    inputs = action["inputs"]
    assert list(inputs) == ["start-ci-run", "registry-url", "github-token"]  # type: ignore[arg-type]
    assert inputs["start-ci-run"]["default"] == ""  # type: ignore[index]
    assert inputs["registry-url"]["default"] == ""  # type: ignore[index]
    pins = load_pins()
    steps = action["runs"]["steps"]  # type: ignore[index]

    def uses(key: str) -> str:
        return f"{pins[key]['uses']}@{pins[key]['sha']}"

    assert [s.get("uses", s.get("run")) for s in steps] == [
        uses("pnpm-setup"),
        "printf '%s\\n' \"$START_CI_RUN\" | xargs pnpm dlx nx start-ci-run",
        uses("setup-node"),
        "pnpm install --frozen-lockfile",
        uses("setup-uv"),
        uses("setup-task"),
    ]
    assert steps[0]["with"] == {"run_install": False}
    assert steps[1]["if"] == "${{ inputs.start-ci-run != '' }}"
    assert steps[2]["with"] == {
        "node-version-file": ".nvmrc",
        "cache": "pnpm",
        "registry-url": "${{ inputs.registry-url }}",
    }
    assert steps[4]["if"] == (
        "${{ hashFiles('**/uv.lock', '!**/node_modules/**') != '' }}"
    )
    assert steps[4]["with"]["cache-dependency-glob"] == "**/uv.lock"
    assert steps[5]["with"]["repo-token"] == "${{ inputs.github-token }}"


def test_hooks_follow_the_setup_task_step(tmp_path: Path) -> None:
    steps = _node_lib_action(tmp_path, HOOKS)["runs"]["steps"]  # type: ignore[index]
    assert [s["name"] for s in steps[-2:]] == [
        "Run ./.github/actions/a",
        "Run ./.github/actions/b",
    ]
    assert "setup-task" in steps[-3]["uses"]


@pytest.mark.parametrize(
    ("archetype", "extra"),
    [
        ("python-app", ""),
        ("python-tool", ""),
        ("python-lib", ""),
        ("python-web-api", ""),
        ("python-web-app", 'frontend = "angular"'),
    ],
)
def test_other_archetypes_render_no_node_lib_action(
    tmp_path: Path, archetype: str, extra: str
) -> None:
    rendered = _rendered(_cell_root(tmp_path, archetype, extra))
    assert "start-ci-run" not in rendered[SETUP_ACTION]
    assert "registry-url" not in rendered[SETUP_ACTION]
    if archetype != "python-web-app":
        assert "npm" not in _updates_of(rendered[".github/dependabot.yml"])


def test_node_lib_dependabot_adds_npm_beside_uv(
    tmp_path: Path,
) -> None:
    updates = YamlUtils.load(
        _rendered(_root(tmp_path, "node-lib"))[".github/dependabot.yml"]
    )["updates"]
    by_ecosystem = {u["package-ecosystem"]: u for u in updates}
    assert set(by_ecosystem) == {"github-actions", "uv", "npm"}
    npm = by_ecosystem["npm"]
    assert npm["directory"] == "/"
    assert npm["schedule"] == {"interval": "weekly"}
    assert list(npm["groups"]) == ["npm"]


# node-lib's action.yml as first rendered, minus the header line, with each pin
# replaced by PIN.
NODE_LIB_ACTION_BEFORE = """name: Setup
description: Install pnpm and Node, uv when the repository commits a uv.lock, optionally start an Nx Cloud CI run, and install dependencies. Run after actions/checkout.

inputs:
  start-ci-run:
    description: Arguments for `nx start-ci-run`; when empty, no Nx Cloud CI run is started
    required: false
    default: ''
  registry-url:
    description: npm registry URL passed to actions/setup-node (needed for npm OIDC publishing)
    required: false
    default: ''
  github-token:
    description: Token for setup-task's release lookup, to avoid rate limits.
    required: true

runs:
  using: composite
  steps:
    - uses: pnpm/action-setup@PIN
      with:
        run_install: false

    - if: ${{ inputs.start-ci-run != '' }}
      env:
        START_CI_RUN: ${{ inputs.start-ci-run }}
      # xargs splits the input into arguments and honours its quotes.
      run: printf '%s\\n' "$START_CI_RUN" | xargs pnpm dlx nx start-ci-run
      shell: bash

    - uses: actions/setup-node@PIN
      with:
        node-version-file: .nvmrc
        cache: pnpm
        registry-url: ${{ inputs.registry-url }}

    - run: pnpm install --frozen-lockfile
      shell: bash

    - if: ${{ hashFiles('**/uv.lock', '!**/node_modules/**') != '' }}
      uses: astral-sh/setup-uv@PIN
      with:
        version: 0.13.1
        enable-cache: true
        ignore-nothing-to-cache: true
        cache-dependency-glob: '**/uv.lock'

    - uses: arduino/setup-task@PIN
      with:
        version: 3.x
        repo-token: ${{ inputs.github-token }}
"""


def _web_app_action(tmp_path: Path) -> dict[str, object]:
    root = _web_root(tmp_path, "python-web-app", extra='frontend = "angular"')
    return YamlUtils.load(_rendered(root)[SETUP_ACTION])


def _step(action: dict[str, object], needle: str) -> dict[str, object]:
    steps = action["runs"]["steps"]  # type: ignore[index]
    return next(s for s in steps if needle in s.get("uses", ""))


def test_pnpm_setup_does_not_install(tmp_path: Path) -> None:
    for action in (
        _node_lib_action(tmp_path / "lib"),
        _web_app_action(tmp_path / "app"),
    ):
        assert _step(action, "pnpm/action-setup")["with"] == {"run_install": False}


def test_setup_node_reads_nvmrc_and_caches_pnpm(tmp_path: Path) -> None:
    lib = _step(_node_lib_action(tmp_path / "lib"), "actions/setup-node")["with"]
    app = _step(_web_app_action(tmp_path / "app"), "actions/setup-node")["with"]
    assert lib == {
        "node-version-file": ".nvmrc",
        "cache": "pnpm",
        "registry-url": "${{ inputs.registry-url }}",
    }
    assert app == {"node-version-file": ".nvmrc", "cache": "pnpm"}


@pytest.mark.parametrize(
    "archetype", ["python-app", "python-tool", "python-lib", "python-web-api"]
)
def test_other_python_archetypes_render_no_pnpm_step(
    tmp_path: Path, archetype: str
) -> None:
    action = _rendered(_cell_root(tmp_path, archetype, ""))[SETUP_ACTION]
    assert "pnpm" not in action
    assert "setup-node" not in action


def test_node_lib_action_is_byte_identical_to_before(tmp_path: Path) -> None:
    text = _rendered(_root(tmp_path, "node-lib"))[SETUP_ACTION].split("\n", 1)[1]
    pinned = re.sub(r"(uses: [\w./-]+)@[0-9a-f]{40} # \S+", r"\1@PIN", text)
    assert pinned == NODE_LIB_ACTION_BEFORE


def test_each_step_is_written_once() -> None:
    template = (
        Path(__file__).resolve().parents[3]
        / "src/rn_forge/kiln/modules/cicd/templates/action.yml.j2"
    )
    text = template.read_text(encoding="utf-8")
    assert text.count('pins["pnpm-setup"].uses') == 1
    assert text.count('pins["setup-node"].uses') == 1


def test_both_node_cells_carry_the_same_npm_block(tmp_path: Path) -> None:
    def updates(root: Path) -> dict[str, object]:
        parsed = YamlUtils.load(_rendered(root)[".github/dependabot.yml"])
        return {u["package-ecosystem"]: u for u in parsed["updates"]}

    lib = updates(_root(tmp_path / "lib", "node-lib"))
    app = updates(
        _web_root(tmp_path / "app", "python-web-app", extra='frontend = "angular"')
    )
    assert "npm" in lib
    assert app["npm"] == lib["npm"]


@pytest.mark.parametrize("archetype", ["python-app", "python-tool", "python-lib"])
def test_python_cells_have_no_npm_block(tmp_path: Path, archetype: str) -> None:
    assert "npm" not in _updates_of(_rendered(_root(tmp_path, archetype))[DEPENDABOT])


def test_web_app_sonar_reads_the_web_lcov_report(tmp_path: Path) -> None:
    properties = _rendered(
        _web_root(tmp_path, "python-web-app", extra='frontend = "angular"')
    )["sonar-project.properties"].splitlines()
    assert "sonar.javascript.lcov.reportPaths=coverage/web/lcov.info" in properties
    assert (
        "sonar.exclusions=**/node_modules/**,**/dist/**,**/*.spec.ts,"
        "apps/web/src/app/api/**"
    ) in properties


def test_sonar_report_path_keeps_the_project_name(tmp_path: Path) -> None:
    properties = _rendered(
        _web_root(
            tmp_path,
            "python-web-app",
            extra='frontend = "angular"\nweb_dir = "apps/frontend"',
        )
    )["sonar-project.properties"]
    assert "sonar.javascript.lcov.reportPaths=coverage/web/lcov.info" in properties


@pytest.mark.parametrize("archetype", ["python-web-api", "python-tool", "node-lib"])
def test_other_archetypes_name_no_web_report(tmp_path: Path, archetype: str) -> None:
    root = (
        _web_root(tmp_path, archetype)
        if archetype == "python-web-api"
        else _root(tmp_path, archetype)
    )
    properties = _rendered(root)["sonar-project.properties"]
    assert "sonar.javascript.lcov.reportPaths" not in properties
    assert "**/dist/**,**/*.spec.ts" not in properties


def test_gate_comment_is_one_text_for_every_archetype(
    tmp_path: Path,
) -> None:
    for archetype in ("node-lib", "python-app", "python-lib"):
        ci = _rendered(_root(tmp_path / archetype, archetype))[
            ".github/workflows/ci.yml"
        ]
        assert "a\n  # release or deploy on a pull request" in ci, archetype


def test_setup_uv_pin_is_v10_3_0(tmp_path: Path) -> None:
    sha = "1c37ad07a6a961277cf70c0d37d6f313000f5884"
    assert UPSTREAM_PINS["setup-uv"] == (sha, "v10.3.0")
    uses = f"astral-sh/setup-uv@{sha} # v10.3.0"
    cases = [(a, _root(tmp_path / a, a)) for a in (*ARCHETYPES, "node-lib")]
    cases += [
        ("python-web-api", _web_root(tmp_path / "api", "python-web-api")),
        (
            "python-web-app",
            _web_root(tmp_path / "app", "python-web-app", extra='frontend = "angular"'),
        ),
    ]
    for archetype, root in cases:
        action = _rendered(root)[".github/actions/setup/action.yml"]
        assert uses in action, archetype


def test_setup_uv_ignores_nothing_to_cache(tmp_path: Path) -> None:
    cases = [(a, _root(tmp_path / a, a)) for a in (*ARCHETYPES, "node-lib")]
    cases += [
        ("python-web-api", _web_root(tmp_path / "api", "python-web-api")),
        (
            "python-web-app",
            _web_root(tmp_path / "app", "python-web-app", extra='frontend = "angular"'),
        ),
    ]
    for archetype, root in cases:
        action = YamlUtils.load(_rendered(root)[".github/actions/setup/action.yml"])
        steps = [
            step
            for step in action["runs"]["steps"]
            if str(step.get("uses", "")).startswith("astral-sh/setup-uv")
        ]
        assert steps, archetype
        for step in steps:
            assert step["with"]["ignore-nothing-to-cache"] is True, archetype
            assert step["with"]["enable-cache"] is True, archetype


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_umbrella_needs_a_release(tmp_path: Path, archetype: str) -> None:
    root = _root(tmp_path, archetype, release="none")
    config = root / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8") + "\n[ci.checks]\numbrella-release = true\n",
        encoding="utf-8",
    )
    with pytest.raises(
        AppException,
        match=r"cicd\.render: ci\.checks\.umbrella-release needs \[ci\] release other than none",
    ):
        _rendered(root)
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'release = "none"', 'release = "tag-exists"'
        ),
        encoding="utf-8",
    )
    assert ".github/workflows/ci.yml" in _rendered(root)
