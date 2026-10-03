"""The artist's update flow inside a real Houdini 22 (needs the Houdini GUI, about a minute).

Installs the current release into throwaway folders, publishes a newer fake release as the
update source, starts Houdini with only those folders in play, and drives the "Check for
Updates" code path with the dialogs answered like an artist would. Your own preferences and
%LOCALAPPDATA% are not touched. Skipped when Houdini 22 is missing.
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

HOUDINI_ROOT = os.environ.get("HOUDINI_ROOT", "C:/Program Files/Side Effects Software")
EXE = (sorted(glob.glob("%s/Houdini 22.0.*/bin/houdini.exe" % HOUDINI_ROOT)) or [None])[-1]


@unittest.skipUnless(EXE and os.name == "nt", "needs Houdini 22 on Windows")
class UpdateInHoudini(unittest.TestCase):
    def test_check_for_updates_flow(self):
        temp = Path(tempfile.mkdtemp(prefix="phiaxis_update_gui_"))
        try:
            documents = temp / "Documents"
            (documents / "houdini22.0").mkdir(parents=True)
            local = temp / "Local"                       # stands in for %LOCALAPPDATA%
            local.mkdir()
            # The release being "installed" now, and a newer one on offer.
            current = make_release.read_version()
            archive, _ = make_release.build(temp / "dist_current")
            with zipfile.ZipFile(archive) as z:
                z.extractall(temp / "unpacked")
            env = dict(os.environ, PHIAXIS_DOCUMENTS=str(documents), LOCALAPPDATA=str(local),
                       HOUDINI_USER_PREF_DIR=str(documents / "houdini22.0"),
                       HOUDINI_ANONYMOUS_STATISTICS="0", PHIAXIS_TEST_OUT=str(temp))
            env.pop("HOUDINI_PACKAGE_DIR", None)
            env.pop("PHIAXIS_UPDATE_SOURCE", None)
            done = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                 str(temp / "unpacked" / "PhiAxis" / "install.ps1"), "-Quiet"],
                capture_output=True, text=True, env=env, timeout=120)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            original = make_release.read_version
            try:
                make_release.read_version = lambda: "9.0.0"
                make_release.build(temp / "feed_new")
                make_release.read_version = lambda: current
                make_release.build(temp / "feed_same")
            finally:
                make_release.read_version = original
            env["PHIAXIS_UPDATE_SOURCE"] = str(temp / "feed_new")
            env["PHIAXIS_TEST_FEED_SAME"] = str(temp / "feed_same")
            subprocess.run([EXE, "-desktop", "Build", "waitforui",
                            str(ROOT / "tests" / "update_houdini.py")], env=env, timeout=420)
            log = json.loads((temp / "houdini_log.json").read_text(encoding="utf-8"))
            self.assertNotIn("error", log, log.get("error"))
            self.assertEqual(log["version"], current)
            self.assertIn(str(local), log["file"], "the plugin must load from the installed copy")
            messages = [m["text"] for m in log["messages"]]
            self.assertTrue(any("9.0.0 is available" in m for m in messages), messages)
            self.assertTrue(any("9.0.0 is installed" in m and "Restart Houdini" in m
                                for m in messages), messages)
            self.assertTrue(any("is up to date" in m["text"] for m in log["up_to_date"]),
                        log["up_to_date"])
            self.assertEqual(len(log["inputs"]), 1, "asked once where updates come from")
            versions = sorted(p.name for p in (local / "PhiAxis" / "versions").iterdir())
            self.assertEqual(versions, sorted([current, "9.0.0"]))
            package = json.loads((documents / "houdini22.0" / "packages" / "phiaxis.json").read_text())
            self.assertTrue(package["env"][0]["PHIAXIS"].endswith("versions/9.0.0"))
        finally:
            shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
