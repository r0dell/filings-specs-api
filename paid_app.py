"""Filings & Specs API mit x402-Bezahlung (USDC auf Base).

Umgebungsvariablen:
  PAY_TO              Deine Wallet-Adresse (0x...), hierhin gehen die Zahlungen. Pflicht.
  X402_NETWORK        "testnet" (Base Sepolia, Standard) oder "mainnet" (Base).
  CDP_API_KEY_ID      Coinbase-Developer-Platform-Key. Für mainnet und Bazaar-Listing nötig.
  CDP_API_KEY_SECRET  dazugehöriges Secret.
  PUBLIC_URL          Öffentliche https-Adresse des Dienstes (für die Bazaar-Beschreibung).

Start:  uvicorn paid_app:app --host 0.0.0.0 --port 8000
Gratis:  /v1/symbols, /v1/sources, /health, /docs
Bezahlt: /v1/filings, /v1/insider (A9), /v1/spec, /v1/tick-value, /v1/position-size (A16)
"""
import os
import re

from x402 import x402ResourceServer
from x402.extensions.bazaar import (
    OutputConfig,
    bazaar_resource_server_extension,
    declare_discovery_extension,
)
from x402.http import FacilitatorConfig, HTTPFacilitatorClient
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import PaymentOption, RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme

from app import app

NETWORKS = {"testnet": "eip155:84532", "mainnet": "eip155:8453"}
TESTNET_FACILITATOR = os.environ.get("FACILITATOR_URL", "https://x402.org/facilitator")

PAY_TO = os.environ.get("PAY_TO", "").strip()
if not re.fullmatch(r"0x[0-9a-fA-F]{40}", PAY_TO):
    raise SystemExit("PAY_TO fehlt oder ist keine gültige Wallet-Adresse (0x + 40 Hex-Zeichen).")

MODE = os.environ.get("X402_NETWORK", "testnet").lower()
if MODE not in NETWORKS:
    raise SystemExit("X402_NETWORK muss 'testnet' oder 'mainnet' sein.")
NETWORK = NETWORKS[MODE]

CDP_ID = os.environ.get("CDP_API_KEY_ID", "").strip().strip('"\'').strip()
CDP_SECRET = os.environ.get("CDP_API_KEY_SECRET", "").strip().strip('"\'').strip()
if "BEGIN" in CDP_SECRET:
    CDP_SECRET = CDP_SECRET.replace("\\n", "\n")  # PEM aus einzeiligem Feld


def _describe_cdp_keys() -> str:
    """Format der Keys beschreiben, ohne Werte preiszugeben."""
    id_kind = ("uuid" if re.fullmatch(r"[0-9a-fA-F-]{36}", CDP_ID)
               else "organizations-path" if CDP_ID.startswith("organizations/") else "other")
    if "BEGIN EC PRIVATE KEY" in CDP_SECRET:
        sec_kind = "ec-pem"
    else:
        try:
            import base64
            sec_kind = f"base64-{len(base64.b64decode(CDP_SECRET, validate=True))}bytes"
        except Exception:
            sec_kind = "unparseable"
    return f"CDP key: id={id_kind} (len {len(CDP_ID)}), secret={sec_kind} (len {len(CDP_SECRET)})"


if CDP_ID and CDP_SECRET:
    from cdp.x402 import create_facilitator_config
    print(_describe_cdp_keys(), flush=True)
    facilitator_cfg = create_facilitator_config(CDP_ID, CDP_SECRET)
elif MODE == "mainnet":
    raise SystemExit("Für mainnet werden CDP_API_KEY_ID und CDP_API_KEY_SECRET benötigt.")
else:
    facilitator_cfg = FacilitatorConfig(url=TESTNET_FACILITATOR)

server = x402ResourceServer(HTTPFacilitatorClient(facilitator_cfg))
server.register(NETWORK, ExactEvmServerScheme())
server.register_extension(bazaar_resource_server_extension)

SVC = "Filings & Specs API"


def pay(price: str) -> PaymentOption:
    return PaymentOption(scheme="exact", pay_to=PAY_TO, price=price, network=NETWORK)


def route(price, desc, tags, inp, schema, required, example):
    return RouteConfig(
        accepts=pay(price), description=desc, mime_type="application/json", service_name=SVC, tags=tags,
        extensions=declare_discovery_extension(
            input=inp, input_schema={"properties": schema, "required": required},
            output=OutputConfig(example=example)))


S = lambda d: {"type": "string", "description": d}
SYM = S("Futures symbol, e.g. ES, MES, NQ, MNQ, YM, RTY, CL, MCL, NG, GC, MGC, SI, HG, ZT, ZF, ZN, ZB, 6E, 6J, 6B, "
        "6S, BTC, MBT, ZC, ZS, ZW, VX, FDAX, FDXM, FDXS, FESX, FSMI, FGBL, FGBM, FGBS")

# Preise je Agent: A9 0.0020, A16 0.0010 USDC
A9, A16 = "$0.002", "$0.001"
routes = {
    "GET /v1/filings": route(
        A9, "Returns the latest SEC EDGAR filings of a US-listed company by ticker (8-K with item titles, 10-Q, "
            "10-K, Form 4, S-1, 13D/G and more) with filing date, acceptance time and direct document links.",
        ["finance", "sec", "filings", "edgar", "stocks"], {"ticker": "AAPL", "type": "8-K"},
        {"ticker": S("US stock ticker, e.g. AAPL"), "type": S("Optional form filter, e.g. 8-K, 10-Q, 10-K, 4; "
                                                                "comma list allowed"),
         "limit": S("Number of filings, 1-100. Default 20.")}, ["ticker"],
        {"ticker": "AAPL", "filings": [{"form": "8-K", "filing_date": "2026-10-30",
                                        "items": [{"item": "2.02", "title": "Results of Operations and "
                                                                           "Financial Condition"}]}]}),
    "GET /v1/insider": route(
        A9, "Returns recent Form 4 insider transactions of a US company by ticker, parsed: insider name and role, "
            "transaction code (purchase, sale, award, exercise), shares, price, value and holdings after, plus a "
            "purchase/sale summary.",
        ["finance", "sec", "insider", "form4", "stocks"], {"ticker": "NVDA"},
        {"ticker": S("US stock ticker"), "limit": S("Number of Form 4 filings, 1-20. Default 10.")}, ["ticker"],
        {"ticker": "NVDA", "summary": {"open_market_sales_value": 1250000.0},
         "form4_filings": [{"owners": [{"name": "Doe John", "roles": ["officer", "CFO"]}],
                            "transactions": [{"code": "S", "shares": 10000, "price": 125.0}]}]}),
    "GET /v1/spec": route(
        A16, "Returns the contract specification of a futures symbol (CME, CBOT, NYMEX, COMEX, Cboe, Eurex): "
             "multiplier, tick size, tick value, point value, currency and trading hours.",
        ["finance", "futures", "contract-specs", "reference"], {"symbol": "ES"}, {"symbol": SYM}, ["symbol"],
        {"symbol": "ES", "tick_size": 0.25, "tick_value": 12.5, "point_value": 50, "currency": "USD"}),
    "GET /v1/tick-value": route(
        A16, "Converts a price move in ticks or points into money per contract for a futures symbol.",
        ["finance", "futures", "risk", "calculator"], {"symbol": "NQ", "points": "10"},
        {"symbol": SYM, "ticks": S("Number of ticks"), "points": S("Number of points (alternative to ticks)")},
        ["symbol"], {"symbol": "NQ", "ticks": 40, "value_per_contract": 200.0, "currency": "USD"}),
    "GET /v1/position-size": route(
        A16, "Calculates how many futures contracts fit a risk budget for a given stop distance (ticks or points), "
             "rounded down, with risk per contract.",
        ["finance", "futures", "risk", "position-sizing"], {"symbol": "MNQ", "risk": "200", "stop_points": "20"},
        {"symbol": SYM, "risk": S("Risk budget in contract currency"), "stop_ticks": S("Stop distance in ticks"),
         "stop_points": S("Stop distance in points")}, ["symbol", "risk"],
        {"symbol": "MNQ", "contracts": 5, "risk_per_contract": 40.0}),
}

app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)
app.title = f"Filings & Specs API ({MODE})"
