"""Validate evidence identity and clock joins without reading live evidence."""

import json
import math
from pathlib import Path
import sys
import atheris

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
with atheris.instrument_imports():
    from sensing_evidence import session


def test_one_input(data):
    try:
        value = session.strict_json(data)
    except (ValueError, UnicodeError):
        return
    if not isinstance(value, dict):
        return
    anchor, record = value.get("anchor"), value.get("record")
    try:
        session.validate_anchor(anchor)
    except ValueError:
        return
    assert session.strict_json(json.dumps(anchor, allow_nan=False)) == anchor
    assert session.checked_time(anchor, anchor) == anchor["monotonic_ns"] / 1e9
    try:
        when = session.checked_time(record, anchor)
    except ValueError:
        return
    assert math.isfinite(when) and when >= anchor["monotonic_ns"] / 1e9
    # A verified join must stop being valid when its session or boot changes.
    for field in ("session_id", "boot_id", "host_id"):
        changed = dict(record, **{field: str(record[field]) + "-different"})
        try:
            session.checked_time(changed, anchor)
        except ValueError:
            pass
        else:
            raise AssertionError("cross-identity clock join accepted")
    assert session.checked_time(record, anchor) == when


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()
