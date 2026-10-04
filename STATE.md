# State

> This repository uses its own tool on itself. The file is a project map, not proof; verify important claims against tests, workflows, tags, and Git history.

## Goal and definition of done

Maintain a small, dependency-free project-memory checker that can run locally and as a pinned GitHub Action. A release is ready when its tests pass on supported Python versions, its action checks the repository successfully, documentation matches behavior, and the published tag points to the reviewed commit.

## Current state — last verified 2026-10-04

- `statefile.py check` and `statefile.py init` are implemented using the Python standard library only.
- Version `v0.2.3` is published at commit `8e9dc90f98ee181b885fec72ce7f771b66d60057`.
- 30 unit tests pass locally.
- `.github/workflows/tests.yml` runs tests on Python 3.9, 3.12, and 3.13.
- `.github/workflows/statefile.yml` runs this repository's local composite action on `STATE.md` with strict mode and least-privilege read access. On commit `67378b0851f33f0b0f0333a916cc1f534daf8783`, strict self-check run `37229520941` and test run `37229520866` completed successfully.
- The checker detects freshness, required structural signals, obvious secret shapes, and recognized instruction-rule patterns. It does not prove that state claims are factually true.

## Repository map

- `statefile.py` — command-line implementation.
- `action.yml` — composite GitHub Action interface.
- `tests/test_statefile.py` — unit and safety tests.
- `.github/workflows/tests.yml` — supported-version test matrix.
- `.github/workflows/statefile.yml` — self-check workflow.
- `README.md`, `CHANGELOG.md`, and `SECURITY.md` — public documentation and policies.

## Decisions

- Keep the implementation standard-library-only to reduce installation friction.
- Measure freshness from Git history first and file modification time second because CI checkouts do not preserve useful source mtimes.
- Keep heuristic rule findings as warnings by default; repositories that adopt the complete Reader Kit explicitly enable strict mode.
- Use immutable commit SHAs when other repositories consume the action.

## Failed approaches — do not repeat

- Parsing state sections with a fixed heading list broke on legitimate variants; structural keyword matching is more portable.
- Skipping only lines beginning with a Markdown fence misses the remaining fenced block; fence state must be tracked.
- A green mechanical check does not prove the statements in this file are current; the previous file passed while still mentioning the obsolete planned `v0.1.0` release.

## Known problems

- No concise repository instruction file was committed before the current local repair.
- The self-check workflow did not explicitly enable strict mode.
- Future release or pre-commit work has not been approved and should not be inferred from old notes.

## Next three tasks

1. Keep release documentation and this state file aligned with published tags.
2. Monitor the strict self-check for real repository instruction changes rather than weakening it for green CI.
3. Consider a pre-commit integration only if a real user need and maintenance plan are established.

## Recent sessions

- 2026-10-04 — Installed concise repository instructions, corrected the obsolete pending-`v0.1.0` state to published `v0.2.3`, and enabled strict self-checking with read-only permissions. All 30 local tests and both public workflows passed on commit `67378b0`.
