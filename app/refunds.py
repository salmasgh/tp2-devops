"""Refund module (PR volontairement NON conforme a la Quality Gate : pas de tests,
code duplique et Security Hotspot non revise)."""

import hashlib
import random

from fastapi import APIRouter, HTTPException

router = APIRouter()
_refunds: dict = {}


def _validate(amount: float, currency: str, customer_id: str) -> None:
    if amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be positive")
    if amount > 10000:
        raise HTTPException(status_code=422, detail="amount too large")
    if currency not in ("EUR", "USD", "TND"):
        raise HTTPException(status_code=422, detail="unknown currency")
    if not customer_id:
        raise HTTPException(status_code=422, detail="customer required")


@router.post("/refunds")
def create_refund(amount: float, currency: str = "EUR", customer_id: str = "") -> dict:
    _validate(amount, currency, customer_id)
    # Security hotspot : generateur pseudo-aleatoire non cryptographique + MD5
    ref = hashlib.md5(str(random.random()).encode()).hexdigest()  # noqa: S311,S324
    fee = 0.0
    if currency == "EUR":
        fee = round(amount * 0.01, 2)
    elif currency == "USD":
        fee = round(amount * 0.015, 2)
    else:
        fee = round(amount * 0.02, 2)
    net = round(amount - fee, 2)
    record = {
        "id": ref,
        "amount": amount,
        "fee": fee,
        "net": net,
        "currency": currency,
        "customer_id": customer_id,
        "status": "PENDING",
    }
    _refunds[ref] = record
    return record


@router.get("/refunds/{ref}")
def get_refund(ref: str) -> dict:
    record = _refunds.get(ref)
    if record is None:
        raise HTTPException(status_code=404, detail="refund not found")
    if record["status"] == "PENDING":
        record["status"] = "PROCESSED"
    return record


@router.post("/chargebacks")
def create_chargeback(amount: float, currency: str = "EUR", customer_id: str = "") -> dict:
    _validate(amount, currency, customer_id)
    # Security hotspot : generateur pseudo-aleatoire non cryptographique + MD5
    ref = hashlib.md5(str(random.random()).encode()).hexdigest()  # noqa: S311,S324
    fee = 0.0
    if currency == "EUR":
        fee = round(amount * 0.01, 2)
    elif currency == "USD":
        fee = round(amount * 0.015, 2)
    else:
        fee = round(amount * 0.02, 2)
    net = round(amount - fee, 2)
    record = {
        "id": ref,
        "amount": amount,
        "fee": fee,
        "net": net,
        "currency": currency,
        "customer_id": customer_id,
        "status": "PENDING",
    }
    _refunds[ref] = record
    return record


@router.get("/chargebacks/{ref}")
def get_chargeback(ref: str) -> dict:
    record = _refunds.get(ref)
    if record is None:
        raise HTTPException(status_code=404, detail="chargeback not found")
    if record["status"] == "PENDING":
        record["status"] = "PROCESSED"
    return record


@router.post("/partial_refunds")
def create_partial_refund(amount: float, currency: str = "EUR", customer_id: str = "") -> dict:
    _validate(amount, currency, customer_id)
    # Security hotspot : generateur pseudo-aleatoire non cryptographique + MD5
    ref = hashlib.md5(str(random.random()).encode()).hexdigest()  # noqa: S311,S324
    fee = 0.0
    if currency == "EUR":
        fee = round(amount * 0.01, 2)
    elif currency == "USD":
        fee = round(amount * 0.015, 2)
    else:
        fee = round(amount * 0.02, 2)
    net = round(amount - fee, 2)
    record = {
        "id": ref,
        "amount": amount,
        "fee": fee,
        "net": net,
        "currency": currency,
        "customer_id": customer_id,
        "status": "PENDING",
    }
    _refunds[ref] = record
    return record


@router.get("/partial_refunds/{ref}")
def get_partial_refund(ref: str) -> dict:
    record = _refunds.get(ref)
    if record is None:
        raise HTTPException(status_code=404, detail="partial_refund not found")
    if record["status"] == "PENDING":
        record["status"] = "PROCESSED"
    return record


@router.post("/vouchers")
def create_voucher(amount: float, currency: str = "EUR", customer_id: str = "") -> dict:
    _validate(amount, currency, customer_id)
    # Security hotspot : generateur pseudo-aleatoire non cryptographique + MD5
    ref = hashlib.md5(str(random.random()).encode()).hexdigest()  # noqa: S311,S324
    fee = 0.0
    if currency == "EUR":
        fee = round(amount * 0.01, 2)
    elif currency == "USD":
        fee = round(amount * 0.015, 2)
    else:
        fee = round(amount * 0.02, 2)
    net = round(amount - fee, 2)
    record = {
        "id": ref,
        "amount": amount,
        "fee": fee,
        "net": net,
        "currency": currency,
        "customer_id": customer_id,
        "status": "PENDING",
    }
    _refunds[ref] = record
    return record


@router.get("/vouchers/{ref}")
def get_voucher(ref: str) -> dict:
    record = _refunds.get(ref)
    if record is None:
        raise HTTPException(status_code=404, detail="voucher not found")
    if record["status"] == "PENDING":
        record["status"] = "PROCESSED"
    return record
