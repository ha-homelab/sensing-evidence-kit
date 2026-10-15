# Contributing

Install Python 3.11+ and `.[dev]`, then run `./scripts/check.sh`. Tests must remain offline with synthetic identities, timestamps and entity names. Include regressions for clock/freshness arithmetic, label interpretation, unknown durations, fingerprints and completion rules when changing them.

Keep `pyproject.toml`, `version` and `__version__` synchronized. Describe contract changes in the changelog and preserve public adapter signatures or document migrations. Do not weaken validation to make a failed recording look complete. Characterization and independent validation are separate responsibilities.

Never contribute live captures, host/boot identifiers, credentials, device inventories, room layouts, operator notes or private deployment code. Build the smallest invented fixture that reproduces a bug. Contributions to project-owned files use the MIT license; preserve third-party notices for any code you add.
