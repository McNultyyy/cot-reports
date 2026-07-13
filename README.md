# COT Reports

### 🔗 Live site: **https://mcnultyyy.github.io/cot-reports/**

An interactive, auto-updating visualisation of the U.S. CFTC **Commitments of
Traders** reports, served as a static site on GitHub Pages.

Every week a GitHub Action downloads the latest CFTC data, regenerates a compact
JSON dataset, and commits it. GitHub Pages serves the site straight from `docs/`,
so the charts refresh with no build step and no server.

## What it shows

- **All 53 markets** across Equities, FX, Rates, Crypto, Metals, Energy,
  Agriculture and Livestock.
- **Three CFTC report families:**
  - **Legacy** — Commercial / Non-Commercial / Non-Reportable net positions (every market).
  - **Traders in Financial Futures (TFF)** — Dealer / Asset Manager / Leveraged / Other (financials).
  - **Disaggregated** — Producer-Merchant / Swap Dealers / Managed Money / Other (commodities).
- **Per market:** net positions by category over time, the **COT index**
  (where net sits within its trailing range, 0–100; ≥80 / ≤20 flag crowded
  positioning), weekly-change z-scores (±2σ flags unusual repositioning), net as
  % of open interest, open interest, and a per-report-date snapshot table you can
  scrub through. A single **lookback** control (26 / 52 / 104 / 156 weeks) drives
  both the z-score and the COT index.
- **Overview grid:** speculator net + weekly move + z-score badge + a COT-index
  gauge (position in its 52-week range) for every market at a glance. History
  back to 2018.

Deep-link a market with `#TICKER` (e.g. `…/index.html#GC`) and force a theme with
`?theme=dark` / `?theme=light`.

The **COT index** (Williams range normalisation) scales the latest net position
against the min/max it held over the lookback window: `100 = top of range`,
`0 = bottom`. It's the standard first-glance gauge for spotting crowded or
washed-out positioning.

## How it works

```
scripts/
  instruments.py   catalogue of markets (edit to add/remove)
  build_data.py    download CFTC zips -> filter -> docs/data/*.json
docs/               <-- GitHub Pages root (zero-build static site)
  index.html
  styles.css
  app.js            fetches the JSON, draws charts with ECharts (CDN)
  data/
    index.json      market list + overview summaries
    <TICKER>.json   per-market time series
.github/workflows/update-cot.yml   weekly download + commit
```

Markets are matched to the CFTC files by **stable contract market code** (not
name), so history survives the contract renames CFTC made around 2021-22 and
Micro contracts are excluded automatically.

### Data sources (annual history files, CFTC)

| Report | URL pattern |
|---|---|
| Legacy | `cftc.gov/files/dea/history/deacot{year}.zip` |
| TFF | `cftc.gov/files/dea/history/fut_fin_txt_{year}.zip` |
| Disaggregated | `cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip` |

Raw downloads land in `data/raw/` (git-ignored). Only the processed JSON in
`docs/data/` is committed — that's the site's dataset.

## Run locally

```bash
pip install -r requirements.txt
python scripts/build_data.py          # writes docs/data/*.json
cd docs && python -m http.server 8899 # open http://localhost:8899
```

Environment overrides: `COT_START_YEAR` (default `2018`), `COT_FORCE=1` (ignore
the raw cache).

## Enable GitHub Pages

After pushing to GitHub:

1. **Settings → Pages → Build and deployment → Source: Deploy from a branch.**
2. Branch: `main`, folder: **`/docs`**. Save.
3. The site publishes at `https://<user>.github.io/<repo>/`.

The weekly Action (`update-cot.yml`) then keeps `docs/data/` current; each commit
it makes republishes the site automatically. You can also trigger it by hand from
the **Actions** tab.

## Adding or removing markets

Edit the `INSTRUMENTS` list in [`scripts/instruments.py`](scripts/instruments.py)
— set `market` to the exact CFTC market name and `reports` to `FIN`
(Legacy + TFF) for financials or `COM` (Legacy + Disaggregated) for commodities,
then re-run the builder. It prints a coverage report showing what matched.

## Data & disclaimer

Source: [U.S. CFTC Commitments of Traders](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)
(public domain). This project is for informational/research use only and is not
investment advice.
