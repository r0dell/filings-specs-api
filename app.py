"""HTTP-API: Filings & Specs API (SEC-Meldungen nach Ticker, Insider-Transaktionen, Kontrakt-Spezifikationen)."""
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

import engine as e

app = FastAPI(
    title="Filings & Specs API",
    version="0.1.0",
    description=("Latest SEC filings (8-K with item titles, 10-Q, 10-K, Form 4 and more) for a US ticker with "
                 "direct links, parsed Form 4 insider transactions, and futures contract specifications with tick "
                 "values and position sizing for CME, Cboe and Eurex products."),
)


def _run(fn, *args):
    try:
        return fn(*args)
    except KeyError as ex:
        raise HTTPException(status_code=404, detail=str(ex).strip("'\""))
    except e.SourceUnavailable as ex:
        raise HTTPException(status_code=503, detail=str(ex))
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


# ---------------------------------------------------------------- A9
@app.get("/v1/filings", summary="Latest SEC filings of a US ticker (optionally filtered by form type)")
def filings(ticker: str = Query(..., examples=["AAPL"]), type: Optional[str] = Query(None, examples=["8-K"]),
            limit: int = Query(20, ge=1, le=100)):
    return _run(e.filings, ticker, type, limit)


@app.get("/v1/insider", summary="Parsed Form 4 insider transactions of a US ticker")
def insider(ticker: str = Query(..., examples=["NVDA"]), limit: int = Query(10, ge=1, le=20)):
    return _run(e.insider, ticker, limit)


# ---------------------------------------------------------------- A16
@app.get("/v1/spec", summary="Contract specification of a futures symbol")
def spec(symbol: str = Query(..., examples=["ES"])):
    return _run(e.spec, symbol)


@app.get("/v1/tick-value", summary="Value of a move in ticks or points for one contract")
def tick_value(symbol: str = Query(..., examples=["NQ"]), ticks: Optional[float] = None,
               points: Optional[float] = None):
    return _run(e.tick_value, symbol, ticks, points)


@app.get("/v1/position-size", summary="Number of contracts for a risk budget and stop distance")
def position_size(symbol: str = Query(..., examples=["MNQ"]), risk: float = Query(..., examples=[200]),
                  stop_ticks: Optional[float] = None, stop_points: Optional[float] = None):
    return _run(e.position_size, symbol, risk, stop_ticks, stop_points)


# ---------------------------------------------------------------- frei
@app.get("/v1/symbols", summary="Futures symbols available for /v1/spec (free)")
def symbols():
    return e.symbols()


@app.get("/v1/sources", summary="Data source status (free)")
def sources(check: bool = False):
    latest = {}
    if check:
        try:
            r = e.filings("AAPL", None, 1)
            latest["sec_aapl_latest_filing"] = r["filings"][0]["filing_date"] if r["filings"] else None
        except Exception as ex:
            latest["sec_aapl_latest_filing"] = f"error: {ex}"[:200]
    from specs import VERIFIED
    return {"specs_verified": VERIFIED, "latest": latest, "status": e.status()}


@app.get("/health", include_in_schema=False)
def health():
    return {"ok": True}
