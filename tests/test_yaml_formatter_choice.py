"""S19.1.1: the YAML formatter is chosen, and the choice is recorded."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURE = ROOT / "docs/specs/epics/E19-formatting-standard/F19.1-yaml-formatter.md"
ADR = ROOT / "docs/adr/ADR-0021.md"
ADR_INDEX = ROOT / "docs/adr/index.md"
KEYS = [
    "Package",
    "Version floor",
    "Executable",
    "Check command",
    "Format command",
    "Config file",
    "Excluded files",
]


def _settled() -> tuple[dict[str, str], str]:
    text = FEATURE.read_text(encoding="utf-8")
    _, _, rest = text.partition("### Settled by S19.1.1")
    lines = rest.splitlines()
    rows: dict[str, str] = {}
    end = 0
    for i, line in enumerate(lines):
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells[0] not in ("Key", "--"):
                rows[cells[0]] = cells[1]
            end = i + 1
        elif rows:
            break
    return rows, "\n".join(lines[end:]).lstrip()


def test_s19_1_1_1_the_adr_is_accepted():
    adr = ADR.read_text(encoding="utf-8")
    assert re.search(r"^\*\*Status:\*\* accepted \(", adr, re.MULTILINE)
    assert "stays proposed" not in adr
    row = next(line for line in ADR_INDEX.read_text().splitlines() if "[0021]" in line)
    assert "(proposed)" not in row


def test_s19_1_1_2_the_settled_table_is_filled():
    rows, after = _settled()
    assert list(rows) == KEYS
    assert all(v and "(S19.1.1)" not in v for v in rows.values())
    assert after.startswith("```yaml")


def test_s19_1_1_3_the_adr_names_the_settled_tool():
    rows, _ = _settled()
    assert rows["Package"].strip("`") in ADR.read_text(encoding="utf-8")
    assert "pnpm-lock.yaml" in rows["Excluded files"]
