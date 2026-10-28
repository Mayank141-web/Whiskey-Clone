import json
import os
import shutil
import tempfile
import unittest
import zipfile
from unittest import mock

from beer import bottles, cli, desktop, games, wine


class TempHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"BEER_HOME": os.path.join(self.tmp, "home")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp)

    def touch(self, rel, size=1):
        path = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"x" * size)
        return path


class GameDetectionTests(TempHome):
    def test_prefers_game_exe(self):
        self.touch("g/Uninstall.exe", 500)
        self.touch("g/mkxp-z.exe", 400)
        exe = self.touch("g/Game.exe", 10)
        self.assertEqual(games.find_game_exe(os.path.join(self.tmp, "g")), exe)

    def test_skips_installers_and_prefers_shallow(self):
        self.touch("g/setup.exe", 999)
        self.touch("g/sub/Other.exe", 999)
        exe = self.touch("g/Reborn.exe", 5)
        self.assertEqual(games.find_game_exe(os.path.join(self.tmp, "g")), exe)

    def test_no_exe(self):
        self.touch("g/readme.txt")
        self.assertIsNone(games.find_game_exe(os.path.join(self.tmp, "g")))

    def test_extract_zip_and_resolve(self):
        archive = os.path.join(self.tmp, "Pokemon Uranium.zip")
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("Pokemon Uranium/Game.exe", "MZ")
            zf.writestr("Pokemon Uranium/Fonts/power green.ttf", "font")
        exe = games.resolve_game(archive)
        self.assertTrue(exe.endswith(os.path.join("Pokemon Uranium", "Game.exe")))
        self.assertEqual(len(games.find_fonts(os.path.dirname(exe))), 1)

    def test_archive_stem(self):
        self.assertEqual(games.archive_stem("/x/Insurgence.tar.gz"), "Insurgence")


class BottleTests(TempHome):
    def test_create_list_programs_delete(self):
        b = bottles.create_bottle("Pokemon", initialize=False)
        exe = self.touch("Pokemon Reborn/Game.exe")
        self.assertEqual(b.add_program(exe), "Pokemon Reborn")
        again = bottles.get_bottle("Pokemon")
        self.assertEqual(again.find_program("pokemon reborn")["path"], exe)
        with open(os.path.join(again.path, "bottle.json")) as fh:
            self.assertEqual(json.load(fh)["windows_version"], "win10")
        self.assertEqual([x.name for x in bottles.list_bottles()], ["Pokemon"])
        with mock.patch.object(wine, "find_wine", return_value=None):
            bottles.delete_bottle("Pokemon")
        self.assertEqual(bottles.list_bottles(), [])

    def test_duplicate_and_bad_names(self):
        bottles.create_bottle("A", initialize=False)
        with self.assertRaises(bottles.BottleError):
            bottles.create_bottle("A", initialize=False)
        with self.assertRaises(bottles.BottleError):
            bottles.safe_name("../")

    def test_environment(self):
        b = bottles.create_bottle("Env", initialize=False)
        b.config["dll_overrides"] = {"d3d9": "native,builtin"}
        b.config["env"] = {"LANG": "ja_JP.UTF-8"}
        env = b.environment()
        self.assertEqual(env["WINEPREFIX"], b.prefix)
        self.assertEqual(env["WINEDLLOVERRIDES"], "d3d9=native,builtin")
        self.assertEqual(env["LANG"], "ja_JP.UTF-8")

    def test_install_fonts(self):
        b = bottles.create_bottle("F", initialize=False)
        font = self.touch("font.ttf")
        self.assertEqual(b.install_fonts([font]), 1)
        self.assertEqual(b.install_fonts([font]), 0)


class WineTests(unittest.TestCase):
    def test_every_package_manager_has_a_plan(self):
        for pm in ("apt-get", "dnf", "yum", "pacman", "zypper", "apk", "xbps-install", "emerge",
                   "eopkg", "nix-env", "swupd", "urpmi", "pkg"):
            self.assertTrue(wine.linux_install_steps(pm), pm)
        self.assertEqual(wine.linux_install_steps("nope"), [])

    def test_pick_mac_asset_prefers_stable(self):
        releases = [{"assets": [
            {"name": "wine-devel-10.17-osx64.tar.xz", "browser_download_url": "d"},
            {"name": "wine-stable-10.0-osx64.tar.xz", "browser_download_url": "s"},
        ]}]
        self.assertEqual(wine.pick_mac_wine_asset(releases), ("wine-stable-10.0-osx64.tar.xz", "s"))
        self.assertIsNone(wine.pick_mac_wine_asset([]))


class CliTests(TempHome):
    def test_help_and_list(self):
        with self.assertRaises(SystemExit):
            cli.main(["--help"])
        self.assertEqual(cli.main(["list"]), 0)
        self.assertEqual(cli.main(["bottle", "create", "X", "--no-init"]), 0)
        self.assertEqual(cli.main(["bottle", "info", "X"]), 0)
        self.assertEqual(cli.main(["bottle", "info", "missing"]), 1)

    def test_desktop_entry(self):
        entry = desktop.desktop_entry()
        self.assertIn("Exec=beer gui %f", entry)
        self.assertIn("application/x-ms-dos-executable", entry)


if __name__ == "__main__":
    unittest.main()
