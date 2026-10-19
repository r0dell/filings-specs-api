"""Tests der Filings & Specs API (ohne Netz). Start: python -m pytest -q"""
from fastapi.testclient import TestClient

import engine
from app import app

c = TestClient(app)

def get(path, **p):
    r = c.get(path, params=p)
    assert r.status_code == 200, r.text
    return r.json()


def test_specs_and_calculators():
    s = get("/v1/spec", symbol="es")
    assert s["tick_value"] == 12.5 and s["point_value"] == 50
    assert get("/v1/tick-value", symbol="NQ", points=10)["value_per_contract"] == 200.0
    assert get("/v1/tick-value", symbol="ZN", ticks=2)["value_per_contract"] == 31.25
    p = get("/v1/position-size", symbol="MNQ", risk=200, stop_points=20)
    assert p["contracts"] == 5 and p["risk_per_contract"] == 40.0
    assert get("/v1/position-size", symbol="FDAX", risk=1000, stop_ticks=30)["contracts"] == 1
    assert c.get("/v1/position-size", params={"symbol": "ES", "risk": 100}).status_code == 400
    assert c.get("/v1/spec", params={"symbol": "XX"}).status_code == 404
    assert len(get("/v1/symbols")) == 37


def test_sources():
    assert get("/v1/sources")["symbols"] == 37
    assert c.get("/v1/filings", params={"ticker": "AAPL"}).status_code == 404
