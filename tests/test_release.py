"""End-to-end: build a release, install it into a throwaway Documents folder, load it in
real Houdini, update it, roll the old versions forward and uninstall.

Uses temporary folders only: your Houdini preferences and %LOCALAPPDATA% are untouched.
Skipped where PowerShell is missing. The Houdini load checks are skipped for versions that
are not installed (set HOUDINI_ROOT to look elsewhere).
"""
import glob
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "python3.10libs"))
import make_release                                  # noqa: E402
from composition_guides import updater               # noqa: E402

HOUDINI_ROOT = os.environ.get("HOUDINI_ROOT", "C:/Program Files/Side Effects Software")
POWERSHELL = shutil.which("powershell")


def hython(label):
    found = sorted(glob.glob("%s/Houdini %s.*/bin/hython.exe" % (HOUDINI_ROOT, label)))
    return found[-1] if found else None


def run_installer(unpacked, documents, root, *arguments):
    command = [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
               str(Path(unpacked) / "install.ps1"), "-Quiet", "-Documents", str(documents),
               "-InstallRoot", str(root)] + list(arguments)
    return subprocess.run(command, capture_output=True, text=True, timeout=120)


@unittest.skipUnless(POWERSHELL and os.name == "nt", "needs Windows PowerShell")
class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = Path(tempfile.mkdtemp(prefix="phiaxis_release_test_"))
        cls.dist = cls.temp / "dist"
        cls.archive, cls.manifest = make_release.build(cls.dist, update_source="D:/share/phiaxis")
        cls.unpacked = cls.temp / "unpacked"
        with zipfile.ZipFile(cls.archive) as z:
            z.extractall(cls.unpacked)
        cls.top = cls.unpacked / "PhiAxis"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp, ignore_errors=True)

    def fresh(self, name):
        documents, root = self.temp / (name + "_docs"), self.temp / (name + "_root")
        for version in ("20.5", "22.0", "19.5", "23.0"):
            (documents / ("houdini" + version)).mkdir(parents=True, exist_ok=True)
        return documents, root

    # ---------------------------------------------------------------- the release
    def test_release_contents(self):
        names = set(zipfile.ZipFile(self.archive).namelist())
        self.assertIn("PhiAxis/install.ps1", names)
        self.assertIn("PhiAxis/Install PhiAxis.cmd", names)
        self.assertIn("PhiAxis/payload/VERSION.json", names)
        self.assertIn("PhiAxis/payload/python3.10libs/composition_guides/__init__.py", names)
        self.assertIn("PhiAxis/payload/config/Icons/PhiAxis.png", names)
        self.assertIn("PhiAxis/payload/update_source.txt", names)
        leaked = [n for n in names if n.split("/")[1:2] and n.split("/")[1] in
                  ("demo", "tests", "showcase", "game_refs", "film_refs", "painting_refs", "ref")]
        self.assertEqual(leaked, [], "reference or demo material must not ship")
        self.assertFalse([n for n in names if "__pycache__" in n or n.endswith(".pyc")])
        self.assertEqual(self.manifest["version"], make_release.read_version())
        self.assertTrue(updater.read_manifest(self.dist)["sha256"] == self.manifest["sha256"])

    # ---------------------------------------------------------------- installing
    def test_install_writes_packages_for_supported_houdinis_only(self):
        documents, root = self.fresh("install")
        legacy = documents / "houdini22.0" / "packages"
        legacy.mkdir()
        (legacy / "composition_guides.json").write_text("{}")
        done = run_installer(self.top, documents, root)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        for label in ("20.5", "22.0"):
            package = documents / ("houdini" + label) / "packages" / "phiaxis.json"
            data = json.loads(package.read_text(encoding="utf-8"))
            self.assertIn("20.5", data["enable"])
            location = Path(data["env"][0]["PHIAXIS"])
            self.assertTrue((location / "python3.10libs" / "composition_guides" / "__init__.py").exists())
        for label in ("19.5", "23.0"):
            self.assertFalse((documents / ("houdini" + label) / "packages").exists(), label)
        self.assertFalse((legacy / "composition_guides.json").exists())
        self.assertEqual(len(list(legacy.glob("composition_guides.json.bak-*"))), 1)
        record = json.loads((root / "installed.json").read_text(encoding="utf-8"))
        self.assertEqual(record["version"], self.manifest["version"])
        self.assertEqual((root / "update_source.txt").read_text().strip(), "D:/share/phiaxis")

    def test_only_requested_versions_and_keep_legacy(self):
        documents, root = self.fresh("only")
        legacy = documents / "houdini22.0" / "packages"
        legacy.mkdir()
        (legacy / "composition_guides.json").write_text("{}")
        done = run_installer(self.top, documents, root, "-Houdini", "22.0", "-KeepLegacy")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue((documents / "houdini22.0" / "packages" / "phiaxis.json").exists())
        self.assertFalse((documents / "houdini20.5" / "packages").exists())
        self.assertTrue((legacy / "composition_guides.json").exists())

    def test_no_houdini_gives_a_clear_message(self):
        documents, root = self.temp / "empty_docs", self.temp / "empty_root"
        documents.mkdir()
        done = run_installer(self.top, documents, root)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("preferences folder", done.stdout)
        self.assertFalse(root.exists())

    def test_installing_twice_is_harmless(self):
        documents, root = self.fresh("twice")
        for _ in range(2):
            done = run_installer(self.top, documents, root)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(list((root / "versions").iterdir())), 1)

    # --------------------------------------------------------- Houdini really loads it
    def test_houdini_loads_the_installed_plugin(self):
        documents, root = self.fresh("houdini")
        self.assertEqual(run_installer(self.top, documents, root).returncode, 0)
        script = self.temp / "probe.py"
        script.write_text(
            "import hou, composition_guides as cg\n"
            "print('LOADED', cg.__version__, hou.applicationVersionString()[:4])\n"
            "print('SHELF', bool(hou.findFile('toolbar/composition_guides.shelf')))\n"
            "print('ICON', bool(hou.findFile('config/Icons/PhiAxis.png')))\n"
            "print('UPDATER', hasattr(cg, 'check_for_updates'))\n", encoding="utf-8")
        checked = 0
        for label in ("20.5", "22.0"):
            exe = hython(label)
            if not exe:
                continue
            env = dict(os.environ, HOUDINI_USER_PREF_DIR=str(documents / ("houdini" + label)))
            env.pop("HOUDINI_PACKAGE_DIR", None)
            done = subprocess.run([exe, str(script)], capture_output=True, text=True,
                                  timeout=180, env=env)
            out = done.stdout
            self.assertIn("LOADED %s" % make_release.read_version(), out, label + "\n" + out + done.stderr)
            self.assertIn("SHELF True", out, label)
            self.assertIn("ICON True", out, label)
            self.assertIn("UPDATER True", out, label)
            checked += 1
        if not checked:
            self.skipTest("no Houdini 20.5 or 22.0 found to load the plugin in")

    # ---------------------------------------------------------------- updating
    def test_update_flow_keeps_one_previous_version(self):
        documents, root = self.fresh("update")
        self.assertEqual(run_installer(self.top, documents, root).returncode, 0)
        installed = make_release.read_version()
        original = make_release.read_version
        try:
            for fake in ("9.0.0", "9.0.1"):
                make_release.read_version = lambda fake=fake: fake
                feed = self.temp / ("feed_" + fake.replace(".", "_"))
                make_release.build(feed)
                manifest = updater.check(feed, installed, (22, 0))
                self.assertEqual(manifest["version"], fake)
                with tempfile.TemporaryDirectory() as downloads:
                    archive = updater.download(feed, manifest, downloads)
                    ok, output = updater.install(archive, ("-Documents", str(documents),
                                                           "-InstallRoot", str(root)))
                self.assertTrue(ok, output)
                installed = fake
        finally:
            make_release.read_version = original
        kept = sorted(p.name for p in (root / "versions").iterdir())
        self.assertEqual(kept, ["9.0.0", "9.0.1"], "this and the previous version only")
        package = json.loads((documents / "houdini22.0" / "packages" / "phiaxis.json").read_text())
        self.assertTrue(package["env"][0]["PHIAXIS"].endswith("versions/9.0.1"))

    def test_tampered_download_never_reaches_the_installer(self):
        feed = self.temp / "feed_tampered"
        feed.mkdir()
        shutil.copy2(self.archive, feed / self.archive.name)
        manifest = dict(self.manifest)
        (feed / "version.json").write_text(json.dumps(manifest))
        (feed / self.archive.name).write_bytes((feed / self.archive.name).read_bytes() + b"!")
        with tempfile.TemporaryDirectory() as downloads:
            with self.assertRaises(updater.UpdateError):
                updater.download(feed, manifest, downloads)

    # --------------------------------------------------------------- uninstalling
    def test_uninstall_removes_the_plugin_and_keeps_settings(self):
        documents, root = self.fresh("uninstall")
        self.assertEqual(run_installer(self.top, documents, root).returncode, 0)
        settings = documents / "houdini22.0" / "composition_guides.json"
        settings.write_text('{"version": 1, "settings": {}}')
        done = run_installer(self.top, documents, root, "-Uninstall")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertFalse((documents / "houdini22.0" / "packages" / "phiaxis.json").exists())
        self.assertFalse(root.exists())
        self.assertTrue(settings.exists())


if __name__ == "__main__":
    unittest.main()
