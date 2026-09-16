"""S4.2.2 — the config manager."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from rn_forge.commons.exceptions import AppException
from rn_forge.commons.fs.documents import ConfigFormat, DocumentUtils
from rn_forge.commons.lang.collections import DictUtils
from rn_forge.commons.lang.models import ModelValidationError

from rn_forge.kiln import archetypes
from rn_forge.kiln.modules.core.config import manager as manager_module
from rn_forge.kiln.modules.core.config.manager import ConfigManager
from rn_forge.kiln.modules.core.config.sources import Source

FLAGS = {"repository": {"name": "demo", "archetype": "python-app"}}


def write_config(root: Path, text: str) -> Path:
    path = root / ".rn-forge" / "kiln" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return root


def write_layer(path: Path, document: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DocumentUtils.dumps(document, ConfigFormat.TOML), encoding="utf-8")
    return path


def commit(root: Path, resolution) -> None:
    """Commit a resolution the way `kiln new` does: config.toml and state provenance."""
    write_config(
        root, DocumentUtils.dumps(resolution.config.to_document(), ConfigFormat.TOML)
    )
    state = root / ".rn-forge" / "kiln" / "state.json"
    state.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "metadata": {"config_provenance": resolution.provenance_metadata()},
                "entries": {},
            }
        ),
        encoding="utf-8",
    )


def test_s4_2_2_an_invalid_config_names_every_failing_key_by_dotted_path(
    tmp_path: Path,
) -> None:
    root = write_config(
        tmp_path,
        """
schema_version = 1

[repository]
archetype = "python-app"
archtype = "python-lib"

[docs]
profile = 3
""",
    )
    with pytest.raises(ModelValidationError) as caught:
        ConfigManager().load(root)
    kinds = {error.path: error.kind for error in caught.value.errors}
    assert kinds["repository.name"] == "missing"
    assert kinds["repository.archtype"] == "extra_forbidden"
    assert kinds["docs.profile"] == "literal_error"
    assert "docs.profile" in caught.value.message


def test_s4_2_2_a_layer_that_sets_a_list_replaces_it_while_tables_and_scalars_merge(
    tmp_path: Path,
) -> None:
    layer = write_layer(
        tmp_path / "profile" / "config.toml",
        {
            "docs": {"profile": "mkdocs", "site_dir": "public"},
            "tasks": {
                "includes": [
                    {"namespace": "a", "taskfile": "tasks/a.yml"},
                    {"namespace": "b", "taskfile": "tasks/b.yml"},
                ],
                "extra_refs": {"lint": ["a:lint"]},
            },
        },
    )
    flags = {
        **FLAGS,
        "docs": {"site_dir": "site"},
        "tasks": {"includes": [{"namespace": "c", "taskfile": "tasks/c.yml"}]},
    }
    resolution = ConfigManager().resolve(flags=flags, source=Source(str(layer)))
    document = resolution.config.to_document()

    assert document["tasks"]["includes"] == [
        {"namespace": "c", "taskfile": "tasks/c.yml"}
    ]
    assert document["tasks"]["extra_refs"] == {"lint": ["a:lint"]}
    assert document["docs"] == {
        "profile": "mkdocs",
        "site_dir": "site",
        "external_url": "",
    }
    layers = {path: entry.layer for path, entry in resolution.provenance.items()}
    assert layers["tasks.includes"] == "flags"
    assert layers["docs.profile"] == "source"
    assert layers["docs.site_dir"] == "flags"
    assert layers["ci.sonar"] == "defaults"


def test_s4_2_2_a_config_from_a_newer_schema_is_refused_naming_the_version_it_needs(
    tmp_path: Path,
) -> None:
    root = write_config(
        tmp_path,
        'schema_version = 2\n[repository]\nname = "x"\narchetype = "python-app"\n',
    )
    with pytest.raises(AppException) as caught:
        ConfigManager().load(root)
    assert "schema_version 2 needs a newer kiln" in caught.value.message


def test_s4_2_2_a_section_for_a_module_the_archetype_does_not_enable_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    without_docs = archetypes.load("python-app").model_copy(
        update={"modules": ["core", "python", "tasks", "cicd", "instructions"]}
    )
    monkeypatch.setattr(archetypes, "load", lambda name: without_docs)
    base = '\nschema_version = 1\n[repository]\nname = "x"\narchetype = "python-app"\n'

    assert ConfigManager().load(write_config(tmp_path, base)).docs_profile == "none"
    with pytest.raises(AppException, match=r"\[docs\] belongs to module 'docs'"):
        ConfigManager().load(
            write_config(tmp_path, base + '[docs]\nprofile = "none"\n')
        )


def test_s4_2_2_a_path_source_resolves_and_is_recorded(tmp_path: Path) -> None:
    write_layer(tmp_path / "profile" / "config.toml", {"ci": {"sonar": False}})
    resolution = ConfigManager().resolve(
        flags=FLAGS, source=Source.parse("profile"), base=tmp_path
    )
    document = resolution.config.to_document()
    assert document["ci"]["sonar"] is False
    assert document["source"] == {"location": "profile"}


def test_s4_2_2_a_git_source_records_location_ref_and_resolved_commit(
    tmp_path: Path,
) -> None:
    work = tmp_path / "work"
    write_layer(work / "config.toml", {"docs": {"profile": "mkdocs"}})
    git = ["git", "-c", "user.name=kiln", "-c", "user.email=kiln@example.com"]
    subprocess.run([*git, "init", "--quiet", "-b", "main", str(work)], check=True)
    subprocess.run([*git, "-C", str(work), "add", "."], check=True)
    subprocess.run(
        [*git, "-C", str(work), "commit", "--quiet", "-m", "profile"], check=True
    )
    commit_sha = subprocess.run(
        ["git", "-C", str(work), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    bare = tmp_path / "profile.git"
    subprocess.run(
        ["git", "clone", "--quiet", "--bare", str(work), str(bare)], check=True
    )

    location = f"git+file://{bare}"
    resolution = ConfigManager().resolve(
        flags=FLAGS, source=Source.parse(f"{location}@main")
    )

    document = resolution.config.to_document()
    assert document["docs"]["profile"] == "mkdocs"
    assert document["source"] == {
        "location": location,
        "ref": "main",
        "commit": commit_sha,
    }


def test_s4_2_2_re_resolution_keeps_and_lists_a_repo_override(tmp_path: Path) -> None:
    layer = tmp_path / "profile" / "config.toml"
    write_layer(
        layer,
        {"docs": {"profile": "mkdocs", "site_dir": "site"}, "ci": {"sonar": False}},
    )
    repo = tmp_path / "repo"
    commit(
        repo, ConfigManager().resolve(flags=FLAGS, source=Source(str(layer)), base=repo)
    )

    config = repo / ".rn-forge" / "kiln" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace("sonar = false", "sonar = true"),
        encoding="utf-8",
    )
    write_layer(
        layer,
        {"docs": {"profile": "mkdocs", "site_dir": "public"}, "ci": {"sonar": False}},
    )

    resolution = ConfigManager().reresolve(repo)
    document = resolution.config.to_document()
    assert document["ci"]["sonar"] is True
    assert document["docs"]["site_dir"] == "public"
    assert document["repository"]["name"] == "demo"
    assert resolution.overrides == ("ci.sonar",)
    assert resolution.provenance["ci.sonar"].layer == "repo"


def test_s4_2_2_the_manager_merges_through_dictutils_merge_layers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    original = DictUtils.merge_layers

    def spy(*layers, **kwargs):
        calls.append(tuple(name for name, _ in layers))
        return original(*layers, **kwargs)

    monkeypatch.setattr(manager_module.DictUtils, "merge_layers", spy)
    resolution = ConfigManager().resolve(flags=FLAGS)
    assert calls == [("defaults", "flags")]
    assert resolution.config.name == "demo"
