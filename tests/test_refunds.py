import pytest
from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


@pytest.mark.parametrize("kind", ["refund", "chargeback", "partial_refund", "voucher"])
@pytest.mark.parametrize("currency", ["EUR", "USD", "TND"])
def test_create_and_get(kind, currency):
    r = client.post(f"/{kind}s", params={"amount": 100, "currency": currency, "customer_id": "c"})
    assert r.status_code == 200
    ref = r.json()["id"]
    assert client.get(f"/{kind}s/{ref}").json()["status"] == "PROCESSED"
    assert client.get(f"/{kind}s/{ref}").json()["status"] == "PROCESSED"
    assert client.get(f"/{kind}s/unknown").status_code == 404
