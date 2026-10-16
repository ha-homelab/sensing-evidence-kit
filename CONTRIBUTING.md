# Contributing

Use [issues](https://github.com/ha-homelab/sensing-evidence-kit/issues) for bugs, questions and enhancement proposals, and pull requests for changes. English discussion is welcome. State the expected behavior, actual behavior and source revision with a small synthetic reproducer. Follow the [Code of Conduct](CODE_OF_CONDUCT.md); vulnerabilities use the private channels in [SECURITY.md](SECURITY.md).

Install Python 3.11+ and `.[dev]`, then run `./scripts/check.sh`. Tests must remain offline with synthetic identities, timestamps and entity names. Include regressions for clock/freshness arithmetic, label interpretation, unknown durations, fingerprints and completion rules when changing them.

Keep `pyproject.toml`, `version` and `__version__` synchronized. Describe contract changes in the changelog and preserve public adapter signatures or document migrations. Do not weaken validation to make a failed recording look complete. Characterization and independent validation are separate responsibilities.

Never contribute live captures, host/boot identifiers, credentials, device inventories, room layouts, operator notes or private deployment code. Build the smallest invented fixture that reproduces a bug. Contributions to project-owned files use the MIT license; preserve third-party notices for any code you add.

Follow Python PEP 8 and the repository's Ruff lint/format configuration. Every major new feature and behavior fix must include automated tests, with negative or regression cases where applicable. Keep assertions enabled during testing. Update interface documentation and the changelog together with behavior. The maintainer reviews changes and evidence before merging through the normal protected-branch process. See [governance](GOVERNANCE.md) and the [roadmap](ROADMAP.md).
