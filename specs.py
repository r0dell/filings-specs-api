"""A16: Kontrakt-Spezifikationen (Fakten aus den öffentlichen Spezifikationen von CME, Cboe und Eurex).

Je Kontrakt: Börse, Multiplikator (Wert pro ganzer Preiseinheit), Tickgrösse, Tickwert, Währung,
Handelszeiten (Kurzform). Keine Margins (ändern sich laufend, sind Sache des Brokers).
"""

VERIFIED = "2026-10-19"

CME_EQ_HOURS = "CME Globex: Sun-Fri 17:00-16:00 CT (daily break 16:00-17:00 CT)"
CME_HOURS = "CME Globex: Sun-Fri 17:00-16:00 CT (daily break 16:00-17:00 CT)"
CME_GRAIN_HOURS = "CME Globex: Sun-Fri 19:00-07:45 CT and Mon-Fri 08:30-13:20 CT"
EUREX_IDX_HOURS = "Eurex T7: continuous trading about 02:10-22:00 CET on exchange days"
EUREX_SMI_HOURS = "Eurex T7: continuous trading about 07:50-22:00 CET on exchange days"
EUREX_FI_HOURS = "Eurex T7: continuous trading about 01:10-22:00 CET on exchange days"
CFE_HOURS = "Cboe Futures Exchange: Sun-Fri 17:00-16:00 CT (break 16:00-17:00 CT)"

# symbol: (Name, Börse, Gruppe, Multiplikator, Einheit des Preises, Tickgrösse, Tickwert, Währung, Handelszeiten, Quelle)
_RAW = [
    ("ES", "E-mini S&P 500", "CME", "equity index", 50, "index points", 0.25, 12.50, "USD", CME_EQ_HOURS),
    ("MES", "Micro E-mini S&P 500", "CME", "equity index", 5, "index points", 0.25, 1.25, "USD", CME_EQ_HOURS),
    ("NQ", "E-mini Nasdaq-100", "CME", "equity index", 20, "index points", 0.25, 5.00, "USD", CME_EQ_HOURS),
    ("MNQ", "Micro E-mini Nasdaq-100", "CME", "equity index", 2, "index points", 0.25, 0.50, "USD", CME_EQ_HOURS),
    ("YM", "E-mini Dow ($5)", "CBOT", "equity index", 5, "index points", 1.0, 5.00, "USD", CME_EQ_HOURS),
    ("MYM", "Micro E-mini Dow", "CBOT", "equity index", 0.5, "index points", 1.0, 0.50, "USD", CME_EQ_HOURS),
    ("RTY", "E-mini Russell 2000", "CME", "equity index", 50, "index points", 0.10, 5.00, "USD", CME_EQ_HOURS),
    ("M2K", "Micro E-mini Russell 2000", "CME", "equity index", 5, "index points", 0.10, 0.50, "USD", CME_EQ_HOURS),
    ("CL", "Crude Oil WTI", "NYMEX", "energy", 1000, "USD per barrel", 0.01, 10.00, "USD", CME_HOURS),
    ("MCL", "Micro WTI Crude Oil", "NYMEX", "energy", 100, "USD per barrel", 0.01, 1.00, "USD", CME_HOURS),
    ("NG", "Henry Hub Natural Gas", "NYMEX", "energy", 10000, "USD per MMBtu", 0.001, 10.00, "USD", CME_HOURS),
    ("GC", "Gold", "COMEX", "metals", 100, "USD per troy ounce", 0.10, 10.00, "USD", CME_HOURS),
    ("MGC", "Micro Gold", "COMEX", "metals", 10, "USD per troy ounce", 0.10, 1.00, "USD", CME_HOURS),
    ("SI", "Silver", "COMEX", "metals", 5000, "USD per troy ounce", 0.005, 25.00, "USD", CME_HOURS),
    ("HG", "Copper", "COMEX", "metals", 25000, "USD per pound", 0.0005, 12.50, "USD", CME_HOURS),
    ("ZT", "2-Year T-Note", "CBOT", "interest rates", 2000, "points of par", 1 / 256, 7.8125, "USD", CME_HOURS),
    ("ZF", "5-Year T-Note", "CBOT", "interest rates", 1000, "points of par", 1 / 128, 7.8125, "USD", CME_HOURS),
    ("ZN", "10-Year T-Note", "CBOT", "interest rates", 1000, "points of par", 1 / 64, 15.625, "USD", CME_HOURS),
    ("ZB", "U.S. Treasury Bond", "CBOT", "interest rates", 1000, "points of par", 1 / 32, 31.25, "USD", CME_HOURS),
    ("6E", "Euro FX", "CME", "currencies", 125000, "USD per EUR", 0.00005, 6.25, "USD", CME_HOURS),
    ("6J", "Japanese Yen", "CME", "currencies", 12500000, "USD per JPY", 0.0000005, 6.25, "USD", CME_HOURS),
    ("6B", "British Pound", "CME", "currencies", 62500, "USD per GBP", 0.0001, 6.25, "USD", CME_HOURS),
    ("6S", "Swiss Franc", "CME", "currencies", 125000, "USD per CHF", 0.00005, 6.25, "USD", CME_HOURS),
    ("BTC", "Bitcoin", "CME", "crypto", 5, "USD per bitcoin", 5.0, 25.00, "USD", CME_HOURS),
    ("MBT", "Micro Bitcoin", "CME", "crypto", 0.1, "USD per bitcoin", 5.0, 0.50, "USD", CME_HOURS),
    ("ZC", "Corn", "CBOT", "agriculture", 5000, "USD per bushel", 0.0025, 12.50, "USD", CME_GRAIN_HOURS),
    ("ZS", "Soybeans", "CBOT", "agriculture", 5000, "USD per bushel", 0.0025, 12.50, "USD", CME_GRAIN_HOURS),
    ("ZW", "Chicago SRW Wheat", "CBOT", "agriculture", 5000, "USD per bushel", 0.0025, 12.50, "USD", CME_GRAIN_HOURS),
    ("VX", "Cboe Volatility Index (VIX) Futures", "CFE", "volatility", 1000, "index points", 0.05, 50.00, "USD",
     CFE_HOURS),
    ("FDAX", "DAX Futures", "Eurex", "equity index", 25, "index points", 1.0, 25.00, "EUR", EUREX_IDX_HOURS),
    ("FDXM", "Mini-DAX Futures", "Eurex", "equity index", 5, "index points", 1.0, 5.00, "EUR", EUREX_IDX_HOURS),
    ("FDXS", "Micro-DAX Futures", "Eurex", "equity index", 1, "index points", 1.0, 1.00, "EUR", EUREX_IDX_HOURS),
    ("FESX", "EURO STOXX 50 Index Futures", "Eurex", "equity index", 10, "index points", 1.0, 10.00, "EUR",
     EUREX_IDX_HOURS),
    ("FSMI", "SMI Futures", "Eurex", "equity index", 10, "index points", 1.0, 10.00, "CHF", EUREX_SMI_HOURS),
    ("FGBL", "Euro-Bund Futures", "Eurex", "interest rates", 1000, "percent of par", 0.01, 10.00, "EUR",
     EUREX_FI_HOURS),
    ("FGBM", "Euro-Bobl Futures", "Eurex", "interest rates", 1000, "percent of par", 0.01, 10.00, "EUR",
     EUREX_FI_HOURS),
    ("FGBS", "Euro-Schatz Futures", "Eurex", "interest rates", 1000, "percent of par", 0.005, 5.00, "EUR",
     EUREX_FI_HOURS),
]

SOURCES = {
    "CME": "https://www.cmegroup.com (contract specifications)", "CBOT": "https://www.cmegroup.com (contract specifications)",
    "NYMEX": "https://www.cmegroup.com (contract specifications)", "COMEX": "https://www.cmegroup.com (contract specifications)",
    "CFE": "https://www.cboe.com/tradable_products/vix/vix_futures/specifications/",
    "Eurex": "https://www.eurex.com (contract specifications)",
}

SPECS = {}
for sym, name, exch, group, mult, unit, tick, tickval, ccy, hours in _RAW:
    SPECS[sym] = {"symbol": sym, "name": name, "exchange": exch, "group": group, "multiplier": mult,
                  "price_unit": unit, "tick_size": tick, "tick_value": tickval, "currency": ccy,
                  "point_value": round(tickval / tick, 6), "trading_hours": hours, "source": SOURCES[exch]}

# Selbstprüfung: Tickwert = Tickgrösse x Multiplikator (bei Bonds: Punkte x 1000 USD)
for s in SPECS.values():
    assert abs(s["tick_size"] * s["multiplier"] - s["tick_value"]) < 1e-6 * max(1, s["tick_value"]), s["symbol"]
