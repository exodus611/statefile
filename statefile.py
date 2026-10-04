#!/usr/bin/env python3
"""
statefile — check that your project's AI memory is real and still fresh.

Every repo that works with an AI assistant needs two different things kept apart:

  * RULES  — how the project should be worked on. They change rarely.
              Living in CLAUDE.md / AGENTS.md / .cursor/rules.
  * STATE  — what is true this week: what runs, what is blocked, what was
              already tried and killed. It changes every session.

State is the part that disappears. This tool checks that it exists, that it
has the five sections that make it useful, that it was touched recently, that
nobody pasted a secret into it, and that your instruction files have not
drifted back into patterns written for older models.

No dependencies. Python 3.9+.

Usage:
    python3 statefile.py check [--path .] [--state-file NOTES.md] [--max-age-days 14] [--json] [--strict]
    python3 statefile.py init  [--path .] [--state-file NOTES.md] [--force]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

VERSION = "0.2.1"

# Existing projects keep the original STATE.md convention. NOTES.md is also
# discovered for book/starter-kit projects; --state-file is the unambiguous
# choice when a repository contains more than one candidate.
STATE_NAMES = [
    "STATE.md",
    "state.md",
    "NOTES.md",
    "notes.md",
    "docs/STATE.md",
    "docs/NOTES.md",
    ".ai/STATE.md",
    ".ai/NOTES.md",
]

INSTRUCTION_NAMES = [
    "CLAUDE.md",
    "AGENTS.md",
    "agent.md",
    "GEMINI.md",
    ".cursorrules",
    ".cursor/rules",
    ".github/copilot-instructions.md",
    "instructions.md",
]

# The five sections that make a state file worth reading.
# Each entry: canonical name -> list of regexes matched against headings.
SECTIONS = {
    "now": [r"\bnow\b", r"\bruns?\b", r"\bcurrent\b", r"\bstatus\b", r"\bworking\b"],
    "in flight": [
        r"in[\s-]?flight",
        r"\bprogress\b",
        r"\bblocked\b",
        r"\bwip\b",
        r"\bpending\b",
        r"\bknown problems?\b",
    ],
    "decisions": [r"\bdecisions?\b", r"\bchoices?\b", r"\bwhy\b"],
    "dead ends": [r"dead[\s-]?ends?", r"\bfailed\b", r"\bdo not repeat\b", r"\bdont repeat\b", r"\btried\b", r"\bruled out\b"],
    "next": [r"\bnext\b", r"\btodo\b", r"\btasks?\b", r"\bfollow[\s-]?ups?\b"],
}

SECRET_PATTERNS = [
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
    (r"\bghp_[A-Za-z0-9]{20,}", "GitHub token (ghp_)"),
    (r"\bgithub_pat_[A-Za-z0-9_]{20,}", "GitHub token (github_pat_)"),
    (r"\bsk-[A-Za-z0-9]{20,}", "API key (sk-)"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key"),
    (r"\{\{\s*secrets\.[A-Z0-9_]+\s*\}\}", "unfilled template value"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}", "Slack token"),
]

# Patterns that frontier models no longer need, per Anthropic's published
# Opus 5 prompting guidance. They cost tokens and can duplicate work.
RULE_ANTIPATTERNS = [
    (r"\bdouble[\s-]?check\b", "verification ritual: the model already self-corrects"),
    (r"\bverify (twice|your work|your answer)\b", "verification ritual: duplicates work"),
    (r"\bre-?verify\b", "verification ritual: duplicates work"),
    (r"\bthink step by step\b", "reasoning scaffold: frontier models reason natively"),
    (r"\b(maximally|extremely|very) thorough\b", "emphasis booster: leads to extra tool calls"),
    (r"\bCRITICAL:|\bYOU MUST ALWAYS\b", "pressure language: turns into noise, not signal"),
]


def run(cmd, cwd):
    try:
        out = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=30
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def is_git_repo(path):
    return bool(run(["git", "rev-parse", "--is-inside-work-tree"], path)) or os.path.isdir(
        os.path.join(path, ".git")
    )


def last_touch_days(path, rel_path):
    """Days since the file was last changed, using git history when available."""
    if is_git_repo(path):
        stamp = run(["git", "log", "-1", "--format=%ct", "--", rel_path], path)
        if stamp.isdigit():
            return (time.time() - int(stamp)) / 86400.0
    full = os.path.join(path, rel_path)
    if os.path.exists(full):
        return (time.time() - os.path.getmtime(full)) / 86400.0
    return None


def normalize_state_file(path, name):
    """Return a safe repository-relative memory-file path.

    The explicit filename may come from a GitHub Action input, so absolute paths,
    traversal, and symlinks escaping the project are rejected before any read or
    write occurs.
    """
    if not name:
        return None
    candidate = os.path.normpath(name.replace("\\", "/"))
    if os.path.isabs(candidate) or candidate in ("", ".", "..") or candidate.startswith("../"):
        raise ValueError("state file must be a path inside the project")
    root = os.path.realpath(path)
    full = os.path.realpath(os.path.join(root, candidate))
    try:
        inside = os.path.commonpath([root, full]) == root
    except ValueError:
        inside = False
    if not inside:
        raise ValueError("state file must be a path inside the project")
    return candidate.replace(os.sep, "/")


def find_state_file(path, requested=None):
    if requested:
        return requested if os.path.isfile(os.path.join(path, requested)) else None
    for name in STATE_NAMES:
        full = os.path.join(path, name)
        if os.path.isfile(full):
            return name
    return None


def read(path, rel):
    with open(os.path.join(path, rel), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def headings(text):
    out = []
    for line in text.splitlines():
        m = re.match(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$", line)
        if m:
            out.append(m.group(1).lower())
    return out


def check_sections(text):
    found = headings(text)
    missing = []
    for canonical, patterns in SECTIONS.items():
        if not any(re.search(p, h) for h in found for p in [p for p in patterns]):
            # a section counts as present if any heading matches any of its patterns
            if not any(any(re.search(p, h) for p in patterns) for h in found):
                missing.append(canonical)
    return missing


def scan_secrets(text):
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if "http" in line and "-----BEGIN" not in line:
            continue
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, line):
                # Never echo the matching line: CI logs and JSON reports must not
                # become a second copy of the secret we are warning about.
                hits.append({"line": lineno, "kind": label})
                break
    return hits


def scan_rules(path):
    hits = []
    for name in INSTRUCTION_NAMES:
        full = os.path.join(path, name)
        if not os.path.isfile(full):
            continue
        try:
            text = read(path, name)
        except Exception:
            continue
        in_fence = False
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for pattern, why in RULE_ANTIPATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    hits.append(
                        {
                            "file": name,
                            "line": lineno,
                            "kind": why,
                            "excerpt": line.strip()[:80],
                        }
                    )
                    break
            else:
                # all-caps emphasis run: three or more shouty words
                if re.search(r"\b[A-Z]{3,}\b(?:\s+[A-Z]{3,}\b){2,}", line):
                    hits.append(
                        {
                            "file": name,
                            "line": lineno,
                            "kind": "all-caps emphasis: reads as pressure, not instruction",
                            "excerpt": line.strip()[:80],
                        }
                    )
    return hits


def check(path, max_age_days, state_file=None):
    findings = []
    state_rel = find_state_file(path, state_file)
    expected = state_file or "STATE.md or NOTES.md"

    if not state_rel:
        findings.append(
            {
                "level": "fail",
                "code": "STATE_MISSING",
                "message": f"No {expected} in this repository.",
                "fix": "Run statefile init with the same --state-file value, then edit the file.",
            }
        )
        state_text = ""
    else:
        state_text = read(path, state_rel)
        missing = check_sections(state_text)
        if missing:
            findings.append(
                {
                    "level": "warn",
                    "code": "STATE_SECTIONS",
                    "message": f"{state_rel} is missing sections: " + ", ".join(missing),
                    "fix": "Add the missing headings, even as placeholders.",
                }
            )
        days = last_touch_days(path, state_rel)
        if max_age_days and days is not None and days > max_age_days:
            findings.append(
                {
                    "level": "fail",
                    "code": "STATE_STALE",
                    "message": f"{state_rel} has not changed in {days:.0f} days (limit {max_age_days}).",
                    "fix": "Update it before the next session, or raise --max-age-days.",
                }
            )
        for hit in scan_secrets(state_text):
            findings.append(
                {
                    "level": "fail",
                    "code": "SECRET_IN_STATE",
                    "message": f"{hit['kind']} at {state_rel}:{hit['line']} — value redacted",
                    "fix": "Remove it and rotate the value. Never keep secrets in a state file.",
                }
            )

    for hit in scan_rules(path):
        findings.append(
            {
                "level": "warn",
                "code": "RULE_ANTIPATTERN",
                "message": f"{hit['file']}:{hit['line']} — {hit['kind']} — {hit['excerpt']}",
                "fix": "Delete the line, or say what you want done instead of how hard to try.",
            }
        )

    return {
        "version": VERSION,
        "path": os.path.abspath(path),
        "state_file": state_rel,
        "requested_state_file": state_file,
        "max_age_days": max_age_days,
        "findings": findings,
        "failed": any(f["level"] == "fail" for f in findings),
        "warned": any(f["level"] == "warn" for f in findings),
    }


MARK = {"fail": "FAIL", "warn": "WARN", "ok": "OK  "}


def render(result):
    lines = []
    if result["state_file"]:
        lines.append(f"state file: {result['state_file']}")
    else:
        lines.append("state file: not found")
    for f in result["findings"]:
        lines.append(f"[{MARK[f['level']]}] {f['code']}: {f['message']}")
        lines.append(f"         fix: {f['fix']}")
    if not result["findings"]:
        lines.append("[OK  ] STATE_OK: state file present, fresh, no secrets, rules clean")
    tail = "failed" if result["failed"] else ("warnings" if result["warned"] else "clean")
    lines.append(f"result: {tail}")
    return "\n".join(lines)


STATE_TEMPLATE = """# State

> One file, five sections, updated at the end of every session.
> The assistant reads this first and writes it back before the session ends.

## Now — what runs

- ...

## In flight

- ... (and what is blocking it)

## Decisions

- ... — because ...

## Dead ends — do not repeat

- ...

## Next three tasks

1. ...
2. ...
3. ...
"""


def cmd_init(path, force, state_file=None):
    rel = state_file or "STATE.md"
    target = os.path.join(path, rel)
    parent = os.path.dirname(target)
    if parent and not os.path.isdir(parent):
        print(f"parent directory does not exist: {parent}")
        return 2
    if os.path.exists(target) and not force:
        print(f"{rel} already exists in {path} — use --force to overwrite.")
        return 1
    body = STATE_TEMPLATE
    if is_git_repo(path):
        branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], path)
        commits = run(["git", "log", "-5", "--pretty=%h %s"], path)
        dirty = run(["git", "status", "--porcelain"], path)
        extra = ["", "<!-- draft notes from git, delete what does not apply -->"]
        if branch:
            extra.append(f"<!-- branch: {branch} -->")
        if commits:
            extra.append("<!-- last commits:")
            for c in commits.splitlines():
                extra.append(f"     {c}")
            extra.append("-->")
        if dirty:
            extra.append("<!-- uncommitted: " + str(len(dirty.splitlines())) + " file(s) -->")
        body = body.replace("## Now — what runs\n", "## Now — what runs\n\n<!-- from git -->\n", 1)
        body += "\n".join(extra) + "\n"
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(body)
    print(f"created {target}")
    print("next: fill in the five sections. It takes five minutes and it is the whole point.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="statefile",
        description="Check that your project's AI memory is real and still fresh.",
    )
    parser.add_argument("--version", action="version", version=f"statefile {VERSION}")
    sub = parser.add_subparsers(dest="command")

    c = sub.add_parser("check", help="check the state file and instruction files")
    c.add_argument("--path", default=".")
    c.add_argument("--state-file", help="repository-relative memory file, for example NOTES.md")
    c.add_argument("--max-age-days", type=int, default=14)
    c.add_argument("--json", action="store_true")
    c.add_argument("--strict", action="store_true", help="treat warnings as failures")

    i = sub.add_parser("init", help="create a state-file draft")
    i.add_argument("--path", default=".")
    i.add_argument("--state-file", help="repository-relative memory file, for example NOTES.md")
    i.add_argument("--force", action="store_true")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if not os.path.isdir(args.path):
        print(f"not a directory: {args.path}")
        return 2
    try:
        state_file = normalize_state_file(args.path, args.state_file)
    except ValueError as exc:
        print(f"invalid --state-file: {exc}")
        return 2
    if args.command == "init":
        return cmd_init(args.path, args.force, state_file)

    result = check(args.path, args.max_age_days, state_file)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render(result))
    if result["failed"] or (args.strict and result["warned"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
