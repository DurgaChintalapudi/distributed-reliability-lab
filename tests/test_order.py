from fastapi.testclient import TestClient
from app.order import app

client = TestClient(app)

def test_health():
    assert client.get("/health").json()["status"] == "ok"

def test_invalid_order_rejected():
    assert client.post("/orders", json={"sku": "TEST", "quantity": 0}).status_code == 422

def test_missing_order():
    assert client.get("/orders/does-not-exist").status_code == 404
