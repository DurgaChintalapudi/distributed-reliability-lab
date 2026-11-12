# Explicit limitations and safety boundaries

- **Synthetic only.** No real customer, payment, or employer data.
- **No production guarantees.** Single broker, plaintext Kafka, no authentication, no persistence for the order API.
- **Idempotency is illustrative only.** The inventory consumer uses an in-memory set, which resets on restart; commit and side effects are not atomic. It does not guarantee exactly-once processing.
- **No business inventory state.** A processed event is logged; stock is not decremented.
- **No distributed tracing or Grafana yet.** Prometheus is the initial observability layer.
- **No formal load testing yet.** The included script sends sequential requests and is intended as a basic smoke-load baseline, not a throughput benchmark.
- **No automatic topic provisioning.** Kafka auto-creates the topic in this local lab; production designs should define topic configurations explicitly.
- **No performance claims.** Publish only measurements collected from reproducible runs.
