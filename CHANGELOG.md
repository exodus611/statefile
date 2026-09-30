# Changelog

## 0.1.0 — 2026-09-30

First release.

**Added**

- `check` — verifies the state file exists, is fresh, has the five sections that make it useful, holds no secrets, and that instruction files are free of patterns written for older models
- `init` — drafts a `STATE.md` from the repository's own git history
- GitHub Action (composite, no dependencies) so the check runs on every push
- `SECURITY.md` — what it reads, what it writes, what it does not protect you from

**Safety properties, enforced by the test suite**

- `check` writes nothing — verified by comparing file hashes before and after
- `init` creates only `STATE.md`, and refuses to overwrite
- no network code anywhere in the source
- stdlib-only imports
- every `git` call is a read-only subcommand

**Tests:** 23, across Python 3.9, 3.12 and 3.13.

**Not in this release:** `--fix` mode, pre-commit hook, packaging on PyPI.
