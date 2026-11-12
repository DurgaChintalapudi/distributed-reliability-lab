"""Reproducible synthetic reliability experiment suite.

Run only against your disposable local Docker Compose lab.
Writes JSON and Markdown artifacts. Never invents measurements.
"""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

API = os.getenv("ORDER_API", "http://localhost:8000")
METRICS = os.getenv("INVENTORY_METRICS", "http://localhost:8001/metrics/")
TOXI = "http://localhost:8474"
results = []


def fetch(url, payload=None, timeout=35, method=None):
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=body, method=method or ("POST" if body else "GET"), headers={"Content-Type": "application/json"} if body else {})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            content = response.read().decode()
    except urllib.error.HTTPError as exc:
        status = exc.code
        content = exc.read().decode()
    except (OSError, TimeoutError) as exc:
        status = 0
        content = str(exc)
    return {"status": status, "latency_ms": round((time.perf_counter() - start) * 1000, 2), "body": content}


def order(base=API):
    return fetch(base + "/orders", {"sku": "SYNTH-" + uuid.uuid4().hex[:8], "quantity": 1})


def sample(label, count, base=API):
    data = [order(base) for _ in range(count)]
    times = sorted(x["latency_ms"] for x in data)
    return {
        "scenario": label, "requests": count,
        "success": sum(x["status"] == 202 for x in data),
        "statuses": {str(code): sum(x["status"] == code for x in data) for code in sorted({x["status"] for x in data})},
        "latency_ms": {"min": min(times), "median": statistics.median(times), "p95_nearest_rank": times[max(0, (95 * len(times) + 99) // 100 - 1)], "max": max(times)},
    }


def compose(*args):
    subprocess.run(["docker", "compose", *args], check=True)


def metric(name):
    response = fetch(METRICS, timeout=5)
    if response["status"] != 200:
        raise RuntimeError("Inventory metrics unavailable")
    for line in response["body"].splitlines():
        if line.startswith(name + " "):
            return float(line.split()[-1])
    raise RuntimeError("Missing metric " + name)


def wait_ready(timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if fetch(API + "/health", timeout=3)["status"] == 200 and fetch(METRICS, timeout=3)["status"] == 200:
            return
        time.sleep(2)
    raise RuntimeError("Lab not ready")


def broker_outage():
    before = order()
    if before["status"] != 202:
        raise RuntimeError("Baseline order not accepted; refusing to disrupt broker")
    stopped = False
    try:
        compose("stop", "kafka")
        stopped = True
        during = order()
    finally:
        if stopped:
            compose("start", "kafka")
    start = time.perf_counter()
    recovered = False
    for _ in range(24):
        response = order()
        if response["status"] == 202:
            recovered = True
            break
        time.sleep(3)
    return {"scenario": "broker_outage", "baseline_status": before["status"], "outage_status": during["status"], "outage_latency_ms": during["latency_ms"], "recovered": recovered, "recovery_seconds": round(time.perf_counter() - start, 2) if recovered else None}


def latency_fault(count):
    # The optional experiments profile must already be running.
    proxy = TOXI + "/proxies/orders/toxics"
    payload = {"name": "suite_latency", "type": "latency", "stream": "downstream", "attributes": {"latency": 800, "jitter": 0}}
    baseline = sample("proxy_baseline", count, "http://localhost:8002")
    created = fetch(proxy, payload)
    if created["status"] not in (200, 201):
        raise RuntimeError("Could not create latency toxic: " + created["body"])
    try:
        degraded = sample("proxy_latency_800ms", count, "http://localhost:8002")
    finally:
        fetch(proxy + "/suite_latency", method="DELETE")
    return [baseline, degraded]


def write_report(out, metadata):
    out.mkdir(parents=True, exist_ok=True)
    payload = {"metadata": metadata, "results": results}
    (out / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    lines = ["# Reliability experiment report", "", f"UTC: {metadata['timestamp_utc']}", "", "All results below are measurements from this execution, not estimates.", "", "## Scenarios", ""]
    for result in results:
        lines.extend(["### " + result["scenario"], "", "```json", json.dumps(result, indent=2), "```", ""])
    lines.extend(["## Interpretation", "", "Interpret only after comparing the measurements to baseline and inspecting logs, resource limits and environment.", "", "## Limitations", "", "- Single Kafka broker and synthetic traffic; not production representative.", "- Sequential requests; no concurrency or throughput saturation analysis.", "- HTTP latency injection is client-facing, not a Kafka network partition.", "- Recovery time includes polling interval and request duration.", ""])
    (out / "report.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="artifacts/reliability")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--broker-outage", action="store_true", help="Disrupt local Kafka container")
    parser.add_argument("--latency", action="store_true", help="Requires --profile experiments stack")
    args = parser.parse_args()
    if not 1 <= args.count <= 1000:
        parser.error("--count must be 1..1000")
    metadata = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "count": args.count, "broker_outage": args.broker_outage, "latency": args.latency}
    try:
        wait_ready()
        results.append(sample("baseline", args.count))
        if args.latency:
            results.extend(latency_fault(args.count))
        if args.broker_outage:
            results.append(broker_outage())
    finally:
        write_report(Path(args.out), metadata)
        print("Report:", Path(args.out) / "report.md")
    if any(x.get("scenario") == "broker_outage" and (x["outage_status"] != 503 or not x["recovered"]) for x in results):
        raise SystemExit("Broker outage expectation failed")
    if any("success" in x and x["success"] != x["requests"] for x in results if x["scenario"] in ("baseline", "proxy_baseline", "proxy_latency_800ms")):
        raise SystemExit("Some synthetic orders were not accepted")


if __name__ == "__main__":
    main()
