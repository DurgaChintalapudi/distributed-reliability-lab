# Milestone 2: integration validation

## What the CI integration job tests

1. Build the FastAPI service image and start the Compose stack.
2. Wait for both HTTP health endpoints.
3. Submit a unique synthetic order to the Order API and expect HTTP 202.
4. Retrieve the accepted order.
5. Poll the inventory Prometheus counter and verify that it increases after Kafka delivery.

Run locally:

```bash
docker compose up --build -d
python3 scripts/integration_smoke.py
docker compose down
```

The test is **not** a durability, throughput, exactly-once, or high-availability guarantee. It demonstrates basic event delivery through the local single-broker stack.

## Controlled broker outage

Only run on your own disposable lab:

```bash
docker compose up --build -d
python3 scripts/integration_smoke.py
python3 scripts/broker_outage.py
```

The script first checks HTTP 202, stops the local Kafka container, expects HTTP 503 for a new order, restarts Kafka in a `finally` block, and waits for HTTP 202 again. It prints observed request latency and recovery time; **no benchmark values are asserted or preclaimed**.

### What to record

| Field | Meaning |
| --- | --- |
| Environment | OS, Docker and Compose versions, CPU and RAM |
| Baseline | HTTP status and request latency before failure |
| Failure | HTTP status and latency while Kafka is stopped |
| Recovery | Elapsed time from Kafka restart to first HTTP 202 |
| Caveats | Single broker, plaintext transport, ephemeral order state |

## Failure semantics

HTTP 202 indicates Kafka acknowledged an event, not that inventory processing completed. If the producer loses the acknowledgement after a successful broker write, clients may retry and create duplicates. The consumer's in-memory deduplication is **not** durable and does not provide exactly-once semantics.

Next: consumer lag metrics, durable deduplication, fault injection, and repeatable load experiments.
