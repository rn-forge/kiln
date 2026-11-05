"""Tests for `rn_forge.kiln.devops.licenses`."""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pytest

from rn_forge.kiln.devops import cli, licenses

PIP = (
    '[{"Name":"a","Version":"1","License":"MIT License"},'
    '{"Name":"b","Version":"2","License":"GNU General Public License v3 (GPLv3)"}]'
)
CLEAN = '[{"Name":"a","Version":"1","License":"MIT License"}]'
GPL3 = "GNU General Public License v3 (GPLv3)"


def _pip(name: str, licence: str) -> str:
    return f'[{{"Name":"{name}","Version":"1","License":"{licence}"}}]'


def test_s15_2_1_1_pip_licenses_json() -> None:
    assert licenses.run(PIP, "pip-licenses", ["GPL-*"], []) == [f"b 2 {GPL3}"]


@pytest.mark.parametrize(
    ("value", "identifier"),
    [
        ("GNU General Public License (GPL)", "GPL"),
        ("GNU General Public License v2 (GPLv2)", "GPL-2.0"),
        ("GNU General Public License v2 or later (GPLv2+)", "GPL-2.0-or-later"),
        ("GNU General Public License v3 (GPLv3)", "GPL-3.0"),
        ("GNU General Public License v3 or later (GPLv3+)", "GPL-3.0-or-later"),
        ("GNU Affero General Public License v3", "AGPL-3.0"),
        (
            "GNU Affero General Public License v3 or later (AGPLv3+)",
            "AGPL-3.0-or-later",
        ),
        ("GNU Lesser General Public License v3 (LGPLv3)", "LGPL-3.0"),
        ("GNU Library or Lesser General Public License (LGPL)", "LGPL"),
        ("GPLv3", "GPL-3.0"),
        ("GPL v3", "GPL-3.0"),
        ("GPL-3", "GPL-3.0"),
        ("GPLv2+", "GPL-2.0-or-later"),
        ("AGPLv3", "AGPL-3.0"),
        ("GPL", "GPL"),
        ("GPL-3.0-only", "GPL-3.0-only"),
        ("MIT License", "MIT License"),
        ("UNKNOWN", "UNKNOWN"),
        ("Unknown", "UNKNOWN"),
        ("", "UNKNOWN"),
    ],
)
def test_s15_2_1_1b_normalise(value: str, identifier: str) -> None:
    assert licenses.normalise(value) == identifier


def test_s15_2_1_2_pnpm_json() -> None:
    text = (
        '{"MIT":[{"name":"a","versions":["1.0.0"]}],'
        '"Unknown":[{"name":"c","versions":["3.0.0"]}]}'
    )
    assert licenses.run(text, "pnpm", ["UNKNOWN"], []) == ["c 3.0.0 Unknown"]


def test_s15_2_1_2b_pnpm_one_line_per_version() -> None:
    text = '{"GPL-3.0":[{"name":"d","versions":["1.0.0","2.0.0"]}]}'
    assert licenses.run(text, "pnpm", ["GPL-*"], []) == [
        "d 1.0.0 GPL-3.0",
        "d 2.0.0 GPL-3.0",
    ]


def _hit(licence: str, deny: list[str]) -> bool:
    return bool(licenses.run(_pip("x", licence), "pip-licenses", deny, []))


def test_s15_2_1_3_matching_is_case_insensitive_and_whole_string() -> None:
    assert not _hit("LGPL-3.0", ["GPL-*"])
    assert not _hit("GNU Lesser General Public License v3 (LGPLv3)", ["GPL-*"])
    assert _hit("gpl-2.0-only", ["GPL-*"])
    assert _hit("GNU General Public License v2 (GPLv2)", ["GPL-*"])
    assert not _hit("GPL", ["GPL-*"])
    assert _hit("GPL", licenses.DEFAULT_DENY)


def test_s15_2_1_4_multiple_licences() -> None:
    value = f"MIT License; {GPL3}"
    assert licenses.run(_pip("m", value), "pip-licenses", ["GPL-*"], []) == [
        f"m 1 {value}"
    ]
    assert not _hit("MIT License; BSD License", ["GPL-*"])


def test_s15_2_1_5_ignore() -> None:
    assert licenses.run(PIP, "pip-licenses", ["GPL-*"], ["b"]) == []


def test_s15_2_1_6_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["licenses", "--format", "pip-licenses", "--deny", "GPL-*"]
    monkeypatch.setattr("sys.stdin", io.StringIO(PIP))
    assert cli.main(argv) == 1
    assert capsys.readouterr().err == f"b 2 {GPL3}\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(CLEAN))
    assert cli.main(argv) == 0
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert cli.main(argv) == 2
    assert capsys.readouterr().err.startswith("kiln-devops: ")


def _dist(root: Path, name: str, *fields: str) -> None:
    info = root / f"{name}-1.0.dist-info"
    info.mkdir()
    lines = ["Metadata-Version: 2.1", f"Name: {name}", "Version: 1.0", *fields]
    (info / "METADATA").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_s15_2_1_7_real_pip_licenses_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("piplicenses")
    _dist(
        tmp_path,
        "gplpkg",
        "Classifier: License :: OSI Approved :: " + GPL3,
    )
    _dist(tmp_path, "mitpkg", "License: MIT")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "piplicenses",
            "--format=json",
            "--packages",
            "gplpkg",
            "mitpkg",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert licenses.run(out, "pip-licenses", licenses.DEFAULT_DENY, []) == [
        f"gplpkg 1.0 {GPL3}"
    ]
