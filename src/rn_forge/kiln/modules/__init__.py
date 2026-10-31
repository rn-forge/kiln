"""kiln's modules: each a template set plus the checks for what it generates.

Every module is `artifacts()` + `checks()` and nothing else, which is what
keeps kiln from becoming a god-kit (kiln ADR-0001). F4.1 ships the `checks()`
half; F4.2 adds the contract and F4.3 the artifacts.
"""
