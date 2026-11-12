# Explicit limitations and safety boundaries

- **Synthetic only:** No customer, payment, or employer data.
- **Local lab only:** One Kafka broker, plaintext transport, no authentication or HA. Bind public-facing endpoints only on trusted machines.
- **Order state is ephemeral:** API state is lost when the order container restarts.
- **Inventory ledger is durable across container restarts:** SQLite database resides in the `inventory-data` Docker volume, but deleting the volume deletes the ledger.
- **No end-to-end exactly-once semantics:** The SQLite transaction and Kafka offset commit are separate. Replays are deduplicated by event ID; stock is not decremented.
- **Consumer lag is approximate:** Scraped per assigned partition after poll loops, not a cluster-wide lag monitor.
- **Tracing scope:** FastAPI HTTP spans and an order-side publish span; Kafka producer-to-consumer context propagation is not yet implemented.
- **Fault injection scope:** Toxiproxy simulates HTTP-facing latency, not broker network partitions.
- **Benchmarks are not measured:** k6 load script and methodology are provided, but results must be collected and published separately.
- **Topic configuration:** Kafka auto-creates topics; no production-grade topic provisioning.
- **Grafana uses a demo password and anonymous local viewing:** Do not expose to the public internet.
