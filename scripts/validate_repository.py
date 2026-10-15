# SPDX-License-Identifier: MIT
"""Small offline consistency checks, also called by the release builder."""

import ast
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    version = metadata["project"]["version"]
    assert (ROOT / "version").read_text().strip() == version, "version mismatch"
    tree = ast.parse((ROOT / "src/sensing_evidence/__init__.py").read_text())
    code_version = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets)
    )
    assert code_version == version, "package version mismatch"
    for file in (ROOT / "schemas").glob("*.json"):
        schema = json.loads(file.read_text())
        assert schema["$schema"].endswith("2020-12/schema"), file
    for file in (ROOT / "examples").glob("*.jsonl"):
        for line in file.read_text().splitlines():
            assert json.loads(line)["schema"] == "sensing.synthetic.v1", file
    for folder in ("src", "tests", "scripts"):
        for file in (ROOT / folder).rglob("*.py"):
            if folder == "scripts" and any(
                line.startswith("# Vendored release toolkit;") for line in file.read_text().splitlines()[:3]
            ):
                continue  # Generated shared toolkit retains its own provenance.
            assert file.read_text().startswith("# SPDX-License-Identifier: MIT"), file
    print(f"Repository metadata and synthetic fixtures valid ({version}).")


if __name__ == "__main__":
    validate()
