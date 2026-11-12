"""Inject and remove latency on the disposable Toxiproxy HTTP endpoint.

Run after: docker compose --profile experiments up --build -d
Send load to http://localhost:8002/orders to observe the injected latency.
"""
import json
import urllib.request
import urllib.error

API = "http://localhost:8474"
NAME = "order_latency"


def send(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(API + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read().decode()


if __name__ == "__main__":
    try:
        send("DELETE", "/proxies/orders/toxics/" + NAME)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    print(send("POST", "/proxies/orders/toxics", {
        "name": NAME, "type": "latency", "stream": "downstream", "attributes": {"latency": 1500, "jitter": 200}
    }))
    print("Latency active on localhost:8002. Remove with:")
    print("curl -X DELETE http://localhost:8474/proxies/orders/toxics/" + NAME)
