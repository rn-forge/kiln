"""`release-evidence` — the newest shipped release carries its `security.md`."""

from __future__ import annotations

from pathlib import Path

from rn_forge.commons.findings import Finding, Severity

from rn_forge.kiln.config import KilnConfig
from rn_forge.kiln.modules.docs.work import load_work

__all__ = ["NAME", "check"]

NAME = "release-evidence"


def check(config: KilnConfig, root: Path) -> list[Finding]:
    """Fail when the newest shipped release has no `security.md`, for a repo recording release evidence."""
    if config.docs_profile != "mkdocs" or NAME not in config.ci_checks:
        return []
    shipped = [
        release
        for release in load_work(root / "docs").releases
        if release.page.get("Status") == "shipped"
    ]
    if not shipped:
        return []
    newest = max(shipped, key=lambda release: release.number)
    if (root / "docs" / "releases" / newest.dir / "security.md").exists():
        return []
    return [
        Finding(
            "docs.release-evidence-missing",
            Severity.ERROR,
            f"{newest.dir} is shipped but has no security.md; run task release:evidence -- <run-id> {newest.number}",
            path=f"docs/releases/{newest.dir}/index.md",
        )
    ]
