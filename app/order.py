import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app
from app.common import producer_with_retry
from app.tracing import configure_tracing

app = FastAPI(title="Order Service", version="0.2.0")
tracer = configure_tracing(app, "order-api")
app.mount("/metrics", make_asgi_app())
orders = {}
created = Counter("orders_created_total", "Orders accepted")
publish_failures = Counter("order_publish_failures_total", "Kafka publish failures")
publish_duration = Histogram("order_publish_seconds", "Kafka publish acknowledgement time")

class OrderRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=100)

@app.get("/health")
def health():
    return {"status": "ok", "service": "orders"}

@app.post("/orders", status_code=202)
def create_order(request: OrderRequest):
    order_id = str(uuid.uuid4())
    event = {"event_id": str(uuid.uuid4()), "event_type": "order.created", "order_id": order_id, "sku": request.sku, "quantity": request.quantity}
    try:
        with tracer.start_as_current_span("kafka.publish.order_created") as span:
            span.set_attribute("messaging.destination.name", "orders")
            with publish_duration.time():
                producer = producer_with_retry(attempts=3, delay=1)
                try:
                    producer.send("orders", event).get(timeout=10)
                finally:
                    producer.close(timeout=5)
    except Exception as exc:
        publish_failures.inc()
        raise HTTPException(status_code=503, detail="Event broker unavailable") from exc
    orders[order_id] = {"order_id": order_id, "status": "accepted", "sku": request.sku, "quantity": request.quantity}
    created.inc()
    return orders[order_id]

@app.get("/orders/{order_id}")
def get_order(order_id: str):
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found")
    return orders[order_id]
