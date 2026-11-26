#!/usr/bin/env python3
"""G3 loader (PREREG_FX_G3 + ERRATA1 H3/H6).
COT Legacy (Non-commercial) + TFF (Leveraged Funds, Asset Manager) for 7 CME FX contracts matched by CODE + name family,
FRED DEX* prices converted to USD per 1 unit of foreign ccy (LONG ccy vs USD return = P1/P0 - 1), OECD 3M rates for swap.
HARD CUTOFF: rows dated > cutoff are skipped while streaming (never stored). cutoff >= 2020-01-01 needs --holdout I_HAVE_OWNER_OK.
"""
import argparse
import csv
import logging
import os
import re

import numpy as np
import pandas as pd

LOG = logging.getLogger("g3.load")
DATA_DIR = os.path.expanduser("~/claude_master/w3/fx/data")
DEFAULT_CUTOFF = "2019-12-31"
HOLDOUT_START = pd.Timestamp("2020-01-01")
HOLDOUT_TOKEN = "I_HAVE_OWNER_OK"
GROUPS = ["LevFunds_TFF", "AssetMgr_TFF", "NonComm_LEG"]
_EXCH = r" - (INTERNATIONAL MONETARY MARKET|CHICAGO MERCANTILE EXCHANGE)$"
# ccy: CFTC code, name family regex (ERRATA1 H3), FRED series, FRED quote convention, OECD rate id, pip, round-trip pips (G3 sec 5)
# round-trip cost fraction = max(rt_pips * pip / quote, rt_min_frac); ERRATA2 J1: rt_min_frac = 3 bp except EURUSD (0.8 pip only)
CCY = {
    "EUR": dict(code="099741", fam=r"EURO FX", fred="DEXUSEU", quote="XXXUSD", rate="EZ", pip=1e-4, rt_pips=0.8, rt_min_frac=0.0,
                min_date="1999-01-01"),
    "GBP": dict(code="096742", fam=r"(BRITISH POUND STERLING- NEW|BRITISH POUND STERLING|BRITISH POUND|POUND STERLING)",
                fred="DEXUSUK", quote="XXXUSD", rate="GB", pip=1e-4, rt_pips=3.0),
    "CAD": dict(code="090741", fam=r"CANADIAN DOLLAR", fred="DEXCAUS", quote="USDXXX", rate="CA", pip=1e-4, rt_pips=3.0),
    "CHF": dict(code="092741", fam=r"SWISS FRANC", fred="DEXSZUS", quote="USDXXX", rate="CH", pip=1e-4, rt_pips=3.0),
    "AUD": dict(code="232741", fam=r"AUSTRALIAN DOLLARS?", fred="DEXUSAL", quote="XXXUSD", rate="AU", pip=1e-4, rt_pips=3.0),
    "JPY": dict(code="097741", fam=r"JAPANESE YEN", fred="DEXJPUS", quote="USDXXX", rate="JP", pip=1e-2, rt_pips=3.0),
    "NZD": dict(code="112741", fam=r"(NEW ZEALAND DOLLARS?|NZ DOLLAR)", fred="DEXUSNZ", quote="XXXUSD", rate="NZ", pip=1e-4,
                rt_pips=3.0),
}
for _c in CCY:
    CCY[_c].setdefault("rt_min_frac", 3e-4)
CCYS = list(CCY)
FRED_QUOTE = {v["fred"]: v["quote"] for v in CCY.values()}
CODE2CCY = {v["code"]: k for k, v in CCY.items()}
LEG_COLS = dict(name="Market and Exchange Names", date="As of Date in Form YYYY-MM-DD", code="CFTC Contract Market Code",
                oi="Open Interest (All)", NonComm_LEG=("Noncommercial Positions-Long (All)", "Noncommercial Positions-Short (All)"))
TFF_COLS = dict(name="Market_and_Exchange_Names", date="Report_Date_as_YYYY-MM-DD", code="CFTC_Contract_Market_Code",
                oi="Open_Interest_All", LevFunds_TFF=("Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All"),
                AssetMgr_TFF=("Asset_Mgr_Positions_Long_All", "Asset_Mgr_Positions_Short_All"))


def check_cutoff(cutoff, holdout=None):
    c = pd.Timestamp(cutoff)
    if c >= HOLDOUT_START and holdout != HOLDOUT_TOKEN:
        raise PermissionError("cutoff %s touches HOLDOUT (>= 2020-01-01); requires --holdout %s (owner only)"
                              % (c.date(), HOLDOUT_TOKEN))
    return c


def to_usd_per_ccy(series_id, v):
    """FRED quote -> USD per 1 unit of foreign ccy. XXXUSD series (DEXUSEU/UK/AL/NZ) are already USD per ccy;
    USDXXX series (DEXJPUS/SZUS/CAUS) are ccy per USD -> invert."""
    q = FRED_QUOTE[series_id]
    v = np.asarray(v, dtype=float)
    return v if q == "XXXUSD" else 1.0 / v


def name_ok(ccy, name):
    return re.match("^" + CCY[ccy]["fam"] + _EXCH, name) is not None


def _norm_name(s):
    return re.sub(r"\s+", " ", (s or "").strip().upper())


def _parse_date(s):
    s = (s or "").strip()
    if "/" in s:
        return pd.Timestamp(pd.to_datetime(s.split(" ")[0], format="%m/%d/%Y"))
    return pd.Timestamp(s[:10])


def read_series(path, cutoff):
    """2-column CSV (date, value); '' or '.' = missing. Rows > cutoff skipped."""
    d, v = [], []
    with open(path, newline="") as fh:
        r = csv.reader(fh)
        next(r)
        for row in r:
            if not row:
                continue
            t = pd.Timestamp(row[0][:10])
            if t > cutoff:
                continue
            x = row[1].strip() if len(row) > 1 else ""
            d.append(t)
            v.append(float(x) if x not in ("", ".") else np.nan)
    return pd.Series(v, index=pd.DatetimeIndex(d), dtype=float).sort_index()


def read_cot(path, kind, cutoff):
    cols = LEG_COLS if kind == "LEG" else TFF_COLS
    groups = [g for g in GROUPS if g in cols]
    keep, dropped = [], {}
    with open(path, newline="") as fh:
        r = csv.DictReader(fh)
        r.fieldnames = [f.strip() for f in r.fieldnames]
        for row in r:
            row = {k.strip() if k else k: v for k, v in row.items()}
            t = _parse_date(row[cols["date"]])
            if t > cutoff:
                continue  # HOLDOUT / beyond cutoff: never stored
            code = row[cols["code"]].strip()
            if code not in CODE2CCY:
                continue
            ccy = CODE2CCY[code]
            name = _norm_name(row[cols["name"]])
            mind = CCY[ccy].get("min_date")
            if not name_ok(ccy, name) or (mind and t < pd.Timestamp(mind)):
                dropped[(code, name)] = dropped.get((code, name), 0) + 1
                continue
            rec = dict(date=t, ccy=ccy, code=code, name=name, oi=float(row[cols["oi"]]))
            for g in groups:
                rec[g + "_L"] = float(row[cols[g][0]])
                rec[g + "_S"] = float(row[cols[g][1]])
            keep.append(rec)
    for (code, name), n in sorted(dropped.items()):
        LOG.info("%s: dropped %d rows code=%s name=%r (name family / min_date, ERRATA1 H3)", kind, n, code, name)
    df = pd.DataFrame(keep)
    dup = df.duplicated(["ccy", "date"], keep=False)
    if dup.any():
        raise ValueError("%s: duplicate (ccy,date) rows: %s" % (kind, df.loc[dup, ["ccy", "date"]].head().values.tolist()))
    out = {}
    for g in groups:
        oi = df["oi"].where(df["oi"] > 0)
        x = (df[g + "_L"] - df[g + "_S"]) / oi
        out[g] = pd.DataFrame(dict(date=df["date"], ccy=df["ccy"], x=x, name=df["name"])).sort_values(
            ["ccy", "date"]).reset_index(drop=True)
    return out, dropped


def load(cutoff=DEFAULT_CUTOFF, holdout=None, data_dir=DATA_DIR, real=True):
    c = check_cutoff(cutoff, holdout)
    der = os.path.join(data_dir, "derived")
    cot, dropped = {}, {}
    leg, dl = read_cot(os.path.join(der, "cot_legacy_fx_cut.csv"), "LEG", c)
    tff, dt_ = read_cot(os.path.join(der, "cot_tff_fx_cut.csv"), "TFF", c)
    cot.update(leg)
    cot.update(tff)
    dropped.update({("LEG",) + k: v for k, v in dl.items()})
    dropped.update({("TFF",) + k: v for k, v in dt_.items()})
    quote, px = {}, {}
    for ccy, s in CCY.items():
        q = read_series(os.path.join(der, "FRED_%s.csv" % s["fred"]), c)
        mind = s.get("min_date")
        if mind:
            q = q[q.index >= pd.Timestamp(mind)]
        quote[ccy] = q
        px[ccy] = pd.Series(to_usd_per_ccy(s["fred"], q.values), index=q.index)
    quote = pd.DataFrame(quote).sort_index()
    px = pd.DataFrame(px).sort_index()
    rates = {}
    for ccy, rid in [("USD", "US")] + [(k, v["rate"]) for k, v in CCY.items()]:
        rates[ccy] = read_series(os.path.join(der, "FRED_IR3TIB01%sM156N.csv" % rid), c)
    rates = pd.DataFrame(rates).sort_index()
    ex = pd.read_csv(os.path.join(data_dir, "cot_release_exceptions.csv"), dtype=str)
    ex = pd.DataFrame(dict(report_date=pd.to_datetime(ex["report_date"]), pub=pd.to_datetime(ex["actual_publish_date"]),
                           event=ex["event"]))
    ex = ex[ex["report_date"] <= c].reset_index(drop=True)
    data = dict(cot=cot, px=px, quote=quote, rates=rates, exceptions=ex, cutoff=c, real=real, dropped=dropped)
    assert_cutoff(data)
    return data


def assert_cutoff(data):
    c = data["cutoff"]
    for g, df in data["cot"].items():
        assert df["date"].max() <= c, g
    for k in ("px", "quote", "rates"):
        assert data[k].index.max() <= c, k
    assert data["exceptions"]["report_date"].max() <= c if len(data["exceptions"]) else True


def inventory(data):
    rows = []
    for g, df in data["cot"].items():
        for ccy, d in df.groupby("ccy"):
            rows.append(dict(group=g, ccy=ccy, first=d["date"].min().date(), last=d["date"].max().date(), n=len(d),
                             n_x=int(d["x"].notna().sum()), names=" | ".join(sorted(d["name"].unique()))))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    ap.add_argument("--holdout", default=None)
    ap.add_argument("--out", default=os.path.expanduser("~/claude_master/w3/fx/g3/out/inventory_g3.csv"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    data = load(a.cutoff, a.holdout)
    inv = inventory(data)
    inv.to_csv(a.out, index=False)
    for r in inv.itertuples():
        LOG.info("%s %s %s..%s n=%d n_x=%d names=%s", r.group, r.ccy, r.first, r.last, r.n, r.n_x, r.names)
    LOG.info("px %s..%s; rates %s..%s; exceptions<=cutoff %d", data["px"].index.min().date(), data["px"].index.max().date(),
             data["rates"].index.min().date(), data["rates"].index.max().date(), len(data["exceptions"]))


if __name__ == "__main__":
    main()
