"""Tests for statefile. Run: python3 -m unittest discover -s tests -v"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOL = os.path.join(ROOT, "statefile.py")

GOOD = """# State

## Now — what runs
- the daily job

## In flight
- price source move, blocked on vendor choice

## Decisions
- keep state in one file — because the chat dies with the window

## Dead ends — do not repeat
- cron in the web app

## Next three tasks
1. a
2. b
3. c
"""


def run(args, cwd):
    return subprocess.run(
        [sys.executable, TOOL] + args, cwd=cwd, capture_output=True, text=True
    )


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def write(self, name, text):
        path = os.path.join(self.dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def as_json(self, *args):
        out = run(["check", "--path", self.dir, "--json"] + list(args), self.dir)
        return out, json.loads(out.stdout)

    def test_missing_state_file_fails(self):
        out, data = self.as_json()
        self.assertEqual(out.returncode, 1)
        self.assertIn("STATE_MISSING", [f["code"] for f in data["findings"]])

    def test_good_state_file_is_clean(self):
        self.write("STATE.md", GOOD)
        out, data = self.as_json()
        self.assertEqual(data["findings"], [])
        self.assertEqual(out.returncode, 0)

    def test_stale_state_file_fails(self):
        path = self.write("STATE.md", GOOD)
        old = time.time() - 90 * 86400
        os.utime(path, (old, old))
        out, data = self.as_json()
        self.assertEqual(out.returncode, 1)
        self.assertIn("STATE_STALE", [f["code"] for f in data["findings"]])

    def test_age_check_can_be_disabled(self):
        path = self.write("STATE.md", GOOD)
        old = time.time() - 90 * 86400
        os.utime(path, (old, old))
        out, data = self.as_json("--max-age-days", "0")
        self.assertEqual(out.returncode, 0)
        self.assertEqual(data["findings"], [])

    def test_missing_sections_warn(self):
        self.write("STATE.md", "# State\n\n## Now\n- x\n")
        out, data = self.as_json()
        self.assertEqual(out.returncode, 0)  # warning, not failure
        codes = [f["code"] for f in data["findings"]]
        self.assertIn("STATE_SECTIONS", codes)

    def test_strict_turns_warnings_into_failure(self):
        self.write("STATE.md", "# State\n\n## Now\n- x\n")
        out = run(["check", "--path", self.dir, "--strict"], self.dir)
        self.assertEqual(out.returncode, 1)

    def test_secret_in_state_file_fails(self):
        self.write("STATE.md", GOOD + "\ntoken: ghp_" + "a" * 30 + "\n")
        out, data = self.as_json()
        self.assertEqual(out.returncode, 1)
        self.assertIn("SECRET_IN_STATE", [f["code"] for f in data["findings"]])

    def test_placeholder_template_fails(self):
        self.write("STATE.md", GOOD + "\ndeploy: {{ secrets.OPENAI_API_KEY }}\n")
        out, data = self.as_json()
        codes = [f["code"] for f in data["findings"]]
        self.assertIn("SECRET_IN_STATE", codes)

    def test_urls_and_prose_are_not_secrets(self):
        self.write("STATE.md", GOOD + "\n- docs: https://example.com/a/very/long/path/that/keeps/going/for/a/while/ok\n")
        out, data = self.as_json()
        self.assertEqual(data["findings"], [])

    def test_rule_antipatterns_warn(self):
        self.write("STATE.md", GOOD)
        self.write("CLAUDE.md", "# Rules\n\nAlways double-check your work.\nThink step by step.\n")
        out, data = self.as_json()
        codes = [f["code"] for f in data["findings"]]
        self.assertEqual(codes.count("RULE_ANTIPATTERN"), 2)
        self.assertEqual(out.returncode, 0)

    def test_allcaps_emphasis_warns(self):
        self.write("STATE.md", GOOD)
        self.write("AGENTS.md", "YOU MUST ALWAYS VERIFY EVERYTHING\n")
        out, data = self.as_json()
        self.assertIn("RULE_ANTIPATTERN", [f["code"] for f in data["findings"]])

    def test_rules_inside_code_fence_are_ignored(self):
        self.write("STATE.md", GOOD)
        self.write("CLAUDE.md", "# Rules\n\n```\nthink step by step\n```\n")
        out, data = self.as_json()
        self.assertEqual(data["findings"], [])

    def test_human_output_contains_result_line(self):
        self.write("STATE.md", GOOD)
        out = run(["check", "--path", self.dir], self.dir)
        self.assertIn("result: clean", out.stdout)


class TestInit(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_init_creates_file(self):
        out = run(["init", "--path", self.dir], self.dir)
        self.assertEqual(out.returncode, 0)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "STATE.md")))

    def test_init_does_not_overwrite(self):
        path = os.path.join(self.dir, "STATE.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("mine")
        out = run(["init", "--path", self.dir], self.dir)
        self.assertEqual(out.returncode, 1)
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "mine")

    def test_init_then_check_passes(self):
        run(["init", "--path", self.dir], self.dir)
        out = run(["check", "--path", self.dir], self.dir)
        self.assertEqual(out.returncode, 0)


class TestCli(unittest.TestCase):
    def test_version(self):
        out = run(["--version"], ROOT)
        self.assertIn("statefile", out.stdout)

    def test_help_without_command(self):
        out = run([], ROOT)
        self.assertIn("check", out.stdout)


if __name__ == "__main__":
    unittest.main()
