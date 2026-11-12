# Repeated consumer backpressure comparison

**Hypothesis:** Delaying each synthetic inventory event increases time to drain a fixed set of accepted orders, while the HTTP Order API can continue acknowledging events through Kafka.

## Independent variable

`INVENTORY_DELAY_SECONDS`: 0 seconds versus 0.5 seconds.

## Controls

Same synthetic order count, same Compose configuration, one broker, one inventory consumer, one host per workflow run. Three sequential repetitions per condition, with inventory recreated before each repetition and 3 seconds to settle. Unique synthetic order IDs are used; SQLite deduplication persists between runs.

## Automated execution

GitHub Actions workflow: **Backpressure comparison**. Download `backpressure-comparison-results` after it finishes.

Local execution:

```bash
docker compose up --build -d
python3 scripts/compare_backpressure.py --repetitions 3 --orders 15 --slow-delay 0.5
```

The script restores `INVENTORY_DELAY_SECONDS=0` in a `finally` block. It requires the disposable lab only.

## Measures

- Accepted synthetic orders, number of ledger events processed
- Total time from first order submission until all events processed
- Drain events per second, **including** order submission time
- Approximate maximum sampled Kafka consumer lag
- Median HTTP order publish latency

## Threats to validity

- No production network or cluster, single Kafka broker.
- Sequential order submission and polling add time; drain throughput is not isolated consumer throughput.
- The lag gauge is approximate and may miss transient peaks.
- CI hardware and scheduling are not fixed; comparisons are within a workflow run.
- No confidence interval or significance claim from three repetitions.

## Follow-up analysis

Compare medians and spread across conditions, examine lag time series and logs, and explain whether buffering decouples acceptance from slow processing. Report measured values only after successful execution.
