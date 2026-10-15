# SPDX-License-Identifier: MIT
"""Run every test with outgoing sockets and DNS blocked."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
with (
    patch("socket.socket.connect", side_effect=AssertionError("Tests must stay offline")),
    patch("socket.getaddrinfo", side_effect=AssertionError("Tests must stay offline")),
):
    suite = unittest.defaultTestLoader.discover(str(root / "tests"))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(not result.wasSuccessful())
