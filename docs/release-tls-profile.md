# Verified release-client transport profile

Application TLS and release-client TLS are separate. The vendored release
helpers invoke `gh` for GitHub API requests. For those operations, use GitHub CLI
2.102.0 built with Go 1.27.1 and this command-local profile:

```sh
gh --version
go version -m "$(command -v gh)"
GH_HOST=github.com GODEBUG=fips140=on python3 scripts/release.py status
```

The first commands must show those exact verified versions. Use the same prefix
for other authorized release operations; do not omit it when invoking the helper
indirectly. The Python subprocess calls inherit the process environment, including
`GODEBUG`. A read-only API probe with this toolchain/profile succeeded on
2026-10-16. This check does not publish a release or modify repository state.

The reviewed Go runtime filters complete verified certificate chains to RSA at
least 2048 bits and its supported modern elliptic/ML-DSA keys. It preserves hostname
and certificate verification, TLS 1.2+ and ephemeral exchange. The shared
[verification record](https://github.com/victron-venus/integration-tests/blob/232df66ba8ec59019ee5444090212f256a88b7e6/docs/release-tls-profile.md)
includes a calibrated synthetic weak/strong certificate experiment for this
runtime family and source references. This document reuses that evidence; it does
not claim a new local weak-certificate experiment.

Other `gh`/Go versions, enterprise/custom endpoints, proxies and custom trust
stores need equivalent qualification. A runtime option is not a FIPS certificate
or an OpenSSF requirement for FIPS certification. Standard package managers,
Git/SSH and manually installed external tools retain their separate trust and
verification requirements. This profile applies to the owned release helpers.
