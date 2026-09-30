# Security

**Short version: statefile reads a few files in one directory, calls `git` for read-only information, and sends nothing anywhere. `check` never writes anything. The whole tool is one file of ~380 lines with no dependencies, so you can verify all of this in ten minutes.**

## What it reads

Only these filenames, and only inside the directory you pass with `--path`:

- `STATE.md` (or `state.md`, `docs/STATE.md`, `.ai/STATE.md`)
- `CLAUDE.md`, `AGENTS.md`, `agent.md`, `GEMINI.md`, `instructions.md`
- `.cursorrules`, `.cursor/rules`, `.github/copilot-instructions.md`

It does not walk your repository, does not read source code, and does not look at any other files.

## What it writes

| Command | Writes |
|---|---|
| `statefile.py check` | **Nothing.** Verified by test — file hashes are identical before and after. |
| `statefile.py init` | Creates `STATE.md` only. Refuses to overwrite an existing file unless you pass `--force`. |

## Network

There is none. No telemetry, no analytics, no update check, no API calls, no accounts, no keys.
Imports are `argparse`, `json`, `os`, `re`, `subprocess`, `sys`, `time` — stdlib only.

Verify it yourself:

```bash
grep -nE "urllib|requests|socket|urlopen|http" statefile.py   # only a string literal used to skip URLs
python3 -m unittest tests.test_statefile.TestSafety -v
```

## Subprocesses

It runs `git` — read-only commands only:

```
git rev-parse --is-inside-work-tree
git rev-parse --abbrev-ref HEAD
git log -1 --format=%ct -- <file>
git log -5 --pretty=%h %s
git status --porcelain
```

No `git` command here changes the repository.

## What it does not protect you from

Being explicit about the limits, since this is a security document:

- It **flags** secrets it recognises in the state file (private-key blocks, `ghp_`, `sk-`, `AKIA`, unfilled `{{ secrets.* }}` templates). It is pattern matching, not entropy analysis: an unusual token format can slip past.
- It reads the files listed above — if you keep secrets in `CLAUDE.md`, the tool will read that file (locally, without sending it anywhere) and may or may not recognise the value.
- It is not a sandbox. Running any tool from the internet is a trust decision; this one is small enough to read, which is the only real defence.

## Reporting

Open an issue, or write to the address in the repository profile. Please do not paste real secrets into an issue.
