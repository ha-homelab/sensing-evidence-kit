# Tutorial

## Start offline

Run `sensing-evidence-demo demo-output` in a fresh directory. Existing output directories are not overwritten. Open the generated HTML and compare `report.json` with `joint-report.json`. Inspect the original JSON/JSONL bytes in the `ha` and `producer` subdirectories. All identifiers and observations are synthetic.

To recreate the consumer report using the CLI, write into a fresh output name: the default report command writes `ha/report.json`, which does not exist in the demo bundle initially.

```sh
sensing-evidence --config demo-output/entities.json demo-output/ha report
sensing-evidence-joint demo-output/ha demo-output/producer \
  --config demo-output/entities.json --output demo-output/joint-second.json
```

These commands perform no network access. Reports never overwrite an existing report file.

## Configure a private experiment

Copy `examples/entities.json` outside the repository and replace the invented room/entity identifiers with your own. The configuration maps rooms to report output identifiers and receivers to input binary entities. The output names are report keys; the package does not create those entities in Home Assistant.

Each receiver supplies `item_id`, `room`, `entity_id` and `sensor`. Optional `node_id` is used only for producer/consumer joins. Use `examples/entities-with-nodes.json` as a synthetic example. `ttl_seconds` limits how long an entity's `last_reported` timestamp can be treated as fresh; it is not a device accuracy threshold.

Create a new owner-only session on the machine that will also record and label it:

```sh
sensing-evidence --config /path/to/entities.json /path/to/private-session init \
  --session-id experiment-001 --transition-seconds 5
```

Optionally supply `--fingerprint` with a producer configuration identifier and `--clock-uncertainty-ms` with an independently measured uncertainty. Missing values remain unknown. A successful initialization is not a successful test.

## Record read-only observations

Install the `record` extra, then set `HA_TOKEN` in your process environment using your normal secret-management workflow. Do not put it in configuration or commit it to the repository. Start a bounded capture against your own explicit Home Assistant HTTP(S) origin:

```sh
sensing-evidence --config /path/to/entities.json /path/to/private-session record \
  --origin https://ha.example.invalid --seconds 120 --interval 2
```

Replace the reserved example hostname. Durations are capped at one hour and polling intervals at 1–5 seconds. Capture records selected states, whitelisted attributes, request/sample timestamps and binding/model fingerprints. It checks bindings again before writing a completion record. It does not start a producer recorder or control a device.

## Add independent labels

In another terminal on the **same machine and OS boot**, observe the experiment directly and mark transitions. Do not derive labels from the sensor predictions.

```sh
sensing-evidence --config /path/to/entities.json /path/to/private-session mark \
  --trial-id empty-1 --target-room zone_a --phase empty_calibration \
  --event settled --occupied-rooms --action "Area confirmed empty" \
  --reference "Independently observed target area"
```

At the end, repeat the command with `--event exit`. For a stillness trial use `--phase still`, `--event settled`, and list the independently occupied room after `--occupied-rooms`. Walking and adjacent-room trials begin with `action_start` and close with matching `action_stop` or `exit`. An adjacent-room trial must identify at least one occupied room while leaving its target room empty.

Use `--uncertainty` or an `interruption` event when you cannot support a clean label. Such intervals are excluded. One operator process should append labels at a time. Do not reboot or move the session between machines while recording or labelling.

## Report and interpret

```sh
sensing-evidence --config /path/to/entities.json /path/to/private-session report
```

The report requires the same adapter configuration and implementation fingerprint. It separates unknown time from known state, trims transition margins and excludes unclosed/uncertain trials. Without independent labels it produces diagnostic snapshot counts, not accuracy metrics. A capture without its verified closing record cannot qualify a labelled trial.

Keep original files unchanged. If you need to rerun reporting, preserve the previous report under another filename first. Do not edit original evidence to obtain a desired result. See the contract for the difference between diagnostic completeness and independent validation.
