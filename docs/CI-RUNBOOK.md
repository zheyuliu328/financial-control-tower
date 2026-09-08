# CI and local verification

Required remote contexts are `lint`, `test`, `e2e`, `verify`, and `gitleaks`. Workflow changes retain these names and execute the checks; branch-protection settings are not modified.

- `lint`: Ruff 0.16.6 linter and formatter on maintained Python files, including legacy scripts. Historical Markdown design snippets are outside this code-formatting scope.
- `test`: substantive isolated tests and coverage artifact.
- `e2e`: build a wheel, normal installation, invoke the installed CLI from outside the checkout, assert fresh reports and nonzero errors.
- `verify`: non-destructive local verification script, Bandit, dependency consistency and a fail-closed dependency vulnerability audit.
- `gitleaks`: the existing Git-history secret scan in the Security workflow.
- Python 3.9 and 3.13 compatibility jobs additionally run the full tests.

A failed check is repaired before merge; a missing or skipped required context is not equivalent to success. No required checks should be disabled or bypassed to obtain a green state.

For local checks install `.[dev]`, then `bash scripts/verify.sh`. It keeps its unique temporary output and propagates the first failure. It does not delete outputs, install dependencies, access network services, or certify confidentiality. Public dependency vulnerability information and GitHub Actions remain separate online checks.
