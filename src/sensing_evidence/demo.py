# SPDX-License-Identifier: MIT
"""Generate invented, offline evidence through the production reporting APIs."""

import argparse
from datetime import datetime, timedelta, timezone
import html
import json
from pathlib import Path

from . import joint, session
from .adapters import EntityAdapter


def configuration():
    return {
        "rooms": {"zone_a": "sensor.zone_a_activity", "zone_b": "sensor.zone_b_activity"},
        "receivers": [
            {
                "item_id": "sample_a",
                "room": "zone_a",
                "entity_id": "binary_sensor.sample_a",
                "sensor": "sensor.sample_a_activity",
                "node_id": 1,
            },
            {
                "item_id": "sample_b",
                "room": "zone_b",
                "entity_id": "binary_sensor.sample_b",
                "sensor": "sensor.sample_b_activity",
                "node_id": 2,
            },
        ],
        "ttl_seconds": 3,
    }


def synthetic_bundle():
    """Return byte-exact evidence and its adapter. No actual host/boot IDs are read."""
    adapter = EntityAdapter(configuration())
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def clock(seconds):
        return {
            "observed_utc": (base + timedelta(seconds=seconds)).isoformat(),
            "monotonic_ns": 1_000_000_000 + round(seconds * 1e9),
        }

    def record(seconds, **values):
        return {
            "schema_version": 1,
            "session_id": "synthetic-session",
            "host_id": "synthetic-host",
            "boot_id": "synthetic-boot",
            **clock(seconds),
            **values,
        }

    metadata = record(
        0,
        contract=adapter.CONFIG,
        contract_sha256=session.digest(adapter.CONFIG),
        resolver_sha256=adapter.fingerprint(),
        recorder_sha256="0" * 64,
        source_revision="synthetic",
        producer_fingerprint="synthetic-producer",
        purpose="characterization",
        clock_tolerance_seconds=2,
        clock_offset_uncertainty_ms=None,
        transition_seconds=0,
        max_sample_gap_seconds=5,
        acceptance_limits=None,
    )
    items = [
        {"id": item["item_id"], "room": item["room"], "entity_id": item["entity_id"]}
        for item in adapter.CONFIG["receivers"]
    ]
    binding = {
        "items": items,
        "binding_sha256": session.digest(items),
        "model_sha256": session.digest(items),
        "inventory_revision": session.digest(adapter.CONFIG),
    }
    capture, producer = [], []
    for index, seconds in enumerate(range(1, 22, 2)):
        active = 4 <= index <= 6
        stale = index in (7, 8)
        states = {}
        for receiver in adapter.CONFIG["receivers"]:
            first = receiver["node_id"] == 1
            states[receiver["entity_id"]] = {
                "state": "on" if first and active else "off",
                "last_reported": clock(0 if first and stale else seconds)["observed_utc"],
                "attributes": {},
            }
        capture.append(
            record(seconds, kind="sample", request_started=clock(seconds - 0.1), **binding, states=states)
        )
        producer.append(
            record(
                seconds,
                stream="ruview_producer",
                kind="sample",
                source="esp32",
                observation_valid=True,
                issues=[],
                nodes=[{"node_id": 1}, {"node_id": 2}],
            )
        )
    capture.append(
        record(
            22,
            kind="complete",
            samples=11,
            inventory_checked=True,
            **{k: v for k, v in binding.items() if k != "items"},
        )
    )
    label = dict(
        trial_id="synthetic-empty",
        phase="empty_calibration",
        target_room="zone_a",
        occupied_rooms=[],
        action="invented empty-room interval",
        reference_point_or_path="synthetic test area",
        uncertainty="",
        note="All data is invented; not a live experiment.",
    )
    labels = [record(1, event="settled", **label), record(21, event="exit", **label)]

    def encoded(value):
        return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()

    def jsonl(values):
        return b"".join((json.dumps(value, sort_keys=True) + "\n").encode() for value in values)

    raw_metadata = encoded(metadata)
    producer_metadata = record(
        0.5,
        stream="ruview_producer",
        kind="metadata",
        requested_duration_s=20,
        local_monotonic_alignment=True,
        consumer_metadata_sha256=joint.sha256(raw_metadata),
        consumer_anchor={
            k: metadata[k]
            for k in (
                "schema_version",
                "session_id",
                "host_id",
                "boot_id",
                "observed_utc",
                "monotonic_ns",
                "clock_tolerance_seconds",
            )
        },
        node_bindings={
            str(item["node_id"]): {"room": item["room"], "floorplan_marker_id": item["item_id"]}
            for item in adapter.CONFIG["receivers"]
        },
        collector_clock_offset_uncertainty_ms=None,
    )
    completion = dict(
        recording_complete=True, capture_status="complete", reasons=[], validation_decision="not_evaluated"
    )
    producer.append(record(22, stream="ruview_producer", kind="terminal", samples=11, **completion))
    raw_producer = jsonl(producer)
    summary = record(
        23,
        stream="ruview_producer",
        kind="summary",
        stream_complete=True,
        sample_count=11,
        samples=11,
        coverage_validated=False,
        evidence_integrity="valid",
        capture_sha256=joint.sha256(raw_producer),
        **completion,
    )
    return {
        "ha_metadata": raw_metadata,
        "ha_capture": jsonl(capture),
        "ha_labels": jsonl(labels),
        "producer_metadata": encoded(producer_metadata),
        "producer_capture": raw_producer,
        "producer_summary": encoded(summary),
    }, adapter


def results(files, adapter):
    report = session.report(
        session.strict_json(files["ha_metadata"]),
        joint.load_jsonl(files["ha_capture"]),
        joint.load_jsonl(files["ha_labels"]),
        adapter,
    )
    return report, joint.analyze(files, adapter)


def render_html(report, combined):
    metrics = report["trials"][0]["observations"]["sensor.zone_a_activity"]
    cards = [
        ("Labelled interval", "20 s", "Invented empty-room observation"),
        ("Known state", f"{metrics['known_seconds']:g} s", "Freshness gates passed"),
        ("Unknown state", f"{metrics['unknown_seconds']:g} s", "Stale data stays unknown"),
        (
            "False presence",
            f"{metrics['false_presence_seconds']:g} s",
            "Positive observation during empty label",
        ),
    ]
    body = "".join(
        f"<article><span>{html.escape(label)}</span><h2>{html.escape(value)}</h2><p>{html.escape(note)}</p></article>"
        for label, value, note in cards
    )
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8"><title>Sensing evidence — synthetic demonstration</title><style>*{box-sizing:border-box}body{background:#f4f3ef;color:#182a31;font:18px system-ui,sans-serif;margin:0;padding:64px;max-width:1400px}.eyebrow{font-size:13px;font-weight:750;letter-spacing:.14em;color:#356762}h1{font-size:54px;letter-spacing:-.045em;margin:18px 0}.lead{max-width:940px;color:#53656b;line-height:1.7}.tag{font-size:13px;display:inline-block;background:#e8dbc3;color:#664d23;border-radius:6px;padding:8px 12px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:36px 0}article{padding:24px;background:white;border:1px solid #d9dfdc;border-radius:12px}article span{font-size:16px;font-weight:650}h2{font-size:42px;margin:20px 0 8px}article p{font-size:14px;color:#617279;line-height:1.5}.timeline{border:1px solid #d9dfdc;border-radius:12px;background:white;padding:28px}.bar{display:flex;height:46px;border-radius:7px;overflow:hidden;margin-top:24px}.quiet{background:#82b6a4;width:40%}.positive{background:#d99e6e;width:30%}.unknown{background:#aebcc4;width:20%}.last{background:#82b6a4;width:10%}.legend{color:#53656b;font-size:15px;line-height:2}.decision{margin-top:28px;font-size:21px;font-weight:650}.decision code{color:#9a633d}footer{border-top:1px solid #cbd6d2;margin-top:32px;padding-top:24px;color:#53656b;font-size:15px;line-height:1.8}</style><span class="eyebrow">HA-HOMELAB / SENSING EVIDENCE KIT</span><h1>Measure the evidence.<br>Keep the uncertainty.</h1><span class="tag">ALL DATA IS SYNTHETIC</span><p class="lead">Independent labels and timestamped observations answer different questions. This invented example measures disagreement and missing data without turning recording completeness into a validated detector.</p><section class="cards">"""
        + body
        + """</section><section class="timeline"><strong>One labelled interval · zone_a empty · 20 seconds</strong><div class="bar"><div class="quiet"></div><div class="positive"></div><div class="unknown"></div><div class="last"></div></div><p class="legend">Green: quiet / consistent with label &nbsp; Orange: presence / disagrees with label &nbsp; Gray: stale / unknown</p></section><div class="decision">Validation decision: <code>not_evaluated</code></div><footer>Consumer recording complete: """
        + str(report["capture_complete"]).lower()
        + """ · Producer/consumer diagnostic: """
        + html.escape(combined["diagnostic_status"])
        + """ · Shared sample window: """
        + str(combined["sample_window_overlap_seconds"])
        + """ seconds<br>Screenshot of an offline synthetic demonstration. No home, device, network, operator or runtime evidence is included.<br>Reproduce: <code>sensing-evidence-demo demo-output</code></footer></html>"""
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory", type=Path, help="New output directory; existing evidence is never overwritten"
    )
    args = parser.parse_args(argv)
    files, adapter = synthetic_bundle()
    report, combined = results(files, adapter)
    args.directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    for group in ("ha", "producer"):
        folder = args.directory / group
        folder.mkdir(mode=0o700)
        for key, value in files.items():
            prefix, name = key.split("_", 1)
            if prefix == group:
                suffix = ".jsonl" if name in {"capture", "labels"} else ".json"
                (folder / (name + suffix)).write_bytes(value)
    session.write_json(args.directory / "entities.json", configuration())
    session.write_json(args.directory / "report.json", report)
    session.write_json(args.directory / "joint-report.json", combined)
    (args.directory / "demo.html").write_text(render_html(report, combined))
    print(f"Created synthetic demonstration in {args.directory}; validation not evaluated.")


if __name__ == "__main__":
    main()
