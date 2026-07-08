"""Catalogue of CFTC-reported futures markets to publish.

Each entry has:
  ticker  - short display symbol / JSON filename
  name    - human-friendly display name
  group   - category used to group the picker in the UI
  market  - the EXACT "Market and Exchange Names" string as it appears in the
            CFTC files (identical across the Legacy / TFF / Disaggregated reports)
  reports - which report families this market appears in:
              "legacy"  -> Commercial / Noncommercial / Nonreportable (all markets)
              "tff"     -> Dealer / Asset Mgr / Leveraged / Other  (financials)
              "disagg"  -> Producer-Merchant / Swap / Managed Money / Other (commodities)

To add or remove a market, edit this list. build_data.py prints a coverage
report so you can see which reports actually matched.
"""

FIN = ["legacy", "tff"]        # financial futures -> Legacy + Traders in Financial Futures
COM = ["legacy", "disagg"]     # physical commodities -> Legacy + Disaggregated

INSTRUMENTS = [
    # ── Equities ──────────────────────────────────────────────────────
    {"ticker": "ES",   "name": "E-Mini S&P 500",        "group": "Equities", "market": "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "NQ",   "name": "E-Mini Nasdaq-100",     "group": "Equities", "market": "NASDAQ MINI - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "YM",   "name": "E-Mini Dow ($5)",       "group": "Equities", "market": "DJIA x $5 - CHICAGO BOARD OF TRADE", "reports": FIN},
    {"ticker": "RTY",  "name": "E-Mini Russell 2000",   "group": "Equities", "market": "RUSSELL E-MINI - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "EMD",  "name": "E-Mini S&P 400 MidCap", "group": "Equities", "market": "E-MINI S&P 400 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "VIX",  "name": "VIX Futures",           "group": "Equities", "market": "VIX FUTURES - CBOE FUTURES EXCHANGE", "reports": FIN},
    {"ticker": "NIK",  "name": "Nikkei 225 (USD)",      "group": "Equities", "market": "NIKKEI STOCK AVERAGE - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},

    # ── FX ────────────────────────────────────────────────────────────
    {"ticker": "EUR",  "name": "Euro FX",               "group": "FX", "market": "EURO FX - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "GBP",  "name": "British Pound",         "group": "FX", "market": "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "JPY",  "name": "Japanese Yen",          "group": "FX", "market": "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "AUD",  "name": "Australian Dollar",     "group": "FX", "market": "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "CAD",  "name": "Canadian Dollar",       "group": "FX", "market": "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "CHF",  "name": "Swiss Franc",           "group": "FX", "market": "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "NZD",  "name": "New Zealand Dollar",    "group": "FX", "market": "NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "MXN",  "name": "Mexican Peso",          "group": "FX", "market": "MEXICAN PESO - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "BRL",  "name": "Brazilian Real",        "group": "FX", "market": "BRAZILIAN REAL - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "DXY",  "name": "US Dollar Index",       "group": "FX", "market": "USD INDEX - ICE FUTURES U.S.", "reports": FIN},

    # ── Rates ─────────────────────────────────────────────────────────
    {"ticker": "ZB",   "name": "US Treasury Bond",      "group": "Rates", "market": "UST BOND - CHICAGO BOARD OF TRADE", "reports": FIN},
    {"ticker": "UB",   "name": "Ultra US T-Bond",       "group": "Rates", "market": "ULTRA UST BOND - CHICAGO BOARD OF TRADE", "reports": FIN},
    {"ticker": "ZN",   "name": "10Y T-Note",            "group": "Rates", "market": "UST 10Y NOTE - CHICAGO BOARD OF TRADE", "reports": FIN},
    {"ticker": "TN",   "name": "Ultra 10Y T-Note",      "group": "Rates", "market": "ULTRA UST 10Y - CHICAGO BOARD OF TRADE", "reports": FIN},
    {"ticker": "ZF",   "name": "5Y T-Note",             "group": "Rates", "market": "UST 5Y NOTE - CHICAGO BOARD OF TRADE", "reports": FIN},
    {"ticker": "ZT",   "name": "2Y T-Note",             "group": "Rates", "market": "UST 2Y NOTE - CHICAGO BOARD OF TRADE", "reports": FIN},
    {"ticker": "ZQ",   "name": "30-Day Fed Funds",      "group": "Rates", "market": "FED FUNDS - CHICAGO BOARD OF TRADE", "reports": FIN},
    {"ticker": "SR3",  "name": "3-Month SOFR",          "group": "Rates", "market": "SOFR-3M - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "SR1",  "name": "1-Month SOFR",          "group": "Rates", "market": "SOFR-1M - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},

    # ── Crypto (CME) ─────────────────────────────────────────────────
    {"ticker": "BTC",  "name": "Bitcoin (CME)",         "group": "Crypto", "market": "BITCOIN - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "ETH",  "name": "Ether (CME)",           "group": "Crypto", "market": "ETHER CASH SETTLED - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "SOL",  "name": "Solana (CME)",          "group": "Crypto", "market": "SOL - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},
    {"ticker": "XRP",  "name": "XRP (CME)",             "group": "Crypto", "market": "XRP - CHICAGO MERCANTILE EXCHANGE", "reports": FIN},

    # ── Metals ────────────────────────────────────────────────────────
    {"ticker": "GC",   "name": "Gold",                  "group": "Metals", "market": "GOLD - COMMODITY EXCHANGE INC.", "reports": COM},
    {"ticker": "SI",   "name": "Silver",                "group": "Metals", "market": "SILVER - COMMODITY EXCHANGE INC.", "reports": COM},
    {"ticker": "HG",   "name": "Copper",                "group": "Metals", "market": "COPPER- #1 - COMMODITY EXCHANGE INC.", "reports": COM},
    {"ticker": "PL",   "name": "Platinum",              "group": "Metals", "market": "PLATINUM - NEW YORK MERCANTILE EXCHANGE", "reports": COM},
    {"ticker": "PA",   "name": "Palladium",             "group": "Metals", "market": "PALLADIUM - NEW YORK MERCANTILE EXCHANGE", "reports": COM},

    # ── Energy ────────────────────────────────────────────────────────
    {"ticker": "CL",   "name": "WTI Crude Oil",         "group": "Energy", "market": "CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE", "reports": COM},
    {"ticker": "BZ",   "name": "Brent Crude (Last Day)","group": "Energy", "market": "BRENT LAST DAY - NEW YORK MERCANTILE EXCHANGE", "reports": COM},
    {"ticker": "NG",   "name": "Natural Gas (Henry Hub)","group": "Energy", "market": "HENRY HUB - NEW YORK MERCANTILE EXCHANGE", "reports": COM},
    {"ticker": "HO",   "name": "NY Harbor ULSD",        "group": "Energy", "market": "NY HARBOR ULSD - NEW YORK MERCANTILE EXCHANGE", "reports": COM},
    {"ticker": "RB",   "name": "RBOB Gasoline",         "group": "Energy", "market": "GASOLINE RBOB - NEW YORK MERCANTILE EXCHANGE", "reports": COM},

    # ── Agriculture ──────────────────────────────────────────────────
    {"ticker": "ZC",   "name": "Corn",                  "group": "Agriculture", "market": "CORN - CHICAGO BOARD OF TRADE", "reports": COM},
    {"ticker": "ZS",   "name": "Soybeans",              "group": "Agriculture", "market": "SOYBEANS - CHICAGO BOARD OF TRADE", "reports": COM},
    {"ticker": "ZW",   "name": "Wheat (SRW)",           "group": "Agriculture", "market": "WHEAT-SRW - CHICAGO BOARD OF TRADE", "reports": COM},
    {"ticker": "KE",   "name": "Wheat (HRW)",           "group": "Agriculture", "market": "WHEAT-HRW - CHICAGO BOARD OF TRADE", "reports": COM},
    {"ticker": "ZM",   "name": "Soybean Meal",          "group": "Agriculture", "market": "SOYBEAN MEAL - CHICAGO BOARD OF TRADE", "reports": COM},
    {"ticker": "ZL",   "name": "Soybean Oil",           "group": "Agriculture", "market": "SOYBEAN OIL - CHICAGO BOARD OF TRADE", "reports": COM},
    {"ticker": "CT",   "name": "Cotton No. 2",          "group": "Agriculture", "market": "COTTON NO. 2 - ICE FUTURES U.S.", "reports": COM},
    {"ticker": "KC",   "name": "Coffee C",              "group": "Agriculture", "market": "COFFEE C - ICE FUTURES U.S.", "reports": COM},
    {"ticker": "CC",   "name": "Cocoa",                 "group": "Agriculture", "market": "COCOA - ICE FUTURES U.S.", "reports": COM},
    {"ticker": "SB",   "name": "Sugar No. 11",          "group": "Agriculture", "market": "SUGAR NO. 11 - ICE FUTURES U.S.", "reports": COM},

    # ── Livestock ────────────────────────────────────────────────────
    {"ticker": "LE",   "name": "Live Cattle",           "group": "Livestock", "market": "LIVE CATTLE - CHICAGO MERCANTILE EXCHANGE", "reports": COM},
    {"ticker": "GF",   "name": "Feeder Cattle",         "group": "Livestock", "market": "FEEDER CATTLE - CHICAGO MERCANTILE EXCHANGE", "reports": COM},
    {"ticker": "HE",   "name": "Lean Hogs",             "group": "Livestock", "market": "LEAN HOGS - CHICAGO MERCANTILE EXCHANGE", "reports": COM},
]

# Display order for groups in the UI.
GROUP_ORDER = ["Equities", "FX", "Rates", "Crypto", "Metals", "Energy", "Agriculture", "Livestock"]
