"""The one function this golden repo exists to have.

A golden repo is a *complete, runnable* repo whose every non-product file is
exactly what kiln must render (kiln ADR-0005). The product is deliberately
trivial — one function, one command and their tests — so that `task validate`
proves the scaffolding and nothing else.

It is not, however, dependency-free. A `python-tool` repo is built on all three
rn-forge python libraries (kiln ADR-0005): `rn-forge-commons` for
runtime-neutral mechanisms, `rn-forge-cli` for the command-line shape, and
`rn-forge-tooling` for the machinery of a program that renders templates and
owns files in someone else's repo. So the one function uses commons and tooling
for real, and `main.py` takes its whole command line from cli, rather than
declaring dependencies nothing exercises.
"""

from __future__ import annotations

from rn_forge.commons import DictUtils
from rn_forge.tooling import TemplateEngine

DEFAULTS: dict[str, str] = {"greeting": "Hello", "punctuation": "!"}

TEMPLATE = "greeting.txt.j2"
"""The template rendered by :func:`greet`, loaded from this package."""


def greet(name: str, **overrides: str) -> str:
    """Return a greeting for ``name``, with ``DEFAULTS`` overridable per call."""
    settings = DictUtils.merge(dict(DEFAULTS), overrides)
    engine = TemplateEngine(package=__name__)
    return engine.render(TEMPLATE, {"name": name, **settings}).rstrip("\n")
