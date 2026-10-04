# statefile

[![self-check](https://github.com/exodus611/statefile/actions/workflows/statefile.yml/badge.svg)](https://github.com/exodus611/statefile/actions/workflows/statefile.yml)
[![tests](https://github.com/exodus611/statefile/actions/workflows/tests.yml/badge.svg)](https://github.com/exodus611/statefile/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Check that your project's AI memory is real — and still fresh.**

A project that continues across AI sessions needs one human-readable file in the repository that holds **state**: what runs now, what is in flight, what was already tried and killed. Call it `STATE.md`, `NOTES.md`, or choose an explicit repository-relative path.

That file rots quietly. It gets stale, it loses sections, secrets creep into it, and instruction files drift back into patterns written for older models. `statefile` catches all of that — locally in one command, or in CI on every push.

```bash
python3 statefile.py init --state-file NOTES.md
python3 statefile.py check --state-file NOTES.md
```

Existing `STATE.md` projects remain compatible: omit `--state-file` and the tool auto-detects `STATE.md` or `NOTES.md`.

No dependencies. Python 3.9+. One file.

**See it catch a real failure:** [exodus611/statefile-demo](https://github.com/exodus611/statefile-demo) is a small project that forgot what it was doing — 47 days of stale state, a leaked placeholder, missing sections, outdated rules. The check fails on `main` and passes on the `fixed` branch, where the whole repair is two files and five minutes.

---

## What it checks

| Check | Level | Why it matters |
|---|---|---|
| `STATE_MISSING` | fail | No state file means every session starts by guessing |
| `STATE_SECTIONS` | warn | The five sections are what make it useful: now / in flight / decisions / dead ends / next |
| `STATE_STALE` | fail | A state file nobody updates is worse than none — it lies with confidence |
| `SECRET_IN_STATE` | fail | State files collect tokens and keys because they describe work. Never keep them there |
| `RULE_ANTIPATTERN` | warn | `double-check`, `think step by step`, `CRITICAL: YOU MUST ALWAYS` — patterns current models no longer need |

Example output:

```
state file: STATE.md
[FAIL] STATE_STALE: STATE.md has not changed in 40 days (limit 14).
         fix: Update it before the next session, or raise --max-age-days.
[WARN] RULE_ANTIPATTERN: CLAUDE.md:12 — verification ritual: the model already self-corrects — Always double-check your work.
         fix: Delete the line, or say what you want done instead of how hard to try.
result: failed
```

---

## Quickstart

```bash
git clone https://github.com/exodus611/statefile
cd statefile
python3 statefile.py init --path /path/to/your/project --state-file NOTES.md
python3 statefile.py check --path /path/to/your/project --state-file NOTES.md
```

Then paste this into your project's instruction file (`CLAUDE.md`, `AGENTS.md`, whatever your tool reads):

```
Before starting work, read NOTES.md. Before the session ends, update it:
what runs now, what is in flight, the decisions with reasons, dead ends,
and the next three tasks.
```

That is the whole method. The checker only makes sure you did not quietly stop.

### Useful flags

```bash
--path DIR          what to check (default: current directory)
--state-file FILE   explicit memory file, for example NOTES.md
--max-age-days N    how old the state file may be (default: 14; 0 disables the check)
--strict            warnings fail the run too
--json              machine-readable output for CI
```

Exit code is `0` when clean, `1` when something failed.

---

## In CI (recommended)

Copy `.github/workflows/statefile.yml` into your project:

```yaml
name: statefile
on: [push, pull_request, workflow_dispatch]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: exodus611/statefile@v0.2.0
        with:
          state-file: NOTES.md
          max-age-days: '14'
```

If you prefer zero Actions, run the script directly:

```bash
curl -sO https://raw.githubusercontent.com/exodus611/statefile/main/statefile.py
python3 statefile.py check --state-file NOTES.md
```

### Badge

Every repository that runs the check can show it in its README — the badge is the workflow status of *your* repo, so it is honest by construction:

```markdown
[![statefile](https://github.com/OWNER/REPO/actions/workflows/statefile.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/statefile.yml)
```

---

## Why this, and not a bigger tool

There are excellent tools for reviewing code, auditing release artefacts and linting prompts. None of them look at the one thing that decides whether your week goes well: **whether the project's state was written down somewhere the assistant will read.**

Rules and state are different:

- **Rules** — how to work here. Change rarely. Live in `CLAUDE.md` / `AGENTS.md`.
- **State** — what is true this week. Changes every session. Lives in the selected memory file, commonly `STATE.md` or `NOTES.md`.

Most projects have the first and no second, which is why they feel like they start over every morning.

## Honest limits

- It checks that the file exists, is fresh, is structured and is safe. It cannot judge whether what you wrote is *true*.
- Freshness is measured from git history when available, file modification time otherwise.
- In CI, "fresh" means the file was touched in a recent commit. If you update state only locally, raise `--max-age-days` or run the check locally.
- The rule patterns are a small, high-signal set drawn from Anthropic's published prompting guidance for current models. They are warnings, not laws — a deliberate `THINK STEP BY STEP` in a test fixture is fine.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

29 tests, run on every push against Python 3.9, 3.12 and 3.13 — including safety properties that are enforced by the suite itself: `check` modifies nothing, `init` creates only the selected memory file, unsafe paths are rejected, the source contains no network code, imports are stdlib only, and every `git` call uses a read-only subcommand. See [SECURITY.md](SECURITY.md) for the full picture and how to verify it in ten minutes.

## License

MIT.

---

*The method behind this tool — and the three levels of checking that keep a state file from rotting into confident nonsense — is written up in **Never Start from Scratch**: <https://exodus611.github.io/>. The tool works on its own; the book explains the parts that are easy to get wrong.*
