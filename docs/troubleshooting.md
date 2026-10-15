# Troubleshooting

## Clock/session mismatch

Capture and label on one machine during one OS boot. Do not copy a session to another machine and append records. Ensure UTC clocks do not jump during a capture. Start a new session after reboot, host migration or clock discontinuity. Joint analysis cannot merge unrelated monotonic clocks by subtracting their displayed UTC times.

## Contract or resolver changed

Use the exact adapter code and configuration captured in metadata. A receiver mapping, TTL or implementation change is a new experiment. Restore the pinned version for reporting or begin a new session. Do not edit fingerprints in the original evidence to suppress the mismatch.

## Everything is unknown

Check the selected input entities, item-to-room binding, `last_reported` values and TTL. A restored state is unknown until refreshed. Future timestamps and unavailable/unknown entity states remain unknown. A normal HA state update cadence may exceed a short TTL; choose and record a justified TTL before capture, rather than changing it after seeing results.

## No labelled intervals or excluded trials

Provide independent start and matching stop/exit labels. Use `settled` for still/empty phases and `action_start` for walking/adjacent phases. Check trial ID, target room and phase consistency. Uncertain/interrupted labels, transition margins longer than the trial, or an incomplete capture exclude intervals. Diagnostic snapshot counts without labels are not accuracy measurements.

## Joint report requires node IDs

Add a unique `node_id` to every receiver before initializing a joint experiment. Use the producer's explicit binding for each ID. Consumer-only analysis does not require IDs. A node-to-room/marker mismatch is rejected even if timestamps overlap.

## Joint diagnostic says invalid

Review its reasons and the original producer/consumer records. Incomplete recordings, producer-declared invalid observations, reported errors, missing overlap, large sample gaps or a short sample span remain invalid diagnostics. A structurally consistent failed experiment is useful evidence and should not be discarded to manufacture a success.

## Report file already exists

Writers use exclusive creation. Preserve or move the earlier report yourself, then rerun. Demo also requires a new output directory. Original capture files should remain immutable.

## Live capture fails

Install the `record` extra and set `HA_TOKEN` in the process environment. Use a bare HTTP(S) origin without credentials, paths, queries or fragments. Verify your own account can read the selected entities. The tool prints exception classes and general diagnostics rather than raw response bodies or tokens. A failed recording may leave an interrupted capture that should be retained and interpreted as incomplete.

Submit bugs with package/Python versions and invented fixtures only. Do not attach real captures, tokens, addresses, host/boot identifiers, room layouts or operator notes to public issues.
