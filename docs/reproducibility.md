# Reproducible operation and upgrades

## What a release establishes

The release channel describes the recorder, evidence contracts and reporting
software. A release candidate or stable release does not certify sensing
accuracy, coverage, a particular Home Assistant integration or the independence
of labels. `validation_decision` remains `not_evaluated`. A joint diagnostic marked
`complete` means the supplied evidence passed structural checks; it is not an
acceptance decision about a detector.

Use the kit for controlled comparisons, investigation of unknown periods, and
review of binding and timing consistency. Decide which conditions, repeats and
error limits matter before recording. Keep failed and interrupted experiments;
discarding them can make an evaluation misleading.

## Pin the environment before collecting evidence

Select a tag from [Releases](https://github.com/ha-homelab/sensing-evidence-kit/releases)
and follow [signature verification](release-signatures.md). Save the verified
wheel, source revision and adapter configuration privately. Use a dedicated
Python 3.11 or newer environment. The core report/demo commands have no runtime
dependencies; capture additionally needs the selected release's `record` extra.
For an exact downloaded wheel:

```sh
python3 -m venv /path/to/evidence-venv
/path/to/evidence-venv/bin/python -m pip install '/path/to/downloaded-release.whl[record]'
/path/to/evidence-venv/bin/sensing-evidence --version
/path/to/evidence-venv/bin/sensing-evidence-demo /path/to/new-demo
```

Replace these paths with the real environment, wheel filename and a new output
directory. Live recording and labelling support macOS and Linux and must remain
on one host and OS boot. Offline reporting can use copied original evidence with
the matching adapter. Never modify host/boot identity or fingerprints to bypass
a mismatch.

Keep credentials in the process environment and use an explicit final Home
Assistant origin. Recorder WebSocket redirects are rejected before authentication.
The recorder requests state snapshots and never invokes Home Assistant services.
It does not subscribe to every event: short changes between polls can be missed.

## Preserve an evidence chain you can actually reproduce

Keep `metadata.json`, the complete `capture.jsonl`, `labels.jsonl` when present,
the adapter configuration, the selected wheel and any custom adapter source.
For a joint report retain the producer metadata, capture and summary as well.
Copy files only after recording and labelling have stopped. Back up exact bytes;
reformatting JSON changes the original-file hashes used by joint analysis.

The metadata pins adapter configuration and resolver implementation. A TTL,
receiver binding, room mapping or resolver change starts a new experiment.
The normal report stores hashes of parsed JSON; the joint report hashes original
bytes. Neither is a digital signature or proof that the supplied measurements or
human labels were honest. Preserve provenance separately if independent review
requires it.

The recorder keeps selected states and an allowlist of attributes. This reduces
collection; it is not automatic anonymization or secret redaction. State text,
allowed attributes (including nested evidence), entity IDs, location labels and
operator notes may still identify people or reveal private activity. Host hashes
are opaque identifiers, not a guarantee against guessing. Review an exported copy
before sharing and use invented fixtures in public issues. Editing or redacting
an export invalidates its original hashes; retain originals privately rather
than presenting changed files as the same evidence.

## Read known and unknown time conservatively

Each snapshot can contribute only until the next snapshot, its freshness expiry,
or the maximum sample gap. The last snapshot has no following sample interval and
contributes no duration. Missing request timing or excessive request duration
also prevents known-time credit. Time outside supported intervals remains
unknown, including intervals before capture starts or after its last sample.

A `last_reported` timestamp later than the sample's receipt time remains unknown
throughout that sample's projected interval, even when the report evaluation
clock later reaches that timestamp. Only a later independently captured sample
can make it usable. Invalid, stale and restored data must never count as a correct
negative. The binary adapter reports presence/quiet; its motion metrics cannot
establish whether a person walked or remained still.

Producer error/boundary records may be written near their related sample rather
than in timestamp order. Their timestamps must still lie between producer
metadata and its terminal record. Passing joint checks does not independently
verify the producer's declared observation validity or exact end-to-end latency.

## Upgrade or roll back without rewriting an experiment

Finish recording and labelling before changing environments. Keep the old
environment for reports against its pinned resolver. Install a candidate in a
separate environment, run its synthetic demonstration, then start a new session
for new measurements. A resolver mismatch after upgrade is an intentional
boundary; use the prior resolver instead of editing metadata.

If comparing reporting-engine versions against compatible evidence, retain both
reports under distinct filenames together with the exact package versions.
This release corrects future-timestamp handling, so previously reported known
seconds can become unknown. That is a calculation correction, not changed raw
evidence. The joint checker also rejects records dated after the producer's
terminal record. Investigate producer timing before repeating an experiment.

Report files are created exclusively. Move an earlier report to a clearly
versioned filename before rerunning the consumer command; the joint command
accepts an explicit new `--output`. Do not overwrite the capture to make a report
pass. To roll back the software, select the saved environment and wheel; original
evidence needs no migration.
