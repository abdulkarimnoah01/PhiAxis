"""Build a PhiAxis release: dist/PhiAxis-<version>.zip and dist/version.json.

    python tools/make_release.py [--out dist] [--update-source <folder or https url>]

The zip holds only what an artist needs: the plugin (python3.10libs, shelf, icon), the
installer and the docs. Demos, tests, reference images and the showcase stay out, so
copyrighted reference material is never shipped. Publish BOTH files in one place (a
shared folder or an https address): the zip, and version.json beside it. That place is
the update source; with --update-source it is baked into the release so installed copies
already know where to look.

The version comes from composition_guides.__version__.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOUDINI_MIN, HOUDINI_MAX_EXCLUSIVE = "20.5", "23.0"       # keep in step with packages/*.json


def read_version():
    text = (ROOT / "python3.10libs" / "composition_guides" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'^__version__ = "([^"]+)"', text, re.M).group(1)


def changelog_notes(version):
    """Bullet lines of this version's CHANGELOG.md section."""
    lines, grab = [], False
    for line in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            if grab:
                break
            grab = line[4:].split(" ")[0] == version
        elif grab and line.strip():
            lines.append(line.strip().lstrip("-").strip())
    return lines


def stage(folder, version, update_source):
    top = folder / "PhiAxis"
    payload = top / "payload"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(ROOT / "python3.10libs", payload / "python3.10libs", ignore=ignore)
    shutil.copytree(ROOT / "toolbar", payload / "toolbar")
    shutil.copytree(ROOT / "config", payload / "config")
    (payload / "VERSION.json").write_text(json.dumps({
        "name": "PhiAxis", "version": version, "built": date.today().isoformat(),
        "houdini": {"min": HOUDINI_MIN, "max_exclusive": HOUDINI_MAX_EXCLUSIVE}}, indent=2),
        encoding="utf-8")
    if update_source:
        (payload / "update_source.txt").write_text(update_source.strip() + "\n", encoding="utf-8")
    for name in ("install.ps1", "Install PhiAxis.cmd", "Uninstall PhiAxis.cmd"):
        shutil.copy2(ROOT / "installer" / name, top / name)
    shutil.copy2(ROOT / "CHANGELOG.md", top / "CHANGELOG.md")
    shutil.copy2(ROOT / "INSTALL.md", top / "README.md")
    for licence in ("LICENSE", "LICENSE.txt", "LICENSE.md"):
        if (ROOT / licence).exists():
            shutil.copy2(ROOT / licence, top / licence)
    return top


def build(out, update_source=""):
    version = read_version()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        top = stage(Path(temp), version, update_source)
        archive = out / ("PhiAxis-%s.zip" % version)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(top.rglob("*")):
                if path.is_file():
                    zipped.write(path, path.relative_to(top.parent).as_posix())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = {"name": "PhiAxis", "version": version, "released": date.today().isoformat(),
                "zip": archive.name, "sha256": digest, "size": archive.stat().st_size,
                "houdini": {"min": HOUDINI_MIN, "max_exclusive": HOUDINI_MAX_EXCLUSIVE},
                "notes": changelog_notes(version)}
    (out / "version.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return archive, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", default=str(ROOT / "dist"))
    parser.add_argument("--update-source", default="")
    arguments = parser.parse_args()
    if not (ROOT / "LICENSE").exists() and not (ROOT / "LICENSE.txt").exists():
        print("note: no LICENSE file in the project, so none is included in the release")
    archive, manifest = build(Path(arguments.out), arguments.update_source)
    print("built", archive, "(%.1f MB)" % (archive.stat().st_size / 1e6))
    print("sha256", manifest["sha256"])
    print("publish %s and version.json together" % archive.name)
