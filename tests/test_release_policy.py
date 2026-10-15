# SPDX-License-Identifier: MIT
"""Exercise package metadata checks alongside the signed source inventory."""

import importlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile


class ReleasePolicyTest(unittest.TestCase):
    def test_source_archive_is_not_treated_as_a_python_distribution(self):
        root = Path(__file__).resolve().parents[1]
        with patch.object(sys, "path", [str(root), *sys.path]):
            stage = importlib.import_module("scripts.stage_release_assets")
            versions = importlib.import_module("scripts.version_plan")
        policy = json.loads((root / ".release-policy.json").read_text())
        plan = versions.create_plan("0.1.0", "beta", 1, "a" * 40, policy)
        metadata = b"Metadata-Version: 2.4\nName: sensing-evidence-kit\nVersion: 0.1.0b1\n"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            wheel = output / "sensing_evidence_kit-0.1.0b1-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("sensing_evidence_kit-0.1.0b1.dist-info/METADATA", metadata)
            sdist = output / "sensing_evidence_kit-0.1.0b1.tar.gz"
            with tarfile.open(sdist, "w:gz") as archive:
                member = tarfile.TarInfo("sensing_evidence_kit-0.1.0b1/PKG-INFO")
                member.size = len(metadata)
                archive.addfile(member, io.BytesIO(metadata))
            source = output / f"source-{'a' * 40}.tar.gz"
            with tarfile.open(source, "w:gz") as archive:
                archive.addfile(tarfile.TarInfo("README.md"), io.BytesIO())
            files = {path.name: path for path in (wheel, sdist, source)}
            inspected = stage.inspect_staged_artifacts(output, files, policy, plan)
            self.assertEqual({item["path"] for item in inspected}, {wheel.name, sdist.name})
            self.assertEqual({item["version"] for item in inspected}, {"0.1.0b1"})
            # Narrowing the source rule must retain validation of actual packages.
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr(
                    "sensing_evidence_kit-0.1.0b1.dist-info/METADATA", metadata.replace(b"0.1.0b1", b"9.9.9")
                )
            with self.assertRaises(versions.VersionError):
                stage.inspect_staged_artifacts(output, files, policy, plan)
