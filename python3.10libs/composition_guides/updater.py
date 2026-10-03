"""Update check and install for PhiAxis. Plain Python: no Houdini, no Qt.

A release is a zip plus a small `version.json` manifest published together in one
place (a shared folder or an https address). The update source is that place:

    {"name": "PhiAxis", "version": "0.6.0", "released": "2026-10-03",
     "zip": "PhiAxis-0.6.0.zip", "sha256": "<64 hex digits>", "size": 123456,
     "houdini": {"min": "20.5", "max_exclusive": "23.0"}, "notes": ["..."]}

Checking is always explicit (nothing runs in the background and nothing is sent
anywhere). The zip is verified against the manifest's SHA-256 before anything is
unpacked, then installed by the same installer an artist runs by hand.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

MANIFEST_NAME = "version.json"
MAX_MANIFEST_BYTES = 256 * 1024
MAX_ZIP_BYTES = 300 * 1024 * 1024


class UpdateError(Exception):
    """A problem the artist can act on; the message is written for them."""


def parse_version(text):
    match = re.match(r"^\s*v?(\d+)\.(\d+)(?:\.(\d+))?", str(text))
    if not match:
        raise ValueError("Not a version number: %r" % (text,))
    return int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)


def is_newer(candidate, current):
    return parse_version(candidate) > parse_version(current)


def _is_url(source):
    return str(source).lower().startswith(("http://", "https://"))


def _read(location, limit):
    if _is_url(location):
        if not location.lower().startswith("https://"):
            raise UpdateError("Updates must come from an https:// address or a folder, "
                              "not plain http.")
        try:
            with urllib.request.urlopen(location, timeout=30) as response:
                data = response.read(limit + 1)
        except OSError as exc:
            raise UpdateError("Could not reach the update location (%s)." % exc)
    else:
        try:
            data = Path(location).read_bytes()
        except OSError as exc:
            raise UpdateError("Could not read %s (%s)." % (location, exc))
    if len(data) > limit:
        raise UpdateError("The file at %s is larger than expected." % location)
    return data


def manifest_location(source):
    """The version.json address for a folder, an https folder URL or a direct path."""
    text = str(source).strip().strip('"')
    if not text:
        raise UpdateError("No update location is set.")
    if _is_url(text):
        return text if text.lower().endswith(".json") else text.rstrip("/") + "/" + MANIFEST_NAME
    path = Path(text)
    return str(path if path.suffix.lower() == ".json" else path / MANIFEST_NAME)


def _sibling(location, name):
    if _is_url(location):
        return urllib.parse.urljoin(location, name)
    return str(Path(location).parent / name)


def read_manifest(source):
    location = manifest_location(source)
    try:
        manifest = json.loads(_read(location, MAX_MANIFEST_BYTES).decode("utf-8"))
        parse_version(manifest["version"])
        zip_name = manifest["zip"]
        digest = manifest["sha256"]
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        raise UpdateError("The update information at %s is not valid." % location)
    if (not isinstance(zip_name, str) or "/" in zip_name or "\\" in zip_name
            or not zip_name.lower().endswith(".zip")):
        raise UpdateError("The update information names an unsafe file.")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", str(digest)):
        raise UpdateError("The update information has no valid checksum.")
    return manifest


def supports_houdini(manifest, houdini):
    """True if `houdini` (major, minor) is inside the release's supported range."""
    limits = manifest.get("houdini") or {}
    try:
        low = parse_version(limits.get("min", "0.0"))[:2]
        high = parse_version(limits.get("max_exclusive", "999.0"))[:2]
    except ValueError:
        return True
    return low <= tuple(houdini[:2]) < high


def check(source, current, houdini=None):
    """The manifest of a newer release, or None when `current` is up to date."""
    manifest = read_manifest(source)
    if not is_newer(manifest["version"], current):
        return None
    if houdini is not None and not supports_houdini(manifest, houdini):
        raise UpdateError("PhiAxis %s does not support this Houdini version." %
                          manifest["version"])
    return manifest


def download(source, manifest, folder):
    """Fetch the release zip into `folder` and verify it against the manifest."""
    location = _sibling(manifest_location(source), manifest["zip"])
    data = _read(location, MAX_ZIP_BYTES)
    if hashlib.sha256(data).hexdigest().lower() != manifest["sha256"].lower():
        raise UpdateError("The downloaded update does not match its checksum, so it was "
                          "not installed. Try again, or ask whoever supplied PhiAxis.")
    target = Path(folder) / manifest["zip"]
    target.write_bytes(data)
    return target


def _safe_extract(zip_path, folder):
    root = Path(folder).resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if not (root / name).resolve().is_relative_to(root):
                raise UpdateError("The update contains an unsafe path, so it was not installed.")
        archive.extractall(folder)


def install(zip_path, extra_arguments=(), timeout=300):
    """Unpack a verified release zip and run its installer. Returns (ok, output)."""
    folder = tempfile.mkdtemp(prefix="phiaxis_update_")
    try:
        _safe_extract(zip_path, folder)
        scripts = list(Path(folder).glob("*/install.ps1")) or list(Path(folder).glob("install.ps1"))
        if not scripts:
            raise UpdateError("The update has no installer, so it was not installed.")
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                   str(scripts[0]), "-Quiet"] + [str(a) for a in extra_arguments]
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return done.returncode == 0, (done.stdout + done.stderr).strip()
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def update_source(prefs_dir=None, install_root=None):
    """Where updates come from: the PHIAXIS_UPDATE_SOURCE variable, the artist's own
    choice (saved in their Houdini preferences), or the address baked into the release."""
    value = os.environ.get("PHIAXIS_UPDATE_SOURCE", "").strip()
    if value:
        return value
    if prefs_dir:
        try:
            saved = json.loads((Path(prefs_dir) / "phiaxis_update.json").read_text(encoding="utf-8"))
            if str(saved.get("source", "")).strip():
                return saved["source"].strip()
        except (OSError, ValueError, AttributeError):
            pass
    if install_root:
        try:
            baked = (Path(install_root) / "update_source.txt").read_text(encoding="utf-8").strip()
            if baked:
                return baked
        except OSError:
            pass
    return ""


def save_update_source(prefs_dir, source):
    target = Path(prefs_dir) / "phiaxis_update.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"source": str(source).strip()}, indent=2), encoding="utf-8")
