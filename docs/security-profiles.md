# Supported workflows and security boundaries

## Complete offline workflow

Install the package without the optional `record` extra, using the README's virtual-environment instructions. The demo, local session/report APIs and joint report operate without network dependencies. `sensing-evidence-demo demo-output` produces synthetic inputs and reports. For actual analysis, use the tutorial to supply local evidence and independent labels, then run the report or joint-report command. This workflow is useful without a Home Assistant connection or a token.

The production parser rejects malformed JSON, non-finite or invalid clock values, inconsistent bindings and incomplete captures. Reports preserve unknown time and `validation_decision: not_evaluated`; neither a valid schema nor a matching hash establishes physical truth. Local evidence can contain private observations and must be protected by the operator. Session creation uses owner-only files and refuses to overwrite existing evidence. Custom adapters execute trusted Python code and require review before loading.

Offline content fingerprints use Python's `hashlib.sha256`. These are consistency checks, not signatures, password verifiers or proof against a party able to replace both evidence and its fingerprint. Offline analysis uses no encrypted session, asymmetric key or password database. Installation and source acquisition can use the network through independent package/Git clients; retain their normal TLS verification and use the documented versioned source and signed release inventory.

## Optional live capture

The `record` extra enables aiohttp capture from one explicitly selected Home Assistant origin. It reads observations through WebSocket and does not issue device service commands. HTTPS origins become WSS; aiohttp performs certificate and hostname validation. The redirect callback rejects redirects before a redirected origin can receive the token. Tests exercise the actual aiohttp redirect path with synthetic responses.

Use a trusted HTTPS origin for remote capture, with minimum account permissions. Plain HTTP remains available for explicitly configured trusted local networks and provides no transport confidentiality. A custom adapter's token provider is trusted code and can create other behavior. Tokens come from the environment or an explicitly supplied adapter and are not evidence fields. This optional transport has not been qualified for an exact minimum public-key size across every possible certificate chain; ordinary TLS verification alone does not prove that property.

## Delivery and assessment boundaries

Source, build scripts, tests, release helpers and optional capture code remain in review and static-analysis scope. The complete offline workflow does not imply that optional capture or external platform tools have all the same security properties. Release signatures authenticate a published inventory; they do not certify the observations or sensing accuracy. See [release signatures](release-signatures.md), [release process](../RELEASING.md) and [security reporting](../SECURITY.md).
