"""Controlled Kafka outage experiment (local development only).

Usage:
  docker compose up --build -d
  python3 scripts/integration_smoke.py
  python3 scripts/broker_outage.py

WARNING: This script intentionally stops and restarts the local Kafka container.
Never run against production or a shared environment.
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

URL = "http://localhost:8000/orders"


def submit():
    payload = json.dumps({"sku": "SYNTH-OUTAGE", "quantity": 1}).encode()
    request = urllib.request.Request(URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    return status, round(time.perf_counter() - started, 3)


def compose(*args):
    subprocess.run(["docker", "compose", *args], check=True)


def main():
    baseline_status, baseline_s = submit()
    if baseline_status != 202:
        raise RuntimeError(f"Baseline request returned {baseline_status}, expected 202. Start and validate the stack first.")
    print(f"Baseline: HTTP {baseline_status}, {baseline_s}s", flush=True)

    try:
        compose("stop", "kafka")
        outage_status, outage_s = submit()
        print(f"Broker stopped: HTTP {outage_status}, {outage_s}s", flush=True)
        if outage_status != 503:
            raise AssertionError(f"Expected HTTP 503 with broker stopped; got {outage_status}")
    finally:
        compose("start", "kafka")

    recovered = False
    recovery_started = time.perf_counter()
    for _ in range(24):
        try:
            status, latency = submit()
            if status == 202:
                recovered = True
                print(f"Recovery: HTTP 202 after {time.perf_counter()-recovery_started:.1f}s; request latency {latency}s")
                break
        except (OSError, TimeoutError):
            pass
        time.sleep(3)
    if not recovered:
        raise AssertionError("Kafka did not recover within the experiment window")
    print("PASS local broker outage and recovery experiment")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL outage experiment: {exc}", file=sys.stderr)
        sys.exit(1)
