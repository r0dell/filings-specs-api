"""HTTP-API: Filings & Specs API (Kontrakt-Spezifikationen, Tickwert, Positionsgrösse)."""
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

import engine as e

app = FastAPI(
    title="Filings & Specs API",
    version="0.1.0",
    description=("Futures contract specifications with tick values and position sizing for CME, CBOT, NYMEX, "
                 "COMEX, Cboe and Eurex products."),
)


def _run(fn, *args):
    try:
        return fn(*args)
    except KeyError as ex:
        raise HTTPException(status_code=404, detail=str(ex).strip("'\""))
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


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
def sources():
    from specs import VERIFIED
    return {"specs_verified": VERIFIED, "symbols": len(e.symbols())}


@app.get("/health", include_in_schema=False)
def health():
    return {"ok": True}
