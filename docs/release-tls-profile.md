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

## Signature verifier

The signed-release path also invokes Cosign. The verified installation is
Cosign 3.1.3 built with Go 1.26.4 (the published Darwin ARM64 binary has SHA-256
`5cf948c2f4dfe59687bdd0b8523709067383e03982cc543475c8a7dc70e92a76`).
Check `cosign version` and `go version -m "$(command -v cosign)"` before using it.
Keep `GODEBUG=fips140=on` set for the signature verifier as well as the GitHub
helper. The existing helper's Cosign subprocess inherits it without replacement.

```sh
GODEBUG=fips140=on cosign initialize
GODEBUG=fips140=on python3 scripts/release_signing.py verify /downloads/release \
  --root /trusted/project --source-sha EXPECTED_REVIEWED_SOURCE_COMMIT
```

The default public Sigstore TUF endpoint uses HTTPS. The reviewed Cosign bundle
verification path loads trusted material through sigstore-go 1.2.2 and go-tuf
2.4.2's default HTTP client. Go 1.26.4 applies the FIPS TLS filter to every
certificate in a verified chain, permits RSA at least 2048 bits and supported
modern elliptic keys, and permits only TLS 1.2/1.3 with ephemeral key exchange.
Do not select custom mirrors, insecure transport flags or alternate key providers
under this profile without separately qualifying them.

On 2026-10-16, an isolated empty-cache initialization succeeded with this exact
binary and setting. Verification of the upstream Cosign 3.1.3 checksum manifest
and its Sigstore bundle succeeded with the expected publisher identity
`keyless@projectsigstore.iam.gserviceaccount.com` and issuer
`https://accounts.google.com`; modifying the manifest caused verification to
fail. These are verifier interoperability and integrity checks, not a claim that
this project has published a signed release or a new weak-certificate experiment.
The application and artifact hashes use their existing standard libraries;
Git SHA-1 object IDs are source identifiers, not a replacement for the signed
SHA-256 asset inventory. A verified cryptographic profile does not establish
that every dependency is free of vulnerabilities.

Source references for this additional path:

- [Cosign trusted-material loading](https://github.com/sigstore/cosign/blob/v3.1.3/cmd/cosign/cli/verify/common.go)
  and [bundle verification](https://github.com/sigstore/cosign/blob/v3.1.3/cmd/cosign/cli/verify/verify_blob.go).
- [Sigstore TUF transport](https://github.com/sigstore/sigstore-go/blob/v1.2.2/pkg/tuf/client.go)
  and [go-tuf default HTTP client](https://github.com/theupdateframework/go-tuf/blob/v2.4.2/metadata/fetcher/fetcher.go).
- [Go 1.26.4 TLS key restrictions](https://github.com/golang/go/blob/go1.26.4/src/crypto/tls/defaults_fips140.go)
  and [whole-chain filter](https://github.com/golang/go/blob/go1.26.4/src/crypto/tls/common.go).
