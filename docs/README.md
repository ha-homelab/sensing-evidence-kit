# Sensing Evidence Kit — documentation index

This index covers the public evidence kit: capturing selected Home Assistant
observations, recording independent operator labels, and producing reports that
measure disagreement and unknown time. Every report keeps
`validation_decision: not_evaluated`; the kit characterizes, it does not validate.

## Get started

- [Tutorial](tutorial.md): configure an adapter, open a private session, record
  observations, add labels and generate a report.
- [Scope and limitations](beta.md): what the package does and does not claim.
- [Reproducible operation and upgrades](reproducibility.md): release channels and
  upgrade expectations.

## Configure

- [Adapter API](adapters.md): `EntityAdapter` configuration and the room/receiver
  contract.
- [Supported workflows and security boundaries](security-profiles.md): install
  without the optional `record` extra, and the demo and local API limits.

## Reference

- [Evidence contract v1](contracts.md): schema version, compatible-reader rules
  and identity, clock and measurement fields.

## Operate

- [Troubleshooting](troubleshooting.md): clock jumps, machine boundaries and
  append rules for captured sessions.

## Development and release

- [Verify a signed release](release-signatures.md) and the
  [patched release signer and verifier](release-signer.md).
- [Qualified GitHub CLI for release operations](release-github-cli.md).
- [Verified release-client transport profile](release-tls-profile.md).
- [Quality evidence](quality.md): the offline contract workflow and its checks.
- [Release-candidate fuzz testing](fuzzing.md) and [RC fuzzing](rc-fuzzing.md).

## Evidence

- `docs/synthetic-demo.html` and `docs/synthetic-demo.png` are the rendered
  output of the offline demonstration; regenerate them with the demo command
  rather than editing them by hand.

Shared repository policy (`release-workflow.md`, `quality.md`,
`release-read-safety.md`, `runner-preflight.md`, `VERSIONING.md`) comes from the
shared release toolkit and is summarized rather than repeated here.
