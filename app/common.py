import json
import logging
import os
import time
from kafka import KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO)
BROKER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

def producer_with_retry(attempts=30, delay=2):
    for attempt in range(attempts):
        try:
            return KafkaProducer(bootstrap_servers=BROKER, value_serializer=lambda v: json.dumps(v).encode("utf-8"), acks="all", retries=3)
        except KafkaError as exc:
            logging.warning("Kafka unavailable (%s/%s): %s", attempt + 1, attempts, exc)
            time.sleep(delay)
    raise RuntimeError("Kafka connection failed after retries")
