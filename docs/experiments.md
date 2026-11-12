# Reliability experiments

Record machine specifications, image versions, load profile, timestamps, baseline metrics and recovery criteria for every run. Never present sample expectations as measured results.

## Experiment 01 — Broker unavailable
1. Start the stack with `docker compose up --build -d`.
2. Confirm an order returns HTTP 202.
3. Run `docker compose stop kafka`.
4. Submit an order; expect HTTP 503 after connection retries/timeouts (exact latency is environment dependent).
5. Restart Kafka with `docker compose start kafka` and repeat.

**Measure:** HTTP 202/503 ratio, request latency, publish failure counter, time until successful acceptance after restart. **Caveat:** the single broker and local environment are not a production failure model.

## Experiment 02 — Slow inventory processing
Set `INVENTORY_DELAY_SECONDS: "2"` in Compose, restart inventory, generate 100 orders, and inspect inventory throughput. Kafka consumer lag instrumentation is a future milestone.

## Experiment template
Hypothesis | independent variable | load profile | metrics | baseline | failure outcome | recovery time | limitations | decision.
