# SPDX-License-Identifier: MIT
import copy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from sensing_evidence import joint, session
from sensing_evidence.adapters import EntityAdapter
from sensing_evidence.demo import configuration, main as demo_main, render_html, results, synthetic_bundle


class FixtureTest(unittest.TestCase):
    def setUp(self):
        self.files, self.adapter = synthetic_bundle()
        self.metadata = session.strict_json(self.files["ha_metadata"])
        self.capture = joint.load_jsonl(self.files["ha_capture"])
        self.labels = joint.load_jsonl(self.files["ha_labels"])

    def report(self):
        return session.report(self.metadata, self.capture, self.labels, self.adapter)

    def put(self, key, value, lines=False):
        self.files[key] = (
            "".join(json.dumps(row) + "\n" for row in value) if lines else json.dumps(value) + "\n"
        ).encode()

    def producer_rows(self):
        return joint.load_jsonl(self.files["producer_capture"])

    def producer_summary(self):
        return session.strict_json(self.files["producer_summary"])

    def update_producer(self, rows):
        self.put("producer_capture", rows, lines=True)
        summary = self.producer_summary()
        summary["capture_sha256"] = joint.sha256(self.files["producer_capture"])
        self.put("producer_summary", summary)


class AdapterTests(unittest.TestCase):
    def test_optional_nodes_and_distinct_identities(self):
        config = configuration()
        for receiver in config["receivers"]:
            receiver.pop("node_id")
        adapter = EntityAdapter(config)
        self.assertNotIn("node_id", adapter.CONFIG["receivers"][0])
        for value in (True, 0, 256, 1.5, "1"):
            invalid = configuration()
            invalid["receivers"][0]["node_id"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                EntityAdapter(invalid)
        for key in ("node_id", "item_id", "sensor", "entity_id"):
            invalid = configuration()
            invalid["receivers"][1][key] = invalid["receivers"][0][key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                EntityAdapter(invalid)

    def test_config_is_detached_and_rejects_invalid_limits(self):
        config = configuration()
        adapter = EntityAdapter(config)
        config["receivers"][0]["room"] = "changed"
        self.assertEqual(adapter.CONFIG["receivers"][0]["room"], "zone_a")
        for ttl in (0, -1, 301, True, float("nan"), float("inf")):
            config = configuration()
            config["ttl_seconds"] = ttl
            with self.subTest(ttl=ttl), self.assertRaises(ValueError):
                EntityAdapter(config)

    def test_fresh_stale_future_restored_and_missing_binding(self):
        adapter = EntityAdapter(configuration())
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        item = {"id": "sample_a", "room": "zone_a", "entity_id": "binary_sensor.sample_a"}
        state = SimpleNamespace(state="on", attributes={}, last_reported=now)
        for age, restored, expected in (
            (0, False, "presence"),
            (2.999, False, "presence"),
            (3, False, "unknown"),
            (-0.1, False, "unknown"),
            (0, True, "unknown"),
        ):
            state.last_reported = now - timedelta(seconds=age)
            state.attributes = {"restored": restored}
            result = adapter.resolve_activity([item], {item["entity_id"]: state}, now)
            self.assertEqual(result["sensor.zone_a_activity"][0], expected)
        self.assertEqual(
            adapter.resolve_activity([], {item["entity_id"]: state}, now)["sensor.zone_a_activity"][0],
            "unknown",
        )
        state.last_reported = now.replace(tzinfo=None)
        self.assertIsNone(adapter.freshness_deadline(state, now))

    def test_malformed_bindings_and_naive_evaluation_rejected(self):
        adapter = EntityAdapter(configuration())
        now = datetime.now(timezone.utc)
        for items in (None, [None], [{"id": []}], [{"id": "x", "room": "zone_a", "entity_id": "a.b"}] * 2):
            with self.subTest(items=items), self.assertRaises(ValueError):
                adapter.resolve_activity(items, {}, now)
        with self.assertRaises(ValueError):
            adapter.resolve_activity([], {}, now.replace(tzinfo=None))


class ClockAndInputTests(FixtureTest):
    def test_duplicate_nonfinite_json_and_truncated_jsonl_rejected(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                session.strict_json(raw)
        for raw in (b"", b"{}", b"{}\n\n", b"{}\n "):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                joint.load_jsonl(raw)

    def test_clock_anchor_rejects_nan_boolean_missing_identity_and_naive_time(self):
        for key, value in (
            ("schema_version", True),
            ("clock_tolerance_seconds", float("nan")),
            ("clock_tolerance_seconds", float("inf")),
            ("clock_tolerance_seconds", True),
            ("clock_tolerance_seconds", 3),
            ("monotonic_ns", True),
            ("monotonic_ns", -1),
            ("host_id", ""),
            ("boot_id", None),
            ("observed_utc", "2026-01-01T00:00:00"),
        ):
            metadata = {**self.metadata, key: value}
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                session.checked_time(self.capture[0], metadata)

    def test_foreign_host_boot_session_and_discontinuities_rejected(self):
        for key, value in (
            ("host_id", "another"),
            ("boot_id", "another"),
            ("session_id", "another"),
            ("schema_version", True),
            ("monotonic_ns", -1),
            ("monotonic_ns", True),
            ("observed_utc", "2026-01-01T00:01:00+00:00"),
        ):
            row = {**self.capture[0], key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                session.checked_time(row, self.metadata)

    def test_records_must_be_strictly_ordered(self):
        self.capture[1]["monotonic_ns"] = self.capture[0]["monotonic_ns"]
        with self.assertRaises(ValueError):
            self.report()

    def test_bad_request_timing_rejected_and_missing_request_unknown(self):
        for value in (
            None,
            {"monotonic_ns": True},
            {
                "observed_utc": self.capture[1]["observed_utc"],
                "monotonic_ns": self.capture[1]["monotonic_ns"],
            },
        ):
            rows = copy.deepcopy(self.capture)
            rows[0]["request_started"] = value
            if value is None:
                result = session.report(self.metadata, rows, self.labels, self.adapter)
                self.assertEqual(
                    result["trials"][0]["observations"]["sensor.zone_a_activity"]["unknown_seconds"], 6
                )
            else:
                with self.assertRaises(ValueError):
                    session.report(self.metadata, rows, self.labels, self.adapter)

    def test_contract_and_bindings_are_checked(self):
        for key in ("resolver_sha256", "contract_sha256"):
            metadata = {**self.metadata, key: "f" * 64}
            with self.subTest(key=key), self.assertRaises(ValueError):
                session.report(metadata, self.capture, self.labels, self.adapter)
        self.capture[0]["items"][0]["room"] = "zone_b"
        with self.assertRaises(ValueError):
            self.report()

    def test_custom_source_marker_can_omit_an_entity(self):
        sample = copy.deepcopy(self.capture[0])
        sample["items"].append({"id": "synthetic_source", "room": "zone_a"})
        sample["binding_sha256"] = session.digest(sample["items"])
        session.validate_sample(sample, self.metadata)
        sample["items"][-1]["entity_id"] = []
        with self.assertRaises(ValueError):
            session.validate_sample(sample, self.metadata)

    def test_malformed_state_and_fingerprint_rejected(self):
        for change in (
            {"states": []},
            {"states": {"x.y": {"state": True}}},
            {"items": [None]},
            {"model_sha256": "bad"},
            {"inventory_revision": []},
        ):
            rows = copy.deepcopy(self.capture)
            rows[0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                session.report(self.metadata, rows, self.labels, self.adapter)

    def test_write_once_and_owner_only_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            session.write_json(path, {"synthetic": True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                session.write_json(path, {})
            path.write_text("{}\n\n")
            with self.assertRaises(ValueError):
                session.rows(path)


class CharacterizationTests(FixtureTest):
    def test_synthetic_metrics_preserve_unknown_time(self):
        result = self.report()
        values = result["trials"][0]["observations"]["sensor.zone_a_activity"]
        self.assertEqual(
            (values["known_seconds"], values["unknown_seconds"], values["false_presence_seconds"]), (16, 4, 6)
        )
        self.assertEqual(result["validation_decision"], "not_evaluated")
        self.assertTrue(result["capture_complete"])

    def test_expiry_splits_interval_without_extending_freshness(self):
        # The first sample expires 1 second into its 2-second interval.
        self.capture[0]["states"]["binary_sensor.sample_a"]["last_reported"] = "2025-12-31T23:59:59+00:00"
        result = self.report()["trials"][0]["observations"]["sensor.zone_a_activity"]
        self.assertEqual(result["unknown_seconds"], 5)

    def test_no_labels_means_no_metrics_or_accuracy_claim(self):
        result = session.report(self.metadata, self.capture, [], self.adapter)
        self.assertEqual(result["trials"], [])
        self.assertEqual(result["validation_decision"], "not_evaluated")

    def test_missing_closure_excludes_trials(self):
        self.capture.pop()
        result = self.report()
        self.assertFalse(result["capture_complete"])
        self.assertIn("excluded", result["trials"][0])

    def test_uncertain_or_unclosed_labels_excluded(self):
        self.labels[0]["uncertainty"] = "operator unsure"
        self.assertIn("excluded", self.report()["trials"][0])
        self.labels[0]["uncertainty"] = ""
        self.labels.pop()
        self.assertIn("excluded", self.report()["trials"][0])

    def test_phase_contradiction_and_duplicate_rooms_rejected(self):
        for rooms in (["zone_a"], ["zone_b", "zone_b"], [[]]):
            label = {**self.labels[0], "occupied_rooms": rooms}
            with self.subTest(rooms=rooms), self.assertRaises(ValueError):
                session.validate_label(label, self.metadata, self.adapter)

    def test_transition_margins_trim_labelled_duration(self):
        self.metadata["transition_seconds"] = 2
        result = self.report()
        self.assertEqual(result["trials"][0]["labelled_seconds"], 16)
        self.metadata["transition_seconds"] = 11
        self.assertIn("excluded", self.report()["trials"][0])

    def test_completed_count_mismatch_is_not_a_success(self):
        self.capture[-1]["samples"] = 999
        self.assertFalse(self.report()["capture_complete"])


class JointTests(FixtureTest):
    def test_complete_diagnostic_never_validates_coverage(self):
        result = joint.analyze(self.files, self.adapter)
        self.assertEqual(result["diagnostic_status"], "complete")
        self.assertEqual(result["sample_window_overlap_seconds"], 20)
        self.assertFalse(result["coverage_validated"])
        self.assertEqual(result["validation_decision"], "not_evaluated")

    def test_original_byte_hash_changes_even_for_json_whitespace(self):
        self.files["ha_metadata"] = b" " + self.files["ha_metadata"]
        with self.assertRaisesRegex(ValueError, "byte_hash"):
            joint.analyze(self.files, self.adapter)

    def test_producer_capture_hash_and_counts_checked(self):
        rows = self.producer_rows()
        rows[0]["observation_valid"] = False
        self.put("producer_capture", rows, lines=True)
        with self.assertRaisesRegex(ValueError, "byte_hash"):
            joint.analyze(self.files, self.adapter)
        rows = self.producer_rows()
        rows[-1]["samples"] = 999
        self.update_producer(rows)
        with self.assertRaisesRegex(ValueError, "sample_count"):
            joint.analyze(self.files, self.adapter)

    def test_missing_duplicate_node_ids_rejected_for_joint_only(self):
        config = configuration()
        for receiver in config["receivers"]:
            receiver.pop("node_id")
        adapter = EntityAdapter(config)
        self.metadata["contract"] = adapter.CONFIG
        self.metadata["contract_sha256"] = session.digest(adapter.CONFIG)
        self.put("ha_metadata", self.metadata)
        pm = session.strict_json(self.files["producer_metadata"])
        pm["consumer_metadata_sha256"] = joint.sha256(self.files["ha_metadata"])
        self.put("producer_metadata", pm)
        with self.assertRaisesRegex(ValueError, "joint_requires_node_ids"):
            joint.analyze(self.files, adapter)

    def test_cross_boot_producer_and_missing_terminal_rejected(self):
        rows = self.producer_rows()
        rows[0]["boot_id"] = "foreign"
        self.update_producer(rows)
        with self.assertRaises(ValueError):
            joint.analyze(self.files, self.adapter)
        rows[0]["boot_id"] = "synthetic-boot"
        rows.pop()
        self.update_producer(rows)
        with self.assertRaisesRegex(ValueError, "terminal"):
            joint.analyze(self.files, self.adapter)

    def test_invalid_but_integral_experiment_reports_failure(self):
        rows = self.producer_rows()
        rows[0].update(observation_valid=False, issues=["synthetic_unavailable"])
        self.update_producer(rows)
        result = joint.analyze(self.files, self.adapter)
        self.assertEqual(result["diagnostic_status"], "invalid")
        self.assertIn("producer_has_invalid_observations", result["reasons"])

    def test_producer_must_not_assert_validation(self):
        summary = self.producer_summary()
        summary["coverage_validated"] = True
        self.put("producer_summary", summary)
        with self.assertRaisesRegex(ValueError, "validation_claim"):
            joint.analyze(self.files, self.adapter)

    def test_producer_sample_nodes_must_match_config(self):
        rows = self.producer_rows()
        rows[0]["nodes"] = [{"node_id": 1}, {"node_id": 1}]
        self.update_producer(rows)
        with self.assertRaisesRegex(ValueError, "node_mismatch"):
            joint.analyze(self.files, self.adapter)

    def test_informational_producer_boundaries_preserve_valid_alignment(self):
        rows = self.producer_rows()
        for kind in ("firmware_boundary", "runtime_boundary"):
            boundary = {**rows[0], "kind": kind}
            modified = [boundary, *rows]
            self.update_producer(modified)
            self.assertEqual(joint.analyze(self.files, self.adapter)["diagnostic_status"], "complete")

    def test_unknown_record_kinds_and_nonbyte_inputs_rejected(self):
        rows = self.producer_rows()
        rows[0]["kind"] = "unrecognized"
        self.update_producer(rows)
        with self.assertRaisesRegex(ValueError, "record_kind"):
            joint.analyze(self.files, self.adapter)
        self.files["ha_metadata"] = "not bytes"
        with self.assertRaisesRegex(ValueError, "evidence_bytes"):
            joint.analyze(self.files, self.adapter)


class DemoTests(FixtureTest):
    def test_demo_runs_offline_and_is_deterministic(self):
        with (
            patch("socket.socket.connect", side_effect=AssertionError("network forbidden")),
            patch("sensing_evidence.session.clock_identity", side_effect=AssertionError("no real identity")),
        ):
            first = results(self.files, self.adapter)
            second = results(self.files, self.adapter)
        self.assertEqual(first, second)
        self.assertIn("ALL DATA IS SYNTHETIC", render_html(*first))

    def test_demo_does_not_overwrite_existing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "demo"
            with patch("sys.stdout", new=io.StringIO()):
                demo_main([str(target)])
            self.assertTrue((target / "demo.html").exists())
            with self.assertRaises(FileExistsError):
                demo_main([str(target)])


class CaptureTests(FixtureTest):
    def run_capture(self, fail_read=False):
        import asyncio
        from unittest.mock import AsyncMock, Mock

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            session.write_json(path / "metadata.json", self.metadata)
            ws = Mock()
            states = [
                {
                    "entity_id": "binary_sensor.sample_a",
                    "state": "on",
                    "last_reported": self.capture[0]["observed_utc"],
                    "attributes": {"restored": False, "secret_note": "must be dropped"},
                },
                {"entity_id": "sensor.untracked", "state": "private", "attributes": {}},
            ]
            ws.receive_json = AsyncMock(
                side_effect=[
                    {"type": "auth_required"},
                    {"type": "auth_ok"},
                    {"id": 1, "success": not fail_read, "result": states},
                ]
            )
            ws.send_json = AsyncMock()
            ws_context = AsyncMock()
            ws_context.__aenter__.return_value = ws
            client = Mock()
            client.ws_connect.return_value = ws_context
            client_context = AsyncMock()
            client_context.__aenter__.return_value = client
            fake_aiohttp = SimpleNamespace(
                ClientSession=Mock(return_value=client_context), ClientTimeout=Mock()
            )
            args = SimpleNamespace(directory=path, origin="https://ha.example.invalid", seconds=1, interval=1)
            base = {
                k: self.capture[0][k]
                for k in (
                    "schema_version",
                    "session_id",
                    "host_id",
                    "boot_id",
                    "observed_utc",
                    "monotonic_ns",
                )
            }
            complete = {k: self.capture[-1][k] for k in base}
            records = iter([base, base, complete])

            def record(_metadata, **values):
                return {**next(records), **values}

            with (
                patch.dict("sys.modules", {"aiohttp": fake_aiohttp}),
                patch.dict("os.environ", {"HA_TOKEN": "synthetic-auth-only"}),
                patch(
                    "sensing_evidence.session.time",
                    new=SimpleNamespace(monotonic=Mock(side_effect=[0, 0, 0, 2])),
                ),
                patch("sensing_evidence.session.stamp", return_value=self.capture[0]["request_started"]),
                patch("sensing_evidence.session.new_record", side_effect=record),
                patch("sensing_evidence.session.asyncio.sleep", new=AsyncMock()),
                patch("sys.stdout", new=io.StringIO()),
            ):
                if fail_read:
                    with self.assertRaises(ValueError):
                        asyncio.run(session.capture(args, self.adapter))
                else:
                    asyncio.run(session.capture(args, self.adapter))
            rows = session.rows(path / "capture.jsonl")
            self.assertNotIn("synthetic-auth-only", (path / "capture.jsonl").read_text())
            self.assertEqual([c.args[0]["type"] for c in ws.send_json.call_args_list], ["auth", "get_states"])
            return rows

    def test_live_capture_transport_is_read_only_and_filtered(self):
        rows = self.run_capture()
        self.assertEqual(rows[-1]["kind"], "complete")
        self.assertEqual(rows[-1]["samples"], 1)
        self.assertEqual(set(rows[0]["states"]), {"binary_sensor.sample_a"})
        self.assertNotIn("secret_note", rows[0]["states"]["binary_sensor.sample_a"]["attributes"])

    def test_read_failure_records_interruption(self):
        rows = self.run_capture(fail_read=True)
        self.assertEqual(rows[-1]["kind"], "interrupted")
