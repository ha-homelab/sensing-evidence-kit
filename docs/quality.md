# Quality evidence

The offline contract workflow runs Ruff lint and format checks, the synthetic application suite and repository validation. Tests reject outgoing sockets and DNS and never load private household evidence. The quality gate also runs release-tooling and workflow contract tests; shared security analysis includes Python CodeQL, dependency review and Trivy. CI results must be inspected for the specific source revision before release. Whole-source coverage, a complete secure-design assurance case and physical sensor accuracy are separate properties and are not implied by a green run.

The build backend is pinned to setuptools 83.0.0, containing the upstream Unicode MANIFEST normalization [fix](https://github.com/pypa/setuptools/commit/dd9f436a36486b4cb8a4c70a2321548b0be09b8f) for [GHSA-h35f-9h28-mq5c](https://github.com/advisories/GHSA-h35f-9h28-mq5c). This addresses source-build tooling; archives must still be inspected for unintended content. Test pytest 9.0.3 and capture aiohttp 3.14.4 remain locked in the dependency manifest.

The primary maintainer personally confirmed knowledge of secure-design principles and common Python/network vulnerabilities, and no bug, enhancement or vulnerability reports outside GitHub during the preceding 12 months. These are maintainer attestations. Public issue/advisory history must also be checked when refreshing the assessment. [Governance](../GOVERNANCE.md) explicitly records the missing continuity arrangement.

## Complete Python warning review, 2026-10-16

A separate review of the clean source archive at
`2a97fdf150d8d1db27355b9898df82323c9b40d6` checked all **49 tracked Python files**,
including inherited release helpers, using **Ruff 0.16.5** with isolated
configuration, the complete F diagnostic family and inline suppressions ignored.
Result: **All checks passed; zero diagnostics**. This is a dated source review;
the routine CI lint/format invocation still covers its documented narrower paths.
It does not claim complete style enforcement or maximum diagnostic coverage.

To reproduce, install that Ruff version, check out the exact source above and run:

```sh
git ls-files -z -- '*.py' | xargs -0 python3 -m ruff check --isolated --select F --ignore-noqa --
```

The recorded review used the equivalent explicit tracked-file list with a clean
`git archive` extraction, so ignored, untracked or modified working files could
not affect the result. No test, query or warning suppression was introduced.
