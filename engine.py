"""Rechenkern der Filings & Specs API: A16 Kontrakt-Spezifikationen, Tickwert und Positionsgrösse.

(A9 SEC-Meldungen wurde am 19.10.2026 entfernt.)
"""
from __future__ import annotations

import math

import specs as SP


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
