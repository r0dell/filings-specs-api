# Filings & Specs API (v0.1)

Futures contract specifications for AI agents, paid per call via x402 (USDC on Base).

| Endpoint | Returns | Price |
|---|---|---|
| `/v1/spec?symbol=ES` | Futures contract specification: multiplier, tick size/value, point value, hours | 0.0010 USDC |
| `/v1/tick-value?symbol=NQ&points=10` | Money value of a move per contract | 0.0010 USDC |
| `/v1/position-size?symbol=MNQ&risk=200&stop_points=20` | Contracts that fit a risk budget | 0.0010 USDC |
| `/v1/symbols`, `/v1/sources`, `/docs` | Symbol list, source status, docs | free |

Sources: public contract specifications of CME Group, Cboe and Eurex (facts; no margins). Not investment advice.

Tests: `python -m pytest -q`
