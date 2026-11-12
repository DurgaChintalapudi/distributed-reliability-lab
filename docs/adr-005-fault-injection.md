# ADR-005: Fault injection through an HTTP proxy

**Decision:** Route optional synthetic client traffic through Toxiproxy, without modifying Kafka broker advertisement or production endpoints.

**Why:** Repeatable client-facing latency experiments are simpler and safer than reconfiguring Kafka listeners. Toxiproxy runs under the optional `experiments` Compose profile.

**Limitations:** Injected HTTP latency measures client experience, not Kafka broker partitions or network jitter inside the event bus. Kafka outages remain a separate manual experiment. Always remove toxics after a run.
