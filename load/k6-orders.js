import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    steady: { executor: 'constant-vus', vus: Number(__ENV.VUS || 5), duration: __ENV.DURATION || '30s' },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<2000'],
  },
};

const endpoint = __ENV.ORDER_URL || 'http://orders:8000/orders';
export default function () {
  const body = JSON.stringify({ sku: 'SYNTH-' + (__VU % 20), quantity: 1 });
  const res = http.post(endpoint, body, { headers: { 'Content-Type': 'application/json' } });
  check(res, { 'order accepted': (r) => r.status === 202 });
  sleep(0.2);
}
