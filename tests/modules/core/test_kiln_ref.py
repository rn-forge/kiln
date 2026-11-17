"""`[kiln] ref` is a tag or a commit SHA; `track` names the branch a SHA came from."""

from __future__ import annotations

from pathlib import Path

import pytest
from rn_forge.commons.exceptions import AppException
from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.core import kiln_ref
from tests.conftest import write_config


def _load(tmp_path: Path, body: str) -> KilnConfig:
    write_config(tmp_path, tail=f"\n[kiln]\n{body}\n")
    return KilnConfig.load(tmp_path)


def test_s18_14_1_1_config_accepts_a_tag_or_a_sha(
    tmp_path: Path, kiln_remote_sha: str
) -> None:
    assert _load(tmp_path, 'ref = "v0.0.1"').kiln_pin is not None
    assert _load(tmp_path, f'ref = "{kiln_remote_sha}"').kiln_pin is not None
    pin = _load(tmp_path, f'ref = "{kiln_remote_sha}"\ntrack = "feature/v1"').kiln_pin
    assert pin is not None
    assert pin.track == "feature/v1"


def test_s18_14_1_2_a_branch_ref_is_refused_with_the_pin_command(
    tmp_path: Path,
) -> None:
    with pytest.raises(AppException) as refused:
        _load(tmp_path, 'ref = "feature/v1"')
    assert "task kiln:pin -- feature/v1" in str(refused.value)


def test_s18_14_1_3_track_needs_a_sha(tmp_path: Path) -> None:
    with pytest.raises(AppException) as refused:
        _load(tmp_path, 'ref = "v0.0.1"\ntrack = "feature/v1"')
    assert "kiln.track" in str(refused.value)


def test_s18_14_1_4_resolve_reads_the_remote(kiln_remote_sha: str) -> None:
    assert kiln_ref.resolve("feature/v1") == kiln_remote_sha
    assert kiln_ref.resolve("v0.0.1") == kiln_remote_sha
    with pytest.raises(AppException, match="kiln.ref-unknown"):
        kiln_ref.resolve("nope")
