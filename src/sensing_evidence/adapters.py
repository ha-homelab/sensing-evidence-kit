# SPDX-License-Identifier: MIT
"""A small configurable binary-entity adapter; custom adapters use the same API."""

from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import math
import re


class EntityAdapter:
    """Characterize ordinary HA binary sensors without changing their state."""

    def __init__(self, config):
        if not isinstance(config, dict) or set(config) != {"rooms", "receivers", "ttl_seconds"}:
            raise ValueError("Configuration requires rooms, receivers and ttl_seconds")
        rooms, receivers, ttl = config["rooms"], config["receivers"], config["ttl_seconds"]
        if not isinstance(rooms, dict) or not rooms or not isinstance(receivers, list) or not receivers:
            raise ValueError("At least one room and receiver are required")
        entity = re.compile(r"[a-z_]+\.[a-z0-9_]+\Z")
        if any(
            not isinstance(k, str)
            or not re.fullmatch(r"[a-z][a-z0-9_-]{0,47}", k)
            or not isinstance(v, str)
            or not entity.fullmatch(v)
            for k, v in rooms.items()
        ):
            raise ValueError("Invalid room or output entity identifier")
        if type(ttl) not in (int, float) or not math.isfinite(ttl) or not 0 < ttl <= 300:
            raise ValueError("ttl_seconds must be finite and between zero and 300")
        markers, outputs, inputs, nodes = set(), set(rooms.values()), set(), set()
        if len(outputs) != len(rooms):
            raise ValueError("Room outputs must be distinct")
        for receiver in receivers:
            if not isinstance(receiver, dict) or not {"item_id", "room", "entity_id", "sensor"} <= set(
                receiver
            ) <= {"item_id", "room", "entity_id", "sensor", "node_id"}:
                raise ValueError("Each receiver needs item_id, room, entity_id and sensor")
            if (
                not isinstance(receiver["room"], str)
                or receiver["room"] not in rooms
                or not isinstance(receiver["item_id"], str)
                or not re.fullmatch(r"[a-z][a-z0-9_-]{0,47}", receiver["item_id"])
            ):
                raise ValueError("Receiver room or marker is invalid")
            if any(
                not isinstance(receiver[k], str) or not entity.fullmatch(receiver[k])
                for k in ("entity_id", "sensor")
            ):
                raise ValueError("Receiver entities are invalid")
            if (
                receiver["item_id"] in markers
                or receiver["sensor"] in outputs
                or receiver["entity_id"] in inputs
            ):
                raise ValueError("Receiver markers and outputs must be distinct")
            if "node_id" in receiver:
                node_id = receiver["node_id"]
                if type(node_id) is not int or not 1 <= node_id <= 255 or node_id in nodes:
                    raise ValueError("Optional node_id must be a distinct integer in 1..255")
                nodes.add(node_id)
            inputs.add(receiver["entity_id"])
            markers.add(receiver["item_id"])
            outputs.add(receiver["sensor"])
        self.CONFIG = {**deepcopy(config), "sources": []}

    def fingerprint(self):
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    def tracked_entities(self):
        return {receiver["entity_id"] for receiver in self.CONFIG["receivers"]}

    def freshness_deadline(self, state, _when):
        reported = getattr(state, "last_reported", None)
        if not isinstance(reported, datetime) or reported.tzinfo is None:
            return None
        try:
            return reported + timedelta(seconds=self.CONFIG["ttl_seconds"])
        except OverflowError:
            return None

    def resolve_activity(self, items, states, when):
        if not isinstance(when, datetime) or when.tzinfo is None:
            raise ValueError("Observation time must have a timezone")
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise ValueError("Bindings must be objects")
        if not all(
            all(isinstance(item.get(key), str) for key in ("id", "room", "entity_id")) for item in items
        ):
            raise ValueError("Invalid binding identity")
        if len({item["id"] for item in items}) != len(items):
            raise ValueError("Duplicate binding identity")
        results, by_room = {}, {room: [] for room in self.CONFIG["rooms"]}
        bindings = {(item.get("id"), item.get("room"), item.get("entity_id")) for item in items}
        for receiver in self.CONFIG["receivers"]:
            state = states.get(receiver["entity_id"])
            binding = (receiver["item_id"], receiver["room"], receiver["entity_id"])
            valid = state is not None and binding in bindings
            if valid:
                deadline = self.freshness_deadline(state, when)
                valid = (
                    deadline is not None
                    and state.last_reported <= when < deadline
                    and isinstance(getattr(state, "attributes", None), dict)
                    and not state.attributes.get("restored")
                )
            value = (
                {"on": "presence", "off": "quiet"}.get(getattr(state, "state", None), "unknown")
                if valid
                else "unknown"
            )
            results[receiver["sensor"]] = (value, {"source": receiver["entity_id"]})
            by_room[receiver["room"]].append(value)
        for room, values in by_room.items():
            value = (
                "presence"
                if "presence" in values
                else "quiet"
                if values and all(v == "quiet" for v in values)
                else "unknown"
            )
            results[self.CONFIG["rooms"][room]] = (value, {})
        return results
