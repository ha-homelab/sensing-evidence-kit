# Changelog

## [0.1.1] - 2026-10-17

### Changed

- Add optional `record --strict-tls` capture with a verified HTTPS-only OpenSSL 3 security-level-3 connector shared by capture and adapter token requests.
- Update the source-build backend to setuptools 83.0.0 and use qualified canonical clients for signed release publication.
- Document Python warning review, maintenance, private reporting and the limits of offline evidence.

### Upgrade

Install the verified wheel or source distribution in an isolated environment and retain the previous version for rollback. Enable strict TLS explicitly when the endpoint and certificate chain meet its requirements. Existing default local-network compatibility and report semantics remain unchanged.

### Security

Strict mode verifies certificate-chain key floors, trust and hostnames with synthetic TLS-handshake regressions. The build-backend update includes the upstream Unicode MANIFEST normalization fix (GHSA-h35f-9h28-mq5c). Published reports still do not claim live sensing accuracy or contain private installation inventory.

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
