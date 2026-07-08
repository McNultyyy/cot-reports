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

from instruments import INSTRUMENTS, GROUP_ORDER

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW_DIR = os.path.join(ROOT, "data", "raw")
OUT_DIR = os.path.join(ROOT, "docs", "data")

START_YEAR = int(os.environ.get("COT_START_YEAR", "2018"))
END_YEAR = datetime.now(timezone.utc).year
FORCE = os.environ.get("COT_FORCE") == "1"
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
    for lc, sc in cfg["categories"].values():
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
            return pd.read_csv(cache, low_memory=False)
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
    return out


def summarize(net: list[int], window: int = 52) -> dict:
    """Latest net, week-over-week change, and z-score of that change.

    Uses the classic 'large speculator' measure. z compares the newest weekly
    change against the mean/std of the trailing `window` weekly changes.
    """
    if len(net) < 3:
        return {"net": net[-1] if net else 0, "wow": 0, "z": 0.0}
    changes = [net[i] - net[i - 1] for i in range(1, len(net))]
    latest = changes[-1]
    hist = changes[-window:]
    mean = sum(hist) / len(hist)
    var = sum((c - mean) ** 2 for c in hist) / len(hist)
    std = var ** 0.5
    z = (latest - mean) / std if std > 0 else 0.0
    return {"net": net[-1], "wow": latest, "z": round(z, 2)}


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

        with open(os.path.join(OUT_DIR, f"{inst['ticker']}.json"), "w", encoding="utf-8") as f:
            json.dump(record, f, separators=(",", ":"))

        # Overview summary: classic large-speculator (legacy Non-Commercial) net.
        summary = {"net": 0, "wow": 0, "z": 0.0}
        if "legacy" in record["reports"]:
            summary = summarize(record["reports"]["legacy"]["categories"]["Non-Commercial"]["net"])

        index["instruments"].append({
            "ticker": inst["ticker"],
            "name": inst["name"],
            "group": inst["group"],
            "reports": matched,
            "latest_date": latest_date,
            "summary": summary,
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
