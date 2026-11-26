#!/usr/bin/env python3
"""Inventory + quality checks for FX raw data. Builds derived/ (cut at 2026-10-31) and DATA_REPORT.md.
No returns / signals / correlations are computed here: data inventory and quality only.
Rows dated after CUTOFF are dropped right after parsing and never enter any statistic or output.
Usage: python3 check_fx.py
"""
import glob, logging, os, sys, zipfile
import numpy as np
import pandas as pd

BASE = os.path.expanduser("~/claude_master/w3/fx/data")
RAW = os.path.join(BASE, "raw")
DER = os.path.join(BASE, "derived")
CUTOFF = pd.Timestamp("2026-10-31")
FLAG = 0.015
FX = {  # ccy: (FRED id, quote) quote 'USDper' = USD per 1 ccy ; 'perUSD' = ccy per 1 USD
    "EUR": ("DEXUSEU", "USDper"), "JPY": ("DEXJPUS", "perUSD"), "GBP": ("DEXUSUK", "USDper"),
    "CHF": ("DEXSZUS", "perUSD"), "CAD": ("DEXCAUS", "perUSD"), "AUD": ("DEXUSAL", "USDper"),
    "NZD": ("DEXUSNZ", "USDper"), "NOK": ("DEXNOUS", "perUSD"), "SEK": ("DEXSDUS", "perUSD")}
RATE = {"USD": "US", "EUR": "EZ", "GBP": "GB", "JPY": "JP", "CHF": "CH", "CAD": "CA", "AUD": "AU", "NZD": "NZ",
        "NOK": "NO", "SEK": "SE"}
OUT = []


def md(s=""):
    OUT.append(s)


def table(df):
    cols = list(df.columns)
    md("| " + " | ".join(str(c) for c in cols) + " |")
    md("|" + "---|" * len(cols))
    for r in df.itertuples(index=False):
        md("| " + " | ".join(str(x) for x in r) + " |")
    md()


def load_fred(sid):
    raw = pd.read_csv(os.path.join(RAW, "FRED_%s.csv" % sid), dtype=str, keep_default_na=False)
    raw.columns = ["date", "v"]
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw[raw["date"] <= CUTOFF].copy()
    n_dot = int((raw["v"] == ".").sum())
    n_empty = int((raw["v"].str.strip() == "").sum())
    raw["x"] = pd.to_numeric(raw["v"], errors="coerce")
    return raw, n_dot, n_empty


def max_missing_run(s):
    m = s.isna().values.astype(int)
    best = cur = 0
    runs = 0
    for v in m:
        if v:
            cur += 1
        else:
            if cur > 3:
                runs += 1
            best = max(best, cur); cur = 0
    if cur > 3:
        runs += 1
    return max(best, cur), runs


def fred_section():
    md("## (a) FRED series (cut <= %s)" % CUTOFF.date())
    md("first/last = first/last row; last_valid = last non-missing value. missing = '.' + empty. "
       "runs>3 = number of runs of > 3 consecutive missing business-day rows (daily only).")
    md()
    rows, series = [], {}
    ids = [v[0] for v in FX.values()] + ["VIXCLS"] + ["IR3TIB01%sM156N" % c for c in RATE.values()]
    for sid in ids:
        d, n_dot, n_empty = load_fred(sid)
        d[["date", "v"]].to_csv(os.path.join(DER, "FRED_%s.csv" % sid), index=False)
        dd = d["date"].diff().dt.days.median()
        freq = "daily(business)" if dd <= 3 else ("monthly" if 27 <= dd <= 31 else "other(%s)" % dd)
        mx, runs = max_missing_run(d["x"]) if freq.startswith("daily") else ("-", "-")
        v = d.dropna(subset=["x"])
        rows.append(dict(id=sid, first=d["date"].min().date(), last=d["date"].max().date(),
                         first_valid=v["date"].min().date(), last_valid=v["date"].max().date(), n_rows=len(d),
                         n_valid=len(v), missing_dot=n_dot, missing_empty=n_empty, freq=freq,
                         max_missing_run=mx, runs_gt3=runs))
        series[sid] = d.set_index("date")["x"]
    table(pd.DataFrame(rows))
    return series


def universe_section(series):
    md("## (b) Universe per month (G1 rule): ccy valid in month m if rate(m-1) present AND FRED price has >=1 valid obs "
       "in month m AND no run of >3 consecutive missing business days inside month m; USD rate(m-1) missing => month empty; "
       "EUR only from 1999-01.")
    md()
    months = pd.period_range("1994-01", "2026-10", freq="M")
    rec = []
    for m in months:
        prev = (m - 1).to_timestamp()
        usd = series["IR3TIB01USM156N"].get(prev, np.nan)
        valid = []
        for c, (sid, _) in FX.items():
            if c == "EUR" and m < pd.Period("1999-01", "M"):
                continue
            r = series["IR3TIB01%sM156N" % RATE[c]].get(prev, np.nan)
            px = series[sid][(series[sid].index >= m.to_timestamp()) & (series[sid].index <= m.to_timestamp(how="end"))]
            ok_px = px.notna().any() and (max_missing_run(px)[0] <= 3)
            if pd.notna(r) and ok_px and pd.notna(usd):
                valid.append(c)
        rec.append(dict(month=str(m), year=m.year, n=len(valid), ccys=",".join(valid), usd_rate=pd.notna(usd)))
    u = pd.DataFrame(rec)
    u.to_csv(os.path.join(DER, "universe_by_month.csv"), index=False)
    md("Per year (min / median / max ccys per month; months with USD rate missing; ccy-months by ccy):")
    md()
    yr = []
    for y, g in u.groupby("year"):
        cnt = {c: int(g["ccys"].str.split(",").apply(lambda L: c in L).sum()) for c in FX}
        yr.append(dict(year=y, months=len(g), min=g["n"].min(), med=g["n"].median(), max=g["n"].max(),
                       usd_missing=int((~g["usd_rate"]).sum()), **cnt))
    table(pd.DataFrame(yr))
    md("Per period:")
    md()
    per = []
    for name, a, b in [("1994-98", 1994, 1998), ("1999-2001", 1999, 2001), ("2002-05", 2002, 2005),
                       ("2006-19", 2006, 2019), ("2020-26(10)", 2020, 2026)]:
        g = u[(u.year >= a) & (u.year <= b)]
        per.append(dict(period=name, months=len(g), min=g["n"].min(), med=g["n"].median(), max=g["n"].max(),
                        months_lt4=int((g["n"] < 4).sum()), months_lt6=int((g["n"] < 6).sum())))
    table(pd.DataFrame(per))
    # months where any ccy has price but no rate (diagnose which input is missing)
    md("Months where a ccy is excluded only because rate(m-1) missing (first..last such month):")
    md()
    miss = []
    for c in FX:
        s = series["IR3TIB01%sM156N" % RATE[c]]
        bad = [str(m) for m in months if pd.isna(s.get((m - 1).to_timestamp(), np.nan))
               and not (c == "EUR" and m < pd.Period("1999-01", "M"))]
        miss.append(dict(ccy=c, n_months_no_rate=len(bad), first=bad[0] if bad else "-", last=bad[-1] if bad else "-"))
    table(pd.DataFrame(miss))
    md("Months with USD rate(m-1) missing (whole month out): " + ", ".join(u.loc[~u["usd_rate"], "month"]))
    md()


def ecb_section(series):
    md("## (c) FRED vs ECB cross-check (1999+), flag |log FRED - log ECB| > 1.5%")
    md("ECB ccy-per-USD = (EUR/ccy)/(EUR/USD). FRED USD-per-ccy series (DEXUSEU, DEXUSUK, DEXUSAL, DEXUSNZ) inverted "
       "to ccy-per-USD before compare; EUR compared as USD per EUR (DEXUSEU vs ECB USD column). Only dates where both valid.")
    md()
    z = zipfile.ZipFile(os.path.join(RAW, "eurofxref-hist.zip"))
    e = pd.read_csv(z.open("eurofxref-hist.csv"), na_values=["N/A"])
    e = e.loc[:, [c for c in e.columns if not c.startswith("Unnamed")]]
    e["Date"] = pd.to_datetime(e["Date"])
    e = e[e["Date"] <= CUTOFF].sort_values("Date")
    e[["Date"] + [c for c in ["USD", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD", "NOK", "SEK"]]].to_csv(
        os.path.join(DER, "ECB_eurofxref_cut.csv"), index=False)
    e = e.set_index("Date")
    md("ECB file: %s .. %s, %d rows (cut)." % (e.index.min().date(), e.index.max().date(), len(e)))
    md()
    rows, flagged, top = [], [], []
    for c, (sid, q) in FX.items():
        f = series[sid]
        if c == "EUR":
            fe, ee = np.log(f), np.log(e["USD"])
        else:
            fe = np.log(f) if q == "perUSD" else -np.log(f)
            ee = np.log(e[c] / e["USD"])
        j = pd.concat([fe.rename("f"), ee.rename("e")], axis=1).dropna()
        j = j[j.index >= "1999-01-01"]
        j["d"] = (j["f"] - j["e"]).abs()
        j["flag"] = j["d"] > FLAG
        for y, g in j.groupby(j.index.year):
            rate = g["flag"].mean()
            rows.append(dict(pair=c, year=y, n=len(g), n_flag=int(g["flag"].sum()), pct=round(100 * rate, 2)))
            if rate > 0.005:
                flagged.append(dict(pair=c, year=y, n=len(g), n_flag=int(g["flag"].sum()), pct=round(100 * rate, 2),
                                    max_abs_logdiff_pct=round(100 * g["d"].max(), 2)))
        for dt, r in j.nlargest(3, "d").iterrows():
            top.append(dict(pair=c, date=dt.date(), abs_logdiff_pct=round(100 * r["d"], 2)))
    r = pd.DataFrame(rows)
    r.to_csv(os.path.join(DER, "fred_vs_ecb_flags_by_pair_year.csv"), index=False)
    md("Overall flag rate by pair:")
    md()
    t = r.groupby("pair")[["n", "n_flag"]].sum()
    t["pct"] = (100 * t["n_flag"] / t["n"]).round(3)
    table(t.reset_index())
    md("Pair-years with > 0.5%% days flagged (MASTER review before DEV): %d" % len(flagged))
    md()
    if flagged:
        table(pd.DataFrame(flagged))
    md("Top-3 largest abs log diffs per pair (for manual look):")
    md()
    table(pd.DataFrame(top))
    md("Full pair x year table: derived/fred_vs_ecb_flags_by_pair_year.csv")
    md()


KEYS = ["EURO FX", "BRITISH POUND", "CANADIAN DOLLAR", "SWISS FRANC", "AUSTRALIAN DOLLAR", "JAPANESE YEN",
        "NEW ZEALAND", "ZEALAND", "NZ DOLLAR", "STERLING", "POUND", "DEUTSCHE", "MARK", "FRENCH", "EURODOLLAR", "U.S. DOLLAR INDEX"]


COTCHK = []


def read_cot(pattern, name_col, date_col, code_col, cols, yymmdd_col):
    frames = []
    for f in sorted(glob.glob(os.path.join(RAW, pattern))):
        z = zipfile.ZipFile(f)
        for n in z.namelist():
            d = pd.read_csv(z.open(n), usecols=[name_col, date_col, code_col, yymmdd_col] + cols,
                            dtype={code_col: str, name_col: str}, low_memory=False, encoding="latin-1")
            d["src"] = os.path.basename(f)
            frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    raw = d[date_col].astype(str).str.strip()
    dt = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce")
    m = dt.isna()
    dt[m] = pd.to_datetime(raw[m], format="%m/%d/%Y %I:%M:%S %p", errors="coerce")
    if dt.isna().any():
        raise SystemExit("unparsed COT dates: %s" % raw[dt.isna()].unique()[:5])
    yy = pd.to_datetime(d[yymmdd_col].astype(str).str.strip().str.zfill(6), format="%y%m%d", errors="coerce")
    COTCHK.append((pattern, int(m.sum()), int((yy != dt).sum())))
    d[date_col] = dt
    d = d[d[date_col] <= CUTOFF].copy()
    d[code_col] = d[code_col].str.strip()
    d[name_col] = d[name_col].str.strip()
    return d


def cot_inventory(d, label, name_col, date_col, code_col, cols, outname):
    up = d[name_col].str.upper()
    sel = up.apply(lambda s: any(k in s for k in KEYS)) & (up.str.contains("CHICAGO MERCANTILE") |
                                                          up.str.contains("INTERNATIONAL MONETARY") | up.str.contains("IMM"))
    fx = d[sel].copy()
    fx = fx[~fx[name_col].str.upper().str.contains("EURODOLLAR|E-MINI|MICRO|CROSS| / |/ ", regex=True)]
    rows = []
    for (code, nm), g in fx.groupby([code_col, name_col]):
        rows.append(dict(code=code, name=nm, first=g[date_col].min().date(), last=g[date_col].max().date(),
                         n_rows=len(g), n_dates=g[date_col].nunique()))
    md("### %s: code x name (FX-like CME contracts, rows <= cutoff)" % label)
    md()
    table(pd.DataFrame(rows).sort_values(["code", "first"]))
    fx.to_csv(os.path.join(DER, outname), index=False)
    return fx


def cot_quality(fx, label, date_col, code_col, codes, since=None):
    if since is not None:
        fx = fx[fx[date_col] >= since]
    md("### %s: per-code quality for prereg codes (ALL rows of the code, any name%s)" % (label, "" if since is None else ", dates >= %s" % since))
    md()
    rows = []
    for c, ccy in codes.items():
        g = fx[fx[code_col] == c]
        if g.empty:
            rows.append(dict(code=c, ccy=ccy, names="NOT FOUND")); continue
        dts = g[date_col].sort_values()
        dup = int(g.duplicated([code_col, date_col]).sum())
        u = dts.drop_duplicates()
        gaps = u.diff().dt.days.dropna()
        exp = pd.date_range(u.min(), u.max(), freq="7D")
        nontue = int((u.dt.dayofweek != 1).sum())
        big = [(str(a.date()), int(b)) for a, b in zip(u[1:][gaps.values > 7], gaps[gaps > 7])]
        rows.append(dict(code=c, ccy=ccy, names=" | ".join(sorted(g["_name"].unique())), first=u.min().date(),
                         last=u.max().date(), n_weeks=len(u), duplicate_rows=dup, weeks_missing_vs_7d_grid=
                         max(0, len(exp) - len(u)), non_tuesday_dates=nontue,
                         gaps_gt7d=";".join("%s(+%dd)" % x for x in big[:12]) + (" ..." if len(big) > 12 else "")))
    table(pd.DataFrame(rows))


def cot_section():
    md("## (d) CFTC COT")
    codes = {"099741": "EUR", "096742": "GBP", "090741": "CAD", "092741": "CHF", "232741": "AUD", "097741": "JPY",
             "112741": "NZD"}
    lc = ["Open Interest (All)", "Noncommercial Positions-Long (All)", "Noncommercial Positions-Short (All)",
          "Noncommercial Positions-Spreading (All)"]
    L = read_cot("deacot*.zip", "Market and Exchange Names", "As of Date in Form YYYY-MM-DD",
                 "CFTC Contract Market Code", lc, "As of Date in Form YYMMDD")
    md("Legacy futures-only exact columns used: `Market and Exchange Names`, `As of Date in Form YYYY-MM-DD`, "
       "`CFTC Contract Market Code`, `Open Interest (All)`, `Noncommercial Positions-Long (All)`, "
       "`Noncommercial Positions-Short (All)` (also `Noncommercial Positions-Spreading (All)`). "
       "Note header `\" Total Reportable Positions-Long (All)\"` has a leading space in raw file.")
    md()
    L["_name"] = L["Market and Exchange Names"]
    fxL = cot_inventory(L, "Legacy", "Market and Exchange Names", "As of Date in Form YYYY-MM-DD",
                        "CFTC Contract Market Code", lc, "cot_legacy_fx_cut.csv")
    cot_quality(L, "Legacy", "As of Date in Form YYYY-MM-DD", "CFTC Contract Market Code", codes, "1993-01-01")
    cot_quality(L, "Legacy", "As of Date in Form YYYY-MM-DD", "CFTC Contract Market Code", codes, "1999-01-01")
    tc = ["Open_Interest_All", "Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All",
          "Asset_Mgr_Positions_Long_All", "Asset_Mgr_Positions_Short_All"]
    T = read_cot("f*_txt_*.zip", "Market_and_Exchange_Names", "Report_Date_as_YYYY-MM-DD",
                 "CFTC_Contract_Market_Code", tc, "As_of_Date_In_Form_YYMMDD")
    md("TFF futures-only exact columns used: `Market_and_Exchange_Names`, `Report_Date_as_YYYY-MM-DD` (NOTE: not "
       "`Report_Date_as_MM_DD_YYYY` as in prereg), `CFTC_Contract_Market_Code`, `Open_Interest_All`, "
       "`Lev_Money_Positions_Long_All`, `Lev_Money_Positions_Short_All`, `Asset_Mgr_Positions_Long_All`, "
       "`Asset_Mgr_Positions_Short_All`.")
    md()
    T["_name"] = T["Market_and_Exchange_Names"]
    fxT = cot_inventory(T, "TFF", "Market_and_Exchange_Names", "Report_Date_as_YYYY-MM-DD",
                        "CFTC_Contract_Market_Code", tc, "cot_tff_fx_cut.csv")
    md("Date parse check (file pattern, rows in M/D/YYYY h:mm:ss AM format, rows where date != YYMMDD column): %s" % COTCHK)
    md()
    cot_quality(T, "TFF", "Report_Date_as_YYYY-MM-DD", "CFTC_Contract_Market_Code", codes)


def main():
    os.makedirs(DER, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(os.path.join(BASE, "check.log")), logging.StreamHandler(sys.stderr)])
    md("# DATA_REPORT - FX raw data inventory (G1 carry, G3 COT)")
    md("Generated by code/check_fx.py. Cutoff %s: rows after cutoff dropped at parse. No returns/signals computed." %
       CUTOFF.date())
    md()
    logging.info("FRED"); s = fred_section()
    logging.info("universe"); universe_section(s)
    logging.info("ECB"); ecb_section(s)
    logging.info("COT"); cot_section()
    man = os.path.join(BASE, "REPORT_NOTES_MANUAL.md")
    if os.path.exists(man):
        md(open(man).read())
    with open(os.path.join(BASE, "DATA_REPORT.md"), "w") as f:
        f.write("\n".join(OUT) + "\n")
    logging.info("wrote DATA_REPORT.md (%d lines)", len(OUT))


if __name__ == "__main__":
    main()
