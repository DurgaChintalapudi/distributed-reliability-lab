"""Repeatable synthetic inventory backpressure comparison.

Runs only against the local disposable Docker Compose lab.
Requires running stack and Docker CLI. Recreates inventory container and restores
its configured delay in finally. Writes measured JSON and Markdown.
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

ORDER = "http://localhost:8000/orders"
METRICS = "http://localhost:8001/metrics/"
PROCESSED = "inventory_events_processed_total"
LAG = "inventory_consumer_lag_records"


def compose(delay):
    env = dict(os.environ, INVENTORY_DELAY_SECONDS=str(delay))
    subprocess.run(["docker", "compose", "up", "-d", "--no-deps", "--force-recreate", "inventory"], check=True, env=env)


def get_metrics():
    with urllib.request.urlopen(METRICS, timeout=4) as response:
        text = response.read().decode()
    values = {}
    for line in text.splitlines():
        if line and not line.startswith("#"):
            parts = line.split()
            if len(parts) == 2 and parts[0] in (PROCESSED, LAG):
                values[parts[0]] = float(parts[1])
    if PROCESSED not in values or LAG not in values:
        raise RuntimeError("Missing inventory metrics")
    return values


def ready(timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return get_metrics()
        except (OSError, TimeoutError, RuntimeError):
            time.sleep(1)
    raise RuntimeError("Inventory metrics not ready")


def publish():
    payload = json.dumps({"sku": "SYNTH-BACKPRESSURE-" + uuid.uuid4().hex[:8], "quantity": 1}).encode()
    req = urllib.request.Request(ORDER, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    return status, round((time.perf_counter() - started) * 1000, 2)


def run_case(delay, count, iteration):
    compose(delay)
    baseline = ready()
    # Allow consumer group rejoin and startup to stabilize.
    time.sleep(3)
    baseline = get_metrics()
    accepted = 0
    request_latencies = []
    started = time.monotonic()
    for _ in range(count):
        status, latency = publish()
        accepted += status == 202
        request_latencies.append(latency)
    submission_seconds = time.monotonic() - started
    if accepted != count:
        raise AssertionError(f"Accepted only {accepted}/{count} orders")
    deadline = time.monotonic() + max(90, count * max(delay, 0.1) * 5)
    max_lag = 0.0
    processed = 0
    while time.monotonic() < deadline:
        metrics = get_metrics()
        processed = int(metrics[PROCESSED] - baseline[PROCESSED])
        max_lag = max(max_lag, metrics[LAG])
        if processed >= count:
            break
        time.sleep(0.25)
    if processed < count:
        raise AssertionError(f"Only {processed}/{count} events processed before deadline")
    elapsed = time.monotonic() - started
    return {
        "delay_seconds": delay, "iteration": iteration, "orders": count,
        "accepted": accepted, "processed": processed,
        "submission_seconds": round(submission_seconds, 3),
        "end_to_end_drain_seconds": round(elapsed, 3),
        "drain_events_per_second": round(count / elapsed, 3),
        "max_sampled_consumer_lag_records": max_lag,
        "median_publish_latency_ms": round(statistics.median(request_latencies), 2),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--orders", type=int, default=15)
    parser.add_argument("--slow-delay", type=float, default=0.5)
    parser.add_argument("--out", default="artifacts/backpressure")
    args = parser.parse_args()
    if not (1 <= args.repetitions <= 10 and 1 <= args.orders <= 200 and 0.05 <= args.slow_delay <= 5):
        parser.error("repetitions 1..10, orders 1..200, slow-delay 0.05..5")
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    data = []
    try:
        for delay in (0.0, args.slow_delay):
            for i in range(1, args.repetitions + 1):
                result = run_case(delay, args.orders, i)
                print(json.dumps(result), flush=True)
                data.append(result)
    finally:
        # Restore fast consumer even if experiment fails.
        compose(0)
        payload = {"utc": datetime.now(timezone.utc).isoformat(), "configuration": vars(args), "results": data}
        (output / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
        lines = ["# Synthetic consumer backpressure comparison", "", "Results from an actual execution; no estimated values.", "", "| Delay (s) | Rep | Orders | Accepted | Drain (s) | Drain events/s | Max sampled lag | Median publish (ms) |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in data:
            lines.append(f"| {r['delay_seconds']} | {r['iteration']} | {r['orders']} | {r['accepted']} | {r['end_to_end_drain_seconds']} | {r['drain_events_per_second']} | {r['max_sampled_consumer_lag_records']} | {r['median_publish_latency_ms']} |")
        lines.extend(["", "## Interpretation notes", "", "- Drain duration includes sequential order submission, processing and polling, not pure consumer service time.", "- Lag is sampled, approximate and may miss transient peaks.", "- The consumer is recreated between runs, resetting in-process counters; the SQLite event ledger persists.", "- A single Kafka broker and shared CI host introduce noise; do not infer production SLOs.", "- Compare distributions across repetitions, not one run."])
        (output / "report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
