"""The one function this golden repo exists to have.

A golden repo is a *complete, runnable* repo whose every non-product file is
exactly what kiln must render (kiln ADR-0006). The product is deliberately
trivial — one function and one test — so that `task validate` proves the
scaffolding and nothing else.

It is not, however, dependency-free. Every rn-forge repo is built on
`rn-forge-commons`, and a `python-cli` repo on `rn-forge-tooling` as well
(kiln ADR-0009): the boilerplate a repo does not write is the boilerplate it
takes from the component libraries. So the one function uses commons for real,
rather than declaring a dependency it never exercises.
"""

from __future__ import annotations

from rn_forge.commons import DictUtils

DEFAULTS: dict[str, str] = {"greeting": "Hello", "punctuation": "!"}


def greet(name: str, **overrides: str) -> str:
    """Return a greeting for ``name``, with ``DEFAULTS`` overridable per call."""
    settings = DictUtils.merge(dict(DEFAULTS), overrides)
    return f"{settings['greeting']}, {name}{settings['punctuation']}"


def main() -> None:
    """The console-script entry point."""
    print(greet("world"))
