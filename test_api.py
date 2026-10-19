"""Tests der Filings & Specs API (ohne Netz). Start: python -m pytest -q"""
import pytest
from fastapi.testclient import TestClient

import engine
from app import app

c = TestClient(app)

TICKERS = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
           "1": {"cik_str": 1067983, "ticker": "BRK-B", "title": "Berkshire Hathaway Inc"}}
SUB = {"filings": {"recent": {
    "accessionNumber": ["0000320193-26-000101", "0000320193-26-000100", "0000320193-26-000099"],
    "filingDate": ["2026-10-30", "2026-10-28", "2026-08-01"],
    "reportDate": ["2026-10-30", "2026-10-24", "2026-06-28"],
    "acceptanceDateTime": ["2026-10-30T16:30:12.000Z", "2026-10-28T18:01:00.000Z", "2026-08-01T16:05:00.000Z"],
    "form": ["8-K", "4", "10-Q"],
    "items": ["2.02,9.01", "", ""],
    "primaryDocument": ["aapl-20261030.htm", "xslF345X05/wk-form4_1.xml", "aapl-20260628.htm"],
    "primaryDocDescription": ["8-K", "FORM 4", "10-Q"]}}}
FORM4 = """<?xml version="1.0"?>
<ownershipDocument>
 <reportingOwner><reportingOwnerId><rptOwnerName>Doe John</rptOwnerName></reportingOwnerId>
  <reportingOwnerRelationship><isOfficer>1</isOfficer><officerTitle>CFO</officerTitle></reportingOwnerRelationship>
 </reportingOwner>
 <nonDerivativeTable>
  <nonDerivativeTransaction>
   <securityTitle><value>Common Stock</value></securityTitle>
   <transactionDate><value>2026-10-24</value></transactionDate>
   <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
   <transactionAmounts><transactionShares><value>1000</value></transactionShares>
    <transactionPricePerShare><value>250.5</value></transactionPricePerShare>
    <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode></transactionAmounts>
   <postTransactionAmounts><sharesOwnedFollowingTransaction><value>50000</value></sharesOwnedFollowingTransaction>
   </postTransactionAmounts>
  </nonDerivativeTransaction>
 </nonDerivativeTable>
</ownershipDocument>"""


class R:
    def __init__(self, js=None, text=None):
        self._js, self.text = js, text

    def json(self):
        return self._js


@pytest.fixture(autouse=True)
def fake(monkeypatch):
    engine._cache.clear()
    calls = []

    def get(url):
        calls.append(url)
        if url.endswith("company_tickers.json"):
            return R(TICKERS)
        if "submissions/CIK0000320193" in url:
            return R(SUB)
        if url.endswith("/000032019326000100/wk-form4_1.xml"):
            return R(text=FORM4)
        raise AssertionError(url)
    monkeypatch.setattr(engine, "_sec_get", get)
    return calls


def get(path, **p):
    r = c.get(path, params=p)
    assert r.status_code == 200, r.text
    return r.json()


def test_filings_and_items():
    r = get("/v1/filings", ticker="aapl")
    assert r["cik"] == 320193 and [f["form"] for f in r["filings"]] == ["8-K", "4", "10-Q"]
    f = r["filings"][0]
    assert f["items"][0] == {"item": "2.02", "title": "Results of Operations and Financial Condition"}
    assert f["url"] == "https://www.sec.gov/Archives/edgar/data/320193/000032019326000101/aapl-20261030.htm"
    assert [x["form"] for x in get("/v1/filings", ticker="AAPL", type="10-Q,10-K")["filings"]] == ["10-Q"]


def test_unknown_ticker():
    assert c.get("/v1/filings", params={"ticker": "ZZZZ"}).status_code == 404


def test_insider_parsed(fake):
    r = get("/v1/insider", ticker="AAPL")
    f = r["form4_filings"][0]
    assert f["owners"][0] == {"name": "Doe John", "roles": ["officer", "CFO"]}
    t = f["transactions"][0]
    assert t["code"] == "S" and t["shares"] == 1000 and t["value"] == 250500.0 and t["acquired_disposed"] == "disposed"
    assert r["summary"]["open_market_sales_value"] == 250500.0
    get("/v1/insider", ticker="AAPL")
    assert sum("wk-form4_1.xml" in u for u in fake) == 1  # zwischengespeichert


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


def test_sources_check():
    assert get("/v1/sources", check="true")["latest"]["sec_aapl_latest_filing"] == "2026-10-30"
