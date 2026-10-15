# SPDX-License-Identifier: MIT
"""Offline integrity/alignment check for consumer + producer evidence; no network calls."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from . import session as ha


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def load_jsonl(raw):
    require(bool(raw) and raw.endswith(b"\n"), "truncated_jsonl")
    lines = raw.decode("utf-8").splitlines()
    require(all(line.strip() for line in lines), "blank_jsonl_record")
    return [ha.strict_json(line) for line in lines]


def validate_identity(record, anchor, stream=None):
    require(isinstance(record, dict), "record_not_object")
    require(type(record.get("schema_version")) is int and record["schema_version"] == 1, "schema_mismatch")
    require(
        all(
            isinstance(record.get(key), str) and record[key] and record[key] == anchor.get(key)
            for key in ("session_id", "host_id", "boot_id")
        ),
        "session_host_or_boot_mismatch",
    )
    if stream:
        require(record.get("stream") == stream, "producer_stream_mismatch")
    ha.checked_time(record, anchor)


def ordered_samples(records):
    samples = [record for record in records if record.get("kind") == "sample"]
    times = [record["monotonic_ns"] for record in samples]
    require(all(b > a for a, b in zip(times, times[1:])), "sample_clock_not_strictly_increasing")
    return samples


def analyze(files, adapter):
    """Input values are original bytes, kept separate from parsed-JSON digests.

    Malformed/mismatched evidence is rejected. A well-formed failed experiment
    still returns its actual overlap and failure reasons, never a readiness pass.
    """
    required = {"ha_metadata", "ha_capture", "producer_metadata", "producer_capture", "producer_summary"}
    require(isinstance(files, dict) and required <= files.keys(), "missing_evidence_files")
    require(
        all(isinstance(files[key], bytes) and len(files[key]) <= ha.MAX_FILE_BYTES for key in required),
        "invalid_evidence_bytes",
    )
    require(
        files.get("ha_labels") is None
        or isinstance(files["ha_labels"], bytes)
        and len(files["ha_labels"]) <= ha.MAX_FILE_BYTES,
        "invalid_label_bytes",
    )
    hm, pm, summary = (
        ha.strict_json(files[key]) for key in ("ha_metadata", "producer_metadata", "producer_summary")
    )
    hc, pc = (load_jsonl(files[key]) for key in ("ha_capture", "producer_capture"))
    labels = load_jsonl(files["ha_labels"]) if files.get("ha_labels") else []
    require(isinstance(hm, dict) and ha.timestamp(hm.get("observed_utc")) is not None, "invalid_ha_anchor")
    require(type(hm.get("monotonic_ns")) is int and hm["monotonic_ns"] >= 0, "invalid_ha_monotonic_anchor")
    require(
        type(hm.get("clock_tolerance_seconds")) in (int, float) and 0 < hm["clock_tolerance_seconds"] <= 2,
        "invalid_clock_tolerance",
    )
    ha.verify_contract(hm, adapter)
    validate_identity(hm, hm)
    for record in (pm, summary, *pc):
        validate_identity(record, hm, "ruview_producer")
    for record in (*hc, *labels):
        validate_identity(record, hm)
    require(
        pm.get("kind") == "metadata" and summary.get("kind") == "summary", "producer_metadata_summary_kind"
    )
    require(
        type(pm.get("requested_duration_s")) is int and 5 <= pm["requested_duration_s"] <= 3600,
        "invalid_producer_requested_duration",
    )
    require(all(row["monotonic_ns"] >= pm["monotonic_ns"] for row in pc), "producer_record_precedes_metadata")
    require(pm.get("local_monotonic_alignment") is True, "cross_host_alignment_not_supported")
    require(
        pm.get("consumer_metadata_sha256") == sha256(files["ha_metadata"]),
        "consumer_metadata_byte_hash_mismatch",
    )
    anchor_keys = (
        "schema_version",
        "session_id",
        "host_id",
        "boot_id",
        "observed_utc",
        "monotonic_ns",
        "clock_tolerance_seconds",
    )
    require(pm.get("consumer_anchor") == {key: hm[key] for key in anchor_keys}, "consumer_anchor_mismatch")
    require(
        summary.get("capture_sha256") == sha256(files["producer_capture"]),
        "producer_capture_byte_hash_mismatch",
    )
    receivers = hm["contract"]["receivers"]
    require(
        bool(receivers)
        and all(type(item.get("node_id")) is int and 1 <= item["node_id"] <= 255 for item in receivers),
        "joint_requires_node_ids",
    )
    expected = {str(item["node_id"]): item for item in receivers}
    require(len(expected) == len(receivers), "duplicate_joint_node_id")
    bindings = pm.get("node_bindings")
    require(isinstance(bindings, dict) and set(bindings) == set(expected), "producer_node_bindings_mismatch")
    for node, item in expected.items():
        require(
            isinstance(bindings[node], dict)
            and bindings[node].get("room") == item["room"]
            and bindings[node].get("floorplan_marker_id") == item["item_id"],
            "producer_room_marker_mismatch",
        )
    require(
        all(
            row.get("kind")
            in {
                "sample",
                "terminal",
                "boundary_error",
                "request_error",
                "runtime_probe_skipped",
                "firmware_boundary",
                "runtime_boundary",
            }
            for row in pc
        ),
        "unknown_producer_record_kind",
    )
    hs, ps = ordered_samples(hc), ordered_samples(pc)
    require(bool(hs), "no_ha_samples")
    terminal = pc[-1]
    require(
        terminal.get("kind") == "terminal" and sum(row.get("kind") == "terminal" for row in pc) == 1,
        "producer_terminal_missing_or_repeated",
    )
    require(summary.get("stream_complete") is True, "producer_stream_incomplete")
    require(
        all(
            type(value) is int and value == len(ps)
            for value in (terminal.get("samples"), summary.get("sample_count"), summary.get("samples"))
        ),
        "producer_sample_count_mismatch",
    )
    require(
        all(row["monotonic_ns"] <= terminal["monotonic_ns"] for row in pc),
        "terminal_precedes_producer_record",
    )
    require(summary["monotonic_ns"] >= terminal["monotonic_ns"], "summary_precedes_terminal")
    for key in ("recording_complete", "capture_status", "reasons", "validation_decision"):
        require(terminal.get(key) == summary.get(key), "producer_terminal_summary_disagreement")
    require(
        type(summary.get("recording_complete")) is bool
        and summary.get("capture_status") in ("complete", "invalid")
        and summary.get("evidence_integrity") in ("valid", "invalid"),
        "invalid_producer_completion_fields",
    )
    require(
        summary.get("coverage_validated") is False and summary.get("validation_decision") == "not_evaluated",
        "unsupported_producer_validation_claim",
    )
    reasons = summary.get("reasons")
    require(isinstance(reasons, list), "invalid_producer_reasons")
    codes = []
    for reason in reasons:
        require(
            isinstance(reason, dict)
            and isinstance(reason.get("code"), str)
            and re.fullmatch(r"[A-Za-z0-9_]+", reason["code"]),
            "invalid_producer_reason_code",
        )
        codes.append(reason["code"])
    # Error records may be stamped just after the sample receive time and
    # emitted before that sample. Only sample timestamps are globally ordered.
    for sample in ps:
        require(
            sample.get("source") == "esp32"
            and type(sample.get("observation_valid")) is bool
            and isinstance(sample.get("issues"), list),
            "invalid_producer_observation",
        )
        require(sample["observation_valid"] == (not sample["issues"]), "producer_observation_issues_disagree")
        nodes = sample.get("nodes")
        require(
            isinstance(nodes, list)
            and len(nodes) == len(expected)
            and all(isinstance(node, dict) and type(node.get("node_id")) is int for node in nodes)
            and {str(node["node_id"]) for node in nodes} == set(expected),
            "producer_sample_node_mismatch",
        )
    diagnostics = ha.report(hm, hc, labels, adapter)
    failures = []
    if not diagnostics["capture_complete"]:
        failures.append("ha_capture_incomplete")
    if summary["recording_complete"] is not True:
        failures.append("producer_recording_incomplete")
    if summary["capture_status"] != "complete" or summary["evidence_integrity"] != "valid":
        failures.append("producer_evidence_invalid")
    if codes or any(
        row.get("kind") in ("boundary_error", "request_error", "runtime_probe_skipped") for row in pc
    ):
        failures.append("producer_has_reported_errors")
    if any(not sample["observation_valid"] for sample in ps):
        failures.append("producer_has_invalid_observations")
    if len(hs) < 2 or len(ps) < 2:
        failures.append("insufficient_samples")
    if ps and (ps[-1]["monotonic_ns"] - ps[0]["monotonic_ns"]) / 1e9 + 10 < pm["requested_duration_s"]:
        # Allow a combined ten-second deficit across sampling boundaries.
        # Exact phase-edge gaps remain the producer's check: metadata predates
        # its opening probes. Do not use the old interrupted-duration summary
        # field, which could incorrectly report zero.
        failures.append("producer_sample_span_shorter_than_requested_window")
    overlap_ns = 0
    overlap = None
    if hs and ps:
        first = max((hs[0], ps[0]), key=lambda row: row["monotonic_ns"])
        last = min((hs[-1], ps[-1]), key=lambda row: row["monotonic_ns"])
        overlap_ns = max(0, last["monotonic_ns"] - first["monotonic_ns"])
        if overlap_ns:
            overlap = dict(
                start={key: first[key] for key in ("observed_utc", "monotonic_ns")},
                end={key: last[key] for key in ("observed_utc", "monotonic_ns")},
            )
    if not overlap_ns:
        failures.append("no_sample_window_overlap")
    gap_seconds = {}
    for name, stream in (("ha", hs), ("producer", ps)):
        gap = max(
            ((b["monotonic_ns"] - a["monotonic_ns"]) / 1e9 for a, b in zip(stream, stream[1:])), default=None
        )
        gap_seconds[name] = gap
        if gap is not None and gap > 5:
            failures.append(name + "_sample_gap_exceeds_5s")
    return dict(
        schema_version=1,
        session_id=hm["session_id"],
        diagnostic_status="invalid" if failures else "complete",
        validation_decision="not_evaluated",
        coverage_validated=False,
        reasons=failures,
        producer_reason_codes=sorted(set(codes)),
        ha_capture_complete=diagnostics["capture_complete"],
        producer_recording_complete=summary["recording_complete"],
        producer_stream_complete=True,
        producer_evidence_integrity=summary["evidence_integrity"],
        ha_samples=len(hs),
        producer_samples=len(ps),
        producer_valid_observations=sum(row["observation_valid"] for row in ps),
        label_count=len(labels),
        sample_window_overlap_seconds=overlap_ns / 1e9,
        overlap=overlap,
        max_sample_gap_seconds=gap_seconds,
        alignment="same_host_boot_monotonic",
        collector_clock_offset_uncertainty_ms=pm.get("collector_clock_offset_uncertainty_ms"),
        original_file_sha256={
            key: sha256(value) if value is not None else None for key, value in files.items()
        },
        limitations=[
            "A complete diagnostic is not calibrated room coverage or a recognition accuracy result.",
            "Sample-window overlap is not continuous valid coverage; snapshots miss short events.",
            "No cross-host monotonic join or exact collector-to-HA event-latency claim.",
            "Individual sampling-boundary gaps require the producer's phase timing checks.",
            "Producer runtime/model fingerprint and independent labelled repeat still require review.",
        ],
    )


def read_files(ha_directory, producer_directory):
    files = {}
    for prefix, directory, names in (
        ("ha", ha_directory, ("metadata", "capture", "labels")),
        ("producer", producer_directory, ("metadata", "capture", "summary")),
    ):
        for name in names:
            path = directory / (name + (".jsonl" if name in ("capture", "labels") else ".json"))
            if prefix == "ha" and name == "labels" and not path.exists():
                files[prefix + "_" + name] = None
            else:
                require(path.stat().st_size <= 256 * 1024 * 1024, "evidence_file_too_large")
                files[prefix + "_" + name] = path.read_bytes()
    return files


def main(adapter=None, argv=None):
    from . import __version__

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("ha_directory", type=Path)
    parser.add_argument("producer_directory", type=Path)
    parser.add_argument(
        "--output", type=Path, required=True, help="New private report; never overwrite original evidence"
    )
    parser.add_argument("--config", type=Path, help="Entity adapter configuration")
    args = parser.parse_args(argv)
    if adapter is None:
        from .adapters import EntityAdapter

        if args.config is None:
            parser.error("--config is required")
        adapter = EntityAdapter(ha.read_json(args.config))
    os.umask(0o077)
    try:
        result = analyze(read_files(args.ha_directory, args.producer_directory), adapter)
        ha.write_json(args.output, result)
    except (OSError, ValueError, KeyError, TypeError) as error:
        # Fixed mismatch codes and exception class only; no private payload echo.
        detail = (
            str(error)
            if isinstance(error, ValueError) and re.fullmatch(r"[a-z0-9_]+", str(error))
            else type(error).__name__
        )
        parser.exit(2, "Joint evidence rejected: " + detail + "\n")
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "diagnostic_status",
                    "ha_samples",
                    "producer_samples",
                    "sample_window_overlap_seconds",
                    "validation_decision",
                )
            }
        )
    )
    parser.exit(0 if result["diagnostic_status"] == "complete" else 1)


if __name__ == "__main__":
    main()
