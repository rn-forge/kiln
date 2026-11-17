"""The licences check in `lint`, and the frontend audit."""

from __future__ import annotations
from pathlib import Path
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.modules.core import cycle
from tests.modules.tasks.support import (
    AUDIT_REF,
    _node_lib_root,
    _node_root,
    _rendered_yaml,
    _root,
    _unmarked,
)


LICENSES_REF = {"task": "python:lint:licenses"}


LICENSES_DENY = " ".join(
    f"--deny '{d}'" for d in ("GPL", "GPL-*", "AGPL", "AGPL-*", "UNKNOWN")
)


def test_python_lint_licenses_task(tmp_path: Path) -> None:
    root = _root(tmp_path, "python-lib")
    cycle.apply(root, home=tmp_path / "home")
    root_tasks, python = _rendered_yaml(root)
    cmds = _unmarked(root_tasks["lint"]["cmds"])
    assert cmds[cmds.index(AUDIT_REF) + 1] == LICENSES_REF
    task = python["lint:licenses"]
    assert task["internal"] is True
    (cmd,) = task["cmds"]
    assert cmd == (
        "set -o pipefail; uv run pip-licenses --format=json "
        f"| {{{{.DEVOPS}}}} licenses --format pip-licenses {LICENSES_DENY} "
        "--ignore 'alpha' --ignore 'beta' --ignore 'demo' --ignore 'text-unidecode'"
    )


def test_policy_reaches_the_task(tmp_path: Path) -> None:
    root = _root(
        tmp_path,
        extra='\n[ci.checks]\nlicenses = { deny = ["GPL-*"], ignore = ["foo"] }\n',
    )
    cycle.apply(root, home=tmp_path / "home")
    _, python = _rendered_yaml(root)
    (cmd,) = python["lint:licenses"]["cmds"]
    assert cmd.endswith(
        "--format pip-licenses --deny 'GPL-*' --ignore 'foo' "
        "--ignore 'demo' --ignore 'text-unidecode'"
    )
    assert cmd.count("--deny") == 1


def test_python_licenses_off_removes_lint_task(tmp_path: Path) -> None:
    root = _root(tmp_path, extra="\n[ci.checks]\nlicenses = false\n")
    cycle.apply(root, home=tmp_path / "home")
    root_tasks, python = _rendered_yaml(root)
    assert "lint:licenses" not in python
    assert LICENSES_REF not in root_tasks["lint"]["cmds"]


NODE_LICENSES_REF = {"task": "node:lint:licenses"}


def _node_lib_rendered(root: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    root_tasks = YamlUtils.load((root / "Taskfile.yml").read_text(encoding="utf-8"))
    node = YamlUtils.load((root / "tasks/node.yml").read_text(encoding="utf-8"))
    return root_tasks["tasks"], node["tasks"]


def test_node_lint_licenses_task(tmp_path: Path) -> None:
    root = _node_lib_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    root_tasks, node = _node_lib_rendered(root)
    assert NODE_LICENSES_REF in root_tasks["lint"]["cmds"]
    task = node["lint:licenses"]
    assert task["internal"] is True
    (cmd,) = task["cmds"]
    assert cmd.startswith(
        "set -o pipefail; pnpm licenses list --json --prod "
        "| {{.DEVOPS}} licenses --format pnpm "
        f"{LICENSES_DENY}"
    )
    assert (
        "DEVOPS"
        in YamlUtils.load((root / "tasks/node.yml").read_text(encoding="utf-8"))["vars"]
    )


def test_node_licenses_off_removes_lint_task(tmp_path: Path) -> None:
    root = _root(tmp_path, "node-lib", extra="\n[ci.checks]\nlicenses = false\n")
    cycle.apply(root, home=tmp_path / "home")
    root_tasks, node = _node_lib_rendered(root)
    assert "lint:licenses" not in node
    assert NODE_LICENSES_REF not in root_tasks["lint"]["cmds"]
    assert "vars" not in YamlUtils.load(
        (root / "tasks/node.yml").read_text(encoding="utf-8")
    )


def test_node_lint_audit_task(tmp_path: Path) -> None:
    root = _node_lib_root(tmp_path)
    cycle.apply(root, home=tmp_path / "home")
    root_tasks, node = _node_lib_rendered(root)
    assert {"task": "node:lint:audit"} in root_tasks["lint"]["cmds"]
    task = node["lint:audit"]
    assert task["internal"] is True
    assert task["cmds"] == ["pnpm audit --prod --audit-level moderate"]
    assert "network" in task["desc"]


def test_python_archetypes_have_none(tmp_path: Path) -> None:
    for archetype in ("python-tool",):
        sub = tmp_path / archetype
        sub.mkdir()
        root = _root(sub, archetype)
        cycle.apply(root, home=sub / "home")
        for path in (root / "Taskfile.yml", *(root / "tasks").glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            assert "pnpm audit" not in text, path
            assert "node:lint:audit" not in text, path


WEB_LINT_TAIL = [
    {"task": "ci:lint:workflows"},
    {"task": "python:lint:audit"},
    {"task": "node:lint:audit"},
    {"task": "python:lint:licenses"},
    {"task": "node:lint:licenses"},
]


def test_web_app_audits_its_frontend(tmp_path: Path) -> None:
    lib = _node_lib_root(tmp_path / "lib")
    app = _node_root(tmp_path / "app")
    cycle.apply(lib, home=tmp_path / "home")
    cycle.apply(app, home=tmp_path / "home")
    root_tasks, node = _node_lib_rendered(app)
    audit = node["lint:audit"]
    assert audit["internal"] is True
    assert audit["cmds"] == ["pnpm audit --prod --audit-level moderate"]
    assert node["lint:licenses"]["internal"] is True
    app_vars = YamlUtils.load((app / "tasks/node.yml").read_text(encoding="utf-8"))[
        "vars"
    ]
    lib_vars = YamlUtils.load((lib / "tasks/node.yml").read_text(encoding="utf-8"))[
        "vars"
    ]
    assert set(app_vars) == {"DEVOPS"}
    assert app_vars == lib_vars
    cmds = _unmarked(root_tasks["lint"]["cmds"])
    assert cmds[-len(WEB_LINT_TAIL) :] == WEB_LINT_TAIL


def test_licences_off_drops_only_the_licences_task(tmp_path: Path) -> None:
    app = _node_root(tmp_path, "\n[ci.checks]\nlicenses = false\n")
    cycle.apply(app, home=tmp_path / "home")
    root_tasks, node = _node_lib_rendered(app)
    assert "lint:audit" in node
    assert "lint:licenses" not in node
    assert "vars" not in YamlUtils.load(
        (app / "tasks/node.yml").read_text(encoding="utf-8")
    )
    cmds = _unmarked(root_tasks["lint"]["cmds"])
    assert {"task": "node:lint:audit"} in cmds
    assert {"task": "python:lint:licenses"} not in cmds
    assert NODE_LICENSES_REF not in cmds
