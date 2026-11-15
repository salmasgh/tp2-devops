"""Unit & integration tests for the Payment API (nominal cases + edge cases)."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from app import main
from app.telemetry import JsonFormatter, configure_otel


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("CHECKOUT_MIN_DELAY", "0")
    monkeypatch.setenv("CHECKOUT_MAX_DELAY", "0.001")
    return TestClient(main.app)


# --- health & metrics ---------------------------------------------------------------
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_metrics_exposes_prometheus_format(client):
    client.get("/products")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    body = r.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds_bucket" in body
    assert 'route="/products"' in body


# --- catalogue ----------------------------------------------------------------------
def test_list_products(client):
    r = client.get("/products")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_get_product_ok(client):
    assert client.get("/products/2").json()["name"] == "Souris sans fil"


@pytest.mark.parametrize("pid,code", [(999, 404), (0, 404), (-1, 404)])
def test_get_product_not_found(client, pid, code):
    assert client.get(f"/products/{pid}").status_code == code


def test_get_product_invalid_id(client):
    assert client.get("/products/abc").status_code == 422


# --- payments -----------------------------------------------------------------------
def test_create_and_get_payment(client):
    r = client.post("/payments", json={"amount": 42.456, "currency": "TND", "customer_id": "c-1"})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "AUTHORIZED"
    assert body["amount"] == 42.46
    again = client.get(f"/payments/{body['id']}")
    assert again.status_code == 200
    assert again.json() == body


def test_payment_default_currency(client):
    r = client.post("/payments", json={"amount": 1, "customer_id": "c-2"})
    assert r.json()["currency"] == "EUR"


@pytest.mark.parametrize(
    "payload",
    [
        {"amount": 0, "customer_id": "c"},  # zero amount
        {"amount": -5, "customer_id": "c"},  # negative
        {"amount": 10_000.01, "customer_id": "c"},  # above max
        {"amount": 10, "currency": "BTC", "customer_id": "c"},  # unknown currency
        {"amount": 10, "customer_id": ""},  # empty customer
        {"amount": 10},  # missing customer
    ],
)
def test_payment_validation_edge_cases(client, payload):
    assert client.post("/payments", json=payload).status_code == 422


def test_payment_upper_bound_accepted(client):
    assert client.post("/payments", json={"amount": 10_000, "customer_id": "c"}).status_code == 201


def test_get_unknown_payment(client):
    assert client.get("/payments/does-not-exist").status_code == 404


# --- slow & flaky endpoints ---------------------------------------------------------
def test_checkout(client):
    r = client.get("/checkout")
    assert r.status_code == 200
    assert r.json()["status"] == "processed"
    assert r.json()["delay_ms"] <= 1.0


def test_checkout_inverted_bounds(client, monkeypatch):
    monkeypatch.setenv("CHECKOUT_MIN_DELAY", "0.002")
    monkeypatch.setenv("CHECKOUT_MAX_DELAY", "0")
    assert client.get("/checkout").json()["delay_ms"] == 2.0


def test_flaky_always_fails(client, monkeypatch):
    monkeypatch.setenv("FLAKY_ERROR_RATE", "1")
    r = client.get("/flaky")
    assert r.status_code == 500
    assert "upstream" in r.json()["detail"]


def test_flaky_never_fails(client, monkeypatch):
    monkeypatch.setenv("FLAKY_ERROR_RATE", "0")
    assert all(client.get("/flaky").status_code == 200 for _ in range(20))


def test_flaky_invalid_rate_falls_back_to_default(client, monkeypatch):
    monkeypatch.setenv("FLAKY_ERROR_RATE", "not-a-number")
    assert main._float_env("FLAKY_ERROR_RATE", 0.1) == 0.1
    assert client.get("/flaky").status_code in (200, 500)


def test_flaky_rate_is_clamped(client, monkeypatch):
    monkeypatch.setenv("FLAKY_ERROR_RATE", "5")
    assert client.get("/flaky").status_code == 500


def test_unknown_route_counted_as_unmatched(client):
    assert client.get("/nope").status_code == 404
    assert 'route="unmatched"' in client.get("/metrics").text


# --- telemetry ----------------------------------------------------------------------
def test_json_formatter_includes_trace_context():
    tracer = main.tracer
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    record.extra_fields = {"route": "/x"}
    with tracer.start_as_current_span("test-span"):
        line = json.loads(JsonFormatter().format(record))
    assert line["message"] == "hello world"
    assert line["route"] == "/x"
    assert len(line["trace_id"]) == 32
    assert len(line["span_id"]) == 16


def test_json_formatter_without_span_and_with_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord("t", logging.ERROR, __file__, 1, "err", (), sys.exc_info())
    line = json.loads(JsonFormatter().format(record))
    assert line["trace_id"] is None
    assert "ValueError" in line["exception"]


def test_configure_otel_is_idempotent():
    configure_otel()
    configure_otel()
