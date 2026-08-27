"""Packaging tests: the things that break an install rather than a run.

Version drift across four manifests, a marketplace entry that clones over SSH,
a skill pointing at a launcher that moved — none of these show up when you run
the tool from a checkout, and all of them break somebody else's install.
"""

import json
import os
import shutil
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "claude-bingo"
SKILL = ROOT / "skills" / "bingo" / "SKILL.md"


def read_json(*parts):
    return json.loads((ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


class VersionLockstepTests(unittest.TestCase):
    def test_all_four_manifests_declare_the_same_version(self):
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))
        package = pyproject["project"]["version"]
        claude = read_json(".claude-plugin", "plugin.json")
        codex = read_json(".codex-plugin", "plugin.json")

        dunder = {}
        exec((ROOT / "claude_bingo" / "__init__.py").read_text("utf-8"), dunder)

        self.assertEqual(claude["version"], package, ".claude-plugin/plugin.json")
        self.assertEqual(codex["version"], package, ".codex-plugin/plugin.json")
        self.assertEqual(dunder["__version__"], package, "claude_bingo.__version__")

    def test_plugin_name_is_the_same_in_both_harnesses(self):
        self.assertEqual(
            read_json(".codex-plugin", "plugin.json")["name"],
            read_json(".claude-plugin", "plugin.json")["name"],
        )


class MarketplaceTests(unittest.TestCase):
    """This repo ships its own catalog for both harnesses."""

    def test_claude_marketplace_entry(self):
        market = read_json(".claude-plugin", "marketplace.json")
        entry, = market["plugins"]
        self.assertEqual(entry["name"], "claude-bingo")
        # The manifest owns the version; a copy here silently drifts.
        self.assertNotIn("version", entry)

    def test_codex_marketplace_entry(self):
        market = read_json(".agents", "plugins", "marketplace.json")
        entry, = market["plugins"]
        self.assertEqual(entry["name"], "claude-bingo")
        # Codex requires both policy fields plus a category to list an entry.
        self.assertIn("installation", entry["policy"])
        self.assertIn("authentication", entry["policy"])
        self.assertTrue(entry["category"])

    def test_every_source_clones_over_https(self):
        """The `github` shorthand clones over SSH and breaks keyless machines."""
        for parts in ((".claude-plugin", "marketplace.json"),
                      (".agents", "plugins", "marketplace.json")):
            for entry in read_json(*parts)["plugins"]:
                with self.subTest(manifest="/".join(parts), plugin=entry["name"]):
                    source = entry["source"]
                    self.assertEqual(source["source"], "url")
                    self.assertTrue(source["url"].startswith("https://"))
                    self.assertTrue(source["url"].endswith(".git"))


class LauncherTests(unittest.TestCase):
    def test_launcher_is_where_the_skill_says_it_is(self):
        self.assertTrue(LAUNCHER.is_file(), f"missing {LAUNCHER}")
        self.assertTrue(os.access(LAUNCHER, os.X_OK), "launcher is not executable")

    def test_runs_without_installing_the_package(self):
        result = subprocess.run(
            [sys.executable, str(LAUNCHER), "phrases"],
            check=False, capture_output=True, text=True,
            cwd=ROOT.parent,  # not the checkout: sys.path must come from the launcher
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("phrases", result.stdout)

    def test_old_python_gets_an_explanation_not_a_traceback(self):
        old = next((exe for exe in map(shutil.which, ("python3.10", "python3.9"))
                    if exe), None)
        if not old:
            self.skipTest("no pre-3.11 interpreter available to test the guard")
        result = subprocess.run(
            [old, str(LAUNCHER), "board"],
            check=False, capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("3.11", result.stderr)


class SkillTests(unittest.TestCase):
    def test_skill_is_declared_and_present(self):
        codex = read_json(".codex-plugin", "plugin.json")
        skills_dir = ROOT / codex["skills"].lstrip("./")
        self.assertTrue(skills_dir.is_dir(), f"missing {skills_dir}")
        self.assertTrue(SKILL.is_file(), f"missing {SKILL}")

    def test_skill_points_at_the_real_launcher(self):
        text = SKILL.read_text("utf-8")
        self.assertIn("scripts/claude-bingo", text)
        self.assertNotIn("/absolute/path/to", text)

    def test_documented_commands_are_real_subcommands(self):
        text = SKILL.read_text("utf-8") + (ROOT / "README.md").read_text("utf-8")
        for cmd in ("board", "score", "phrases"):
            self.assertIn(f"claude-bingo {cmd}", text)



class ScoringTests(unittest.TestCase):
    """The tool's own output is the loudest thing in a heavy user's logs."""

    def setUp(self):
        sys.path.insert(0, str(ROOT))
        from claude_bingo import cli
        self.cli = cli

    def test_a_rendered_board_would_have_self_scored(self):
        """Guard the premise: without the skip, playing inflates the next round."""
        from claude_bingo import phrases
        board = self.cli.make_board(5, 424242)
        text = self.cli.render(board)
        bank = phrases.load()["by_label"]
        hits = [c for c in board["cells"]
                if c != self.cli.FREE and bank[c].search(text)]
        self.assertGreater(len(hits), 5, "premise no longer holds; revisit the skip")

    def test_board_output_is_skipped_but_prose_is_not(self):
        board = self.cli.render(self.cli.make_board(5, 424242))
        self.assertIn(self.cli.BOARD_MARK, board)
        self.assertNotIn(
            self.cli.BOARD_MARK,
            "I'll go ahead and delve into the load-bearing parts — happy to!",
        )


if __name__ == "__main__":
    unittest.main()
