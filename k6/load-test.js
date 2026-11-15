// k6 - test de charge payment-api : ramp-up 100 VU -> stress 500 VU -> spike 1500 VU (30 s)
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE = __ENV.BASE_URL || 'http://payment-api.tp2.svc';
const serverErrors = new Rate('server_errors');      // SLI disponibilite (status >= 500)
const checkoutLatency = new Trend('checkout_latency', true);

export const options = {
  discardResponseBodies: true,
  scenarios: {
    ramp_up: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 100 },
        { duration: '1m', target: 100 },
        { duration: '20s', target: 0 },
      ],
      gracefulRampDown: '10s',
      tags: { scenario: 'ramp_up' },
    },
    stress: {
      executor: 'ramping-vus',
      startTime: '2m30s',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 500 },
        { duration: '4m', target: 500 },   // stress prolonge
        { duration: '30s', target: 0 },
      ],
      gracefulRampDown: '10s',
      tags: { scenario: 'stress' },
    },
    spike: {
      executor: 'ramping-vus',
      startTime: '8m30s',
      startVUs: 0,
      stages: [
        { duration: '5s', target: 1500 },  // pic soudain
        { duration: '30s', target: 1500 }, // maintenu 30 s
        { duration: '10s', target: 0 },
      ],
      gracefulRampDown: '5s',
      tags: { scenario: 'spike' },
    },
  },
  thresholds: {
    // Contrat de service (SLO) evalue cote client
    server_errors: ['rate<0.005'],                 // 99.5 % de succes
    'http_req_duration{expected_response:true}': ['p(95)<200'],
    checkout_latency: ['p(95)<300'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

function record(res, name) {
  serverErrors.add(res.status >= 500 || res.status === 0);
  check(res, { [`${name} status < 500`]: (r) => r.status > 0 && r.status < 500 });
}

export default function () {
  const p = Math.random();
  if (p < 0.30) {
    record(http.get(`${BASE}/products`, { tags: { name: 'GET /products' } }), 'products');
  } else if (p < 0.50) {
    const body = JSON.stringify({ amount: Math.round(Math.random() * 500 + 1), currency: 'TND', customer_id: `vu-${__VU}` });
    record(http.post(`${BASE}/payments`, body, { headers: { 'Content-Type': 'application/json' }, tags: { name: 'POST /payments' } }), 'payments');
  } else if (p < 0.75) {
    const res = http.get(`${BASE}/checkout`, { tags: { name: 'GET /checkout' } });
    checkoutLatency.add(res.timings.duration);
    record(res, 'checkout');
  } else {
    record(http.get(`${BASE}/flaky`, { tags: { name: 'GET /flaky' } }), 'flaky');
  }
  sleep(Math.random() * 0.5 + 0.5);
}
