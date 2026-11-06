# SPDX-License-Identifier: MIT
"""Named release inputs remain available without building distribution archives."""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_release_under_test", ROOT / "scripts/build_release.py")
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
with patch.dict(sys.modules):
    with patch.object(sys, "path", [str(ROOT / "scripts"), *sys.path]):
        SPEC.loader.exec_module(BUILDER)


class ReleaseSourcesTests(unittest.TestCase):
    def test_all_selected_release_sources_are_regular_files(self):
        missing = [str(path.relative_to(ROOT)) for path in BUILDER.selected_files() if not path.is_file()]
        self.assertFalse(missing, f"Missing release source files: {missing}")


if __name__ == "__main__":
    unittest.main()
