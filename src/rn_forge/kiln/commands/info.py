"""`kiln version` and `kiln prompt`."""

from __future__ import annotations

from importlib import metadata
from importlib.resources import files

from rn_forge.commons.exceptions import AppException
from rn_forge.commons.runtime.console import console

from rn_forge.kiln.commands import output

__all__ = ["prompt", "version"]


_DISTRIBUTION = "rn-forge-kiln"


def prompt(name: str = "", json: bool = False) -> None:
    """Print the shipped prompt `--name`, or list the prompts when it is not given.

    A prompt is a one-time procedure shipped in the distribution; printing one
    reads no repository and writes nothing.

    Raises:
        AppException: NAME is not a shipped prompt.
    """
    output.use_json(json)
    directory = files("rn_forge.kiln").joinpath("prompts")
    available = {
        entry.name.removesuffix(".md"): entry.read_text(encoding="utf-8")
        for entry in directory.iterdir()
        if entry.name.endswith(".md")
    }
    if not name:
        rows = [
            {"name": key, "summary": _prompt_summary(text)}
            for key, text in sorted(available.items())
        ]

        def listing() -> None:
            for row in rows:
                console.print(f"{row['name']}: {row['summary']}", markup=False)

        output.emit({"prompts": rows}, listing)
        return
    if name not in available:
        raise AppException(
            "no prompt named {}; available: {}", name, ", ".join(sorted(available))
        )
    output.emit(
        {"name": name, "text": available[name]},
        lambda: console.print(available[name], markup=False),
    )


def _prompt_summary(text: str) -> str:
    """The first paragraph after the title, on one line."""
    paragraphs = [part for part in text.split("\n\n") if part.strip()]
    return " ".join(paragraphs[1].split())


def version(json: bool = False) -> None:
    """Print kiln's installed distribution version."""
    installed = metadata.version(_DISTRIBUTION)
    output.use_json(json)
    output.emit({"version": installed}, lambda: console.print(installed))
