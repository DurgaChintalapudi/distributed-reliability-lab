import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from kafka import KafkaConsumer, TopicPartition
from kafka.errors import KafkaError
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from app.common import BROKER
from app.store import connect, record_event
from app.tracing import configure_tracing

processed = Counter("inventory_events_processed_total", "New inventory events recorded")
duplicates = Counter("inventory_duplicate_events_total", "Replayed events safely skipped")
failures = Counter("inventory_processing_failures_total", "Inventory event processing failures")
processing = Histogram("inventory_processing_seconds", "Inventory processing duration")
lag = Gauge("inventory_consumer_lag_records", "Approximate assigned-partition Kafka consumer lag")
stop_event = threading.Event()


def consume():
    db = connect()
    try:
        while not stop_event.is_set():
            try:
                consumer = KafkaConsumer("orders", bootstrap_servers=BROKER, group_id="inventory-lab", auto_offset_reset="earliest", enable_auto_commit=False, value_deserializer=lambda v: json.loads(v.decode("utf-8")), consumer_timeout_ms=1000)
                try:
                    while not stop_event.is_set():
                        for message in consumer:
                            if stop_event.is_set():
                                break
                            with processing.time():
                                try:
                                    time.sleep(float(os.getenv("INVENTORY_DELAY_SECONDS", "0")))
                                    if record_event(db, message.value):
                                        logging.info("Recorded synthetic inventory event for order %s", message.value["order_id"])
                                        processed.inc()
                                    else:
                                        duplicates.inc()
                                    consumer.commit()
                                except Exception:
                                    failures.inc()
                                    logging.exception("Processing failed; event will be retried")
                                    time.sleep(1)
                        assigned = consumer.assignment()
                        if assigned:
                            ends = consumer.end_offsets(assigned)
                            lag.set(sum(max(0, ends[tp] - consumer.position(tp)) for tp in assigned))
                        else:
                            lag.set(0)
                finally:
                    consumer.close()
            except (KafkaError, OSError):
                logging.exception("Consumer disconnected; retrying")
                stop_event.wait(2)
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event.clear()
    thread = threading.Thread(target=consume, daemon=True)
    thread.start()
    yield
    stop_event.set()
    thread.join(timeout=3)

app = FastAPI(title="Inventory Service", version="0.2.0", lifespan=lifespan)
configure_tracing(app, "inventory-api")
app.mount("/metrics", make_asgi_app())

@app.get("/health")
def health():
    return {"status": "ok", "service": "inventory"}
