# Beta scope

This package provides a standard-library-only reporting engine, a binary-entity adapter, optional read-only Home Assistant recording, and an optional same-host producer/consumer integrity report. Synthetic tests cover freshness expiry, restored/future data, malformed JSON, clock identities/discontinuities, binding fingerprints, independent label closure, byte hashes, stream completion and node mappings.

Tests establish behavior on those cases, not hardware support or sensing accuracy. Live Home Assistant recording is not exercised by the offline suite. No producer recorder, firmware, calibration engine, emergency monitoring, automated acceptance decision or private deployment inventory is included.

The generic binary adapter cannot determine whether a device's `last_reported` actually corresponds to fresh physical sensing; verify that interpretation for your integration. Producer validity flags are declarations requiring producer-specific review. Snapshot polling misses short events. Known seconds, label intervals and overlap windows have different meanings and must not be substituted for one another.

Evaluate a controlled, noncritical setup, record independent labels and keep original evidence. Repeat experiments across relevant conditions before drawing broader conclusions. The kit does not choose the acceptance criteria for you and always returns validation as not evaluated.
