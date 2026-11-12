# ADR-004: Durable event deduplication

**Status:** Implemented for the synthetic inventory ledger; production considerations remain.

## Context

Kafka consumers may receive an event more than once due to retries, crashes, or offset replays. An in-memory set cannot survive a restart.

## Decision

Use a SQLite database on a Docker named volume with `event_id` as a primary key. The synthetic inventory effect is the insertion of the event ledger row. SQLite's transaction ensures duplicate insert attempts do not create additional ledger rows. Commit the Kafka offset only after database success.

## Consequences

- Durable across inventory container restarts if the named volume is retained.
- A crash after database commit but before Kafka offset commit replays the event, which is safely ignored.
- This **does not** provide end-to-end exactly-once semantics; Kafka offsets and SQLite transactions are not atomically committed together.
- SQLite is appropriate for a single-consumer local lab, not a multi-replica inventory service.
- No stock reservation, cross-service transaction, or transactional outbox is implemented.
