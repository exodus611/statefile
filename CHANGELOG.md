# Changelog

## 0.2.3 — 2026-10-04

**Added**

- scan `PROTOCOL.md` and `docs/PROTOCOL.md` alongside recognized agent-instruction files
- regression coverage confirming protocol files receive rule-antipattern checks

## 0.2.2 — 2026-10-04

**Fixed**

- quote the action description so GitHub's action-manifest parser accepts the colon in the text
- verify the composite action in the repository's self-check workflow

## 0.2.1 — 2026-10-04

**Security**

- redact matched secret values from human-readable and JSON findings so CI logs do not create another copy of a detected credential
- add a regression test covering both output formats

## 0.2.0 — 2026-10-04

**Added**

- `--state-file FILE` for `check` and `init`, so projects can explicitly use `NOTES.md`, `STATE.md`, or another repository-relative memory file
- GitHub Action input `state-file`
- automatic discovery of common `NOTES.md` locations when no explicit file is supplied
- path-safety checks that reject absolute paths, traversal, and symlinks escaping the project
- tests for explicit selection, auto-detection, missing-file behavior, initialization, and path safety

**Compatibility**

- existing `STATE.md` projects and workflows continue to work without changes
- `STATE.md` remains first in auto-detection order; use `state-file: NOTES.md` when both files exist

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
