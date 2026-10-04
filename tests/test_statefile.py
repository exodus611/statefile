"""Tests for statefile. Run: python3 -m unittest discover -s tests -v"""

import hashlib
import json
import os
import re
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

GOOD_NOTES = """# Project Notes

## Goal and definition of done
- ship a working project

## Current state — last verified 2026-10-04
- the daily job runs

## Repository map
- source is in src/

## Decisions made
- keep project memory with the project

## Failed approaches — do not repeat
- cron in the web app

## Known problems
- price source move is blocked on vendor choice

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

    def test_notes_file_is_auto_detected(self):
        self.write("NOTES.md", GOOD_NOTES)
        out, data = self.as_json()
        self.assertEqual(out.returncode, 0)
        self.assertEqual(data["state_file"], "NOTES.md")
        self.assertEqual(data["findings"], [])

    def test_explicit_notes_file_is_checked(self):
        self.write("STATE.md", GOOD)
        self.write("NOTES.md", GOOD_NOTES)
        out, data = self.as_json("--state-file", "NOTES.md")
        self.assertEqual(out.returncode, 0)
        self.assertEqual(data["state_file"], "NOTES.md")
        self.assertEqual(data["requested_state_file"], "NOTES.md")

    def test_explicit_missing_file_does_not_fall_back(self):
        self.write("STATE.md", GOOD)
        out, data = self.as_json("--state-file", "NOTES.md")
        self.assertEqual(out.returncode, 1)
        self.assertIsNone(data["state_file"])
        self.assertIn("NOTES.md", data["findings"][0]["message"])

    def test_state_file_path_cannot_escape_project(self):
        out = run(["check", "--path", self.dir, "--state-file", "../NOTES.md"], self.dir)
        self.assertEqual(out.returncode, 2)
        self.assertIn("inside the project", out.stdout)

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

    def test_secret_in_state_file_fails_without_echoing_value(self):
        secret = "ghp_" + "a" * 30
        self.write("STATE.md", GOOD + f"\ntoken: {secret}\n")
        out, data = self.as_json()
        self.assertEqual(out.returncode, 1)
        self.assertIn("SECRET_IN_STATE", [f["code"] for f in data["findings"]])
        self.assertNotIn(secret, out.stdout)
        human = run(["check", "--path", self.dir], self.dir)
        self.assertNotIn(secret, human.stdout)
        self.assertIn("value redacted", human.stdout)

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

    def test_init_can_create_notes_file(self):
        out = run(["init", "--path", self.dir, "--state-file", "NOTES.md"], self.dir)
        self.assertEqual(out.returncode, 0)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "NOTES.md")))
        self.assertFalse(os.path.exists(os.path.join(self.dir, "STATE.md")))
        checked = run(["check", "--path", self.dir, "--state-file", "NOTES.md"], self.dir)
        self.assertEqual(checked.returncode, 0)

    def test_init_rejects_path_outside_project(self):
        parent = os.path.dirname(self.dir)
        target = os.path.join(parent, "escaped-NOTES.md")
        if os.path.exists(target):
            os.unlink(target)
        out = run(["init", "--path", self.dir, "--state-file", "../escaped-NOTES.md"], self.dir)
        self.assertEqual(out.returncode, 2)
        self.assertFalse(os.path.exists(target))


class TestCli(unittest.TestCase):
    def test_version(self):
        out = run(["--version"], ROOT)
        self.assertIn("statefile", out.stdout)

    def test_help_without_command(self):
        out = run([], ROOT)
        self.assertIn("check", out.stdout)


if __name__ == "__main__":
    unittest.main()


class TestSafety(unittest.TestCase):
    """Properties that make the tool safe to run: no writes, no network.

    These are regression tests. If someone later adds a network call or makes
    `check` modify files, these fail before the change reaches anyone.
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        with open(os.path.join(self.dir, "STATE.md"), "w", encoding="utf-8") as fh:
            fh.write(GOOD)

    def _hashes(self):
        out = {}
        for root, _dirs, files in os.walk(self.dir):
            for name in files:
                full = os.path.join(root, name)
                with open(full, "rb") as fh:
                    out[full] = hashlib.sha256(fh.read()).hexdigest()
        return out

    def test_check_modifies_nothing(self):
        before = self._hashes()
        run(["check", "--path", self.dir], self.dir)
        run(["check", "--path", self.dir, "--json"], self.dir)
        run(["check", "--path", self.dir, "--strict"], self.dir)
        self.assertEqual(before, self._hashes())

    def test_init_creates_only_the_state_file(self):
        empty = tempfile.mkdtemp()
        run(["init", "--path", empty], empty)
        self.assertEqual(os.listdir(empty), ["STATE.md"])

    def test_source_makes_no_network_calls(self):
        with open(TOOL, encoding="utf-8") as fh:
            source = fh.read()
        # the single "http" occurrence is a string used to skip URLs while scanning
        for bad in ("urllib", "requests", "socket", "urlopen", "http.client", "webbrowser"):
            self.assertNotIn(bad, source, f"{bad} must not appear in the tool")

    def test_source_imports_stdlib_only(self):
        with open(TOOL, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        imports = [l.split()[1] for l in lines if l.startswith("import ")]
        self.assertEqual(sorted(imports), sorted(["argparse", "json", "os", "re", "subprocess", "sys", "time"]))

    def test_git_commands_are_read_only(self):
        """Every git call must use a read-only subcommand.

        Allowed: rev-parse, log, status. Anything that can change a repository
        (push, commit, checkout, reset, clean, merge, rebase, fetch, pull, tag)
        must never appear as a git subcommand in this tool.
        """
        with open(TOOL, encoding="utf-8") as fh:
            source = fh.read()
        subcommands = re.findall(r'run\(\[\s*"git"\s*,\s*"([a-z-]+)"', source)
        self.assertTrue(subcommands, "expected to find git calls in the source")
        for sub in subcommands:
            self.assertIn(sub, {"rev-parse", "log", "status"}, f"git {sub} is not read-only")
        for forbidden in ("push", "commit", "checkout", "reset", "clean", "merge", "rebase", "fetch", "pull", "tag"):
            self.assertNotIn(f'"git", "{forbidden}"', source, f"git {forbidden} must not be used")
