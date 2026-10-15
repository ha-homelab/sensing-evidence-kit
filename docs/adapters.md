# Adapter API

`EntityAdapter(config)` offers a generic binary-entity adapter. Configuration requires exactly `rooms`, `receivers` and `ttl_seconds`; each receiver requires `item_id`, `room`, `entity_id` and `sensor`, plus optional unique integer `node_id`. Input entities, receiver markers and output report identifiers must be distinct. The adapter deep-copies the configuration and adds `sources: []` for compatibility with the shared engine.

Existing private integrations can keep their deployment inventory and specialized semantics private and import the generic engine:

```python
from sensing_evidence import session, joint
from sensing_evidence.adapters import EntityAdapter

# adapter = EntityAdapter(your_private_config)
# report = session.report(metadata, capture_rows, labels, adapter)
# combined = joint.analyze(original_file_bytes, adapter)
# session.main(adapter=adapter)  # Existing private CLI facade.
```

Supported adapter members:

- `CONFIG`: dictionary with `rooms` (room ID → output key), `receivers` and `sources`. Binding items supply `item_id`, `room`, `entity_id`; receivers also supply `sensor` and optionally `node_id`.
- `tracked_entities()`: set of source entity IDs. The engine adds room/receiver output IDs to its capture selection.
- `freshness_deadline(state, when)`: offset-aware datetime or `None`. Never extend an event's original freshness merely because it was read again.
- `resolve_activity(items, states, when)`: mapping from output IDs to `(state_name, attributes)`. Return every configured room and receiver output; use `unknown` for missing evidence. Recognized metric states are `quiet`, `motion`, `presence`, `experimental` and corresponding `unverified_` forms.
- `fingerprint()`: implementation SHA-256 string; if absent, the engine hashes `adapter.__file__` for module-style adapters.
- Optional async `bindings(call)`: return `items`, `revision`, `model_sha256` using read-only HA calls. Custom source markers may omit `entity_id`; their `id` and `room` and complete fingerprint remain required. Default bindings derive from configuration and are fingerprinted.
- Optional async `access_token(client, origin)`: custom credential resolver when `HA_TOKEN` is absent. Never persist a token into evidence.
- Optional `source_revision` and `request_timeout`: provenance label and HA request timeout (seconds, or a callable receiving the request kind).

The engine trusts adapter semantics; a custom adapter must be tested separately. Do not publish private configuration or replace an adapter after a capture and expect its contract hash to match. Pin the public package in private deployment requirements and keep thin facades rather than copying its source.

Core signatures remain `session.report(metadata, capture_rows, labels, adapter)`, `joint.analyze(files, adapter)` and `session.main(adapter=None)` / `joint.main(adapter=None)`. Both CLIs also accept optional `argv` for embedding/tests. The JSON parsing, clock, selection, digest, writer and observation helpers remain importable from `session`. Tightened validation rejects malformed clocks, fingerprints and bindings that older code may have allowed.
