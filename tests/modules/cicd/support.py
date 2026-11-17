"""Helpers shared by the workflow tests."""

from __future__ import annotations
from pathlib import Path
from rn_forge.commons.fs.documents import YamlUtils
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.cicd import CICD
from rn_forge.kiln.modules.tasks import TASKS
from tests.conftest import module_findings, LIB_PACKAGES, write_config
from tests.modules.cicd import workflows


ARCHETYPES = ("python-app", "python-tool", "python-lib")


CI_KEYS = (
    ".github/actions/setup/action.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/_integration.yml",
    ".github/workflows/_smoke.yml",
    ".github/workflows/_sonar.yml",
    ".github/workflows/_release.yml",
    ".github/workflows/_verify-release.yml",
    ".github/workflows/_docs.yml",
    ".github/dependabot.yml",
    "sonar-project.properties",
)


WORKFLOWS = (".github/workflows/ci.yml",)


def _root(
    tmp_path: Path,
    archetype: str = "python-tool",
    profile: str = "mkdocs",
    sonar: bool = True,
    release: str | None = None,
    provider: str = "github",
) -> Path:
    return write_config(
        tmp_path,
        archetype,
        name="demo",
        docs=profile,
        sonar=sonar,
        release=release or ("nx-dispatch" if archetype == "node-lib" else "tag-exists"),
        provider=provider,
        packages=LIB_PACKAGES if archetype == "python-lib" else None,
    )


def _rendered(root: Path) -> dict[str, str]:
    return {a.path: a.content for a in CICD.artifacts(KilnConfig.load(root), root)}


def _codes(root: Path) -> list[str]:
    return sorted(f.code for f in module_findings("cicd", KilnConfig.load(root), root))


WEB_CONFIG = """
schema_version = 1

[repository]
name = "demo"
owner = "rn-forge"
archetype = "{archetype}"

[docs]
profile = "none"

[archetype."{archetype}"]
backend = "fastapi"
{extra}
"""


def _web_root(tmp_path: Path, archetype: str, extra: str = "") -> Path:
    config = tmp_path / ".rn-forge" / "kiln" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        WEB_CONFIG.format(archetype=archetype, extra=extra), encoding="utf-8"
    )
    return tmp_path


SETUP_ACTION = "./.github/actions/setup"


def _ci_jobs(root: Path) -> dict[str, dict[str, object]]:
    return workflows.jobs(_rendered(root))


def _release_steps(root: Path) -> list[dict[str, object]]:
    return _ci_jobs(root)["release"]["steps"]  # type: ignore[return-value]


def _release_roots(tmp_path: Path) -> list[Path]:
    return [
        _root(tmp_path / archetype, archetype)
        for archetype in ARCHETYPES
        if archetype != "python-lib"
    ]


def _step_index(steps: list[dict[str, object]], name: str) -> int:
    return next(i for i, step in enumerate(steps) if step.get("name") == name)


UPSTREAM_PINS = {
    "setup-uv": ("1c37ad07a6a961277cf70c0d37d6f313000f5884", "v10.3.0"),
    "sonarqube-scan": ("d209202bc7d53ff1cc128f7f907dac145c9d6ae9", "v8.3.0"),
    "deploy-pages": ("368f82528645a54fb793d4d04e342629a3f51346", "v5.0.1"),
    "upload-artifact": ("cf430e030ddbb5b0abf93d22962f4752f3646cd9", "v7.0.2"),
    "download-artifact": ("9000827ccba6bdab643e8b6fd33ac0654aef8333", "v8.0.2"),
    "pnpm-setup": ("0ebf47130e4866e96fce0953f49152a61190b271", "v6.0.9"),
    "setup-node": ("820762786026740c76f36085b0efc47a31fe5020", "v7.0.0"),
}


KILN_DOCTOR_FULL_EXPRESSION = (
    "${{ ((github.event_name == 'push' && github.ref_name == "
    "github.event.repository.default_branch) || "
    "github.event_name == 'workflow_dispatch') && '1' || '' }}"
)


RELEASE_PERMISSIONS = {
    "contents": "write",
    "id-token": "write",
    "attestations": "write",
}


def _lib_jobs(tmp_path: Path, **kwargs: object) -> dict[str, dict[str, object]]:
    return _ci_jobs(_root(tmp_path, "python-lib", **kwargs))  # type: ignore[arg-type]


def _ci_tasks_text_of(root: Path) -> dict[str, object]:
    from rn_forge.kiln.modules.tasks import TASKS

    rendered = {a.path: a.content for a in TASKS.artifacts(KilnConfig.load(root), root)}
    return YamlUtils.load(rendered["tasks/ci.yml"])


def _with_ci(root: Path, extra: str) -> Path:
    """Add `extra` to the `[ci]` section of `root`'s config."""
    config = root / ".rn-forge" / "kiln" / "config.toml"
    text = config.read_text(encoding="utf-8")
    if "[ci]" not in text:
        text += "\n[ci]\n"
    ci_end = text.index("[ci]")
    section_end = text.find("\n[", ci_end + 1)
    if section_end == -1:
        text += extra
    else:
        text = text[:section_end] + extra + text[section_end:]
    config.write_text(text, encoding="utf-8")
    return root


def _action(root: Path) -> str:
    return _rendered(root)[".github/actions/setup/action.yml"]


HOOKS = '\n[ci.hooks]\nsetup = ["./.github/actions/a", "./.github/actions/b"]\n'


CALL = "./.github/workflows/golden-render.yml"


SECURITY_CELLS = [
    ("python-app", ""),
    ("python-tool", ""),
    ("python-lib", ""),
    ("python-web-api", ""),
    ("python-web-app", 'frontend = "angular"'),
]


def _cell_root(tmp_path: Path, archetype: str, extra: str) -> Path:
    if archetype.startswith("python-web"):
        return _web_root(tmp_path, archetype, extra=extra)
    return _root(tmp_path, archetype)


DEPENDABOT = ".github/dependabot.yml"


def _dependabot(root: Path) -> dict[str, object]:
    return YamlUtils.load(_rendered(root)[DEPENDABOT])


def _hook_entry(root: Path) -> dict[str, object]:
    """The `github-actions` entry for hook directories (no `directory`)."""
    (entry,) = [
        u
        for u in _dependabot(root)["updates"]  # type: ignore[attr-defined]
        if u["package-ecosystem"] == "github-actions" and "directories" in u
    ]
    return entry


def _updates(root: Path) -> dict[str, dict[str, object]]:
    return {u["package-ecosystem"]: u for u in _dependabot(root)["updates"]}  # type: ignore[attr-defined]


DOCS_HOOKS = '\n[ci.hooks]\ndocs = ["./.github/actions/a", "./.github/actions/b"]\n'


def _job_steps(root: Path, workflow: str, job: str) -> list[dict[str, object]]:
    return workflows.jobs(_rendered(root))[job]["steps"]


def _pypi_root(tmp_path: Path, archetype: str = "python-lib", **kwargs: object) -> Path:
    return _root(tmp_path, archetype, release="pypi", **kwargs)  # type: ignore[arg-type]


def _lib_root(path: Path) -> Path:
    return _root(path, "python-lib")


SETUP_ACTION = ".github/actions/setup/action.yml"


NGKIT = Path(__file__).resolve().parents[4] / "ngkit"


NGKIT_REF = "0c2cd2a"


CI_YML = ".github/workflows/ci.yml"


def _node_lib_ci(tmp_path: Path) -> dict[str, object]:
    files = _rendered(_root(tmp_path, "node-lib"))
    return {**YamlUtils.load(files[CI_YML]), "jobs": workflows.jobs(files)}


def _sonar_root(tmp_path: Path, archetype: str, extra: str = "") -> Path:
    if archetype == "python-web-app":
        root = _web_root(tmp_path, archetype, extra='frontend = "angular"')
    elif archetype == "python-web-api":
        root = _web_root(tmp_path, archetype)
    else:
        root = _root(tmp_path, archetype)
    return _with_ci(root, extra) if extra else root
