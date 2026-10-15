# SPDX-License-Identifier: MIT
"""Sensing evidence and independent labels; never certifies a detector.

Adapters supply observation semantics; the shared engine checks clocks,
bindings, recording completeness and independent labels.
"""

import argparse
import asyncio
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from types import SimpleNamespace
from urllib.parse import urlsplit

MAX_FILE_BYTES = 256 * 1024 * 1024

PHASES = ("empty_calibration", "still", "walking", "adjacent_target_empty", "empty_recovery")
EVENTS = ("entry", "settled", "action_start", "action_stop", "exit", "interruption")
ATTRIBUTES = {
    "source",
    "node_id",
    "placement_valid",
    "measurement_location",
    "configured_room",
    "room_id",
    "room_coverage_validation",
    "csi_age_ms",
    "inference_age_ms",
    "classification",
    "confidence",
    "restored",
    "room",
    "evidence",
}


@lru_cache(maxsize=1)
def clock_identity():
    """Opaque host identity and actual OS boot ID; no cross-host monotonic joins."""
    if sys.platform == "darwin":
        boot = subprocess.check_output(["sysctl", "-n", "kern.bootsessionuuid"], text=True).strip()
    elif sys.platform.startswith("linux"):
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    else:
        raise ValueError("Live evidence clock identity currently supports macOS and Linux")
    return dict(host_id=hashlib.sha256(socket.gethostname().encode()).hexdigest(), boot_id=boot)


def stamp():
    return {"observed_utc": datetime.now(timezone.utc).isoformat(), "monotonic_ns": time.monotonic_ns()}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def read_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Evidence file exceeds size limit")
    return strict_json(path.read_text())


def strict_json(text):

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("Duplicate JSON key in evidence")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("Non-finite JSON number in evidence")

    def finite_float(text):
        value = float(text)
        if not math.isfinite(value):
            invalid_constant(text)
        return value

    return json.loads(
        text, object_pairs_hook=pairs, parse_constant=invalid_constant, parse_float=finite_float
    )


def write_json(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(value, output, indent=2, allow_nan=False)
        output.write("\n")


def rows(path):
    result = []
    if Path(path).stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Evidence file exceeds size limit")
    with Path(path).open() as source:
        for line in source:
            if not line.endswith("\n") or not line.strip():
                raise ValueError("Truncated or blank JSONL evidence record")
            result.append(strict_json(line))
    return result


def write_row(output, value):
    output.write(json.dumps(value, allow_nan=False) + "\n")
    output.flush()


def timestamp(text):
    try:
        if isinstance(text, str) and text.endswith("Z"):
            text = text[:-1] + "+00:00"
        value = datetime.fromisoformat(text)
        return value if value.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def validate_anchor(metadata):
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be an object")
    if type(metadata.get("schema_version")) is not int or metadata["schema_version"] != 1:
        raise ValueError("Unsupported evidence schema")
    for key in ("session_id", "host_id", "boot_id"):
        value = metadata.get(key)
        if not isinstance(value, str) or not 1 <= len(value) <= 256 or any(ord(c) < 32 for c in value):
            raise ValueError("Missing or invalid session/clock identity")
    if timestamp(metadata.get("observed_utc")) is None:
        raise ValueError("Metadata requires an offset-aware timestamp")
    if type(metadata.get("monotonic_ns")) is not int or not 0 <= metadata["monotonic_ns"] <= 2**64 - 1:
        raise ValueError("Invalid monotonic clock anchor")
    tolerance = metadata.get("clock_tolerance_seconds")
    if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or not 0 < tolerance <= 2:
        raise ValueError("Clock tolerance must be finite and in (0, 2] seconds")


def checked_time(record, metadata):
    validate_anchor(metadata)
    if not isinstance(record, dict):
        raise ValueError("Evidence record must be an object")
    if (
        type(record.get("schema_version")) is not int
        or record.get("schema_version") != 1
        or record.get("session_id") != metadata["session_id"]
    ):
        raise ValueError("Record schema/session does not match metadata")
    if any((record.get(key) != metadata.get(key) for key in ("host_id", "boot_id"))):
        raise ValueError("Cannot compare monotonic clocks across hosts or boots")
    when, start = (timestamp(record.get("observed_utc")), timestamp(metadata["observed_utc"]))
    ns = record.get("monotonic_ns")
    if not when or type(ns) is not int or not 0 <= ns <= 2**64 - 1:
        raise ValueError("Record needs UTC with an offset and integer monotonic_ns")
    elapsed = (ns - metadata["monotonic_ns"]) / 1000000000.0
    if elapsed < 0 or abs((when - start).total_seconds() - elapsed) > metadata["clock_tolerance_seconds"]:
        raise ValueError("Clock discontinuity or another host/boot: start a new session")
    return ns / 1000000000.0


def new_record(metadata, **values):
    return dict(schema_version=1, session_id=metadata["session_id"], **clock_identity(), **stamp(), **values)


def init_session(args, adapter):
    if not re.fullmatch("[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", args.session_id):
        raise ValueError("Use a short session ID containing letters, digits, dash, dot or underscore")
    args.directory.mkdir(parents=True, exist_ok=False, mode=448)
    revision = getattr(adapter, "source_revision", "adapter-defined")
    metadata = dict(
        schema_version=1,
        session_id=args.session_id,
        **clock_identity(),
        **stamp(),
        source_revision=revision,
        recorder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        contract=adapter.CONFIG,
        contract_sha256=digest(adapter.CONFIG),
        resolver_sha256=adapter_fingerprint(adapter),
        producer_fingerprint=args.fingerprint,
        purpose="characterization",
        clock_source="capture host UTC + monotonic_ns; labels must use the same host/boot",
        clock_offset_uncertainty_ms=args.clock_uncertainty_ms,
        clock_tolerance_seconds=2,
        transition_seconds=args.transition_seconds,
        max_sample_gap_seconds=5,
        acceptance_limits=None,
    )
    write_json(args.directory / "metadata.json", metadata)
    print(f"Created session {args.session_id}; no labels or validation assumed")


def validate_label(label, metadata, adapter):
    checked_time(label, metadata)
    if label.get("phase") not in PHASES or label.get("event") not in EVENTS:
        raise ValueError("Unknown phase or event")
    room, occupied = (label.get("target_room"), label.get("occupied_rooms"))
    if (
        not isinstance(room, str)
        or room not in adapter.CONFIG["rooms"]
        or not isinstance(occupied, list)
        or any((not isinstance(r, str) or r not in adapter.CONFIG["rooms"] for r in occupied))
        or (len(occupied) != len(set(occupied)))
    ):
        raise ValueError(
            "Use explicit distinct room IDs; an empty list independently declares no occupied rooms"
        )
    if not all(
        (
            isinstance(label.get(key), str) and 0 < len(label[key].strip()) <= 512
            for key in ("trial_id", "action", "reference_point_or_path")
        )
    ):
        raise ValueError("trial_id, action and reference_point_or_path are required")
    if label["event"] in ("settled", "action_start"):
        expected_occupied = label["phase"] in ("still", "walking")
        if (room in occupied) != expected_occupied:
            raise ValueError("Occupied rooms contradict the phase")
        if label["phase"] == "adjacent_target_empty" and (not occupied):
            raise ValueError("Identify the occupied adjacent room independently")


def mark(args, adapter):
    metadata = read_json(args.directory / "metadata.json")
    verify_contract(metadata, adapter)
    label = new_record(
        metadata,
        trial_id=args.trial_id,
        target_room=args.target_room,
        phase=args.phase,
        event=args.event,
        occupied_rooms=args.occupied_rooms,
        action=args.action,
        reference_point_or_path=args.reference,
        uncertainty=args.uncertainty,
        note=args.note,
    )
    validate_label(label, metadata, adapter)
    path = args.directory / "labels.jsonl"
    previous = rows(path) if path.exists() else []
    if previous and checked_time(previous[-1], metadata) >= checked_time(label, metadata):
        raise ValueError("Labels must be ordered; use a single operator/host")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(descriptor, "a") as output:
        write_row(output, label)
    print(f"Recorded {args.trial_id}: {args.phase}/{args.event}; independent operator label")


def select_states(states, adapter):
    return {
        s["entity_id"]: {
            "state": s["state"],
            "last_reported": s.get("last_reported"),
            "last_updated": s.get("last_updated"),
            "attributes": {k: v for k, v in s.get("attributes", {}).items() if k in ATTRIBUTES},
        }
        for s in states
        if s.get("entity_id") in tracked_entities(adapter)
    }


def select_items(view, adapter):
    keys = ("id", "room", "entity_id", "position", "rotation", "dimensions")
    return sorted(
        (
            {k: item[k] for k in keys if k in item}
            for item in view["items"]
            if item.get("id") in tracked_items(adapter)
        ),
        key=lambda item: item["id"],
    )


async def reject_capture_redirect(_client, _context, params):
    """Abort before a redirected socket can request the Home Assistant token."""
    params.response.close()
    raise ValueError("Home Assistant redirects are not allowed")


async def capture(args, adapter):
    try:
        import aiohttp
    except ImportError as error:
        raise ValueError("Live recording requires aiohttp; use the documented virtual environment") from error
    url = urlsplit(args.origin)
    if (
        url.scheme not in ("http", "https")
        or not url.hostname
        or url.username
        or url.password
        or (url.path not in ("", "/"))
        or url.query
        or url.fragment
    ):
        raise ValueError("Provide an HTTP(S) origin without credentials, path, query or fragment")
    origin = args.origin.rstrip("/")
    metadata = read_json(args.directory / "metadata.json")
    verify_contract(metadata, adapter)
    checked_time(new_record(metadata), metadata)
    token = os.environ.get("HA_TOKEN")
    trace = aiohttp.TraceConfig()
    trace.on_request_redirect.append(reject_capture_redirect)
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=20), trace_configs=[trace]
    ) as client:
        if not token:
            if not hasattr(adapter, "access_token"):
                raise ValueError("Set HA_TOKEN in the environment for read-only recording")
            token = await adapter.access_token(client, origin)
        async with client.ws_connect(
            origin.replace("https:", "wss:").replace("http:", "ws:") + "/api/websocket",
            origin=origin,
            compress=15,
            max_msg_size=40 * 1024 * 1024,
        ) as ws:
            if (await ws.receive_json(timeout=20)).get("type") != "auth_required":
                raise ValueError("Unexpected HA authentication handshake")
            await ws.send_json(dict(type="auth", access_token=token))
            if (await ws.receive_json(timeout=20)).get("type") != "auth_ok":
                raise ValueError("HA authentication failed")
            del token
            sequence = 0

            async def call(kind, **values):
                nonlocal sequence
                sequence += 1
                await ws.send_json(dict(id=sequence, type=kind, **values))
                try:
                    timeout = getattr(adapter, "request_timeout", 20)
                    result = await ws.receive_json(timeout=timeout(kind) if callable(timeout) else timeout)
                except asyncio.TimeoutError as error:
                    raise ValueError(f"HA read timed out: {kind}") from error
                if result.get("id") != sequence or not result.get("success"):
                    raise ValueError(f"HA read failed: {kind}")
                return result["result"]

            binding = await read_binding(adapter, call)
            items = select_items({"items": binding["items"]}, adapter)
            binding_hash = digest(items)
            model_hash = binding["model_sha256"]
            revision = binding["revision"]
            start = time.monotonic()
            with (args.directory / "capture.jsonl").open("x") as output:
                count = 0
                try:
                    while time.monotonic() - start < args.seconds:
                        request = stamp()
                        selected = select_states(await call("get_states"), adapter)
                        sample = new_record(
                            metadata,
                            kind="sample",
                            request_started=request,
                            inventory_revision=revision,
                            binding_sha256=binding_hash,
                            model_sha256=model_hash,
                            items=items,
                            states=selected,
                        )
                        checked_time(sample, metadata)
                        write_row(output, sample)
                        count += 1
                        await asyncio.sleep(
                            min(args.interval, max(0, args.seconds - (time.monotonic() - start)))
                        )
                    closing = await read_binding(adapter, call)
                    if (
                        digest(select_items({"items": closing["items"]}, adapter)) != binding_hash
                        or closing["revision"] != revision
                        or closing["model_sha256"] != model_hash
                    ):
                        raise ValueError("Bindings changed during capture; start a new session")
                except BaseException:
                    write_row(
                        output,
                        new_record(
                            metadata, kind="interrupted", reason="capture stopped; review this session"
                        ),
                    )
                    raise
                write_row(
                    output,
                    new_record(
                        metadata,
                        kind="complete",
                        samples=count,
                        inventory_checked=True,
                        binding_sha256=binding_hash,
                        model_sha256=model_hash,
                        inventory_revision=revision,
                    ),
                )
            print(f"Captured {count} filtered HA snapshots; no devices controlled or labels inferred")


def verify_contract(metadata, adapter):
    validate_anchor(metadata)
    for key, lower, upper in (("transition_seconds", 0, 300), ("max_sample_gap_seconds", 0.001, 60)):
        value = metadata.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper:
            raise ValueError("Invalid transition or sample-gap limit")
    if (
        metadata.get("schema_version") != 1
        or metadata.get("contract_sha256") != digest(adapter.CONFIG)
        or metadata.get("resolver_sha256") != adapter_fingerprint(adapter)
        or (digest(metadata.get("contract")) != metadata.get("contract_sha256"))
    ):
        raise ValueError("Consumer contract/resolver changed; use the pinned revision or start a new session")


def as_states(sample):
    states = sample.get("states")
    if not isinstance(states, dict):
        raise ValueError("Sample states must be an object")
    result = {}
    for key, value in states.items():
        if (
            not isinstance(key, str)
            or not isinstance(value, dict)
            or not isinstance(value.get("state"), str)
            or not isinstance(value.get("attributes", {}), dict)
        ):
            raise ValueError("Invalid state record")
        result[key] = SimpleNamespace(
            state=value["state"],
            attributes=value.get("attributes", {}),
            last_reported=timestamp(value.get("last_reported")) or datetime.min.replace(tzinfo=timezone.utc),
        )
    return result


def validate_sample(sample, metadata):
    if not isinstance(sample.get("items"), list):
        raise ValueError("Sample items must be a list")
    ids = []
    for item in sample["items"]:
        if not isinstance(item, dict) or not all(
            isinstance(item.get(key), str) and item[key] for key in ("id", "room")
        ):
            raise ValueError("Invalid sample binding")
        if "entity_id" in item and (not isinstance(item["entity_id"], str) or not item["entity_id"]):
            raise ValueError("Invalid optional binding entity")
        ids.append(item["id"])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate sample binding")
    for key in ("binding_sha256", "model_sha256"):
        if not isinstance(sample.get(key), str) or not re.fullmatch(r"[a-f0-9]{64}", sample[key]):
            raise ValueError("Invalid sample fingerprint")
    revision = sample.get("inventory_revision")
    if type(revision) not in (str, int) or revision == "":
        raise ValueError("Invalid inventory revision")
    as_states(sample)
    request = sample.get("request_started")
    if request is not None:
        if not isinstance(request, dict):
            raise ValueError("Invalid request start")
        anchor = {key: metadata[key] for key in ("schema_version", "session_id", "host_id", "boot_id")}
        requested = checked_time({**anchor, **request}, metadata)
        if requested > checked_time(sample, metadata):
            raise ValueError("Request starts after the sample")


def observations(sample, when, adapter):
    return adapter.resolve_activity(sample["items"], as_states(sample), when)


def metrics():
    return dict(
        known_seconds=0.0,
        unknown_seconds=0.0,
        positive_seconds=0.0,
        experimental_seconds=0.0,
        false_presence_seconds=0.0,
        missed_presence_seconds=0.0,
        motion_during_still_seconds=0.0,
        no_motion_during_walking_seconds=0.0,
        adjacent_leakage_seconds=0.0,
    )


def add_metric(result, value, phase, duration):
    experimental = value.startswith("unverified_") or value == "experimental"
    state = value.removeprefix("unverified_")
    if state not in ("quiet", "motion", "presence", "experimental"):
        return
    positive = state != "quiet"
    result["known_seconds"] += duration
    result["positive_seconds"] += duration * positive
    result["experimental_seconds"] += duration * experimental
    if phase in ("empty_calibration", "empty_recovery", "adjacent_target_empty"):
        result["false_presence_seconds"] += duration * positive
    else:
        result["missed_presence_seconds"] += duration * (not positive)
    if phase == "still":
        result["motion_during_still_seconds"] += duration * (state == "motion")
    if phase == "walking":
        result["no_motion_during_walking_seconds"] += duration * (state in ("quiet", "presence"))
    if phase == "adjacent_target_empty":
        result["adjacent_leakage_seconds"] += duration * positive


def report(metadata, capture_rows, labels, adapter):
    verify_contract(metadata, adapter)
    if not isinstance(capture_rows, list) or not isinstance(labels, list):
        raise ValueError("Capture and labels must be lists")
    for stream in (capture_rows, labels):
        times = [checked_time(record, metadata) for record in stream]
        if any((b <= a for a, b in zip(times, times[1:]))):
            raise ValueError("Evidence must be strictly ordered on one monotonic clock")
    for label in labels:
        validate_label(label, metadata, adapter)
    samples = [row for row in capture_rows if row.get("kind") == "sample"]
    if not samples:
        raise ValueError("No observation samples")
    for sample in samples:
        validate_sample(sample, metadata)
    if any((s.get("binding_sha256") != digest(s["items"]) for s in samples)) or any(
        (
            len({s.get(key) for s in samples}) != 1
            for key in ("binding_sha256", "model_sha256", "inventory_revision")
        )
    ):
        raise ValueError("Coverage binding/placement fingerprint changed or is inconsistent")
    interrupted_trials = {label["trial_id"] for label in labels if label["event"] == "interruption"}
    warnings = [
        "Characterization only: no automatic pass, calibration or validated promotion.",
        "HA snapshots are not raw CSI/inference capture; short events can fall between polls.",
        "Producer fingerprint, calibration receipt and independent repeat must be reviewed separately.",
    ]
    if not metadata.get("producer_fingerprint"):
        warnings.append("Producer configuration fingerprint is missing.")
    if metadata.get("clock_offset_uncertainty_ms") is None:
        warnings.append("Cross-host clock offset/uncertainty is not measured.")
    complete = capture_rows[-1]
    closed = (
        complete.get("kind") == "complete"
        and complete.get("inventory_checked") is True
        and (type(complete.get("samples")) is int)
        and (complete["samples"] == len(samples))
        and all((r.get("kind") == "sample" for r in capture_rows[:-1]))
        and (complete.get("binding_sha256") == samples[0]["binding_sha256"])
        and (complete.get("model_sha256") == samples[0].get("model_sha256"))
        and (complete.get("inventory_revision") == samples[0].get("inventory_revision"))
        and (not any((r.get("kind") == "interrupted" for r in capture_rows)))
    )
    if not closed:
        warnings.append("Capture did not complete normally; this session cannot qualify coverage.")
    readiness = {}
    for sample in samples:
        for entity, (state, _) in observations(sample, timestamp(sample["observed_utc"]), adapter).items():
            histogram = readiness.setdefault(entity, {})
            histogram[state] = histogram.get(state, 0) + 1
    trials = []
    for index, label in enumerate(labels):
        start_event = "action_start" if label["phase"] in ("walking", "adjacent_target_empty") else "settled"
        if label["event"] != start_event:
            continue
        entry = dict(trial_id=label["trial_id"], phase=label["phase"], target_room=label["target_room"])
        trials.append(entry)
        if not closed:
            entry["excluded"] = "Capture incomplete or closing inventory/model verification missing"
            continue
        if index + 1 == len(labels):
            entry["excluded"] = "Unclosed label interval; mark action_stop or exit"
            continue
        finish = labels[index + 1]
        if label["trial_id"] in interrupted_trials or label.get("uncertainty") or finish.get("uncertainty"):
            entry["excluded"] = "Interrupted or uncertain trial"
            continue
        if (
            finish["trial_id"] != label["trial_id"]
            or finish["target_room"] != label["target_room"]
            or finish["phase"] != label["phase"]
            or (finish["event"] not in ("action_stop", "exit"))
        ):
            entry["excluded"] = "Explicit matching action_stop/exit is required"
            continue
        left = checked_time(label, metadata) + metadata["transition_seconds"]
        right = checked_time(finish, metadata) - metadata["transition_seconds"]
        duration = right - left
        if duration <= 0:
            entry["excluded"] = "No interval after transition exclusion"
            continue
        room = label["target_room"]
        ids = [adapter.CONFIG["rooms"][room]] + [
            s["sensor"] for s in adapter.CONFIG["receivers"] if s["room"] == room
        ]
        results = {entity: metrics() for entity in ids}
        for position, sample in enumerate(samples):
            at = checked_time(sample, metadata)
            if position + 1 == len(samples):
                continue
            a, b = (
                max(left, at),
                min(
                    right,
                    checked_time(samples[position + 1], metadata),
                    at + metadata["max_sample_gap_seconds"],
                ),
            )
            if not isinstance(sample.get("request_started"), dict):
                continue
            request_ns = sample["request_started"]["monotonic_ns"]
            if (
                b <= a
                or (sample["monotonic_ns"] - request_ns) / 1000000000.0 > metadata["max_sample_gap_seconds"]
            ):
                continue
            utc = timestamp(sample["observed_utc"])
            cuts = {a, b}
            for state in as_states(sample).values():
                if deadline := adapter.freshness_deadline(state, utc):
                    expiry = at + (deadline - utc).total_seconds()
                    if a < expiry < b:
                        cuts.add(expiry)
            ordered = sorted(cuts)
            for low, high in zip(ordered, ordered[1:]):
                when = datetime.fromtimestamp(utc.timestamp() + (low + high) / 2 - at, timezone.utc)
                values = observations(sample, when, adapter)
                for entity, result in results.items():
                    add_metric(result, values[entity][0], label["phase"], high - low)
        for value in results.values():
            value["unknown_seconds"] = max(0, duration - value["known_seconds"])
            for key in value:
                value[key] = round(value[key], 3)
        entry.update(labelled_seconds=round(duration, 3), observations=results)
    return dict(
        schema_version=1,
        session_id=metadata["session_id"],
        validation_decision="not_evaluated",
        capture_complete=closed,
        sample_count=len(samples),
        label_count=len(labels),
        warnings=warnings,
        trials=trials,
        diagnostic_snapshot_counts=readiness,
        parsed_json_sha256={
            "metadata": digest(metadata),
            "capture": digest(capture_rows),
            "labels": digest(labels),
        },
    )


def positive_number(text):
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("Expected a finite positive number")
    return value


def main(adapter=None, argv=None):
    from . import __version__

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "directory", type=Path, help="Private session directory (use an owner-only local folder)"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a session before recording or labelling")
    init.add_argument("--session-id", required=True)
    init.add_argument(
        "--fingerprint", help="Optional producer configuration fingerprint; absent means unknown"
    )
    init.add_argument("--clock-uncertainty-ms", type=positive_number)
    init.add_argument("--transition-seconds", type=positive_number, default=5)
    record = commands.add_parser("record", help="Read-only bounded HA snapshot capture; needs aiohttp")
    record.add_argument("--origin", required=True)
    record.add_argument("--seconds", type=positive_number, required=True)
    record.add_argument("--interval", type=positive_number, default=2)
    label = commands.add_parser("mark", help="Append a human observation, independent of predictions")
    label.add_argument("--trial-id", required=True)
    label.add_argument("--target-room", required=True)
    label.add_argument("--phase", choices=PHASES, required=True)
    label.add_argument("--event", choices=EVENTS, required=True)
    label.add_argument("--occupied-rooms", nargs="*", required=True)
    label.add_argument("--action", required=True)
    label.add_argument("--reference", required=True)
    label.add_argument("--uncertainty", default="")
    label.add_argument("--note", default="")
    commands.add_parser("report", help="Write characterization report, never a validation decision")
    parser.add_argument("--config", type=Path, help="Entity adapter JSON")
    args = parser.parse_args(argv)
    if adapter is None:
        from .adapters import EntityAdapter

        if args.config is None:
            parser.error("--config is required")
        adapter = EntityAdapter(read_json(args.config))
    os.umask(63)
    try:
        if args.command == "init":
            init_session(args, adapter)
        elif args.command == "record":
            if not 1 <= args.interval <= 5 or args.seconds > 3600:
                raise ValueError("Use a 1–5 second interval and at most 3600 seconds per capture")
            asyncio.run(capture(args, adapter))
        elif args.command == "mark":
            mark(args, adapter)
        else:
            path = args.directory
            result = report(
                read_json(path / "metadata.json"),
                rows(path / "capture.jsonl"),
                rows(path / "labels.jsonl") if (path / "labels.jsonl").exists() else [],
                adapter,
            )
            output = path / "report.json"
            write_json(output, result)
            print(f"Wrote {output}: {len(result['trials'])} labelled intervals; validation not evaluated")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, asyncio.TimeoutError) as error:
        detail = "Check session inputs, clocks and HA access; raw evidence is not logged."
        parser.exit(1, f"Coverage session stopped ({type(error).__name__}): {detail}\n")


def adapter_fingerprint(adapter):
    """Pin resolver implementation independently from its configuration."""
    if hasattr(adapter, "fingerprint"):
        return adapter.fingerprint()
    return hashlib.sha256(Path(adapter.__file__).read_bytes()).hexdigest()


def tracked_entities(adapter):
    return (
        adapter.tracked_entities()
        | set(adapter.CONFIG["rooms"].values())
        | {receiver["sensor"] for receiver in adapter.CONFIG["receivers"]}
    )


def tracked_items(adapter):
    return {item["item_id"] for item in adapter.CONFIG["sources"] + adapter.CONFIG["receivers"]}


async def read_binding(adapter, call):
    """An adapter may verify its own model without exporting that model."""
    if hasattr(adapter, "bindings"):
        return await adapter.bindings(call)
    items = [
        {"id": item["item_id"], "room": item["room"], "entity_id": item["entity_id"]}
        for item in adapter.CONFIG["sources"] + adapter.CONFIG["receivers"]
    ]
    return {"items": items, "revision": digest(adapter.CONFIG), "model_sha256": digest(items)}
