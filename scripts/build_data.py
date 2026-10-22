"""Download CFTC Commitments of Traders data and emit the JSON the site reads.

For every year in [START_YEAR, current year] this downloads three annual report
families from cftc.gov, filters them to the markets listed in instruments.py,
and writes one compact JSON file per instrument plus an index.json.

  Legacy        deacot{year}.zip          -> annual.txt   (all markets)
  TFF           fut_fin_txt_{year}.zip     -> FinFutYY.txt (financials)
  Disaggregated fut_disagg_txt_{year}.zip  -> f_year.txt   (commodities)

Raw downloads are cached under data/raw/ (git-ignored). The generated JSON in
docs/data/ is the committed artefact that GitHub Pages serves.

Run:  python scripts/build_data.py
Env:  COT_START_YEAR (default 2018)   COT_FORCE=1 to ignore the raw cache
"""
from __future__ import annotations

import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone

import pandas as pd
import requests

from instruments import FOCUS, GROUP_ORDER, INSTRUMENTS, PRICE_SYMBOLS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW_DIR = os.path.join(ROOT, "data", "raw")
OUT_DIR = os.path.join(ROOT, "docs", "data")

START_YEAR = int(os.environ.get("COT_START_YEAR", "2018"))
END_YEAR = datetime.now(timezone.utc).year
FORCE = os.environ.get("COT_FORCE") == "1"

# Trailing window (weeks) for the overview summary's z-score and COT index.
SUMMARY_WINDOW = 52
UA = {"User-Agent": "cot-reports (github pages data builder)"}

BASE = "https://www.cftc.gov/files/dea/history"

# ── Per-report configuration ──────────────────────────────────────────────
# url template, market-name column, date column, open-interest column, and the
# category -> (long_col, short_col) mapping for that report family.
REPORTS = {
    "legacy": {
        "url": BASE + "/deacot{year}.zip",
        "market_col": "Market and Exchange Names",
        "code_col": "CFTC Contract Market Code",
        "date_col": "As of Date in Form YYYY-MM-DD",
        "oi_col": "Open Interest (All)",
        "categories": {
            "Commercial":    ("Commercial Positions-Long (All)",    "Commercial Positions-Short (All)"),
            "Non-Commercial": ("Noncommercial Positions-Long (All)", "Noncommercial Positions-Short (All)"),
            "Non-Reportable": ("Nonreportable Positions-Long (All)", "Nonreportable Positions-Short (All)"),
        },
        # Number of reporting traders on each side (no counts exist for Non-Reportable).
        "traders": {
            "Commercial":     ("Traders-Commercial-Long (All)",    "Traders-Commercial-Short (All)"),
            "Non-Commercial": ("Traders-Noncommercial-Long (All)", "Traders-Noncommercial-Short (All)"),
        },
    },
    "tff": {
        "url": BASE + "/fut_fin_txt_{year}.zip",
        "market_col": "Market_and_Exchange_Names",
        "code_col": "CFTC_Contract_Market_Code",
        "date_col": "Report_Date_as_YYYY-MM-DD",
        "oi_col": "Open_Interest_All",
        "categories": {
            "Dealer":        ("Dealer_Positions_Long_All",    "Dealer_Positions_Short_All"),
            "Asset Manager": ("Asset_Mgr_Positions_Long_All", "Asset_Mgr_Positions_Short_All"),
            "Leveraged":     ("Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All"),
            "Other":         ("Other_Rept_Positions_Long_All", "Other_Rept_Positions_Short_All"),
        },
    },
    "disagg": {
        "url": BASE + "/fut_disagg_txt_{year}.zip",
        "market_col": "Market_and_Exchange_Names",
        "code_col": "CFTC_Contract_Market_Code",
        "date_col": "Report_Date_as_YYYY-MM-DD",
        "oi_col": "Open_Interest_All",
        "categories": {
            "Producer/Merchant": ("Prod_Merc_Positions_Long_All", "Prod_Merc_Positions_Short_All"),
            "Swap Dealers":      ("Swap_Positions_Long_All",      "Swap__Positions_Short_All"),  # note: double underscore in source
            "Managed Money":     ("M_Money_Positions_Long_All",   "M_Money_Positions_Short_All"),
            "Other":             ("Other_Rept_Positions_Long_All", "Other_Rept_Positions_Short_All"),
        },
    },
}


def _needed_cols(cfg):
    cols = [cfg["market_col"], cfg["code_col"], cfg["date_col"], cfg["oi_col"]]
    for lc, sc in [*cfg["categories"].values(), *cfg.get("traders", {}).values()]:
        cols += [lc, sc]
    return cols


def download_year(report: str, year: int) -> pd.DataFrame | None:
    """Return a DataFrame of one report/year, using the raw cache when possible."""
    cfg = REPORTS[report]
    os.makedirs(RAW_DIR, exist_ok=True)
    cache = os.path.join(RAW_DIR, f"{report}_{year}.csv")

    if os.path.exists(cache) and not FORCE and year < END_YEAR:
        # Past years never change once published -> trust the cache.
        try:
            df = pd.read_csv(cache, low_memory=False)
            # A cache written before a column was added to the config is stale.
            if set(_needed_cols(cfg)) <= set(df.columns):
                return df
        except Exception:
            pass

    url = cfg["url"].format(year=year)
    try:
        r = requests.get(url, headers=UA, timeout=90)
    except requests.RequestException as e:
        print(f"  ! {report} {year}: request failed ({e})")
        return None
    if not r.ok:
        print(f"  ! {report} {year}: HTTP {r.status_code}")
        return None

    z = zipfile.ZipFile(io.BytesIO(r.content))
    inner = [n for n in z.namelist() if n.lower().endswith((".txt", ".csv"))][0]
    df = pd.read_csv(io.BytesIO(z.read(inner)), low_memory=False)
    df.columns = [c.strip() for c in df.columns]

    keep = [c for c in _needed_cols(cfg) if c in df.columns]
    df = df[keep].copy()
    df.to_csv(cache, index=False)
    return df


def load_report(report: str) -> pd.DataFrame:
    frames = []
    for year in range(START_YEAR, END_YEAR + 1):
        df = download_year(report, year)
        if df is not None and len(df):
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out[REPORTS[report]["market_col"]] = out[REPORTS[report]["market_col"]].astype(str).str.strip()
    return out


def series_for(df: pd.DataFrame, cfg: dict, market: str) -> dict | None:
    """Extract the per-category long/short/net time series for one market.

    We resolve the market's stable CFTC contract code from its current name,
    then select every row carrying that code. This recovers history from years
    when the contract had a different name (CFTC renamed several around 2021-22)
    and cleanly excludes look-alikes such as the Micro contracts, which carry
    their own distinct codes.
    """
    mcol, ccol = cfg["market_col"], cfg["code_col"]
    codes = df.loc[df[mcol] == market, ccol].astype(str).str.strip().unique()
    codes = [c for c in codes if c and c.lower() != "nan"]
    if not codes:
        return None
    sub = df[df[ccol].astype(str).str.strip().isin(codes)]
    if sub.empty:
        return None

    sub = sub.copy()
    sub["_date"] = pd.to_datetime(sub[cfg["date_col"]], errors="coerce")
    sub = sub.dropna(subset=["_date"]).sort_values("_date")
    sub = sub.drop_duplicates(subset=["_date"], keep="last")

    def col(name):
        return pd.to_numeric(sub[name], errors="coerce").fillna(0).round().astype("int64").tolist()

    dates = [d.strftime("%Y-%m-%d") for d in sub["_date"]]
    out = {"dates": dates, "oi": col(cfg["oi_col"]), "categories": {}}
    for cat, (lc, sc) in cfg["categories"].items():
        longs, shorts = col(lc), col(sc)
        nets = [l - s for l, s in zip(longs, shorts)]
        out["categories"][cat] = {"long": longs, "short": shorts, "net": nets}
    if "traders" in cfg:
        out["traders"] = {}
        for cat, (lc, sc) in cfg["traders"].items():
            if lc in sub.columns and sc in sub.columns:
                longs, shorts = col(lc), col(sc)
                out["traders"][cat] = {"long": longs, "short": shorts, "net": [l - s for l, s in zip(longs, shorts)]}
    return out


def fetch_closes(symbol: str) -> pd.Series | None:
    """Daily closes for a Yahoo Finance symbol, or None if the request fails."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"period1": int(datetime(START_YEAR, 1, 1, tzinfo=timezone.utc).timestamp()),
              "period2": int(datetime.now(timezone.utc).timestamp()), "interval": "1d"}
    try:
        r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0 (cot-reports)"}, timeout=60)
        res = r.json()["chart"]["result"][0]
        closes = pd.Series(res["indicators"]["quote"][0]["close"],
                           index=pd.to_datetime(res["timestamp"], unit="s").normalize(), dtype="float64")
    except Exception as e:
        print(f"  ! price {symbol}: {e}")
        return None
    closes = closes.dropna()
    return closes[~closes.index.duplicated(keep="last")] if len(closes) > 1 else None


def price_for(symbol: str, dates: list[str], previous: dict | None) -> dict | None:
    """Close on (or the last trading day before) each report date.

    Falls back to the price block already published for this market when the
    download fails, so a Yahoo outage never wipes the line from the site.
    """
    closes = fetch_closes(symbol)
    if closes is None:
        return previous if previous and previous.get("symbol") == symbol else None
    aligned = closes.reindex(pd.to_datetime(dates), method="ffill")
    return {"symbol": symbol, "dates": dates,
            "close": [None if pd.isna(v) else round(float(v), 6) for v in aligned]}


def cot_index(net: list[int], window: int = SUMMARY_WINDOW) -> float | None:
    """COT Index: where the latest net sits within its trailing `window` range.

    Scales the current net position 0-100 against the min/max it held over the
    lookback window (the classic Williams range normalisation). 100 = top of the
    range (most bullish that category has been positioned); 0 = bottom. Readings
    >=80 / <=20 flag crowded positioning. Returns None if there is too little
    history, and 50.0 for a perfectly flat range.
    """
    if len(net) < 2:
        return None
    win = net[-window:]
    lo, hi = min(win), max(win)
    if hi == lo:
        return 50.0
    return round((net[-1] - lo) / (hi - lo) * 100, 1)


def summarize(net: list[int], window: int = SUMMARY_WINDOW) -> dict:
    """Latest net, week-over-week change, z-score of that change, and COT index.

    Uses the classic 'large speculator' measure. z compares the newest weekly
    change against the mean/std of the trailing `window` weekly changes; the COT
    index compares the latest net against the same window's min/max range.
    """
    ci = cot_index(net, window)
    if len(net) < 3:
        return {"net": net[-1] if net else 0, "wow": 0, "z": 0.0, "cot_index": ci}
    changes = [net[i] - net[i - 1] for i in range(1, len(net))]
    latest = changes[-1]
    hist = changes[-window:]
    mean = sum(hist) / len(hist)
    var = sum((c - mean) ** 2 for c in hist) / len(hist)
    std = var ** 0.5
    z = (latest - mean) / std if std > 0 else 0.0
    return {"net": net[-1], "wow": latest, "z": round(z, 2), "cot_index": ci}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Building COT data {START_YEAR}-{END_YEAR}")

    loaded = {}
    for report in REPORTS:
        print(f"Loading {report} ...")
        loaded[report] = load_report(report)
        n = 0 if loaded[report].empty else len(loaded[report])
        print(f"  {report}: {n:,} rows")

    index = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "U.S. CFTC Commitments of Traders",
        "start_year": START_YEAR,
        "summary_window": SUMMARY_WINDOW,
        "group_order": GROUP_ORDER,
        "instruments": [],
    }
    latest_overall = ""

    for inst in INSTRUMENTS:
        record = {
            "ticker": inst["ticker"],
            "name": inst["name"],
            "group": inst["group"],
            "market": inst["market"],
            "reports": {},
            "updated": index["generated"],
        }
        matched = []
        latest_date = ""
        for report in inst["reports"]:
            df = loaded.get(report)
            if df is None or df.empty:
                continue
            s = series_for(df, REPORTS[report], inst["market"])
            if s and s["dates"]:
                record["reports"][report] = s
                matched.append(report)
                latest_date = max(latest_date, s["dates"][-1])

        status = ",".join(matched) if matched else "NO MATCH"
        print(f"  {inst['ticker']:5s} {inst['group']:12s} -> {status}")
        if not matched:
            continue

        out_path = os.path.join(OUT_DIR, f"{inst['ticker']}.json")
        focus = FOCUS.get(inst["ticker"])
        if focus:
            record["focus"] = focus
        symbol = PRICE_SYMBOLS.get(inst["ticker"])
        if symbol:
            previous = None
            if os.path.exists(out_path):
                try:
                    with open(out_path, encoding="utf-8") as f:
                        previous = json.load(f).get("price")
                except (OSError, ValueError):
                    pass
            base = record["reports"].get("legacy") or record["reports"][matched[0]]
            price = price_for(symbol, base["dates"], previous)
            if price:
                record["price"] = price

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, separators=(",", ":"))

        # Overview summary: classic large-speculator (legacy Non-Commercial) net,
        # unless the market sets its own focus category for the Legacy report.
        summary = {"net": 0, "wow": 0, "z": 0.0, "cot_index": None}
        summary_cat = (focus or {}).get("legacy", "Non-Commercial")
        if "legacy" in record["reports"]:
            summary = summarize(record["reports"]["legacy"]["categories"][summary_cat]["net"])

        index["instruments"].append({
            "ticker": inst["ticker"],
            "name": inst["name"],
            "group": inst["group"],
            "reports": matched,
            "latest_date": latest_date,
            "summary": summary,
            "summary_cat": summary_cat,
        })
        latest_overall = max(latest_overall, latest_date)

    index["latest_report_date"] = latest_overall
    with open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    print(f"\nWrote {len(index['instruments'])} instruments to {OUT_DIR}")
    print(f"Latest report date: {latest_overall}")
    if not index["instruments"]:
        sys.exit("No instruments matched — aborting.")


if __name__ == "__main__":
    main()
