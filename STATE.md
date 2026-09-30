# State

> This repository uses its own tool on itself. If this file goes stale, the
> badge goes red — which is the most honest demo a tool like this can have.

## Now — what runs

- `statefile.py check` and `statefile.py init`; 23 unit tests, all passing
- CI: the check runs on every push, and the test suite runs on Python 3.9, 3.12 and 3.13
- GitHub Action `action.yml`, composite, no dependencies
- CI: `.github/workflows/statefile.yml` runs the check on every push

## In flight

- `v0.1.0` release tag — waiting on the repository owner
- whether the tool should also ship as a pre-commit hook

## Decisions

- stdlib only, single file — because the audience runs this on machines where installing things is the friction
- freshness measured from git history first, file mtime second — because CI checkouts do not preserve mtimes
- rule patterns are warnings, never failures — they are heuristics about style, not correctness

## Dead ends — do not repeat

- parsing STATE.md sections with a fixed heading list — broke on every variant people actually write; keyword matching works
- skipping only lines that start with ``` — misses the rest of the fenced block; need to track fence state

## Next three tasks

1. tag `v0.1.0` so other projects can pin a version instead of `main`
2. add a `--fix` mode that appends the missing section headings
3. write the pre-commit hook docs, or drop the idea
