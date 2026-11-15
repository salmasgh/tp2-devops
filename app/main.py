"""Payment API - FastAPI microservice instrumented for SRE (RED metrics, traces, JSON logs)."""

from __future__ import annotations

import asyncio
import os
import secrets
import time
import uuid
from enum import StrEnum

from fastapi import FastAPI, HTTPException, Request, Response
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

from app.telemetry import VERSION, configure_logging, configure_otel

configure_otel()
logger = configure_logging()
tracer = trace.get_tracer(__name__)
_rng = secrets.SystemRandom()

# --- RED metrics (Rate / Errors / Duration) -----------------------------------------
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.5, 0.75, 1.0, 2.5, 5.0),
)
PAYMENTS = Counter("payments_processed_total", "Payments processed", ["currency", "status"])


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


class Currency(StrEnum):
    EUR = "EUR"
    USD = "USD"
    TND = "TND"


class PaymentRequest(BaseModel):
    amount: float = Field(gt=0, le=10_000, description="Amount, strictly positive, max 10000")
    currency: Currency = Currency.EUR
    customer_id: str = Field(min_length=1, max_length=64)


class Payment(BaseModel):
    id: str
    amount: float
    currency: Currency
    customer_id: str
    status: str


PRODUCTS = {
    1: {"id": 1, "name": "Clavier mecanique", "price": 89.9},
    2: {"id": 2, "name": "Souris sans fil", "price": 29.5},
    3: {"id": 3, "name": "Ecran 27 pouces", "price": 249.0},
}
_payments: dict[str, Payment] = {}

app = FastAPI(title="Payment API", version=VERSION)
FastAPIInstrumentor.instrument_app(app, excluded_urls="metrics,health")


@app.middleware("http")
async def red_metrics(request: Request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        path = getattr(route, "path", "unmatched")
        if path not in ("/metrics", "/health"):
            elapsed = time.perf_counter() - start
            REQUESTS.labels(request.method, path, str(status)).inc()
            LATENCY.labels(request.method, path).observe(elapsed)
            logger.info(
                "request handled",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "route": path,
                        "status": status,
                        "duration_ms": round(elapsed * 1000, 2),
                    }
                },
            )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": VERSION}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/products")
def list_products() -> list[dict]:
    return list(PRODUCTS.values())


@app.get("/products/{product_id}")
def get_product(product_id: int) -> dict:
    product = PRODUCTS.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return product


@app.post("/payments", status_code=201)
def create_payment(req: PaymentRequest) -> Payment:
    with tracer.start_as_current_span("payment.authorize") as span:
        span.set_attribute("payment.currency", req.currency.value)
        span.set_attribute("payment.amount", req.amount)
        payment = Payment(
            id=str(uuid.uuid4()),
            amount=round(req.amount, 2),
            currency=req.currency,
            customer_id=req.customer_id,
            status="AUTHORIZED",
        )
        _payments[payment.id] = payment
        PAYMENTS.labels(req.currency.value, payment.status).inc()
        logger.info("payment authorized", extra={"extra_fields": {"payment_id": payment.id}})
        return payment


@app.get("/payments/{payment_id}")
def get_payment(payment_id: str) -> Payment:
    payment = _payments.get(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")
    return payment


@app.get("/checkout")
async def checkout() -> dict:
    """Simulated slow processing (latency between CHECKOUT_MIN_DELAY and CHECKOUT_MAX_DELAY)."""
    low = _float_env("CHECKOUT_MIN_DELAY", 0.05)
    high = max(low, _float_env("CHECKOUT_MAX_DELAY", 0.25))
    delay = _rng.uniform(low, high)
    with tracer.start_as_current_span("checkout.process") as span:
        span.set_attribute("checkout.delay_ms", round(delay * 1000, 1))
        await asyncio.sleep(delay)
    return {"status": "processed", "delay_ms": round(delay * 1000, 1)}


@app.get("/flaky")
def flaky() -> dict:
    """Intermittent failures: returns HTTP 500 with probability FLAKY_ERROR_RATE."""
    error_rate = min(max(_float_env("FLAKY_ERROR_RATE", 0.1), 0.0), 1.0)
    if _rng.random() < error_rate:
        logger.error("flaky dependency failure", extra={"extra_fields": {"error_rate": error_rate}})
        raise HTTPException(status_code=500, detail="upstream dependency failure")
    return {"status": "ok"}
