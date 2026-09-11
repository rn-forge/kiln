# Phase C review: package boundaries and implementation

Reviewed 2026-09-09 against pykit commit `4624bfe` (`Phase-C`), its parent, and
the current local kiln standardization plan, revision 8. Scope: the extraction,
new commons/tooling APIs, tests, packaging, CI integration, and Phase C consumer
wiring. This is a review; no implementation changes were made.

## Decisions on the three observations

**Keep `rn-forge-tooling`; correct the boundary instead of broadening the
name.** Most of the extraction is defensible, but not every filesystem primitive
belongs there. `ManagedBlock` is a better tooling candidate than the generic
lock and symlink helpers. `Finding` can remain common diagnostics. `utils.py`
should not move wholesale.

These are architectural recommendations, not requirements imposed by a Python
standard. Packaging standards specify dependencies and extras; they do not
prescribe whether a package must be called `commons`, `tooling`, or `core`. The
useful test is the API's contract, consumers, dependencies, and reasons to
change—not whether its first caller happened to be a developer tool.

| Name | Verdict | Decisive reason |
| -- | -- | -- |
| `rn-forge-tooling` | **Recommended** | Fits developer CLI conventions, generation, installation orchestration, and documentation tooling. |
| `rn-forge-devtools` | Reasonable alternative | Makes the development audience explicit, but changes no architectural property. |
| `rn-forge-automation` | Too broad for the current contract | Suggests business jobs and production automation, which the present state/template APIs do not fully serve. |
| `rn-forge-cli` | Too narrow | Omits generation, state, installation, and docs APIs. |
| `rn-forge-core` / `foundation` | Reject | Creates another vaguely defined common package beside commons. |

### A1 — The workstation/runtime distinction is too absolute

Evidence: `tooling's package contract` says deployed packages must not depend on
tooling outside a `codegen` extra. That is a fleet policy, not a general
industry rule. Business systems have maintenance commands, scheduled imports,
local files, and report generation. Django explicitly supports application
management commands, including scripts run periodically; a terminal interface
does not make code exclusively development-time.
[Django documentation](https://docs.djangoproject.com/en/6.0/howto/custom-management-commands/)

**Change:** preserve the rule that framework runtime libraries do not import the
developer stack. Distinguish that from an application's separate operational CLI
choosing a tooling dependency. Do not describe Jinja, filesystem access, or
console support as inherently unsafe in deployed software.

| API | Recommended home | Assessment of the actual implementation |
| -- | -- | -- |
| `build_app`, Typer options, `AppConsole` | tooling | CLI presentation and application wiring; keep these out of commons' eager imports. |
| `generation` | tooling | Artifact ownership, drift classification, staging, and application of generated files form a coherent developer-tool capability. |
| `ManagedBlock` | **Move to tooling** | Encodes generator ownership through fenced source/config regions. Current examples are gitignore, instructions, and MkDocs. Pure string manipulation alone does not make the abstraction common runtime infrastructure. |
| `Finding`, `Severity`, `JsonValue` | commons | Useful for data import validation, configuration checks, and business diagnostics without a CLI dependency. Generalize wording: paths need not be repo-relative, and severity need not dictate process exit policy. Fix F3 below. |
| `DirectoryLock`, `atomic_symlink` | **Move back to commons**, preferably a focused filesystem module | Their signatures contain no installer policy. Local workers can serialize filesystem operations or atomically publish a new snapshot. This does not make a directory lock a distributed lock. |
| Current `extract_archive` | tooling | Its requirement for exactly one root directory is a release-bundle convention. A webapp accepting arbitrary archives has a different contract. Do not generalize merely because both unpack files. |
| Current `StateStore` | tooling for now | Local JSON state and generator metadata fit the current clients. It deliberately proceeds unlocked when locking is unavailable; it is not a substitute for transactional shared application persistence. Promote a neutral store only with a concrete runtime requirement. |
| Current `TemplateEngine` | tooling | Strict undefined values, TOML/YAML filters, and hardcoded `autoescape=False` target generated configuration. Business apps need templates, but not necessarily this wrapper. |
| Remaining `utils.py` | commons | Phase C removes helpers here; it does not add a new tooling-oriented utility collection. Boolean parsing and string joining already have Django consumers; hashing, confinement, atomic writes, and environment helpers remain general mechanisms. |
| Docs link/nav mechanics | tooling | Reusable docs operations. Separate the specific repository policy described in A2. |

References: `install contracts`, `template environment`,
`best-effort state locking`, `runtime utility consumer`.

Jinja supports HTML autoescaping; the current wrapper instead hardcodes it off,
and passing `autoescape=True` through its constructor raises a duplicate-keyword
`TypeError`. That supports retaining its config-generation scope rather than
presenting it as the shared web rendering solution.
[Jinja API](https://jinja.palletsprojects.com/en/stable/api/)

### A2 — Docs extraction carries kiln policy into tooling

`structure.py` hardcodes ADR numbering/statuses, epic/feature/release naming,
and instruction-file names. Lines 95–97 inspect fixed `adr`, `releases`, and
`specs/epics` paths. Reading `_areas.yml` does not make all these rules
repository-configured.

This follows the Phase C extraction instructions, but conflicts with the broader
claim that rn-forge repository policy belongs to kiln. **Change:** keep generic
link, Markdown, and nav mechanics in tooling; move these policy rules to
`rn-forge-kiln-checks`, or pass an explicit policy from it. Prefer that small
separation over introducing a generic validation framework.

### A3 — The package contract unnecessarily bundles every consumer with the whole CLI stack

`tooling's eager exports` import CLI, console, state, install, and templates.
Importing a submodule executes the package initializer too. Therefore the
generator protocol may be Typer-free in its signature, but its package import is
not independent of Typer/Jinja.

For the current developer-tool audience, hard dependencies are a reasonable
simplicity tradeoff; this is **not a release-blocking defect**. However, the
claim that every tool renders templates on every run is false for check-only and
state-only consumers. If runtime reuse is intended, move the genuinely common
primitives as above before creating extras. Extras add dependencies; they do not
conditionally exclude source modules or prevent eager imports.
[PyPA dependency specification](https://packaging.python.org/en/latest/specifications/dependency-specifiers/)

## Implementation findings

Priorities: P1 = potential data loss or silent incorrect outcome on a supported
workflow; P2 = correctness, integration, or boundary enforcement gap; P3 =
documentation/interface consistency. Existing defects carried with moved modules
are identified where relevant.

### F1 — P1: Multiple blocks in one file overwrite each other

**Evidence:** `generation.py:482`. Each block renders against the original
on-disk text, but staging is keyed only by file path. The last block overwrites
the preceding staged result. State nevertheless records every artifact.

**Reproduced:** two differently named block artifacts targeting one file leave
only the last block; the next plan reports the first as drift. This is a natural
use of the per-block ownership model.

The apply loop also backs up the same destination repeatedly to the same backup
path (lines 498–501). After the first replacement, a later backup can overwrite
the original with already-modified content, undermining rollback for these
multi-block changes.

**Fix:** group changes by destination, compose block edits against one evolving
file buffer, and back up/write each file once. Reject incompatible whole-file
and block ownership of the same path. Test two inserts, two updates, and a
removal plus update.

### F2 — P1: Ctrl-C bypasses transactional rollback

**Evidence:** `generation.py:514` catches only `Exception`.

**Reproduced:** a `verify` callback raising `KeyboardInterrupt` leaves generated
content on disk without the corresponding state. Interrupting a CLI is ordinary
user behavior, and the advertised transaction does not hold for it.

**Fix:** perform rollback for `BaseException`, then re-raise interruption
exceptions without converting them into ordinary application failures. Test
interruption after at least one replacement. This does not imply that Python
cleanup can recover from power loss or SIGKILL; crash recovery would require a
separately defined contract.

### F3 — P1: JSON-loaded error findings become non-errors

**Evidence:** `findings.py:62` compares enum identity, while inherited
deserialization leaves a JSON severity as `str`.

```python
restored = Finding.from_json(Finding("rule.error", Severity.ERROR, "failed").to_json())
print(type(restored.severity).__name__, restored.is_error)
# str False
```

**Fix:** explicitly reconstruct and validate `Severity` during deserialization.
Test actual JSON round trips and unknown severity values; the existing
dictionary round-trip test retains enum objects and misses this.

### F4 — P2: Artifact paths can escape the root and bypass staging

**Evidence:** `Artifact validation` checks only block/kind consistency;
`staging` joins an unchecked path.

**Reproduced in temporary directories:** an absolute artifact path is accepted
and written directly during staging, before backups. A subsequent failed apply
leaves the outside file. Relative traversal and symlink containment also lack a
root check. The documented repo-relative precondition is not enforced. This is
an API safety defect, not evidence of a remote exploit.

**Fix:** normalize and validate artifact and stale-state paths before any
mutation; enforce containment under the repo and staging/backup roots using the
existing path helpers. Recheck at execution where needed. Test absolute paths,
`..`, and escaping symlinks.

### F5 — P2: Forced removal of stale drift forgets ownership without removing content

**Evidence:** `generation.py:421`, `apply loop`, and `_next_entries` at line
522\.

**Reproduced:** generate a managed file, edit it, stop rendering it, then
approve its stale drift via `force`. Apply backs it up, leaves it on disk, and
removes its state entry. The same missing-artifact rendering branch affects
stale blocks.

**Fix:** preserve the intended deletion/removal separately from the blocking
drift classification. Once approved, execute that operation and retain unrelated
block content. Test the stale managed-file and stale-block cases.

### F6 — P2: Managed blocks rewrite content outside their ownership

**Evidence:** `blocks.py:145` splits/rejoins the whole file, normalizing CRLF to
LF and appending a final newline. Removal at line 165 deletes all preceding
whitespace-only lines, not just an inserted separator. This contradicts the
byte-preservation promise.

**Reproduced:** replacing a block in
`before\r\n# BEGIN x\r\nold\r\n# END x\r\nafter` changes the unowned
prefix/suffix and adds a terminal newline. Removing a block preceded by two
blank lines deletes both.

**Fix:** replace only the identified span while preserving original
prefix/suffix and newline sequences. Generation's `read_text` also normalizes
newlines, so fix the file-reading path as well. Test CRLF, absent terminal
newline, and existing blank lines.

### F7 — P2: Tooling has no CI test/build/release job; import contracts are not gated

**Evidence:** `main.yml:14` invokes package CI only for commons and Django.
Coverage at lines 50–52 explicitly excludes tooling, although Sonar now includes
its source/tests. Neither workflow invokes `lint-imports`.

Moving tests out of commons consequently removes them from those CI pytest runs.
The new package also cannot receive its release through the existing package
workflow. A locally passing import contract is not continuously enforced.

**Fix:** add tooling to package verification/build/release and coverage; run
root import contracts as a required gate. This is necessary current integration
even if Phase F later regenerates the skeleton.

### F8 — P2: Phase C consumer wiring is unfinished

**Evidence:** the `Phase C addendum` explicitly requires a tooling release,
golden-cli usage, dependency checks/state updates, and post-split commons pins.
Current `golden-cli metadata` still depends only on commons `v0.2.2`;
`kiln metadata` has empty dependencies. The local tag list contains no tooling
release tag.

**Fix:** track these as outstanding Phase C acceptance work and exercise tooling
in golden-cli after publishing a usable release. Local tags do not prove remote
release absence; remote release availability was not checked. The local consumer
files are sufficient to establish incomplete wiring.

### F9 — P2: Standalone dependency resolution is not established

**Evidence:** `tooling metadata` declares unconstrained `rn-forge-commons`, with
a workspace source override. The `installation guide` says
`uv add rn-forge-tooling`, while the plan's distribution model uses GitHub
release/tag sources rather than PyPI.

The workspace proves compatibility only with its editable commons checkout. It
does not establish that an outside installer can locate the required commons
distribution, or prevent selecting an older commons lacking Phase C symbols.

**Fix:** define the standalone source and compatible commons version in the
release contract, then smoke-test installation outside the workspace using the
documented command. Keep workspace overrides for local development. If
continuing with D46, use the appropriate released direct reference; if using an
index, declare a compatible version floor. No standalone wheel installation was
run in this review.
[uv workspace behavior](https://docs.astral.sh/uv/concepts/projects/workspaces/),
[PyPA project metadata](https://packaging.python.org/en/latest/specifications/pyproject-toml/)

### F10 — P2: Command-level JSON mode can emit logs before JSON

**Evidence:** `cli.py:151` merges command flags and changes the console mode
after the root callback initializes logging. It does not redirect logging
output.

**Reproduced:** a command accepting `--json`, calling `command_options`, logging
a warning, and emitting a JSON object exits successfully but writes
configuration/warning log text before the object on stdout. The parser cannot
consume stdout as JSON. This behavior is carried in the extracted CLI surface.

**Fix:** route diagnostic console logging to stderr from initialization, leaving
stdout for structured results regardless of flag position. Test real log output
with both root-level and command-level `--json`.

### F11 — P2: Navigation generation interpolates invalid YAML

**Evidence:** `nav.py:82` and lines 86–87 insert titles and paths as unquoted
YAML scalars.

**Reproduced:** a valid area title `Guides: development` produces a
`ScannerError` when the generated navigation is parsed as YAML.

**Fix:** serialize nav values with the existing YAML library, preserving the
managed-block layout. Test colons, quotes, and other YAML-significant characters
in configured titles and paths.

### F12 — P2: Anchor checking disagrees with the docs renderer

**Evidence:** `markdown.py:38` implements a separate heading slug algorithm.

**Reproduced against installed Python-Markdown's `toc` extension:** `# Résumé`
yields checker anchor `résumé` versus rendered `resume`; repeated `## Repeat`
headings yield only `repeat` in the checker versus `repeat` and `repeat_1` in
the renderer. Valid rendered links can therefore fail validation.

The same regex-based parser ignores reference-style links and counts headings
inside fenced code, so it also misses broken references and can accept anchors
that the renderer never creates.

**Fix:** align checking with the supported renderer/configuration, including
duplicate identifiers and link syntax. Test accented text, repeated headings,
fenced code, reference links, and configured explicit IDs. Do not claim generic
Markdown anchor correctness when supporting one rendering profile.

### F13 — P3: Docs nav's JSON flag produces no result

**Evidence:** `docs/cli.py:89` uses only human-oriented console methods for nav
results.

**Reproduced:** `rn-forge-docs --json nav` updates the file and exits 0 with
empty stdout. **Fix:** emit a structured result, including changed/path/check
status, and cover both rewrite and `--check` branches.

### F14 — P3: Agent instructions still describe the pre-extraction tree

**Evidence:** `AGENTS.md:13` still puts CLI/console/state/templates in commons;
lines 28–30 say extraction is blocked. `CLAUDE.md` was updated by Phase C.

**Fix:** reconcile the instructions or use the intended single-source pointer so
future agents do not reintroduce removed imports or follow a stale extraction
gate.

## Validation and limits

- Existing focused suite:
  `.venv/bin/pytest -q packages/rn-forge-tooling/tests packages/rn-forge-commons/tests/test_blocks.py packages/rn-forge-commons/tests/test_findings.py packages/rn-forge-commons/tests/test_utils.py`
  — **350 passed**.
- `.venv/bin/lint-imports` — **3 contracts kept, 0 broken** against the current
  source tree.
- The findings above include separate temporary-directory/Python/CliRunner
  reproductions; the passing existing tests do not cover those failing cases.
- No dependencies installed, code changed, releases created, or remote CI runs
  inspected. No full workspace test run, strict typecheck, or standalone
  package installation is claimed.

The package-placement proposals revise parts of confirmed D29/D35/D51 because
this review explicitly reopens those choices. They should not be confused with
implementation failures to follow the plan; F8 is the separate plan-completion
gap.
