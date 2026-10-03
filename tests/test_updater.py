import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python3.10libs"))
from composition_guides import updater
from composition_guides.updater import UpdateError


def write_release(folder, version="1.2.0", houdini=None, tamper=False, zip_name=None):
    folder = Path(folder)
    zip_name = zip_name or "PhiAxis-%s.zip" % version
    archive = folder / zip_name
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("PhiAxis/readme.txt", "hello")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = {"name": "PhiAxis", "version": version, "zip": zip_name,
                "sha256": digest, "houdini": houdini or {"min": "20.5", "max_exclusive": "23.0"},
                "notes": ["one", "two"]}
    (folder / "version.json").write_text(json.dumps(manifest), encoding="utf-8")
    if tamper:
        archive.write_bytes(archive.read_bytes() + b"x")
    return manifest


class VersionTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(updater.parse_version("0.5.1"), (0, 5, 1))
        self.assertEqual(updater.parse_version("v1.2"), (1, 2, 0))
        self.assertEqual(updater.parse_version("2.0.3-beta"), (2, 0, 3))
        for bad in ("", "abc", "1"):
            with self.assertRaises(ValueError):
                updater.parse_version(bad)

    def test_ordering_is_numeric_not_textual(self):
        self.assertTrue(updater.is_newer("0.10.0", "0.9.9"))
        self.assertTrue(updater.is_newer("1.0.0", "0.99.99"))
        self.assertFalse(updater.is_newer("0.5.1", "0.5.1"))
        self.assertFalse(updater.is_newer("0.5.0", "0.5.1"))


class ManifestTests(unittest.TestCase):
    def test_locations(self):
        self.assertTrue(updater.manifest_location("D:/share/phiaxis").replace("\\", "/")
                        .endswith("D:/share/phiaxis/version.json"))
        self.assertEqual(updater.manifest_location("https://x.org/p/"), "https://x.org/p/version.json")
        self.assertEqual(updater.manifest_location("https://x.org/p/version.json"),
                         "https://x.org/p/version.json")
        self.assertEqual(updater.manifest_location('"C:/a/version.json"').replace("\\", "/"),
                         "C:/a/version.json")
        with self.assertRaises(UpdateError):
            updater.manifest_location("   ")

    def test_read_valid_and_rejects_bad_ones(self):
        with tempfile.TemporaryDirectory() as folder:
            write_release(folder)
            self.assertEqual(updater.read_manifest(folder)["version"], "1.2.0")
            path = Path(folder) / "version.json"
            good = json.loads(path.read_text())
            for change in ({"zip": "../evil.zip"}, {"zip": "a/b.zip"}, {"zip": "x.exe"},
                           {"sha256": "abc"}, {"version": "nope"}):
                path.write_text(json.dumps(dict(good, **change)))
                with self.assertRaises(UpdateError, msg=change):
                    updater.read_manifest(folder)
            path.write_text("{not json")
            with self.assertRaises(UpdateError):
                updater.read_manifest(folder)
            path.unlink()
            with self.assertRaises(UpdateError):
                updater.read_manifest(folder)

    def test_plain_http_is_refused(self):
        with self.assertRaises(UpdateError):
            updater.read_manifest("http://example.org/phiaxis")


class CheckTests(unittest.TestCase):
    def test_newer_equal_older(self):
        with tempfile.TemporaryDirectory() as folder:
            write_release(folder, "1.2.0")
            self.assertEqual(updater.check(folder, "1.1.9")["version"], "1.2.0")
            self.assertIsNone(updater.check(folder, "1.2.0"))
            self.assertIsNone(updater.check(folder, "2.0.0"))

    def test_unsupported_houdini_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            write_release(folder, "1.2.0", houdini={"min": "21.0", "max_exclusive": "23.0"})
            self.assertIsNotNone(updater.check(folder, "1.0.0", (21, 0)))
            with self.assertRaises(UpdateError):
                updater.check(folder, "1.0.0", (20, 5))
            with self.assertRaises(UpdateError):
                updater.check(folder, "1.0.0", (23, 0))


class DownloadTests(unittest.TestCase):
    def test_download_verifies_checksum(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
            manifest = write_release(source)
            path = updater.download(source, manifest, target)
            self.assertTrue(path.is_file())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest["sha256"])

    def test_tampered_zip_is_rejected_and_not_written(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
            manifest = write_release(source, tamper=True)
            with self.assertRaises(UpdateError):
                updater.download(source, manifest, target)
            self.assertEqual(list(Path(target).iterdir()), [])

    def test_unsafe_zip_paths_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "bad.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("../escape.txt", "x")
            with self.assertRaises(UpdateError):
                updater.install(archive)

    def test_zip_without_installer_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "empty.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("PhiAxis/readme.txt", "x")
            with self.assertRaises(UpdateError):
                updater.install(archive)


class SourceTests(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.pop("PHIAXIS_UPDATE_SOURCE", None)

    def tearDown(self):
        os.environ.pop("PHIAXIS_UPDATE_SOURCE", None)
        if self._saved is not None:
            os.environ["PHIAXIS_UPDATE_SOURCE"] = self._saved

    def test_precedence_environment_then_artist_then_baked(self):
        with tempfile.TemporaryDirectory() as prefs, tempfile.TemporaryDirectory() as root:
            self.assertEqual(updater.update_source(prefs, root), "")
            (Path(root) / "update_source.txt").write_text("D:/baked\n")
            self.assertEqual(updater.update_source(prefs, root), "D:/baked")
            updater.save_update_source(prefs, "  D:/mine ")
            self.assertEqual(updater.update_source(prefs, root), "D:/mine")
            os.environ["PHIAXIS_UPDATE_SOURCE"] = "D:/env"
            self.assertEqual(updater.update_source(prefs, root), "D:/env")

    def test_unreadable_files_do_not_raise(self):
        with tempfile.TemporaryDirectory() as prefs:
            (Path(prefs) / "phiaxis_update.json").write_text("{broken")
            self.assertEqual(updater.update_source(prefs, None), "")


if __name__ == "__main__":
    unittest.main()
