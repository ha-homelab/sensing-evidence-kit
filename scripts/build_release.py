# SPDX-License-Identifier: MIT
"""Build a wheel, normalized sdist and deterministic source ZIP. Never publishes."""

import gzip
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

from validate_repository import validate

ROOT = Path(__file__).resolve().parents[1]
# Fixed release timestamp; callers may deliberately override for later releases.
EPOCH = int(os.environ.get("SOURCE_DATE_EPOCH", "1792022400"))
FILES = (
    "pyproject.toml",
    "MANIFEST.in",
    "version",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "THIRD_PARTY_NOTICES.md",
    ".gitignore",
)
DIRECTORIES = (
    "src",
    "tests",
    "docs",
    "examples",
    "schemas",
    "scripts",
    "LICENSES",
    ".github",
)
SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".jsonl",
    ".sh",
    ".txt",
    ".html",
    ".png",
    ".yaml",
    ".yml",
}


def selected_files():
    selected = [ROOT / name for name in FILES]
    selected.extend(
        ROOT / name for name in ("RELEASING.md", ".release-policy.json", "uv.lock") if (ROOT / name).is_file()
    )
    for name in DIRECTORIES:
        folder = ROOT / name
        if folder.exists():
            selected.extend(
                file
                for file in folder.rglob("*")
                if file.is_file()
                and file.suffix in SUFFIXES
                and not any(
                    part.startswith(".") or part == "__pycache__" or part.endswith(".egg-info")
                    for part in file.relative_to(folder).parts
                )
                and ".local." not in file.name
            )
    for file in selected:
        if file.is_symlink():
            raise ValueError("Release source cannot contain symlinks")
    return sorted(selected)


def normalize_sdist(path):
    with tarfile.open(path, "r:gz") as archive:
        entries = [
            (member, archive.extractfile(member).read() if member.isfile() else None)
            for member in archive.getmembers()
        ]
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=buffer, mode="wb", mtime=EPOCH) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for member, data in sorted(entries, key=lambda pair: pair[0].name):
                member.uid = member.gid = 0
                member.uname = member.gname = ""
                member.mtime = EPOCH
                member.pax_headers = {}
                member.mode = 0o755 if member.isdir() or member.name.endswith(".sh") else 0o644
                archive.addfile(member, io.BytesIO(data) if data is not None else None)
    path.write_bytes(buffer.getvalue())


def main():
    validate()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    stem = f"sensing_evidence_kit-{version}"
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sensing-evidence-release-") as directory:
        staging = Path(directory) / stem
        for file in selected_files():
            target = staging / file.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)
        temporary_output = Path(directory) / "artifacts"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--sdist",
                "--wheel",
                "--outdir",
                str(temporary_output),
                str(staging),
            ],
            check=True,
            env={**os.environ, "SOURCE_DATE_EPOCH": str(EPOCH)},
        )
        artifacts = []
        for artifact in sorted(temporary_output.iterdir()):
            if artifact.name.endswith(".tar.gz"):
                normalize_sdist(artifact)
            target = output / artifact.name
            shutil.copyfile(artifact, target)
            artifacts.append(target)
        zip_path = output / f"{stem}-source.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for file in selected_files():
                info = zipfile.ZipInfo(
                    f"{stem}/{file.relative_to(ROOT).as_posix()}",
                    (2026, 10, 15, 0, 0, 0),
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (0o100755 if file.suffix == ".sh" else 0o100644) << 16
                archive.writestr(info, file.read_bytes())
        artifacts.append(zip_path)
    lines = [f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.name}" for file in sorted(artifacts)]
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
