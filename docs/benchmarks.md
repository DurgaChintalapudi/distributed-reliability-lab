# Benchmark methodology and reporting template

No benchmark measurements are included until the experiments have actually been executed.

## Setup

Start the lab: `docker compose --profile load up --build -d`.

Run: `docker compose --profile load run --rm -e VUS=5 -e DURATION=30s k6 run /scripts/k6-orders.js`.

Repeat at 5, 10, and 20 virtual users. Record host hardware, Docker limits, image versions, UTC timestamps, total requests, success rate, p50/p95/p99 latency, Kafka publish failures, inventory throughput, and consumer lag. Allow warm-up and repeat each scenario at least three times.

**Do not compare runs across differing machines or resource limits as if equivalent.** The simple per-request Kafka producer is a known bottleneck and is an explicit candidate for optimization.

## Results template

| Run | VUs | Duration | Accepted | Error % | p95 (ms) | Inventory lag max | Notes |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| Not yet measured | — | — | — | — | — | — | Execute locally or in CI first |

## Resilience comparisons

- Baseline versus 1.5-second HTTP latency injected through Toxiproxy.
- Baseline versus inventory consumer delay of 2 seconds.
- Baseline versus Kafka broker stopped (manual experiment).

Evaluate throughput, queue buildup, recovery, and client-visible error rates. Separate observations from causal hypotheses.
