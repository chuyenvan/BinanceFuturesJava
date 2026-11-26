"""FX G1 loader (PREREG_FX_G1 sec 1-4 + ERRATA1 H2/H6).

Loads FRED H.10 daily FX, OECD monthly 3m interbank rates, VIXCLS from data/derived (read only).
Every price is converted to USD per 1 unit of foreign currency, so a LONG foreign-vs-USD position earns
P_t / P_{t-1} - 1.

Cutoff guard (ERRATA1 H6): rows dated after `cutoff` are skipped while reading (value never parsed);
a cutoff later than 2019-12-31 is refused unless holdout == HOLDOUT_TOKEN.
"""
import argparse
import csv
import logging
import os
from collections import namedtuple

import numpy as np
import pandas as pd

LOG = logging.getLogger("g1.load")

DEFAULT_DATA = os.path.expanduser("~/claude_master/w3/fx/data/derived")
DEFAULT_CUTOFF = "2019-12-31"
HOLDOUT_TOKEN = "I_HAVE_OWNER_OK"

CCYS = ["EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD", "NOK", "SEK"]
USD_PER = "USD_PER"   # FRED value = USD per 1 foreign unit
CCY_PER = "CCY_PER"   # FRED value = foreign units per 1 USD
FX = {"EUR": ("DEXUSEU", USD_PER), "JPY": ("DEXJPUS", CCY_PER), "GBP": ("DEXUSUK", USD_PER),
      "CHF": ("DEXSZUS", CCY_PER), "CAD": ("DEXCAUS", CCY_PER), "AUD": ("DEXUSAL", USD_PER),
      "NZD": ("DEXUSNZ", USD_PER), "NOK": ("DEXNOUS", CCY_PER), "SEK": ("DEXSDUS", CCY_PER)}
RATE = {"USD": "US", "EUR": "EZ", "JPY": "JP", "GBP": "GB", "CHF": "CH", "CAD": "CA", "AUD": "AU",
        "NZD": "NZ", "NOK": "NO", "SEK": "SE"}
# pip size in the FRED/market quote unit (FRED quote direction == market convention for all 9 pairs)
PIP = {"EUR": 1e-4, "GBP": 1e-4, "AUD": 1e-4, "NZD": 1e-4, "JPY": 1e-2, "CHF": 1e-4, "CAD": 1e-4,
       "NOK": 1e-4, "SEK": 1e-4}
EUR_START = pd.Timestamp("1999-01-01")   # EUR only from 1999 (no DEM splice)
MAX_GAP = 3                              # prereg sec 3: > 3 consecutive missing business days

MonthInfo = namedtuple("MonthInfo", "m T rate_month univ r_usd r")


def check_cutoff(cutoff, holdout=None):
    c = pd.Timestamp(cutoff)
    if c > pd.Timestamp(DEFAULT_CUTOFF) and holdout != HOLDOUT_TOKEN:
        raise PermissionError("cutoff %s > %s refused (HOLDOUT, ERRATA1 H6)" % (c.date(), DEFAULT_CUTOFF))
    return c


def to_usd_per(raw, quote):
    """raw FRED quote -> USD per 1 foreign unit."""
    raw = np.asarray(raw, dtype=float)
    if quote == USD_PER:
        return raw
    if quote == CCY_PER:
        return 1.0 / raw
    raise ValueError(quote)


def read_series(path, cutoff):
    """Read a FRED-style 2-column csv (date,v). Rows dated > cutoff are skipped BEFORE parsing the value."""
    cut = pd.Timestamp(cutoff)
    dates, vals, dropped = [], [], 0
    with open(path, newline="") as fh:
        rd = csv.reader(fh)
        next(rd)
        for row in rd:
            if not row:
                continue
            d = pd.Timestamp(row[0])
            if d > cut:
                dropped += 1
                continue
            s = row[1].strip() if len(row) > 1 else ""
            dates.append(d)
            vals.append(np.nan if s in ("", ".") else float(s))
    LOG.info("read %s: %d rows kept, %d rows > cutoff skipped", os.path.basename(path), len(dates), dropped)
    return pd.Series(vals, index=pd.DatetimeIndex(dates), dtype=float)


class G1Data:
    """Container. dates: business-day calendar (union of FRED DEX rows); raw/P: (n, c) arrays, NaN = missing."""

    def __init__(self, dates, ccys, quote, raw, rates, vix, cutoff, pip=None, rt_pips=None):
        self.dates = pd.DatetimeIndex(dates)
        self.ccys = list(ccys)
        self.quote = dict(quote)
        self.raw = np.asarray(raw, dtype=float)
        self.P = np.column_stack([to_usd_per(self.raw[:, j], self.quote[c]) for j, c in enumerate(self.ccys)])
        self.valid = ~np.isnan(self.P)
        self.Pf = pd.DataFrame(self.P).ffill().to_numpy()
        self.rates = rates          # DataFrame, PeriodIndex (M), columns USD + ccys, % per year
        self.vix = np.asarray(vix, dtype=float)
        self.cutoff = pd.Timestamp(cutoff)
        self.pip = dict(PIP if pip is None else pip)
        self.rt_pips = rt_pips if rt_pips is not None else {c: (0.8 if c == "EUR" else 3.0) for c in self.ccys}
        self.month = self.dates.to_period("M")
        self._cache = {}
        self.is_real = False        # set True by load(); simulate/evaluate then need the A1 token (ERRATA3 NHO-7)
        assert self.dates.is_monotonic_increasing and self.dates.is_unique
        assert self.dates.max() <= self.cutoff, "row after cutoff"
        if len(self.rates):
            assert self.rates.index.max().to_timestamp() <= self.cutoff, "rate after cutoff"

    def months(self):
        if "months" not in self._cache:
            self._cache["months"] = monthly_universe(self)
        return self._cache["months"]


def load(data_dir=DEFAULT_DATA, cutoff=DEFAULT_CUTOFF, holdout=None):
    cut = check_cutoff(cutoff, holdout)
    px = {c: read_series(os.path.join(data_dir, "FRED_%s.csv" % FX[c][0]), cut) for c in CCYS}
    cal = sorted(set().union(*[set(s.index) for s in px.values()]))
    cal = pd.DatetimeIndex(cal)
    raw = np.column_stack([px[c].reindex(cal).to_numpy() for c in CCYS])
    raw[cal < EUR_START, CCYS.index("EUR")] = np.nan
    rates = {}
    for c, code in RATE.items():
        s = read_series(os.path.join(data_dir, "FRED_IR3TIB01%sM156N.csv" % code), cut)
        s.index = s.index.to_period("M")
        rates[c] = s
    rates = pd.DataFrame(rates)[["USD"] + CCYS].sort_index()
    vix = read_series(os.path.join(data_dir, "FRED_VIXCLS.csv"), cut).reindex(cal).to_numpy()
    d = G1Data(cal, CCYS, {c: FX[c][1] for c in CCYS}, raw, rates, vix, cut)
    d.is_real = True
    LOG.info("loaded %d rows %s..%s, cutoff %s", len(cal), cal[0].date(), cal[-1].date(), cut.date())
    return d


def max_missing_run(valid_bool):
    best = cur = 0
    for v in valid_bool:
        cur = 0 if v else cur + 1
        best = max(best, cur)
    return best


def monthly_universe(data):
    """For every calendar month m in data: rebalance row T = last row of m with >= 1 valid price;
    universe = ccys with rate(m-1) and USD rate(m-1) present, >= 1 valid price in m (rows <= T) and no run of
    > 3 consecutive missing rows in m (rows <= T). Uses only information dated <= T and rates of month m-1."""
    out = []
    any_valid = data.valid.any(axis=1)
    per = data.month
    for m in pd.period_range(per[0], per[-1], freq="M"):
        rows = np.flatnonzero(per == m)
        rows_v = rows[any_valid[rows]]
        if len(rows_v) == 0:
            out.append(MonthInfo(m, None, m - 1, [], np.nan, {}))
            continue
        T = int(rows_v[-1])
        rows = rows[rows <= T]
        rm = m - 1
        r_usd = data.rates["USD"].get(rm, np.nan) if len(data.rates) else np.nan
        univ, r = [], {}
        for j, c in enumerate(data.ccys):
            rc = data.rates[c].get(rm, np.nan) if c in data.rates else np.nan
            v = data.valid[rows, j]
            if np.isnan(r_usd) or np.isnan(rc) or not v.any() or max_missing_run(v) > MAX_GAP:
                continue
            univ.append(c)
            r[c] = float(rc)
        if np.isnan(r_usd):
            LOG.debug("month %s: USD rate(m-1) missing -> empty universe", m)
        out.append(MonthInfo(m, T, rm, univ, float(r_usd), r))
    return out


def ecb_flag_dates(data, data_dir=DEFAULT_DATA, thr=0.015):
    """ERRATA1 H1: dates where |log FRED - log ECB| > 1.5% for any ccy (USD per ccy). Cutoff-guarded."""
    cut = data.cutoff
    path = os.path.join(data_dir, "ECB_eurofxref_cut.csv")
    rows = []
    with open(path, newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        for row in rd:
            if not row or pd.Timestamp(row[0]) > cut:
                continue
            rows.append(row)
    e = pd.DataFrame(rows, columns=hdr)
    e.index = pd.DatetimeIndex(pd.to_datetime(e.pop("Date")))
    e = e.apply(pd.to_numeric, errors="coerce")
    usd = e["USD"]
    flags = pd.Series(False, index=data.dates)
    for j, c in enumerate(data.ccys):
        ecb = usd if c == "EUR" else usd / e[c]
        fred = pd.Series(data.P[:, j], index=data.dates)
        both = pd.concat([fred, ecb.reindex(data.dates)], axis=1).dropna()
        bad = (np.log(both.iloc[:, 0]) - np.log(both.iloc[:, 1])).abs() > thr
        flags.loc[bad[bad].index] = True
    return flags


def main():
    ap = argparse.ArgumentParser(description="G1 loader summary (no returns computed)")
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    ap.add_argument("--holdout", default=None)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    d = load(a.data, a.cutoff, a.holdout)
    ms = [mi for mi in d.months() if mi.m >= pd.Period("1994-01", "M")]
    by_year = {}
    for mi in ms:
        by_year.setdefault(mi.m.year, []).append(len(mi.univ))
    for y, v in sorted(by_year.items()):
        LOG.info("universe %d: min %d max %d", y, min(v), max(v))


if __name__ == "__main__":
    main()
