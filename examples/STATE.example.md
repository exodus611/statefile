# State

## Now — what runs
- the nightly job writes results to `data/latest.json`
- the dashboard reads that file; nothing else is wired up yet

## In flight
- moving the price source from vendor A to B — blocked: B has no intraday endpoint
- half-finished auth rewrite on branch `auth-v2`; the old path still serves traffic

## Decisions
- single state file, not a folder — because the assistant has to find it in one guess
- keep failed experiments forever — the list has already stopped two rebuilds

## Dead ends — do not repeat
- cron inside the web app: the process restarts every deploy, so jobs died silently
- scraping the vendor page: broke twice in a week, no warning either time

## Next three tasks
1. finish the auth rewrite behind a flag
2. pick the price vendor and write down why
3. add the stale-data warning to the dashboard
