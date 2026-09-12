"""The one function this golden repo exists to have.

A golden repo is a *complete, runnable* repo whose every non-product file is
exactly what kiln must render (kiln ADR-0005). The product is deliberately
trivial — one function, one command and their tests — so that `task validate`
proves the scaffolding and nothing else.

It is not, however, dependency-free. A `python-app` repo is built on two of the
three rn-forge python libraries (kiln ADR-0005): `rn-forge-commons` for
runtime-neutral mechanisms and `rn-forge-cli` for the process and command-line
shape. It stops there. `rn-forge-tooling` is the machinery of a program that
installs itself, owns files in someone else's repo or renders templates — a
`python-tool`, not a batch behind a command line — and taking it here would be
the decoration kiln ADR-0005 argues against.

So the one function uses commons for real, and `main.py` takes its whole
command line from cli.
"""

from __future__ import annotations

from rn_forge.commons import DictUtils

DEFAULTS: dict[str, str] = {"greeting": "Hello", "punctuation": "!"}


def greet(name: str, **overrides: str) -> str:
    """Return a greeting for ``name``, with ``DEFAULTS`` overridable per call."""
    settings = DictUtils.merge(dict(DEFAULTS), overrides)
    return f"{settings['greeting']}, {name}{settings['punctuation']}"
