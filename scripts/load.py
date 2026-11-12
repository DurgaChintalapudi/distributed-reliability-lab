"""Synthetic HTTP load generator. Usage: python scripts/load.py --count 100"""
import argparse
import json
import time
import urllib.request
import urllib.error

parser = argparse.ArgumentParser()
parser.add_argument("--count", type=int, default=100)
parser.add_argument("--url", default="http://localhost:8000/orders")
args = parser.parse_args()
results = {}
start = time.perf_counter()
for i in range(args.count):
    body = json.dumps({"sku": f"DEMO-{i % 5}", "quantity": 1 + i % 3}).encode()
    request = urllib.request.Request(args.url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except Exception:
        status = "connection-error"
    results[str(status)] = results.get(str(status), 0) + 1
elapsed = time.perf_counter() - start
print(json.dumps({"requests": args.count, "seconds": round(elapsed, 2), "requests_per_second": round(args.count / elapsed, 2) if elapsed else None, "responses": results}, indent=2))
