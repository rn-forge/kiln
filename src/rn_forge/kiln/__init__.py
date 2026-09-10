"""kiln — the rn-forge repository generator.

Phase B of the standardization plan deliberately ships no generator code. What
exists first is the canon (`docs/adr/`, `docs/reference/standard-repo.md`) and
the golden repos under `tests/fixtures/golden/`, which are reviewed as if they
were the finished product. The templates are then the golden output
parameterized, and the snapshot tests assert `render(golden config) == golden
bytes` (kiln ADR-0005).

Building the generator first would mean reviewing the standard through the
generator's diffs, which is how three of the four repos in the fleet ended up
with three different Taskfiles.
"""

from __future__ import annotations

__version__ = "0.1.0"
