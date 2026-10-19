"""Rechenkern der Filings & Specs API.

A9  SEC-Meldungen nach Ticker (SEC EDGAR, frei; User-Agent mit Kontakt Pflicht, max. 10 Anfragen/s)
A16 Kontrakt-Spezifikationen, Tickwert und Positionsgrösse
"""
from __future__ import annotations

import datetime as dt
import math
import os
import threading
import time
import xml.etree.ElementTree as ET

import httpx

import specs as SP

UTC = dt.timezone.utc


class SourceUnavailable(RuntimeError):
    pass


# ================================================================== A16 Spezifikationen
def _spec(symbol: str) -> dict:
    s = SP.SPECS.get((symbol or "").upper().strip())
    if not s:
        raise KeyError(f"Unknown symbol '{symbol}'. Use one of: {', '.join(SP.SPECS)}")
    return s


def symbols() -> list[dict]:
    return [{"symbol": s["symbol"], "name": s["name"], "exchange": s["exchange"], "group": s["group"]}
            for s in SP.SPECS.values()]


def spec(symbol: str) -> dict:
    return {**_spec(symbol), "verified": SP.VERIFIED,
            "note": "Facts from public exchange specifications. Margins are not included (set by clearing/broker)."}


def tick_value(symbol: str, ticks: float | None = None, points: float | None = None) -> dict:
    s = _spec(symbol)
    if ticks is not None and points is not None:
        raise ValueError("Give either ticks or points, not both")
    if points is not None:
        ticks = points / s["tick_size"]
    ticks = 1 if ticks is None else ticks
    value = ticks * s["tick_value"]
    return {"symbol": s["symbol"], "ticks": round(ticks, 6), "points": round(ticks * s["tick_size"], 10),
            "value_per_contract": round(value, 4), "currency": s["currency"],
            "tick_size": s["tick_size"], "tick_value": s["tick_value"], "point_value": s["point_value"]}


def position_size(symbol: str, risk: float, stop_ticks: float | None = None,
                  stop_points: float | None = None) -> dict:
    s = _spec(symbol)
    if risk is None or risk <= 0:
        raise ValueError("risk must be a positive amount in the contract currency")
    if (stop_ticks is None) == (stop_points is None):
        raise ValueError("Give exactly one of stop_ticks or stop_points")
    ticks = stop_ticks if stop_ticks is not None else stop_points / s["tick_size"]
    if ticks <= 0:
        raise ValueError("stop must be positive")
    risk_per_contract = ticks * s["tick_value"]
    n = math.floor(risk / risk_per_contract + 1e-9)
    return {"symbol": s["symbol"], "risk_budget": risk, "currency": s["currency"], "stop_ticks": round(ticks, 4),
            "stop_points": round(ticks * s["tick_size"], 10), "risk_per_contract": round(risk_per_contract, 4),
            "contracts": n, "risk_used": round(n * risk_per_contract, 4),
            "note": "Rounded down. Excludes commissions, fees and slippage. Not investment advice."}


# ================================================================== A9 SEC EDGAR
SEC_UA = os.environ.get("SEC_USER_AGENT", "MarketDataAPIs/0.1 data-api@users.noreply.github.com")
_cache: dict[str, tuple[float, object]] = {}
_lock = threading.Lock()
_rate_lock = threading.Lock()
_last: list[float] = []
STATUS: dict[str, dict] = {}

FORM_GROUPS = {"10-K": {"10-K", "10-K/A"}, "10-Q": {"10-Q", "10-Q/A"}, "8-K": {"8-K", "8-K/A"},
               "4": {"4", "4/A"}, "S-1": {"S-1", "S-1/A"}, "13D": {"SC 13D", "SC 13D/A", "SCHEDULE 13D"},
               "13G": {"SC 13G", "SC 13G/A", "SCHEDULE 13G"}, "DEF 14A": {"DEF 14A"}, "6-K": {"6-K"}, "20-F": {"20-F"}}

ITEMS_8K = {
    "1.01": "Entry into a Material Definitive Agreement", "1.02": "Termination of a Material Definitive Agreement",
    "1.03": "Bankruptcy or Receivership", "1.05": "Material Cybersecurity Incidents",
    "2.01": "Completion of Acquisition or Disposition of Assets", "2.02": "Results of Operations and Financial Condition",
    "2.03": "Creation of a Direct Financial Obligation", "2.04": "Triggering Events That Accelerate an Obligation",
    "2.05": "Costs Associated with Exit or Disposal Activities", "2.06": "Material Impairments",
    "3.01": "Notice of Delisting or Failure to Satisfy a Listing Rule", "3.02": "Unregistered Sales of Equity Securities",
    "3.03": "Material Modification to Rights of Security Holders",
    "4.01": "Changes in Registrant's Certifying Accountant",
    "4.02": "Non-Reliance on Previously Issued Financial Statements", "5.01": "Changes in Control of Registrant",
    "5.02": "Departure/Election of Directors or Officers; Compensatory Arrangements",
    "5.03": "Amendments to Articles of Incorporation or Bylaws", "5.07": "Submission of Matters to a Vote of Security Holders",
    "7.01": "Regulation FD Disclosure", "8.01": "Other Events", "9.01": "Financial Statements and Exhibits",
}
TX_CODES = {"P": "open market purchase", "S": "open market sale", "A": "grant/award", "M": "option exercise",
            "F": "tax withholding", "G": "gift", "D": "disposition to issuer", "C": "conversion",
            "X": "exercise of in-the-money derivative", "J": "other"}


def _throttle():
    """Höchstens 8 Anfragen pro Sekunde an die SEC (Limit 10/s)."""
    with _rate_lock:
        now = time.time()
        while _last and now - _last[0] > 1:
            _last.pop(0)
        if len(_last) >= 8:
            time.sleep(1 - (now - _last[0]) + 0.01)
        _last.append(time.time())


def _sec_get(url: str):
    _throttle()
    r = httpx.get(url, headers={"User-Agent": SEC_UA, "Accept-Encoding": "gzip, deflate"}, timeout=30)
    r.raise_for_status()
    return r


def _cached(key, ttl, loader):
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    try:
        val = loader()
        with _lock:
            _cache[key] = (now, val)
            if len(_cache) > 2000:  # einfache Begrenzung
                for k in sorted(_cache, key=lambda k: _cache[k][0])[:500]:
                    _cache.pop(k, None)
        STATUS[key.split(":")[0]] = {"ok": True, "loaded_at": dt.datetime.now(UTC).isoformat()}
        return val
    except KeyError:
        raise
    except Exception as e:
        STATUS[key.split(":")[0]] = {"ok": False, "error": str(e)[:200], "at": dt.datetime.now(UTC).isoformat()}
        if hit:
            return hit[1]
        raise SourceUnavailable(f"SEC EDGAR temporarily unavailable ({key.split(':')[0]}). Please retry later.")


def _tickers() -> dict[str, dict]:
    def load():
        data = _sec_get("https://www.sec.gov/files/company_tickers.json").json()
        return {v["ticker"].upper(): {"cik": int(v["cik_str"]), "name": v["title"]} for v in data.values()}
    return _cached("tickers", 24 * 3600, load)


def _company(ticker: str) -> dict:
    t = (ticker or "").upper().strip().replace(".", "-")
    m = _tickers().get(t)
    if not m:
        raise KeyError(f"Unknown US ticker '{ticker}' (not in SEC company_tickers list)")
    return {"ticker": t, **m}


def _submissions(cik: int) -> dict:
    return _cached(f"submissions:{cik}", 600,
                   lambda: _sec_get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json").json())


def _rows(sub: dict) -> list[dict]:
    rec = sub.get("filings", {}).get("recent", {})
    keys = list(rec.keys())
    n = len(rec.get("accessionNumber", []))
    return [{k: rec[k][i] for k in keys if i < len(rec[k])} for i in range(n)]


def _links(cik: int, acc: str, doc: str | None):
    folder = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}"
    return (f"{folder}/{doc}" if doc else None), f"{folder}/{acc}-index.htm"


def filings(ticker: str, form_type: str | None = None, limit: int = 20) -> dict:
    if not 1 <= int(limit) <= 100:
        raise ValueError("limit must be between 1 and 100")
    co = _company(ticker)
    wanted = None
    if form_type:
        wanted = set()
        for f in form_type.split(","):
            f = f.strip().upper()
            if not f:
                continue
            wanted |= FORM_GROUPS.get(f, {f})
    out = []
    for r in _rows(_submissions(co["cik"])):
        form = r.get("form", "")
        if wanted and form.upper() not in wanted:
            continue
        url, idx = _links(co["cik"], r["accessionNumber"], r.get("primaryDocument"))
        row = {"form": form, "filing_date": r.get("filingDate"), "report_date": r.get("reportDate") or None,
               "accepted": r.get("acceptanceDateTime"), "accession_number": r["accessionNumber"],
               "description": r.get("primaryDocDescription") or None, "url": url, "index_url": idx}
        items = [i.strip() for i in (r.get("items") or "").split(",") if i.strip()]
        if items:
            row["items"] = [{"item": i, "title": ITEMS_8K.get(i, "")} for i in items]
        out.append(row)
        if len(out) >= int(limit):
            break
    return {"ticker": co["ticker"], "cik": co["cik"], "company": co["name"], "filter": form_type,
            "filings": out, "source": "SEC EDGAR (public data, sec.gov)",
            "note": "Most recent filings first (up to ~1000 recent filings are searched)."}


def _text(node, path):
    el = node.find(path)
    if el is None:
        return None
    v = el.find("value")
    t = (v.text if v is not None else el.text) or ""
    return t.strip() or None


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_form4(xml_text: str) -> dict:
    root = ET.fromstring(xml_text)
    owners = []
    for o in root.findall("reportingOwner"):
        rel = o.find("reportingOwnerRelationship")
        roles = []
        if rel is not None:
            for tag, label in (("isDirector", "director"), ("isOfficer", "officer"),
                               ("isTenPercentOwner", "10% owner"), ("isOther", "other")):
                if (rel.findtext(tag) or "").strip() in ("1", "true"):
                    roles.append(label)
            title = (rel.findtext("officerTitle") or "").strip()
            if title:
                roles.append(title)
        owners.append({"name": (o.findtext("reportingOwnerId/rptOwnerName") or "").strip(), "roles": roles})
    tx = []
    for t in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
        code = (t.findtext("transactionCoding/transactionCode") or "").strip()
        shares = _num(_text(t, "transactionAmounts/transactionShares"))
        price = _num(_text(t, "transactionAmounts/transactionPricePerShare"))
        ad = _text(t, "transactionAmounts/transactionAcquiredDisposedCode")
        tx.append({"date": _text(t, "transactionDate"), "security": _text(t, "securityTitle"), "code": code,
                   "code_meaning": TX_CODES.get(code, ""), "shares": shares, "price": price,
                   "acquired_disposed": {"A": "acquired", "D": "disposed"}.get(ad, ad),
                   "value": round(shares * price, 2) if shares is not None and price is not None else None,
                   "shares_owned_after": _num(_text(t, "postTransactionAmounts/sharesOwnedFollowingTransaction"))})
    return {"owners": owners, "transactions": tx}


def _form4(cik: int, acc: str, doc: str) -> dict:
    raw = doc.split("/")[-1] if doc else None
    if not raw or not raw.lower().endswith(".xml"):
        return {"owners": [], "transactions": [], "note": "no XML document"}
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{raw}"
    return _cached(f"form4:{acc}", 7 * 24 * 3600, lambda: parse_form4(_sec_get(url).text))


def insider(ticker: str, limit: int = 10) -> dict:
    if not 1 <= int(limit) <= 20:
        raise ValueError("limit must be between 1 and 20")
    co = _company(ticker)
    rows = [r for r in _rows(_submissions(co["cik"])) if r.get("form") in ("4", "4/A")][:int(limit)]
    out, buys, sells = [], 0.0, 0.0
    for r in rows:
        url, idx = _links(co["cik"], r["accessionNumber"], r.get("primaryDocument"))
        try:
            d = _form4(co["cik"], r["accessionNumber"], r.get("primaryDocument"))
        except SourceUnavailable:
            d = {"owners": [], "transactions": [], "note": "details temporarily unavailable"}
        for t in d["transactions"]:
            if t["code"] == "P" and t["value"]:
                buys += t["value"]
            if t["code"] == "S" and t["value"]:
                sells += t["value"]
        out.append({"filing_date": r.get("filingDate"), "accession_number": r["accessionNumber"], "url": url,
                    "index_url": idx, **d})
    return {"ticker": co["ticker"], "cik": co["cik"], "company": co["name"], "form4_filings": out,
            "summary": {"open_market_purchases_value": round(buys, 2), "open_market_sales_value": round(sells, 2),
                        "filings_analyzed": len(out)},
            "source": "SEC EDGAR Form 4 (public data, sec.gov)",
            "note": "Transaction codes: P purchase, S sale, A award, M option exercise, F tax withholding, G gift."}


def status() -> dict:
    return STATUS
