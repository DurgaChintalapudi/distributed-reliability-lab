import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from prometheus_client import Counter, Histogram, make_asgi_app
from app.common import BROKER

processed = Counter("inventory_events_processed_total", "Inventory events processed")
failures = Counter("inventory_processing_failures_total", "Inventory event processing failures")
processing = Histogram("inventory_processing_seconds", "Inventory processing duration")
seen_ids = set()  # Demo only: lost on restart. See docs/limitations.md.
stop_event = threading.Event()

def consume():
    while not stop_event.is_set():
        try:
            consumer = KafkaConsumer("orders", bootstrap_servers=BROKER, group_id="inventory-lab", auto_offset_reset="earliest", enable_auto_commit=False, value_deserializer=lambda v: json.loads(v.decode("utf-8")), consumer_timeout_ms=1000)
            try:
                while not stop_event.is_set():
                    for message in consumer:
                        if stop_event.is_set():
                            break
                        event = message.value
                        with processing.time():
                            try:
                                if event["event_id"] not in seen_ids:
                                    time.sleep(float(os.getenv("INVENTORY_DELAY_SECONDS", "0")))
                                    logging.info("Reserved synthetic inventory for order %s", event["order_id"])
                                    seen_ids.add(event["event_id"])
                                    processed.inc()
                                consumer.commit()
                            except Exception:
                                failures.inc()
                                logging.exception("Inventory processing failed; event will be retried")
                                time.sleep(1)
            finally:
                consumer.close()
        except (KafkaError, OSError):
            logging.exception("Consumer disconnected; retrying")
            stop_event.wait(2)

@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event.clear()
    thread = threading.Thread(target=consume, daemon=True)
    thread.start()
    yield
    stop_event.set()
    thread.join(timeout=3)

app = FastAPI(title="Inventory Service", version="0.1.0", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())

@app.get("/health")
def health():
    return {"status": "ok", "service": "inventory"}
