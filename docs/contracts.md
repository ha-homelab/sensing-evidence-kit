# Evidence contract v1

The public Python package uses `schema_version: 1`. Compatible readers may accept additional informational fields; changes to identity, clock or measurement semantics require a new contract. No report grants calibrated coverage or a validated detector status.

## Identity, clocks and immutable inputs

Metadata contains a session ID, opaque host ID, OS boot ID, offset-aware UTC anchor, integer `monotonic_ns` anchor and finite clock tolerance no greater than 2 seconds. Every record must agree on session/host/boot identity. UTC elapsed time and monotonic elapsed time must remain within tolerance. Naive timestamps, future request starts, negative/noninteger clocks, clock discontinuities and out-of-order streams are rejected.

Live identities are local to macOS or Linux. Monotonic clocks from separate hosts or boots cannot be joined. A recorded clock-offset uncertainty is informational; this beta does not estimate or correct clock offsets. Strict JSON parsing rejects duplicate object keys, NaN, infinity and overflowing numeric values. JSONL records require nonblank newline-terminated lines. File readers cap each evidence file at 256 MiB.

Metadata pins the complete adapter configuration and resolver implementation with SHA-256. The recorder fingerprint is retained for manual provenance review. Samples pin the binding list, model fingerprint and inventory revision. Binding or model changes invalidate a session. The package writes reports exclusively and never overwrites originals.

## Consumer observations

`capture.jsonl` contains sample records followed by exactly one verified completion record. Samples include `items`, selected `states`, `binding_sha256`, `model_sha256`, `inventory_revision`, and a `request_started` clock. Each state has a string state, a `last_reported` timestamp and optional attributes. Missing or invalid state timestamps become unknown. Request timing missing from older evidence prevents that sample from contributing labelled durations, though its snapshot may still appear in diagnostics.

The built-in adapter maps fresh `on` to `presence` and fresh `off` to `quiet`. Other states, missing bindings, restored values, future `last_reported` and expired TTLs yield `unknown`. Freshness uses the half-open interval `last_reported <= evaluation_time < last_reported + TTL`. A room is positive if any configured receiver is positive; it is quiet only when all its receivers are quiet. Otherwise it is unknown.

A `last_reported` later than the sample receipt time is invalid for that entire snapshot. Advancing evaluation time while projecting a sample never rehabilitates a future timestamp; only a later sample can supply fresh evidence.

A report projects each sample only to the next sample, caps that interval by `max_sample_gap_seconds`, and splits at freshness expiry. Excessive request duration contributes unknown time. This is snapshot-based characterization; it cannot recover short events between polls.

## Independent labels and metrics

Labels identify a trial, target room, phase, event, independently occupied rooms, action and reference point/path. Phases are `empty_calibration`, `still`, `walking`, `adjacent_target_empty` and `empty_recovery`. The name `empty_calibration` identifies a trial phase; it does not certify calibration.

Still/empty phases begin at `settled`; walking/adjacent phases begin at `action_start`. The next label must close the same trial/room/phase with `action_stop` or `exit`. Uncertain, interrupted or unclosed intervals are excluded. Both ends are trimmed by `transition_seconds`.

Reports show labelled seconds, known seconds, unknown seconds, positive seconds, experimental seconds, false presence, missed presence, motion during stillness, no motion during walking and adjacent leakage. The binary adapter never generates motion, so motion-related metrics are only meaningful with an adapter that distinguishes motion. There is no automatic accuracy percentage, threshold pass or promotion decision.

## Optional joint producer contract

Joint analysis requires original bytes for `ha_metadata`, `ha_capture`, optional `ha_labels`, `producer_metadata`, `producer_capture` and `producer_summary`. Producers use stream `ruview_producer` and the same identity/clock anchor. Producer metadata includes `local_monotonic_alignment: true`, the exact consumer metadata byte hash, a copied consumer anchor, requested duration and node-to-room/marker bindings.

Every receiver must have a distinct integer `node_id` in `1..255` for joint analysis. Consumer-only reports do not require node IDs. Producer samples identify source `esp32`, the configured node set, `observation_valid` and an `issues` list. This generic checker validates producer-declared validity and structural consistency; **it does not independently recompute CSI/inference freshness or authenticate producer claims**. That requires a producer-specific recorder/validator. The package does not ship or start that recorder.

Producer streams end with one terminal record. The summary must match its count and completion fields and hash the exact capture bytes. The joint checker rejects mismatched clocks, hashes, node bindings and unsupported validation claims. It reports invalid diagnostics for incomplete/errorful captures, insufficient samples, no overlap or sample gaps exceeding 5 seconds. Its duration check retains a 10-second boundary allowance; review exact producer phase timings separately. Sample-window overlap does not prove continuous valid coverage or exact event latency.

All producer records must be timestamped between metadata and the terminal record. Boundary/error records may otherwise be emitted out of timestamp order around a related sample.

Byte hashes detect changes relative to the supplied companions. They are not digital signatures or independent proof that supplied evidence is authentic. The normal consumer report also records hashes of parsed JSON; those do not preserve whitespace or original byte representation. Joint reports explicitly report original-file hashes.
