# Changelog

## [0.1.0] - 2026-10-15

Initial public beta:

- Configurable binary-entity adapter and importable session/report APIs.
- Independent labels, source-age expiry, unknown-time accounting and completion checks.
- Strict clock/JSON/binding validation and optional same-host joint byte-integrity diagnostics.
- Optional per-receiver node IDs for producer joins; consumer reports remain node-ID independent.
- Optional read-only Home Assistant capture, offline synthetic demonstration, documentation and reproducible source/wheel packaging.

All reports retain `validation_decision: not_evaluated`. No live evidence or private inventory is included.

Release candidate hardening:

- Keep future-dated state timestamps unknown for the whole projected sample interval instead of adding false known time.
- Reject producer records timestamped after their terminal record, and reject extreme numeric limits without integer-conversion failures.
- Document pinned environments, private evidence preservation, software upgrades, rollback and the limits of filtering and integrity hashes.

### Upgrade

Install the selected beta wheel in an isolated Python 3.11 or newer environment. Existing private integrations should map their entity inventory explicitly and preserve raw captures before importing them. This initial public beta does not migrate private configuration or change the meaning of prior observations.

### Security

Keep Home Assistant tokens in local environment variables and use the recorder only against a trusted Home Assistant URL. Captures may contain occupancy data; review them before sharing. This release validates input sizes, timestamps and binding metadata, rejects recorder redirects, and includes patched aiohttp and test-only pytest dependencies. Offline tests do not establish device compatibility or certify a physical sensing system.
