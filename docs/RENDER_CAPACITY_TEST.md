# Independent-workflow capacity test — 2026-11-06

The user proposed splitting the movie across several workflows to target a five-hour completion time.

## Existing production split

Run [42202373037](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42202373037) already has 100 independently encoded clips of 12 native frames, with up to 20 simultaneous render jobs. Assembly stream-copies these clips into the 1,200-frame movie without another lossy encode.

## Experiment

A separate, tiny workflow was pushed on the same session branch, without the production workflow's concurrency group and without rendering any duplicate frames. Capacity-test run [42257825181](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42257825181) remained queued throughout the approximately four-minute observation window while 20 production render jobs were active. The diagnostic was then cancelled; the production render was not cancelled or restarted.

This test did not obtain additional immediate worker capacity. Separate workflows do not create independent account concurrency allowances. The precise account plan/limit was not retrieved: the billing endpoint was inaccessible to this integration. The observation is consistent with a shared 20-job hosted-runner capacity limit, rather than proving the account's configured quota from billing data.

## Measured timing

At the check, 23 clips had succeeded, 20 were rendering and 57 were queued; the full-resolution hero still had also succeeded. Completed clips averaged 3.86 hours each, with a 2.62–5.08-hour range.

Using that mean, 100 clips / 20 workers * 3.86 hours is about 19.3 hours of total wall time under steady utilization. A five-hour total would need roughly 78 comparable simultaneous workers, plus scheduling/assembly allowance. These are projections: later frame costs may differ and running jobs have already made partial progress.

No production quality, resolution, frame rate, sampling settings or completed clips were changed by this experiment. No additional paid compute was provisioned.
