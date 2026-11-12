"""End-to-end smoke test for the local Docker Compose lab.

Requires: docker compose up --build -d
Uses only synthetic data. No external Python dependencies.
"""
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

ORDER_URL = "http://localhost:8000"
INVENTORY_URL = "http://localhost:8001"
TIMEOUT_SECONDS = 120


def request(url, payload=None, timeout=12):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def await_health(url, label):
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            status, _ = request(url, timeout=3)
            if status == 200:
                print(f"READY {label}", flush=True)
                return
        except (OSError, TimeoutError):
            pass
        time.sleep(2)
    raise AssertionError(f"{label} not healthy within {TIMEOUT_SECONDS}s")


def metric_value(text, name):
    # The inventory counter is unlabeled; exact sample name avoids matching HELP/TYPE.
    for line in text.splitlines():
        if line.startswith(name + " "):
            return float(line.split()[-1])
    return 0.0


def main():
    await_health(ORDER_URL + "/health", "orders")
    await_health(INVENTORY_URL + "/health", "inventory")
    status, body = request(INVENTORY_URL + "/metrics/")
    assert status == 200, f"inventory metrics HTTP {status}"
    baseline = metric_value(body, "inventory_events_processed_total")

    sku = "SYNTH-" + uuid.uuid4().hex[:10]
    status, body = request(ORDER_URL + "/orders", {"sku": sku, "quantity": 2}, timeout=30)
    assert status == 202, f"order publish expected 202, got {status}: {body}"
    order = json.loads(body)
    assert order["status"] == "accepted" and order["order_id"]
    print("PASS order accepted with Kafka acknowledgement", flush=True)

    status, body = request(ORDER_URL + "/orders/" + order["order_id"])
    assert status == 200 and json.loads(body)["sku"] == sku
    print("PASS order retrievable from API", flush=True)

    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        status, body = request(INVENTORY_URL + "/metrics/")
        if status == 200 and metric_value(body, "inventory_events_processed_total") > baseline:
            print("PASS inventory consumer processed Kafka event", flush=True)
            return
        time.sleep(2)
    raise AssertionError("inventory did not process event before timeout")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL integration smoke: {exc}", file=sys.stderr)
        sys.exit(1)
