"""A generated `python-tool` repository installs itself from an archive."""

from __future__ import annotations

import os
import subprocess
import tarfile
from collections.abc import Callable
from pathlib import Path

from tests.conftest import requires

ROOT = Path(__file__).resolve().parents[2]


def _run(
    args: list[str], cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, cwd=cwd, env=env, capture_output=True, text=True, check=False
    )


@requires("uv")
def test_a_generated_tool_installs_itself_from_an_archive(
    rendered_copy: Callable[..., Path], tmp_path: Path
) -> None:
    root = rendered_copy("python-tool")
    cache = os.environ.get("UV_CACHE_DIR") or str(ROOT / ".uv-cache")
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env["UV_CACHE_DIR"] = str(Path(cache).resolve())
    env["RNF_HOME"] = str(tmp_path / "home")

    sync = _run(["uv", "sync"], root, env)
    assert sync.returncode == 0, sync.stderr

    tarball = tmp_path / "python-tool-0.1.0.tar.gz"
    with tarfile.open(tarball, "w:gz") as archive:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if any(
                part in {".venv", ".uv-cache", ".git", "__pycache__"}
                for part in relative.parts
            ):
                continue
            archive.add(path, arcname=f"python-tool-0.1.0/{relative}", recursive=False)

    tool = root / ".venv" / "bin" / "python-tool"
    install = _run(
        [str(tool), "install", "--archive", str(tarball), "--version", "0.1.0"],
        root,
        env,
    )
    assert install.returncode == 0, install.stdout + install.stderr

    link = tmp_path / "home" / "bin" / "python-tool"
    helped = _run([str(link), "--help"], root, env)
    assert helped.returncode == 0, helped.stdout + helped.stderr

    doctor = _run([str(tool), "doctor"], root, env)
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    assert "install.ok" in doctor.stdout
