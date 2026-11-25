# Release 4 — security evidence

|  |  |
| -- | -- |
| **Release** | [Release 4](index.md) |
| **Repository** | rn-forge/kiln |
| **Commit** | `abc1234def` |
| **Run** | [123, attempt 1](https://github.com/rn-forge/kiln/actions/runs/123/attempts/1) |

Rendered by `task release:evidence` from the run's `security-evidence` record.
Do not edit it by hand.

Passing this baseline is not a claim that the release is secure.

| Control | Effect | Result | Evidence |
| -- | -- | -- | -- |
| Dependency audit | fails the build | passed | [job validate, step Validate](https://github.com/rn-forge/kiln/actions/runs/123/job/0) |
| Licence inventory | fails the build | passed | [job validate, step Validate](https://github.com/rn-forge/kiln/actions/runs/123/job/1) |
| Source scan | fails the build | passed | [job validate, step Validate](https://github.com/rn-forge/kiln/actions/runs/123/job/2) |
| Secret scan | fails the build | passed | [job secret-scan](https://github.com/rn-forge/kiln/actions/runs/123/job/3) |
| Push protection | blocks the push | not checked | not read by CI |
| SBOM | reports only | passed | [rn-forge-kiln-v0.4.0: rn-forge-kiln.cdx.json](https://github.com/rn-forge/kiln/releases/tag/rn-forge-kiln-v0.4.0) |
| Attestation | reports only | passed | rn-forge-kiln-0.4.0.tar.gz 200; rn-forge-kiln-0.4.0-py3-none-any.whl 200 |
| `SECURITY.md` | reports only | passed | [SECURITY.md](https://github.com/rn-forge/kiln/blob/abc1234def/SECURITY.md) |
| Scorecard | reports only | passed | [commit abc1234def](https://github.com/rn-forge/kiln/actions/runs/99) |
