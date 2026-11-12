# Case study: Does slow downstream processing slow API acceptance?

**Experiment date:** 2026-11-12 UTC  
**Evidence:** [Successful GitHub Actions run](https://github.com/DurgaChintalapudi/distributed-reliability-lab/actions/runs/43194266487), artifact `backpressure-comparison-results`  
**Environment:** GitHub-hosted Ubuntu runner, disposable Docker Compose lab, single Kafka broker, synthetic orders only.

## Engineering question

In an asynchronous order-to-inventory pipeline, what happens to order acknowledgement latency and total event drain time when inventory processing becomes slower?

**Hypothesis:** A slower inventory consumer increases completion time while order acknowledgement remains relatively insensitive because the API acknowledges broker acceptance, not downstream completion.

## Method

The workflow ran three repetitions of each condition, submitting 15 unique synthetic orders sequentially per repetition. The inventory consumer was recreated for each run, with `INVENTORY_DELAY_SECONDS` set to either 0 or 0.5. The runner measured HTTP acceptance, time from first submission to observing all 15 processed events, approximate sampled consumer lag, and median HTTP publish latency. The SQLite idempotency ledger persisted between repetitions.

The raw JSON and Markdown measurements are downloadable from the linked Actions run.

## Observations

| Delay | Rep | Accepted | Drain time (s) | Effective drain rate (events/s) | Median HTTP publish latency (ms) | Max sampled lag |
|---|---:|---:|---:|---:|---:|---:|
| 0 s | 1 | 15/15 | 2.026 | 7.404 | 116.42 | 0 |
| 0 s | 2 | 15/15 | 1.749 | 8.575 | 114.40 | 0 |
| 0 s | 3 | 15/15 | 1.957 | 7.664 | 112.97 | 0 |
| 0.5 s | 1 | 15/15 | 7.779 | 1.928 | 111.82 | 0 |
| 0.5 s | 2 | 15/15 | 7.743 | 1.937 | 111.45 | 0 |
| 0.5 s | 3 | 15/15 | 7.750 | 1.935 | 111.53 | 0 |

Median drain time increased from **1.957 s** to **7.750 s**, a **3.96×** increase. Median effective drain rate fell from **7.664** to **1.935 events/s** (about **74.8% lower**). Across all six repetitions, **90/90 orders were accepted and observed as processed**. Median publish latency was **114.40 ms** for baseline and **111.53 ms** with delay; these tiny differences are not evidence of a performance improvement.

## Architectural interpretation

The data are consistent with an asynchronous boundary: accepting an event into Kafka does not require the inventory consumer to complete processing first. This lets the API continue accepting events while downstream completion slows. It does **not** prove that the system can sustain arbitrary load, meet a production SLO, or avoid backlog growth.

**Instrumentation gap:** The approximate consumer lag gauge returned zero in all repetitions, even when drain time increased. Its sampling frequency or implementation may miss transient backlog. Therefore this experiment **does not demonstrate measured lag growth**. A future experiment should use broker end offsets minus committed consumer offsets, record a time series throughout the run, and validate with sustained concurrent load.

## Limitations and next decisions

- Only three repetitions per condition, sequential order submissions, a small fixed batch, and one shared CI runner. No confidence interval or statistical significance claim.
- Drain duration includes order submission and polling overhead, so effective drain rate is not isolated consumer throughput.
- This test does not measure end-user order completion latency, saturation behavior, partitions, broker redundancy, or production-grade durability.
- Repeat at increasing offered load, collect consumer lag at subsecond intervals, report per-run distributions, and establish an explicit SLO/error-budget policy before evaluating mitigation strategies.

## Reproduce

```bash
docker compose up --build -d
python3 scripts/compare_backpressure.py --repetitions 3 --orders 15 --slow-delay 0.5
```

Run only in the disposable local lab. See [experiment methodology](backpressure-comparison.md).
