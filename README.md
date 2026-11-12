# Distributed Systems Reliability Lab

**A reproducible, synthetic environment for studying failure propagation, recovery, and architectural tradeoffs in distributed systems.**

> **Status:** Milestone 1 scaffold. The services and Compose configuration are initial implementations, not yet validated end-to-end on a running Docker environment. This repository makes no performance or production-readiness claims.

## Why this exists

Distributed systems fail in ways that are hard to understand from a happy-path microservices demo. This lab makes failure modes observable, repeatable, and measurable. The emphasis is on engineering reasoning: hypotheses, failure injection, recovery criteria, limitations, and architecture decisions.

## Initial architecture

```text
Synthetic HTTP load
        |
        v
FastAPI Order API -- order.created --> Kafka --> Inventory consumer
        |                                       |
        +------------------+--------------------+
                           v
                      Prometheus
```

The order API returns HTTP 202 after Kafka acknowledges an event. The inventory consumer logs a synthetic reservation; there is no real stock or payment processing.

## Run locally

Prerequisites: Docker Engine / Docker Desktop with Compose, Python 3.12+ for local load scripts.

```bash
git clone https://github.com/DurgaChintalapudi/distributed-reliability-lab.git
cd distributed-reliability-lab
docker compose up --build -d
docker compose ps
```

Services:

| Service | Local address |
| --- | --- |
| Order API / OpenAPI docs | http://localhost:8000/docs |
| Inventory health | http://localhost:8001/health |
| Prometheus | http://localhost:9090 |
| Order metrics | http://localhost:8000/metrics/ |
| Inventory metrics | http://localhost:8001/metrics/ |

Create a **synthetic** order:

```bash
curl -i -X POST http://localhost:8000/orders \
  -H 'Content-Type: application/json' \
  -d '{"sku":"DEMO-001","quantity":2}'
```

A successful response contains an `order_id` and `status: accepted`. Inspect inventory container logs to see event consumption:

```bash
docker compose logs -f inventory
```

Run a sequential smoke-load experiment (not a formal benchmark):

```bash
python3 scripts/load.py --count 100
```

Stop everything:

```bash
docker compose down
```

## Experiment 01: broker outage

With the stack running, submit a baseline order, stop Kafka with `docker compose stop kafka`, and submit another order. Record status codes, request latency, and `order_publish_failures_total`. Restart Kafka and measure recovery. See [experiment protocol](docs/experiments.md).

**Important:** A local single-broker failure is intentionally simplified. Do not extrapolate results to a production Kafka cluster.

## Repository map

- `app/order.py` — HTTP order acceptance and publish metrics
- `app/inventory.py` — Kafka consumer and processing metrics
- `app/common.py` — Kafka producer configuration
- `compose.yaml` — local services
- `observability/prometheus.yml` — metrics scraping
- `scripts/load.py` — synthetic sequential request generator
- `tests/` — initial API tests
- `docs/architecture.md` — design and ADRs
- `docs/experiments.md` — reproducible experiment protocols
- `docs/limitations.md` — known limitations and safety boundaries

## Roadmap

- [x] First service implementations and local infrastructure scaffold
- [x] Basic Prometheus instrumentation and API unit tests
- [ ] Verify full Docker Compose startup and Kafka end-to-end flow
- [ ] Add Grafana dashboards, consumer lag metrics and distributed traces
- [ ] Add Toxiproxy fault injection and controlled latency experiments
- [ ] Implement durable idempotency and explicit failure handling
- [ ] Run repeatable load tests and publish evidence-backed results
- [ ] Document resilience patterns and architecture tradeoffs

## Principles

1. **Synthetic data only:** never use employer data, code, diagrams, or confidential operational information.
2. **Measure before claiming:** benchmark numbers must come from documented runs.
3. **Make failure visible:** describe the failure, its propagation, and recovery.
4. **Be explicit about limitations:** this lab is a teaching and research environment, not production infrastructure.

MIT licensed. Contributions and constructive technical review are welcome.
