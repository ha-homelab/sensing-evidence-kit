# Release-candidate fuzz testing

## Evidence identity and clock joins

The target sends mutated JSON through the production strict decoder, anchor validator and clock-join validator. Accepted anchors round-trip without nonfinite values, valid joins are deterministic and nondecreasing, and changing host, boot or session identity must reject the join. Seeds exercise same-time and next-time samples, backwards clocks, duplicate fields and mismatched boot identities.

All evidence is synthetic and in memory. The harness does not call capture, clock discovery, filesystem recording or an external service. It validates evidence structure and provenance boundaries, not a sensing device or occupancy model.

## When it runs and what it costs

This public repository uses the pinned `venus-os-ci-toolkit` reusable fuzz workflow from its existing release pipeline. A maintainer dispatches `release-pipeline.yml` on the default branch with `channel=rc`. Public visibility, the default branch and the RC channel are checked before allocating a fuzz runner and again by the runner. Unknown visibility fails closed. Beta, nightly, stable, pull-request and ordinary push events do not launch a mutation campaign.

The manifest contains 1 target(s), each bounded to 60 seconds, for 60 seconds of mutation plus dependency/build setup. The shared job has a 30-minute cap. Dependencies and the shared workflow are pinned; Python wheels use reviewed SHA-256 locks, and Go uses its committed module locks. Targets run with a restricted environment and without network access in an isolated Linux network namespace.

Ordinary CI retains fixed regression tests. Python adopters also perform cheap deterministic seed replay and instrumentation checks on relevant changes. These checks are not an RC fuzz campaign and do not qualify a release.

## Reproducing and reading results

Read `.github/fuzz.json` for exact commands, target budgets and corpus paths. On a Linux machine with the declared toolchain, run its setup commands and then:

```sh
python3 scripts/release_fuzz.py preflight --output /tmp/sensing-evidence-kit-fuzz-preflight
```

Use a new output directory. This replays seeds without a timed mutation campaign. A qualified RC must come from the public default-branch release dispatch.

The workflow retains bounded diagnostics and generated failure inputs. A successful `fuzz-report.json` includes the source SHA, run and attempt, manifest digest, positive engine execution counts and available coverage metrics. Python reports additionally include proof that the declared production functions were instrumented. The RC publisher verifies the report against the frozen release inputs and includes it in the release asset inventory. Failure, unexpected skip or missing evidence blocks the RC. Counters describe this campaign, not complete application coverage.

A failure must become a committed regression seed and a focused production fix before a new RC is accepted. Never dismiss a crash by swallowing unexpected exceptions or weakening an invariant. Do not upload credentials, household identifiers or captured private data as corpus.

## Adoption status

The harness and gates are being introduced in this change. The first accepted RC and its source-bound report will be recorded after the actual campaign succeeds; the documentation badge indicates RC-only adoption, not a coverage guarantee.

[Shared execution, evidence and promotion contract](https://github.com/victron-venus/venus-os-ci-toolkit/blob/5087530d6f327565b818fd84f64639abe03ad5e3/docs/rc-fuzzing.md).
